import logging
from aioesphomeapi import APIClient
from aioesphomeapi.model import SwitchInfo
import re, os

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)

# Function to power on the esphome system
async def power_on_esphome_system(nodename):
    # Set up connection to ESPHome API client
    api = APIClient(
        address=os.getenv("bmc_hostname"),
        port=os.getenv("bmc_port", 6053),
        password=os.getenv("bmc_password"),
        noise_psk=os.getenv("bmc_encryptionkey"),
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
                logger.info("Power switch found for node" + nodename + "! Turning on switch")
                # Create a command to turn the switch on
                command = api.switch_command(key=entity.key, state=True)
