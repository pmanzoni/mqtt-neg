import socket
import sys
import base64

class ddtalker:
	''' A class to talk with the IBR-DTN daemon '''

	HOST='localhost'
	PORT=4550
	DEBUG_MSG_ON = False
	DEBUG2_MSG_ON = True
	bin_count = 0	# bundles input counter at bundle load queue step

	def __init__(self, host=HOST, port=PORT):

		# create a socket
		try:
			self.dsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		except socket.error, msg:
			sys.stderr.write("[ERROR:ddtalker:__init__] %s\n" % msg)
			exit(9)

		# connect to the daemon
		try:
			self.dsock.connect((host, port))
			readfromdaemon_s = self.dsock.makefile()
			writetodaemon_s = self.dsock
		except socket.error, msg:
			sys.stderr.write("[ERROR:ddtalker:__init__] %s\n" % msg)
			exit(9)

		# read header
		daemonbanner = readfromdaemon_s.readline()
		if self.__class__.DEBUG_MSG_ON: sys.stderr.write("[DEBUG:ddtalker:__init__] %s" % daemonbanner)

		# switch into protocol extended mode
		writetodaemon_s.send("protocol extended\n")
		dretval = readfromdaemon_s.readline()
		if "200" in dretval:
			if self.__class__.DEBUG_MSG_ON: sys.stderr.write("[DEBUG:ddtalker:__init__] %s" % dretval)
		else:
			sys.stderr.write("[ERROR:ddtalker:__init__] %s\n" % dretval)
			exit(9)

	def get_neighbours(self):

		readfromdaemon_s = self.dsock.makefile()
		writetodaemon_s = self.dsock

		writetodaemon_s.send("neighbor list\n")
		dretval = readfromdaemon_s.readline()
		if "200" in dretval:
			if self.__class__.DEBUG_MSG_ON: sys.stderr.write("[DEBUG] %s\n" % dretval)
		else:
			sys.stderr.write("[DISASTER] %s\n" % dretval)
			return ((1,dretval))

		the_neighb = []
		data = readfromdaemon_s.readline()
		while (len(data) > 1):    
			the_neighb.append(data[:-1])    # taking off the final newline char
			data = readfromdaemon_s.readline()

		return the_neighb

	def send_1_bundle(self, pload, eid):

		'''may seem dumb but it allows me to remeber where to write and where to read'''
		readfromdaemon_s = self.dsock.makefile()
		writetodaemon_s = self.dsock

		pload64 = base64.b64encode(pload)

		writetodaemon_s.send("bundle put plain\n")
		dretval = readfromdaemon_s.readline()
		if "100" in dretval:
			if self.__class__.DEBUG_MSG_ON: sys.stderr.write("[DEBUG] %s\n" % dretval)
		else:
			sys.stderr.write("[ERROR:ddtalker:send_1_bundle] bundle put plain %s\n" % dretval)
			sys.exit(1)

		writetodaemon_s.send("Source: api:me\n")
		writetodaemon_s.send("Destination: "+eid+"\n")
		if self.__class__.DEBUG_MSG_ON: sys.stderr.write("[DEBUG] %s\n" % "Destination: "+eid+"\n")

		writetodaemon_s.send("Blocks: 1\n")
		writetodaemon_s.send("\n")          # Required empty line
		writetodaemon_s.send("Block: 1\nFlags: LAST_BLOCK\nLength: "+str(len(pload))+"\n")
		writetodaemon_s.send("\n")          # Required empty line
		writetodaemon_s.send(pload64+"\n")
		writetodaemon_s.send("\n")          # Required empty line

		dretval = readfromdaemon_s.readline()
		if "200" in dretval:
			if self.__class__.DEBUG_MSG_ON: sys.stderr.write("[DEBUG] %s\n" % dretval)
		else:
			sys.stderr.write("[ERROR:ddtalker:send_1_bundle] %s\n" % dretval)
			sys.exit(1)

		writetodaemon_s.send("bundle send\n")
		dretval = readfromdaemon_s.readline()
		if "200" in dretval:
			if self.__class__.DEBUG_MSG_ON: sys.stderr.write("[DEBUG] %s\n" % dretval)
		else:
			sys.stderr.write("[ERROR:ddtalker:send_1_bundle] bundle send %s\n" % dretval)
			sys.exit(1)

	def recv_set_endpoint(self, eid):

		'''may seem dumb but it allows me to remeber where to write and where to read'''
		readfromdaemon_s = self.dsock.makefile()
		writetodaemon_s = self.dsock

		writetodaemon_s.send("set endpoint "+eid+"\n")
		dretval = readfromdaemon_s.readline()
		if "200" in dretval:
			if self.__class__.DEBUG_MSG_ON: sys.stderr.write("[DEBUG:ddtalker:recv_1_bundle] set endpoint: %s" % dretval)
		else:
			sys.stderr.write("[ERROR] %s\n" % dretval)
			sys.exit(1)

		writetodaemon_s.send("registration list\n")
		dretval = readfromdaemon_s.readline()
		if "200" in dretval:
			if self.__class__.DEBUG_MSG_ON: sys.stderr.write("[DEBUG:ddtalker:recv_1_bundle] %s" % dretval)
			data = readfromdaemon_s.readline()
			while (len(data) > 1):    
				if self.__class__.DEBUG_MSG_ON: sys.stderr.write("[DEBUG:ddtalker:recv_1_bundle] %s" % data)
				data = readfromdaemon_s.readline()
		else:
			sys.stderr.write("[ERRORwexit:recv_set_endpoint] %s\n" % dretval)
			sys.exit(1)

	def readline_from_daemon(self, f_s, msg="generic"):
		rval = f_s.readline()
		while "602 NOTIFY BUNDLE" in rval:	# new bundle incoming... 
			sys.stderr.write("[ERROR602 - %s] %s\n" % (msg,rval))
			self.__class__.bin_count = self.__class__.bin_count + 1
			rval = f_s.readline()
		return rval

	def wait_in_bundle(self):

		if self.__class__.DEBUG2_MSG_ON: 
			if self.__class__.bin_count != 0: sys.stderr.write("[MSG:recv_1_bundle.bin_count] %d\n" % self.__class__.bin_count)
		readfromdaemon_s = self.dsock.makefile()
		dretval = readfromdaemon_s.readline()
		if "602 NOTIFY BUNDLE" in dretval:
			if self.__class__.DEBUG_MSG_ON: sys.stderr.write("[DEBUG:ddtalker:recv_1_bundle] %s" % dretval)
		else:
			sys.stderr.write("[DISASTER:wait_in_bundle] %s\n" % dretval)
			sys.exit(1)

	def recv_1_bundle(self):

		'''may seem dumb but it allows me to remeber where to write and where to read'''
		readfromdaemon_s = self.dsock.makefile()
		writetodaemon_s = self.dsock

		if self.__class__.DEBUG2_MSG_ON: 
			if self.__class__.bin_count != 0: sys.stderr.write("[MSG:recv_1_bundle.bin_count] %d\n" % self.__class__.bin_count)

		if self.__class__.bin_count > 0: 
			self.__class__.bin_count = self.__class__.bin_count - 1
		else:
			self.wait_in_bundle()

		writetodaemon_s.send("bundle load queue\n")
		dretval = self.readline_from_daemon(readfromdaemon_s, "bundle load queue")
		if "200 BUNDLE LOADED" in dretval:
			if self.__class__.DEBUG_MSG_ON: sys.stderr.write("[DEBUG:ddtalker:recv_1_bundle] %s" % dretval)
		else:
			sys.stderr.write("[DISASTER-bundle load queue] %s\n" % dretval)
			sys.exit(1)

		writetodaemon_s.send("bundle get plain\n")
		dretval = self.readline_from_daemon(readfromdaemon_s, "bundle get plain")
		if "200 BUNDLE GET PLAIN" in dretval:
			if self.__class__.DEBUG_MSG_ON: sys.stderr.write("[DEBUG:ddtalker:recv_1_bundle] %s" % dretval)
		else:
			sys.stderr.write("[DISASTER-bundle get plain] %s\n" % dretval)
			sys.exit(1)

		# read main header into 'inb_mhead' dictionary
		inb_mhead = {}
		data = self.readline_from_daemon(readfromdaemon_s, "data1")
		while (len(data) > 1):    
			ll = data.split()
			inb_mhead[ll[0]] = ll[1]
			data = self.readline_from_daemon(readfromdaemon_s, "data2")

		# read actual data block header into 'inb_bhead' dictionary
		if inb_mhead['Blocks:'] == '1':
			inb_bhead = {}
			data = self.readline_from_daemon(readfromdaemon_s, "data3")
			while (len(data) > 1):    
				ll = data.split()
				inb_bhead[ll[0]] = ll[1]
				data = self.readline_from_daemon(readfromdaemon_s, "data4")

			# read actual data of the bundle
			the_data = ""
			if inb_bhead['Flags:'] == 'LAST_BLOCK':
				data = self.readline_from_daemon(readfromdaemon_s, "data5")
				while (len(data) > 1):    
					the_data = the_data + data
					data = self.readline_from_daemon(readfromdaemon_s, "data6")
			else:
				sys.stderr.write("[DISASTER] not LAST_BLOCK\n")
				sys.exit(1)

		else:
			sys.stderr.write("[ERROR:ddtalker:recv_1_bundle] not ready yet for bundles with %d block\n" % inb_mhead['Blocks:'])
			sys.exit(1)

		# clean up the bundle register
		writetodaemon_s.send("bundle free\n")
		dretval = self.readline_from_daemon(readfromdaemon_s, "bundle free")
		if "200 BUNDLE FREE" in dretval:
			if self.__class__.DEBUG_MSG_ON: sys.stderr.write("[DEBUG:bundle free] %s\n" % dretval)
		elif "\n" == dretval:
			sys.stderr.write("[STRANGE THINGS in bundle free; a newline received... trying once more]\n")
			dretval = self.readline_from_daemon(readfromdaemon_s, "bundle free")
			if not "200 BUNDLE FREE" in dretval:
				sys.stderr.write("[DISASTER:bundle free ST] >>>%s<<<\n" % dretval)
				sys.exit(1)
		else:
			sys.stderr.write("[DISASTER:bundle free] >>>%s<<<\n" % dretval)
			sys.exit(1)

		return base64.b64decode(the_data)

