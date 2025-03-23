import logging
from kubernetes import client, config, watch
from src.event_parser import handle_event
from src.classes import PendingPod
from src.inventory_handler import get_capabilities_by_node, get_nodes_by_requirement, get_node_inventory
from src.bmc_handler import power_on_node
from src.kubernetes import get_pods_on_node, check_node_presence_in_cluster

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

def check_pod_requirements_for_node_capabilities(pod, node_capabilities, nodename):
    for node_capability in node_capabilities:
        if node_capability == "gpu":
            for container in pod.spec.containers:
                if container.resources.requests != None:
                    if "nvidia.com/gpu" in container.resources.requests: #Check if pod needs the gpu node_capability of this node
                        logger.info(f"Pod '{pod.metadata.name}' requires resource '{node_capability}' that node '{nodename}' offers")  
                        return True 
                
        elif node_capability == "nodespecificresources":
            if pod.spec.node_selector == f"kubernetes.io/hostname: {nodename}": #Check if pod has a nodeselector pointing to this node
                logger.info(f"Pod {pod.metadata.name} requires resource {node_capability} that this node ({nodename}) offers")
                return True
        else: 
            logger.error("Node has unknown capability? Fix your code, developer!")
            return True
        

def check_node_for_scaledown_eligibility(nodename):
    """
    This functions checks wether the node is still necessary according to the pods on the node, combined with the capabilities the node offers. 
    Assuming nodes in inventory are always "extra", they can be shutdown/removed when there are no pods running that require it's resources.
    This will create a problem with CPU/Memory scaling in the future, since that is a resource any pod will require. #Todo; Fix this
    """
    if check_node_presence_in_cluster(node_name=nodename) == False:
        logger.info(f"{nodename} is not in the cluster, so we cannot downscale it")
        # Get the pods list for the specified node
        return False
    node_pods = get_pods_on_node(node_name=nodename) #Get all pods on node
    node_capabilities = get_capabilities_by_node(node_name=nodename) #Get capabilities node offers
    if len(node_pods.items) <= 0:
        logger.info(f"No pods to process for {nodename} downscaling-process")
        return False
    else:
        for pod in node_pods.items:
            node_required_by_pod = check_pod_requirements_for_node_capabilities(pod=pod, node_capabilities=node_capabilities, nodename=nodename)
            if node_required_by_pod:
                break
            
        else:
            return True

def handle_downscale(nodename):
    pass

def check_downscale_possibility():
    try:
        inventory=get_node_inventory()
        for node in inventory:
            nodename=node["nodeName"]
            logger.info(f"Checking node {nodename} for downscaling possibility")
            result = check_node_for_scaledown_eligibility(nodename=nodename)
            if result == True:
                logger.info(f"Node {nodename} IS eligible for downscale")
            else:
                logger.info(f"Node {nodename} NOT eligible for downscale")
            
        
    except Exception as e:
        logger.error(f"{e}")