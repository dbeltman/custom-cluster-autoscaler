import logging
from kubernetes import client, config, watch

def main():
    configuration = client.Configuration()
    configuration.api_key["authorization"] = 'eyJhbGciOiJSUzI1NiIsImtpZCI6ImU3Z0QxNzI1SjNCdkRwOFVqdW5YTHlyZ0dkalhHMFJzb0ZINnNtemZqXzQifQ.eyJhdWQiOlsiaHR0cHM6Ly9rdWJlcm5ldGVzLmRlZmF1bHQuc3ZjLmNsdXN0ZXIubG9jYWwiLCJrM3MiXSwiZXhwIjoxNzQ2MjE5OTkxLCJpYXQiOjE3MTQ2ODM5OTEsImlzcyI6Imh0dHBzOi8va3ViZXJuZXRlcy5kZWZhdWx0LnN2Yy5jbHVzdGVyLmxvY2FsIiwia3ViZXJuZXRlcy5pbyI6eyJuYW1lc3BhY2UiOiJkZXZlbG9wbWVudC1hcHBzIiwicG9kIjp7Im5hbWUiOiJ2c2NvZGUtc2VydmVyLWI3NmI5YjVjZC01aG52ZCIsInVpZCI6IjRjNTA2OTgxLWI0MjItNDI1OS1iMzlmLWZlN2MyNDI0NzdlNyJ9LCJzZXJ2aWNlYWNjb3VudCI6eyJuYW1lIjoidnNjb2RlLXNlcnZlciIsInVpZCI6ImRiNzg0OGMxLTIyMzgtNDkwZC1iNzgzLTU4YmZhYzFhNDk5OSJ9LCJ3YXJuYWZ0ZXIiOjE3MTQ2ODc1OTh9LCJuYmYiOjE3MTQ2ODM5OTEsInN1YiI6InN5c3RlbTpzZXJ2aWNlYWNjb3VudDpkZXZlbG9wbWVudC1hcHBzOnZzY29kZS1zZXJ2ZXIifQ.vlPXjgw0RjhZUg-4vEa8UOjAJlzLlLZNSaPBsmYI9sGs4P-x7HpVzHYqmoVsRjrN8UPQZARo51jbuxK9i8OryfqtGxXr0l1ov8irtB9WspCHvpO4iluPmVvn8cAWaQnoSJ2sOV4lXJgfDBP9byWusCPfFsq3_yu6xhtcnrKcnfHpmQ0jmxP3_YcaA89BtlvKQrnbUyo3z-LT84LGdVuZJGrFc8DbUw6OhQnmDdnUYFGz-ZshpsLmMQKZM21uUIYoi8NeWpnkXc10-lWLQYm57lSCS20U_liwmENLaYizZ0t__5n4rSIeWa3DosH9zEU27_ssc7-8f3dWMnse-q-Jmg'
    configuration.api_key_prefix['authorization'] = 'Bearer'
    configuration.host = 'https://10.43.0.1'
    configuration.ssl_ca_cert = '/var/run/secrets/kubernetes.io/serviceaccount/ca.crt'

    # Set up logging
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    ch = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    v1 = client.CoreV1Api(client.ApiClient(configuration))
    ret = v1.list_pod_for_all_namespaces(watch=False)
    for i in ret.items:
        if i.status.phase == "Pending":
            print("%s\t%s\t%s" % (i.metadata.namespace, i.metadata.name, i.status.phase))
            field_selector='involvedObject.name='+i.metadata.name
            stream = watch.Watch().stream(v1.list_namespaced_event, i.metadata.namespace, field_selector=field_selector, timeout_seconds=1)
            for event in stream:
                print(event['object'].message)

if __name__ == "__main__":
    main()