import json
import sys
import time
import paho.mqtt.client as mqtt 

HOST='localhost'
PORT=1883
DEBUG_MSG_ON = False

# The callback used when the client receives a CONNACK response from the broker.
def on_connect(client, userdata, flags, rc):
	if DEBUG_MSG_ON: sys.stderr.write("[DEBUG:on_connect] Connected to %s : %d\n" % (client._host, client._port))
	if rc > 0:
		sys.stderr.write("[DISASTER:on_connect]: %d - calling on_connect()\n" % rc)
		sys.exit(2)
	else:
		client.subscribe("external/pingpongprobe", qos=0)

def on_message(client, userdata, msg):

	if msg.topic.startswith("external"):
		if DEBUG_MSG_ON: sys.stdout.write("received pingpong probe %s\n" % str(msg.payload))
	else:
		sys.stderr.write("[DISASTER:on_message] Received: '%s', topic: '%s' (qos=%d)\n" % (msg.payload, msg.topic, msg.qos))
		sys.exit(22)

	client.publish("global/pingpongprobe", msg.payload)

if __name__ == '__main__':
	client=mqtt.Client(client_id="", clean_session=True, userdata=None, protocol='MQTTv311')
	client.on_connect = on_connect
	client.on_message = on_message

	# Connect to the MQTT broker
	try:
		client.connect(HOST, PORT, keepalive=60)
	except socket.error as serr:
		sys.stderr.write("[ERROR] %s\n" % serr)
		sys.exit(2)

	client.loop_forever()

