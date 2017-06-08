import argparse
import json
import random
import socket
import sys
import threading
import time

import paho.mqtt.client as mqtt 

HOST='10.1.1.101'
PORT=1883
DEBUG_MSG_ON = False
DEVICE_NUM = 0
TOT_PROBES = 50
IP_DELAY = 1.0 # sec

tot_elapsed_time = 0.0
min_elapsed_time = 1000000.0 # a very high value
max_elapsed_time = -min_elapsed_time # a very low value
in_probes = 1


# The callback used when the client receives a CONNACK response from the broker.
def on_connect(client, userdata, flags, rc):
	if DEBUG_MSG_ON: sys.stderr.write("[DEBUG:on_connect] Connected to %s : %d\n" % (client._host, client._port))
	if rc > 0:
		sys.stderr.write("[DISASTER:on_connect]: %d - calling on_connect()\n" % rc)
		sys.exit(2)
	else:
		client.subscribe("external/pingpongprobe", qos=0)

def on_message(client, userdata, msg):
	global tot_elapsed_time
	global min_elapsed_time
	global max_elapsed_time
	global in_probes

	in_time = time.time()
	themsg = json.loads(str(msg.payload))
	
	if msg.topic.startswith("external"):
		if DEBUG_MSG_ON: sys.stdout.write("device "+str(DEVICE_NUM)+": received pingpong probe "+str(themsg['device'])+"\n")
	else:
		sys.stderr.write("[DEBUG:on_message] Received: '%s', topic: '%s' (qos=%d)\n" % (msg.payload, msg.topic, msg.qos))
		sys.exit(22)

	device_id = themsg['device']	
	probe_num = themsg['num']	
	probe_stime = themsg['time']
	elapsed_time = (in_time - probe_stime)*1000.0 # to transform in milliseconds

	if DEBUG_MSG_ON: sys.stdout.write("received probe "+str(probe_num)+" elapsed time = "+str(elapsed_time)+"\n")

	in_probes += 1
	tot_elapsed_time += elapsed_time
	if elapsed_time < min_elapsed_time: min_elapsed_time = elapsed_time
	if elapsed_time > max_elapsed_time: max_elapsed_time = elapsed_time

def producing_data(snum):
	for probe_num in range(0, TOT_PROBES):
		# creating the probe message
		the_time = time.time()
		the_msg={'device': snum, 'num': probe_num, 'time': the_time}
		the_msg_str = json.dumps(the_msg)

		client.publish("global/pingpongprobe", the_msg_str)
		sys.stdout.write("produced pingpong probe %s\n" % the_msg_str)

		time.sleep(IP_DELAY)# sleep for IP_DELAY seconds before next call
	return 0

if __name__ == '__main__':

	# getting specific data about the sender
	parser = argparse.ArgumentParser()
	parser.add_argument("--totprobes", help="number of probes")
	parser.add_argument("--ipdelay", help="inter-probes delay in seconds")
	args = parser.parse_args()
	if args.totprobes:
		TOT_PROBES = int(args.totprobes)
	if args.ipdelay:
		IP_DELAY = float(args.ipdelay)

	client=mqtt.Client(client_id="", clean_session=True, userdata=None, protocol='MQTTv311')
	client.on_connect = on_connect
	client.on_message = on_message

	# Connect to the MQTT broker
	try:
		client.connect(HOST, PORT, keepalive=60)
	except socket.error as serr:
		sys.stderr.write("[ERROR] %s\n" % serr)
		sys.exit(2)

	random.seed(a=None)
	DEVICE_NUM = random.randint(1,1000)
	t = threading.Thread(target=producing_data, args=(DEVICE_NUM,))
	t.setDaemon(True)
	t.start()

	client.loop_start()
	t.join()
	client.loop_stop()

	while in_probes < (TOT_PROBES):
		print in_probes
		client.loop(1.0)

	# prints stats
	sys.stdout.write("TOT_PROBES = %d IP_DELAY = %1.3f FREQ = %1.3f\n" % (TOT_PROBES, IP_DELAY, 1.0/IP_DELAY))
	sys.stdout.write("average, min, max\n")
	sys.stdout.write("%10.3f, %10.3f, %10.3f\n" % (tot_elapsed_time/TOT_PROBES, min_elapsed_time, max_elapsed_time))


