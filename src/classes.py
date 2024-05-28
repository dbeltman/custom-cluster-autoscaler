import yaml
import os

if os.getenv("PRODUCTION") == "True":
    reasons_yaml = "/config/reasons/reasons.yaml"
else:
    reasons_yaml = "example/config/reasons.yaml"


class NodeCapabilities:
    def __init__(self):
        self.pet_node = False
        self.resources = {"cpu": 0, "memory": 0, "gpu": 0}

    @property
    def pet_node(self):
        return self._pet_node

    @pet_node.setter
    def pet_node(self, value):
        if not isinstance(value, bool):
            raise TypeError("pet_node must be a boolean")
        self._pet_node = value

    @property
    def resources(self):
        return self._resources

    @resources.setter
    def resources(self, resources):
        if (
            not isinstance(resources, dict)
            or not all(isinstance(key, str) for key in resources.keys())
            or not all(isinstance(value, int) for value in resources.values())
        ):
            raise TypeError("resources must be a dictionary with integer values")
        self._resources = resources

    @property
    def cpu(self):
        return self.resources.get("cpu", 0)

    @cpu.setter
    def cpu(self, value):
        if not isinstance(value, int):
            raise TypeError("cpu must be an integer")
        self.resources["cpu"] = value

    @property
    def memory(self):
        return self.resources.get("memory", 0)

    @memory.setter
    def memory(self, value):
        if not isinstance(value, int):
            raise TypeError("memory must be an integer")
        self.resources["memory"] = value

    @property
    def gpu(self):
        return self.resources.get("gpu", 0)

    @gpu.setter
    def gpu(self, value):
        if not isinstance(value, int):
            raise TypeError("gpu must be an integer")
        self.resources["gpu"] = value


class AutoScaleNode:
    def __init__(self, name, description):
        self.name = name
        self.description = description

    @property
    def capabilities(self):
        return NodeCapabilities()


class PendingPod:
    def __init__(self, pendingpodreason, podname):
        self.reason = pendingpodreason
        self.podname = podname


class PendingPodReason:
    _reasons = None

    def __init__(self, name, message, regex, requirement):
        self.name = name
        self.message = message
        self.regex = regex
        self.requirement = requirement

    @classmethod
    def load_reasons_from_yaml(cls, reasons_yaml):
        with open(reasons_yaml, "r") as f:
            reasons_data = yaml.safe_load(f)
        cls._reasons = [PendingPodReason(**reason) for reason in reasons_data]

    @classmethod
    def get_all_reasons(cls):
        return cls._reasons


# Load the YAML file containing the reasons
PendingPodReason.load_reasons_from_yaml(reasons_yaml)

# Get all the reasons
all_reasons = PendingPodReason.get_all_reasons()
