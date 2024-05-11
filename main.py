import logging
from kubernetes import client, config, watch
import os
import re
import time


if os.getenv("PRODUCTION") == "True":
    tokenpath = "/var/run/secrets/kubernetes.io/serviceaccount/token"
    capath = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"
    apiserverhost = "https://10.43.0.1"

else:
    import debugpy

    print("DEVELOPMODE is ON!")
    debugpy.listen(5678)
    tokenpath = "dev-secrets/token"
    capath = "dev-secrets/ca.crt"
    apiserverhost = "https://192.168.230.15:6443"

token = open(tokenpath)
token_text = token.read()


def main():
    configuration = client.Configuration()
    configuration.api_key["authorization"] = token_text
    configuration.api_key_prefix["authorization"] = "Bearer"
    configuration.host = apiserverhost
    configuration.ssl_ca_cert = capath

    # Set up logging
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    ch = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    v1 = client.CoreV1Api(client.ApiClient(configuration))
    ret = v1.list_pod_for_all_namespaces(watch=False)
    matches = 0
    for i in ret.items:
        if i.status.phase == "Pending":
            print(
                "%s\t%s\t%s" % (i.metadata.namespace, i.metadata.name, i.status.phase)
            )
            fs = "involvedObject.name=" + i.metadata.name
            stream = watch.Watch().stream(
                v1.list_namespaced_event,
                i.metadata.namespace,
                field_selector=fs,
                timeout_seconds=1,
            )
            for event in stream:
                msg = event["object"].message
                if re.search(".*Insufficient nvidia.com/gpu.*", msg):
                    print("GPU-bound pending pod found.")
                    print(msg)
                    matches += matches
                    break
    if matches == 0:
        print("No pending pods found with GPU requirements!")
        print("Sleeping for 30 seconds")


if __name__ == "__main__":
    while True:
        main()
        time.sleep(30)
