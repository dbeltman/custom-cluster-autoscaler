import logging
from kubernetes import client, config, watch
from src.event_parser import handle_event
from src.classes import PendingPod
import os

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
        apiserverhost = "https://192.168.230.15:6443"

    token = open(tokenpath)
    token_text = token.read()
    configuration = client.Configuration()
    configuration.api_key["authorization"] = token_text
    configuration.api_key_prefix["authorization"] = "Bearer"
    configuration.host = apiserverhost
    configuration.ssl_ca_cert = capath
    return configuration

# Function to check if a node is present in the cluster
def check_node_presence(node_name):
    configuration = main()
    # Create a Kubernetes client with the configured configuration
    v1 = client.CoreV1Api(configuration)
    
    # Get the nodes list from the API
    nodes_list = v1.list_node()

    # Iterate through the nodes and filter for the given node name
    for node in nodes_list.items:
        if node.metadata.labels.get("name") == node_name:
            return True  # Node is present
    return False  # Node is not found

def get_pending_pods():
    configuration = main()
    v1 = client.CoreV1Api(client.ApiClient(configuration))
    ret = v1.list_pod_for_all_namespaces(watch=False)  # Get all pods
    matches = 0
    pending_pods = []
    for i in ret.items:
        if i.status.phase == "Pending":  # Check if pending
            logger.info(
                "%s\t%s\t%s" % (i.metadata.namespace, i.metadata.name, i.status.phase)
            )
            fs = "involvedObject.name=" + i.metadata.name
            stream = watch.Watch().stream(
                v1.list_namespaced_event,
                i.metadata.namespace,
                field_selector=fs,
                timeout_seconds=1,
            )  # Get all events for pod
            latest_event = None
            for event in stream:  # Check if pending reasons match our reason_inventory
                # Update the latest event variable
                if (
                    latest_event is None
                    or event["object"].metadata.creation_timestamp
                    > latest_event["object"].metadata.creation_timestamp
                ):
                    latest_event = event
            pendingpodreason = handle_event(latest_event["object"].message)
            logger.info(
                pendingpodreason.message
                + " | "
                + pendingpodreason.name
                + ": "
                + i.metadata.name
            )
            pending_pod = PendingPod(pendingpodreason, i.metadata.name)
            if pendingpodreason.name != "Unknown":
                pending_pods.append(pending_pod)
    return pending_pods
