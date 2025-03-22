import logging
from kubernetes import client, config, watch
from src.event_parser import handle_event
from src.classes import PendingPod
from src.inventory_handler import get_capabilities_by_node, get_nodes_by_requirement
from src.bmc_handler import power_on_node
import os
import time
import asyncio
import datetime 

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)


def main():

    # Set up kubernetes
    if os.getenv("PRODUCTION") == "True":
        tokenpath = "/var/run/secrets/kubernetes.io/serviceaccount/token"
        capath = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"
        apiserverhost = "https://10.43.0.1"

    else:
        # print("DEVELOPMODE is ON!")
        tokenpath = "dev/secrets/token"
        capath = "dev/secrets/ca.crt"
        apiserverhost = "https://192.168.230.17:6443"

    token = open(tokenpath)
    token_text = token.read()
    configuration = client.Configuration()
    configuration.api_key["authorization"] = token_text
    configuration.api_key_prefix["authorization"] = "Bearer"
    configuration.host = apiserverhost
    configuration.ssl_ca_cert = capath
    return configuration

# Function to check if a node is present in the cluster
def check_node_presence_in_cluster(node_name):
    logger.info("Checking node presence in cluster")
    configuration = main()
    # Create a Kubernetes client with the configured configuration
    v1 = client.CoreV1Api(client.ApiClient(configuration))
    
    # Get the nodes list from the API
    nodes_list = v1.list_node(watch=False)

    # Iterate through the nodes and filter for the given node name
    for node in nodes_list.items:
        if node.metadata.name == node_name:
            logger.debug("Node " + node_name + " is present")
            return True  # Node is present
    logger.debug("Node " + node_name + " NOT present")
    return False  # Node is not found

# Function to get all pods on a certain node
def get_pods_on_node(node_name):
    logger.info(f"Getting all pods on node {node_name}")
    configuration = main()
    v1 = client.CoreV1Api(client.ApiClient(configuration))

    # Get the pods list for the specified node
    pods_list = v1.list_pod_for_all_namespaces(field_selector=f"spec.nodeName={node_name}", watch=False)

 

    return pods_list


def label_pod_with_custom_autoscaler_trigger(pod_name, namespace):
    # Set up the Kubernetes client
    configuration = main()
    v1 = client.CoreV1Api(client.ApiClient(configuration))

    # Get the pod object
    pod = v1.read_namespaced_pod(name=pod_name, namespace=namespace)
    pod.metadata.labels["cluster-autoscaler-triggered"] = "true"    
    # Label the pod
    for attempt in range(0,3):
        try:
            time.sleep(1)
            v1.patch_namespaced_pod(pod_name, namespace=namespace, body=pod)
        except client.exceptions.ApiException as e:
            logger.info(f"Got API Exception {e.status}, sleeping 3 seconds, retry #{attempt}")
            logger.debug(f"{e}")
            time.sleep(3)
            
    logger.info("Labeled pod {} in namespace {} to be marked as handled".format(pod_name, namespace))

async def check_node_for_scaledown(nodename):
    """
    This functions checks wether the node is still necessary according to the pods on the node, combined with the capabilities the node offers. 
    Assuming nodes in inventory are always "extra", they can be shutdown/removed when there are no pods running that require it's resources.
    This will create a problem with CPU/Memory scaling in the future, since that is a resource any pod will require. #Todo; Fix this
    """
    nodepods=get_pods_on_node(node_name=nodename) #Get all pods on node
    nodecapabilities=get_capabilities_by_node(node_name=nodename) #Get capabilities node offers
    for pod in nodepods:
        for capability in nodecapabilities:
            if capability == "gpu":
                if pod.spec.requirements.gpu > 0: #Check if pod needs the gpu capability of this node
                    logger.debug("Pod requires a resource this node offers")
            if capability == "nodespecificresources":
                if pod.spec.nodeselector == f"kubernetes.io/hostname: {nodename}": #Check if pod has a nodeselector pointing to this node
                    logger.debug("Pod requires a resource this node offers")
            else: 
                logger.error("unknown capability? Fix your code, developer!")

def check_pending_pod_eligibility(pod):
    if "cluster-autoscaler-triggered" in pod.metadata.labels:
        logger.info(f"Found already handled pod: {pod.metadata.name} in namespace {pod.metadata.namespace}")
        return False    
    elif pod.metadata.owner_references[0].kind == "DaemonSet":
        logger.info(f"Ignoring pod {pod.metadata.name} because it's part of a daemonset")
        return False
    else:
        return True

