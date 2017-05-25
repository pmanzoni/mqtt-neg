#!/usr/bin/python

import argparse
import logging
import socket
import sys
import threading
import time

import paho.mqtt.client as mqtt
import talktodd

B_HOST='localhost'	# MQTT broker host
B_PORT=1883			# MQTT broker port
DD_HOST='localhost'	# IBR-DTN daemon host
DD_PORT=4550		# IBR-DTN daemon port

OUTB_LINK= None			 # 'ddtalker' element to deliver global messages as bundles TO neighbouring nodes
LOCAL_EID = 'themqproxy' # Endpoint ID for the IBR-DTN protocol

# Debugging related stuff
DEBUG_MSG_ON = False
logging.basicConfig(level=logging.DEBUG, format='[%(levelname)s] [%(threadName)-10s%(message)s',)


#------ BEGIN of the proxy core 

def handle_input_from_inside(dd_link, in_topic, in_payload):
# gets 'global' content from the MQTT local net
# sends to the neighbours through the DTN daemon

	# preparing bundle content
	content = in_topic+'\n'+in_payload

	# looks for all the neighbours and send a copy of the message to all of them
	neig = dd_link.get_neighbours()
	if neig:
		for c_neig in neig:
			destination = c_neig+'/'+LOCAL_EID
			if DEBUG_MSG_ON: sys.stderr.write("[DEBUG:mqttproxycore:handle_input_from_inside] forwarding:\n-BEGIN-\n%s\n-END-\nto: '%s'\n" % (content, destination))
			in_msg = dd_link.send_1_bundle(content, destination)
	else:
		if DEBUG_MSG_ON: sys.stderr.write("[DEBUG:mqttproxycore:handle_input_from_inside] no neighbours, content:\n%s\n" % content)


def handle_input_from_outside(mqttc, dd_host, dd_port):
# reads from the rest of the world through the DTN daemon
# send to the MQTT local net

	# Connects to the DTN daemon to handle bundles with messages incoming FROM neighbouring nodes
	inb_link = talktodd.ddtalker(dd_host, dd_port)

	if DEBUG_MSG_ON: logging.debug(":mqttproxycore:handle_input_from_outside]")
	while True:
		in_msg = inb_link.recv_1_bundle(LOCAL_EID)

		delim = in_msg.find('\n') # the first newline separates the topic from the message
		in_msg_topic = 'external'+in_msg[6:delim] # substituting 'global' with 'external' to evoid loops
		in_msg_data = in_msg[delim+1:]
		mqttc.publish(in_msg_topic, payload=in_msg_data, qos=0, retain=False)
#		mqttc.publish(in_msg_topic, in_msg_data)
		if DEBUG_MSG_ON: sys.stderr.write("[DEBUG:mqttproxycore:handle_input_from_outside] sent content:\n%s-%s\n" % (in_msg_topic, in_msg_data))

#------ END of the proxy core 

def on_connect(mqttc, userdata, rc):
	if DEBUG_MSG_ON: sys.stderr.write("[DEBUG:mqttproxy:on_connect] Connected to %s : %d\n" % (mqttc._host, mqttc._port))
	if rc > 0:
		sys.stderr.write("[ERROR:mqttproxy:on_connect]: %d - calling on_connect()\n" % rc)
		sys.exit(2)
	else:
		mqttc.subscribe("global/#", qos=0)

def on_subscribe(mqttc, userdata, mid, granted_qos):
	if DEBUG_MSG_ON: sys.stderr.write("[DEBUG:mqttproxy:on_subscribe] Subscribed: "+str(mid)+" "+str(granted_qos)+"\n")

def on_message(mqttc, userdata, msg):
	if DEBUG_MSG_ON: sys.stderr.write("[DEBUG:mqttproxy:on_message] Received: '%s', topic: '%s' (qos=%d)\n" % (msg.payload, msg.topic, msg.qos))
	handle_input_from_inside(OUTB_LINK, msg.topic, msg.payload)

def on_publish(mqttc, userdata, mid):
	if DEBUG_MSG_ON: sys.stderr.write("[DEBUG:mqttproxy:on_publish] Sent messageid '%d'\n" % mid)

def on_log(mqttc, userdata, level, string):
	if DEBUG_MSG_ON: sys.stderr.write('[DEBUG:mqttproxy:on_publish] '+string+"\n")

if __name__ == '__main__':

	# getting specific data about the MQTT broker and the IBR-DTn daemon
	parser = argparse.ArgumentParser()
	parser.add_argument("--dtnadd", help="address of the dtn daemon, 'localhost' is default")
	parser.add_argument("--mqttadd", help="address of the mqtt broker, 'localhost' is default")
	parser.add_argument("--dtnport", type=int, help="port of the mqtt broker, '4550' is default")
	parser.add_argument("--mqttport", type=int, help="port of the mqtt broker, '1883' is default")
	args = parser.parse_args()
	if args.dtnadd:
		DD_HOST = args.dtnadd
	if args.mqttadd:
		B_HOST = args.mqttadd
	if args.dtnport:
	    DD_PORT = args.dtnport
	if args.mqttport:
	    B_PORT = args.mqttport
	if DEBUG_MSG_ON: sys.stderr.write('[DEBUG:main_argsparser] '+'DTN:'+DD_HOST+':'+str(DD_PORT)+' MQTT:'+B_HOST+':'+str(B_PORT)+'\n')

	# Preparing the MQTT Client
	mqttc = mqtt.Client(client_id="", clean_session=True, userdata=None, protocol='MQTTv311')
	mqttc.on_message = on_message
	mqttc.on_connect = on_connect
	mqttc.on_publish = on_publish
	mqttc.on_subscribe = on_subscribe
	# mqttc.on_log = on_log

	# Connect to the MQTT broker
	try:
		mqttc.connect(B_HOST, B_PORT, keepalive=60)
	except socket.error as serr:
		sys.stderr.write("[ERROR] %s\n" % serr)
		sys.exit(2)

	# Connect to the DTN daemon to deliver global messages as bundles TO neighbouring nodes
	OUTB_LINK = talktodd.ddtalker(DD_HOST, DD_PORT)

	# Creating and starting thread to handle bundles with messages incoming FROM neighbouring nodes
	t = threading.Thread(name='in_handler', target=handle_input_from_outside, args=(mqttc, DD_HOST, DD_PORT,))
	t.setDaemon(True)
	t.start()

	# Start the handling of messages to and from the MQTT broker
	mqttc.loop_forever()
