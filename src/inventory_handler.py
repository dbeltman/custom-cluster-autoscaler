import yaml, os

class Node:
    def __init__(self, node_name, bmc_method):
        self.node_name = node_name
        self.bmc_method = bmc_method


def get_node_inventory():
    if os.getenv("PRODUCTION") == "True":
        node_inventory_file = "/config/inventory/inventory.yaml"

    else:
        node_inventory_file = "dev/config/inventory.yaml"
    with open(node_inventory_file, "r") as f:
        available_nodes = yaml.safe_load(f)
    return available_nodes

def get_nodes_by_requirement(requirement):
    available_nodes = get_node_inventory()
    compatible_nodes = []
    for node in available_nodes:
        if requirement in node["capabilities"]:
            node_object = Node(node["nodeName"],node["bmcMethod"])
            compatible_nodes.append(node_object)
    return compatible_nodes
