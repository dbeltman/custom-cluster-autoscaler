import asyncio
from aioesphomeapi import APIClient
from aioesphomeapi.model import SwitchInfo
import re, os


async def power_on_esphome_system(nodename):
    api = APIClient(
        address=os.getenv("bmc_hostname"),
        port=os.getenv("bmc_port", 6053),
        password=os.getenv("bmc_password"),
        noise_psk=os.getenv("bmc_encryptionkey"),
    )
    await api.connect(login=True)
    entities = await api.list_entities_services()

    # def power_on_system(nodename):

    for entity in entities[0]:  # TODO investigate robustness
        if type(entity) is SwitchInfo:
            if re.search(".*_power$", entity.object_id):
                # state = api.
                print("Power switch found! Turning on switch")
                command = api.switch_command(key=entity.key, state=True)


# asyncio.run(main())
