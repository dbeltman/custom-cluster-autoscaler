import logging
import os
import time
import sys
import signal
import asyncio
from src.classes import all_reasons, PendingPodReason, NodeCapabilities, AutoScaleNode
from src.kubernetes_handler import get_pending_pods, check_node_presence, label_pod_with_custom_autoscaler_trigger
from src.inventory_handler import get_nodes_by_requirement
from src.bmc_handler import power_on_esphome_system

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
    pending_pods = get_pending_pods()

    if len(pending_pods) > 0:
        for pending_pod in pending_pods:
            for node in get_nodes_by_requirement(pending_pod.reason.requirement):  # Loop through each node by requirement
                node_status = check_node_presence(node.node_name)   # Check node presence
                if node_status == True:
                        logger.info(f"{node.node_name} is present, skipping auto-scaling.")  # Skip this node if present
                        continue
                else:
                        logger.info(f"{node.node_name} is not present, turning on the node.")
                        # Check BMC method and perform action for esphome
                        if node.bmc_method == "esphome":
                            logger.info(f"Turning on the {node.node_name} using esphome system.")
                            asyncio.run(power_on_esphome_system(node.node_name))
                            label_pod_with_custom_autoscaler_trigger(pending_pod.podname, pending_pod.podnamespace)
                        else:
                            logger.warning(f"No mechanism for BMC method '{node.bmc_method}' yet!")
                        
                        break  # If the node is not present, proceed with auto-scaling and break the loop
    else:
        logger.info("No pending or unhandled pods as of now")
if __name__ == "__main__":
    while True:
        main()
        time.sleep(30)
