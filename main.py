import logging
import os
import time, datetime
import sys
import signal
import asyncio
from src.classes import all_reasons, PendingPodReason, NodeCapabilities, AutoScaleNode, PendingPod
from src.kubernetes_handler import check_node_presence_in_cluster, label_pod_with_custom_autoscaler_trigger, get_pods_on_node
from src.inventory_handler import get_nodes_by_requirement, get_requirements_by_node
from src.bmc_handler import power_on_esphome_system
from src.event_parser import handle_event
from kubernetes import client, config, watch
# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)


if os.getenv("PRODUCTION") == "True":
    logger.info("Running in PRODUCTION mode!")
else:
    import debugpy

    logger.warning("Running in DEVELOPMENT mode!")
    debugpy.listen(5679)

def signal_handler(signum, frame):
    """
    This function handles the SIGTERM signal to gracefully shutdown the application and logs a message indicating that it is stopping.

    Args:
        signum (int): Signal number, which is 15 for SIGTERM.
        frame (FrameType): Frame object containing information about the current call stack.
    """
    logger.info('Caught SIGTERM signal. Stopping...')
    sys.exit(0)
    
def main():
    """
    Auto-scales nodes based on pending pods in Kubernetes cluster.
    If there are pending pods, it checks for available nodes in the inventory that meet the required conditions.
    If a node is not present, it turns on the node using the specified BMC method (esphome by default).
    """
    signal.signal(signal.SIGTERM, signal_handler)
    handle_pending_pods()

def setup_kubernetes_client():
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

def handle_pending_pods():
    start_time = datetime.datetime.now(datetime.timezone.utc)
    configuration = setup_kubernetes_client()
    v1 = client.CoreV1Api(client.ApiClient(configuration))
    w = watch.Watch()
    for event in w.stream(v1.list_event_for_all_namespaces,):
        if event["object"].reason == "FailedScheduling" and event["object"].message.startswith("skip schedule deleting pod") == False and event["type"] == "ADDED":
            event_time=event["object"].event_time
            if (start_time - event_time).total_seconds() > 2:
                print("Event is from the past, ignoring")
                continue
            print ("Event has failedscheduling reason:")
            # print("Event: %s %s %s" % (event['object'].reason, event['object'].message, event['object'].involved_object.name))
            try:
                pendingpodreason = handle_event(event["object"].message)
                obj=event['object'].involved_object
                pod = v1.read_namespaced_pod(name=obj.name, namespace=obj.namespace)
                if "cluster-autoscaler-triggered" in pod.metadata.labels:
                    logger.info(f"Found already handled pod: {pod.metadata.name} in namespace {pod.metadata.namespace}")
                    continue                    
                logger.info(
                    pendingpodreason.message
                    + " | "
                    + pendingpodreason.name
                    + ": "
                    + obj.name
                )
                pending_pod = PendingPod(pendingpodreason, obj.name, obj.namespace)
                if pendingpodreason.name != "Unknown":
                    matching_nodes=get_nodes_by_requirement(pending_pod.reason.requirement)
                    if len(matching_nodes) > 0:
                        for node in matching_nodes:  # Loop through each node by requirement
                            node_status = check_node_presence_in_cluster(node.node_name)   # Check node presence
                            if node_status == True:
                                    logger.info(f"{node.node_name} is present, skipping auto-scaling and trying to find another node.")  # Skip this node if present
                                    continue
                            else:
                                    logger.info(f"{node.node_name} is not present, turning on the node.")
                                    # Check BMC method and perform action for esphome
                                    if node.bmc_method == "esphome":
                                        logger.info(f"Turning on the {node.node_name} using esphome system.")
                                        if asyncio.run(power_on_esphome_system(node.node_name)) != False:
                                            label_pod_with_custom_autoscaler_trigger(pending_pod.podname, pending_pod.podnamespace)
                                    else:
                                        logger.warning(f"No mechanism for BMC method '{node.bmc_method}' yet!")
                                        label_pod_with_custom_autoscaler_trigger(pending_pod.podname, pending_pod.podnamespace)

                                    break  # If the node is not present, proceed with auto-scaling and break the loop
                    else:
                        logger.error(f"No matching nodes found for {pending_pod.reason.requirement}")
            except TypeError as e:
                print(f'ERROR: {e}')
if __name__ == "__main__":
    while True:
        main()
