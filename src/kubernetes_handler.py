import logging
from kubernetes import client, config, watch
from src.event_parser import handle_events

import os

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)


def main():

    # Set up kubernetes
    if os.getenv("PRODUCTION") == "True":
        tokenpath = "/var/run/secrets/kubernetes.io/serviceaccount/token"
        capath = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"
        apiserverhost = "https://10.43.0.1"

    else:
        print("DEVELOPMODE is ON!")
        tokenpath = "dev/secrets/token"
        capath = "dev/secrets/ca.crt"
        apiserverhost = "https://192.168.230.15:6443"

    token = open(tokenpath)
    token_text = token.read()
    configuration = client.Configuration()
    configuration.api_key["authorization"] = token_text
    configuration.api_key_prefix["authorization"] = "Bearer"
    configuration.host = apiserverhost
    configuration.ssl_ca_cert = capath
    return configuration


def handle_pending_pods():
    configuration = main()
    v1 = client.CoreV1Api(client.ApiClient(configuration))
    ret = v1.list_pod_for_all_namespaces(watch=False)
    matches = 0
    for i in ret.items:
        if i.status.phase == "Pending":
            logger.info(
                "%s\t%s\t%s" % (i.metadata.namespace, i.metadata.name, i.status.phase)
            )
            fs = "involvedObject.name=" + i.metadata.name
            stream = watch.Watch().stream(
                v1.list_namespaced_event,
                i.metadata.namespace,
                field_selector=fs,
                timeout_seconds=1,
            )
            result=handle_events(stream)
            if len(result) > 0:
                logger.info("Found pods that match a known reason!")
            else: 
                logger.warn("No pods found!")
            # logger.info(result)
    
