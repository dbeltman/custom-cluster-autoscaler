from src.classes import all_reasons, PendingPodReason
import re
import logging

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)


def handle_event(msg):
    # compatible_pods = []
    for reason in all_reasons:
        try:
            if re.search(
                reason.regex, msg
            ):  # Match the k8s event message with a regex defined in the reasons.yaml
                logger.debug(msg)
                return reason
        except TypeError as e:
            print(f'[ERROR] TypeError: {e}')
    return PendingPodReason(
                name="Unknown",
                message="No reason has been defined for this pod's pending status!",
                regex="Unknown Regex",
                requirement="unknown",
            )