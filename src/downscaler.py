import logging
from kubernetes import client, config, watch
from src.event_parser import handle_event
from src.classes import PendingPod
from src.inventory_handler import get_capabilities_by_node, get_nodes_by_requirement, get_node_inventory
from src.bmc_handler import power_on_node
from src.kubernetes import get_pods_on_node, check_node_presence_in_cluster, create_downscale_job, create_downscale_drain_job_object, get_job_status, create_downscale_shutdown_job_object, wait_for_node_to_become_notready, delete_node_from_cluster, delete_downscale_jobs

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
    pending_upscale=check_for_pending_upscale(nodename=nodename)
    if pending_upscale:
        logger.warning(f"Node {nodename} has pending upscale by pods")
        return False
    drain_job_object=create_downscale_drain_job_object(nodename=nodename)
    create_downscale_job(job=drain_job_object)    
    drain_status=get_job_status(job_name=drain_job_object.metadata.name)
    if drain_status:
        logger.info(f"Draining node was succesful, shutting down {nodename}")
        shutdown_job_object=create_downscale_shutdown_job_object(nodename=nodename)
        create_downscale_job(job=shutdown_job_object)
        node_status=wait_for_node_to_become_notready(nodename=nodename)
        if node_status==True:
            logger.info("Deleting node from the cluster")
            delete_node_from_cluster(nodename=nodename)
            delete_downscale_jobs(nodename=nodename)
        else:
            logger.error(f"Downscale failed, node {nodename} was not deemed NotReady")

def check_downscale_possibility():
    try:
        inventory=get_node_inventory()
        for node in inventory:
            nodename=node["nodeName"]
            logger.info(f"Checking node {nodename} for downscaling possibility")
            result = check_node_for_scaledown_eligibility(nodename=nodename)
            if result == True:
                logger.info(f"Node {nodename} IS eligible for downscale")
                handle_downscale(nodename=nodename)
            else:
                logger.info(f"Node {nodename} NOT eligible for downscale")
            
        
    except Exception as e:
        logger.error(f"{e}")