def match_pod_to_node(matching_nodes, pendingpodreason, pod, pending_pod):
    logger.info(f"Checking for nodes that fit the required resource: {pendingpodreason.requirement}")
    for node in matching_nodes:  # Loop through each node by requirement
        node_presence=check_node_presence_in_cluster(node.node_name)
        if node_presence == True:
            logger.info(f"Node {node.node_name} is already present in the cluster. Cannot autoscale.")
            label_pod_with_custom_autoscaler_trigger(pending_pod.podname, pending_pod.podnamespace)
            return False
        if (
            pendingpodreason.requirement == 'nodespecificresources' 
            and node.node_name == pod.spec.node_selector['kubernetes.io/hostname']
            ):
            # Check whether the pendingpodreason requirement is nodespecific resources 
            # and check whether it requests this specific node
            logger.info(f"{node.node_name} matches pod requirement and requests this specific node. Turning on the node.")
            power_on_result=power_on_node(node=node)
            if power_on_result == True:
                logger.debug("Power on seems to be succesful, breaking loop as we expect node will be up soon")
                label_pod_with_custom_autoscaler_trigger(pending_pod.podname, pending_pod.podnamespace)
                break 
            else:
                logger.warning("Something went wrong powering on the node!")
                label_pod_with_custom_autoscaler_trigger(pending_pod.podname, pending_pod.podnamespace)
        elif (pendingpodreason.requirement == 'gpu'):
            # Check whether the pendingpodreason requirement is a gpu resource
            # and whether it isn't already in the cluster
            logger.info(f"{node.node_name} matches pod requirement and is not present in the cluster. Turning on the node.")
            power_on_result=power_on_node(node=node)
            if power_on_result == True:
                logger.debug("Power on seems to be succesful, breaking loop as we expect node will be up soon")
                label_pod_with_custom_autoscaler_trigger(pending_pod.podname, pending_pod.podnamespace)
                break 
            else:
                logger.warning("Something went wrong powering on the node!")
                label_pod_with_custom_autoscaler_trigger(pending_pod.podname, pending_pod.podnamespace)
        else:
            logger.info(f"Could not match {node.node_name} to {pending_pod.podname} with requirement {pendingpodreason.requirement}")
            matching_nodes.remove(node)
            if len(matching_nodes) > 0:
                #If this is not the last available node in inventory, move on to the next item
                logger.info("Trying next available node")
                continue
            else:
                #If this is the last item, we cant do anything now but label the pod as handled and prevent further action for this pod. 
                #We assume pods will get descheduled after a long enough failurestate (high restart count, pending)
                logger.warning("No more matching nodes left that match this pending requirement")
                label_pod_with_custom_autoscaler_trigger(pending_pod.podname, pending_pod.podnamespace)
                break

def handle_pending_pod(event):
    configuration = main()
    v1 = client.CoreV1Api(client.ApiClient(configuration))  
    pendingpodreason = handle_event(event["object"].message)
    obj=event['object'].involved_object
    pod = v1.read_namespaced_pod(name=obj.name, namespace=obj.namespace)
    pending_pod = PendingPod(pendingpodreason, obj.name, obj.namespace)
    matching_nodes=get_nodes_by_requirement(pending_pod.reason.requirement)
    if (
        pendingpodreason.name != "Unknown" 
        and len(matching_nodes) > 0
        and check_pending_pod_eligibility(pod) == True
        ):
        logger.info(f"Found eligible pod for autoscaling: {pending_pod.podname}")
        if match_pod_to_node(matching_nodes=matching_nodes, pendingpodreason=pendingpodreason, pod=pod, pending_pod=pending_pod):
            logger.info("Succesfully matched pod to node")
            return True
        else:
            return False
    else:
        return False
async def watch_pending_pods():
    configuration = main()
    v1 = client.CoreV1Api(client.ApiClient(configuration))      
    start_time = datetime.datetime.now(datetime.timezone.utc)
    w = watch.Watch()
    for event in w.stream(v1.list_event_for_all_namespaces):
        if event["object"].reason == "FailedScheduling" and event["object"].message.startswith("skip schedule deleting pod") == False and event["type"] == "ADDED":
            event_time=event["object"].event_time
            if (start_time - event_time).total_seconds() > 2:
                logger.debug("Event is from the past, ignoring")
                continue
            # print("Event: %s %s %s" % (event['object'].reason, event['object'].message, event['object'].involved_object.name))
            try:
                handle_pending_pod(event=event)
            except TypeError as e:
                print(f'ERROR: {e}')

              