import logging
import os
import time
from src.classes import all_reasons, PendingPodReason, NodeCapabilities, AutoScaleNode
from src.kubernetes_handler import handle_pending_pods
from src.node_handler import find_node_by_capability

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
    pending_pods = handle_pending_pods()
    for pending_pod in pending_pods:
        # print(pending_pod.reason.requirement, "needed!")
        print(find_node_by_capability(pending_pod.reason.requirement))


if __name__ == "__main__":
    while True:
        main()
        time.sleep(5)
