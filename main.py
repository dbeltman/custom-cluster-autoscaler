import logging
import os
import time, datetime
import sys
import signal
import asyncio
import threading
from concurrent.futures import ProcessPoolExecutor
from src.classes import all_reasons, PendingPodReason, NodeCapabilities, AutoScaleNode, PendingPod
from src.kubernetes import watch_pending_pods
from src.downscaler import check_downscale_possibility
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

def periodic_tasks():
    while True:
        check_downscale_possibility()
        time.sleep(60)

def main():
    """
    Auto-scales nodes based on pending pods in Kubernetes cluster.
    If there are pending pods, it checks for available nodes in the inventory that meet the required conditions.
    If a node is not present, it turns on the node using the specified BMC method (esphome by default).
    """
    signal.signal(signal.SIGTERM, signal_handler)
    t1 = threading.Thread(target=watch_pending_pods)
    t1.daemon = True
    t1.start()    
    periodic_tasks()

if __name__ == "__main__":
    main()