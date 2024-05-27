import logging
import os
import time
from src.classes import all_reasons, PendingPodReason, NodeCapabilities, AutoScaleNode
from kubernetes_handler import get_pending_pods, check_node_presence
from inventory_handler import get_nodes_by_requirement
from bmc_handler import power_on_esphome_system
# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)
# Set up kubernetes
if os.getenv("PRODUCTION") == "True":
    logger.info("Running in PRODUCTION mode!")
else:
    import debugpy

    logger.warning("Running in DEVELOPMENT mode!")
    debugpy.listen(5679)


def main():
    pending_pods = get_pending_pods()
    if len(pending_pods) > 0:
        for pending_pod in pending_pods:
            # print(pending_pod.reason.requirement, "needed!")
            print(get_nodes_by_requirement(pending_pod.reason.requirement))
            # Note: Hardcoding the first-in-list option is not desired. A better approach would be to handle all found nodes.
            node = get_nodes_by_requirement(pending_pod.reason.requirement)[0]  # [0] indexing is used here, which may lead to issues if there are multiple suitable nodes
            node_status = check_node_presence(node.node_name)  # Add the "check_node_presence" function from kubernetes_handler.py to check for node presence
            if node_status == True:
                power_on_esphome_system(node.node_name)
                break
            else:
                logger.warning(f"{node.node_name} is not present. Auto-scaling skipped for this node.")
    else:
        logger.info("No pending pods as of now")


if __name__ == "__main__":
    while True:
        main()
        time.sleep(5)
