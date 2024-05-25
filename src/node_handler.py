import yaml, os
from src.esphome_handler import power_on_esphome_system
import asyncio

if os.getenv("PRODUCTION") == "True":
    node_inventory_file = "/config/node_inventory.yaml"

else:
    node_inventory_file = "example/config/inventory.yaml"
with open(node_inventory_file, "r") as f:
    nodes = yaml.safe_load(f)


def find_node_by_capability(capability):

    result = []
    for node in nodes:
        if capability in node["capabilities"]:
            result.append(node)
    return result


def get_bmc_method(node_name, node_info_list):
    for node in node_info_list:
        if node["nodeName"] == node_name:
            return node["bmcMethod"]
    return None  # or raise an exception


def handle_node_request(nodename):
    bmc_method = get_bmc_method(nodename, nodes)
    if bmc_method is not None:
        if bmc_method == "esphome":
            asyncio.run(power_on_esphome_system(nodename))
            print("turning on bmc")
