import logging
from aioesphomeapi import APIClient
from aioesphomeapi.model import SwitchInfo
import re, os
from src.mqtt_handler import publish as mqtt_publish
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)


def power_on_mqtt_system(nodename):
    mqtt_publish(payload=os.getenv(f"{nodename}_mqtt_poweron_payload","poweron"), topic=os.getenv(f"{nodename}_mqtt_poweron_topic"))
    return True


async def power_on_esphome_system(nodename):
    # Function to power on the esphome system for a given node name
    #
    # This function connects to ESPHome API, logs in with provided credentials, and searches for a switch entity that ends with "_power". If found, it turns the switch on.
    #
    # Args:
    #     nodename (str): The name of the node whose power switch should be turned on.    
    # Set up connection to ESPHome API client
    address=os.getenv(f"{nodename}_bmc_hostname")
    if not address:
        logger.error(f"A hostname for {nodename} was not found in an ENV variable")
        return False
    api = APIClient(
        address=os.getenv(f"{nodename}_bmc_hostname"),
        port=os.getenv(f"{nodename}_bmc_port", 6053),
        password=os.getenv(f"{nodename}_bmc_password"),
        noise_psk=os.getenv(f"{nodename}_bmc_encryptionkey"),
    )
    # Connect to the API and log in
    await api.connect(login=True)
    # Get a list of entities and services from the API
    entities = await api.list_entities_services()

    # Loop through each entity
    for entity in entities[0]:  # TODO investigate robustness
        # Check if it's a switch and its name ends with "_power"
        if type(entity) is SwitchInfo:
            if re.search(".*_power$", entity.object_id):
                logger.info(f"Power switch found for node {nodename}! Turning on switch")
                # Create a command to turn the switch on
                command = api.switch_command(key=entity.key, state=True)
                return True


