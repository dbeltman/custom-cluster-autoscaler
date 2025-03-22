import paho.mqtt.publish as mqtt_publish
import os
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)

mqtt_host = os.getenv('MQTTHOST', 'MQTT-Server')
mqtt_port = os.getenv('MQTTPORT', 1883)
mqtt_username = os.getenv('MQTTUSERNAME', 'iot')
mqtt_password = os.getenv('MQTTPASSWORD', 'changeme')
mqtt_client_name = os.getenv('MQTTCLIENTNAME', 'custom-cluster-autoscaler')

def publish(topic, payload):
    print("Publishing " +str(payload) + " @" + str(topic))
    try:
        mqtt_publish.single(topic, payload,
                        hostname=mqtt_host,
                        client_id=mqtt_client_name,
                        port=mqtt_port,
                        retain=True,
                        auth={'username':mqtt_username, 'password':mqtt_password})
    except:
        print("ERROR: Something went wrong publishing '" + str(payload) + "' to topic '" + str(topic) + "'!")
