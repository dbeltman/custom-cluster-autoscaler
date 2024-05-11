from src.classes import all_reasons
import re
import logging

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)


def handle_events(stream):
    compatible_pods=[]
    for event in stream:
        msg = event["object"].message
        for reason in all_reasons:
            if re.search(reason.regex, msg):
                compatible_pods.append(reason)
                logger.info(reason.message)
                logger.debug(msg)
                return compatible_pods

