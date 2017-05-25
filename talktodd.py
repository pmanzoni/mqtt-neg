import socket
import sys
import base64

class ddtalker:
	''' A class to establish a flow of communication between the IBR-DTN daemon '''

	HOST='localhost'
	PORT=4550
	DEBUG_MSG_ON = False

	def __init__(self, host=HOST, port=PORT):

		# create a socket
		try:
			self.dsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		except socket.error, msg:
			sys.stderr.write("[ERROR:talktodd:__init__] %s\n" % msg)
			exit(9)

		# connect to the daemon
		try:
			self.dsock.connect((host, port))
			readfromdeamon_s = self.dsock.makefile()
			writetodeamon_s = self.dsock
		except socket.error, msg:
			sys.stderr.write("[ERROR:talktodd:__init__] %s\n" % msg)
			exit(9)

		# read header
		daemonbanner = readfromdeamon_s.readline()
		if self.__class__.DEBUG_MSG_ON: sys.stderr.write("[DEBUG:talktodd:__init__] %s" % daemonbanner)

		# switch into protocol extended mode
		writetodeamon_s.send("protocol extended\n")
		dretval = readfromdeamon_s.readline()
		if "200" in dretval:
			if self.__class__.DEBUG_MSG_ON: sys.stderr.write("[DEBUG:talktodd:__init__] %s" % dretval)
		else:
			sys.stderr.write("[ERROR:talktodd:__init__] %s\n" % dretval)
			exit(9)

	def get_neighbours(self):

		readfromdeamon_s = self.dsock.makefile()
		writetodeamon_s = self.dsock

		writetodeamon_s.send("neighbor list\n")
		dretval = readfromdeamon_s.readline()
		if "200" in dretval:
			if self.__class__.DEBUG_MSG_ON: sys.stderr.write("[DEBUG] %s\n" % dretval)
		else:
			sys.stderr.write("[DISASTER] %s\n" % dretval)
			return ((1,dretval))

		the_neighb = []
		data = readfromdeamon_s.readline()
		while (len(data) > 1):    
			the_neighb.append(data[:-1])    # taking off the final newline char
			data = readfromdeamon_s.readline()

		return the_neighb

	def send_1_bundle(self, pload, eid):

		'''may seem dumb but it allows me to remeber where to write and where to read'''
		readfromdeamon_s = self.dsock.makefile()
		writetodeamon_s = self.dsock

		pload64 = base64.b64encode(pload)

		writetodeamon_s.send("bundle put plain\n")
		dretval = readfromdeamon_s.readline()
		if "100" in dretval:
			if self.__class__.DEBUG_MSG_ON: sys.stderr.write("[DEBUG] %s\n" % dretval)
		else:
			sys.stderr.write("[ERROR:talktodd:send_1_bundle] bundle put plain %s\n" % dretval)
			sys.exit(1)

		writetodeamon_s.send("Source: api:me\n")
		writetodeamon_s.send("Destination: "+eid+"\n")
		if self.__class__.DEBUG_MSG_ON: sys.stderr.write("[DEBUG] %s\n" % "Destination: "+eid+"\n")

		writetodeamon_s.send("Blocks: 1\n")
		writetodeamon_s.send("\n")          # Required empty line
		writetodeamon_s.send("Block: 1\nFlags: LAST_BLOCK\nLength: "+str(len(pload))+"\n")
		writetodeamon_s.send("\n")          # Required empty line
		writetodeamon_s.send(pload64+"\n")
		writetodeamon_s.send("\n")          # Required empty line

		dretval = readfromdeamon_s.readline()
		if "200" in dretval:
			if self.__class__.DEBUG_MSG_ON: sys.stderr.write("[DEBUG] %s\n" % dretval)
		else:
			sys.stderr.write("[ERROR:talktodd:send_1_bundle] %s\n" % dretval)
			sys.exit(1)

		writetodeamon_s.send("bundle send\n")
		dretval = readfromdeamon_s.readline()
		if "200" in dretval:
			if self.__class__.DEBUG_MSG_ON: sys.stderr.write("[DEBUG] %s\n" % dretval)
		else:
			sys.stderr.write("[ERROR:talktodd:send_1_bundle] bundle send %s\n" % dretval)
			sys.exit(1)

	def recv_1_bundle(self, eid):

		'''may seem dumb but it allows me to remeber where to write and where to read'''
		readfromdeamon_s = self.dsock.makefile()
		writetodeamon_s = self.dsock

		writetodeamon_s.send("set endpoint "+eid+"\n")
		dretval = readfromdeamon_s.readline()
		if "200" in dretval:
			if self.__class__.DEBUG_MSG_ON: sys.stderr.write("[DEBUG:talktodd:recv_1_bundle] set endpoint: %s" % dretval)
		else:
			sys.stderr.write("[ERROR] %s\n" % dretval)
			sys.exit(1)

		writetodeamon_s.send("registration list\n")
		dretval = readfromdeamon_s.readline()
		if "200" in dretval:
			if self.__class__.DEBUG_MSG_ON: sys.stderr.write("[DEBUG:talktodd:recv_1_bundle] %s" % dretval)
			data = readfromdeamon_s.readline()
			while (len(data) > 1):    
				if self.__class__.DEBUG_MSG_ON: sys.stderr.write("[DEBUG:talktodd:recv_1_bundle] %s" % data)
				data = readfromdeamon_s.readline()
		else:
			sys.stderr.write("[ERROR] %s\n" % dretval)
			sys.exit(1)

		dretval = readfromdeamon_s.readline()
		if "602" in dretval:        # NOTIFY BUNDLE
			if self.__class__.DEBUG_MSG_ON: sys.stderr.write("[DEBUG:talktodd:recv_1_bundle] %s" % dretval)
		else:
			sys.stderr.write("[ERROR] %s\n" % dretval)
			sys.exit(1)

		writetodeamon_s.send("bundle load queue\n")
		dretval = readfromdeamon_s.readline()
		if "200" in dretval:
			if self.__class__.DEBUG_MSG_ON: sys.stderr.write("[DEBUG:talktodd:recv_1_bundle] %s" % dretval)
		else:
			sys.stderr.write("[ERROR] %s\n" % dretval)
			sys.exit(1)

		writetodeamon_s.send("bundle get plain\n")
		dretval = readfromdeamon_s.readline()
		if "200" in dretval:
			if self.__class__.DEBUG_MSG_ON: sys.stderr.write("[DEBUG:talktodd:recv_1_bundle] %s" % dretval)
		else:
			sys.stderr.write("[ERROR] %s\n" % dretval)
			sys.exit(1)

		# read main header into 'inb_mhead' dictionary
		inb_mhead = {}
		data = readfromdeamon_s.readline()
		while (len(data) > 1):    
			ll = data.split()
			inb_mhead[ll[0]] = ll[1]
			data = readfromdeamon_s.readline()

		# read actual data block header into 'inb_bhead' dictionary
		if inb_mhead['Blocks:'] == '1':
			inb_bhead = {}
			data = readfromdeamon_s.readline()
			while (len(data) > 1):    
				ll = data.split()
				inb_bhead[ll[0]] = ll[1]
				data = readfromdeamon_s.readline()
		else:
			sys.stderr.write("[ERROR:talktodd:recv_1_bundle] not ready yet for bundles with more than 1 block\n")
			sys.exit(1)

		# read actual data of the bundle
		the_data = ""
		if inb_bhead['Flags:'] == 'LAST_BLOCK':
			data = readfromdeamon_s.readline()
			while (len(data) > 1):    
				the_data = the_data + data
				data = readfromdeamon_s.readline()
		else:
			sys.stderr.write("[ERROR] not LAST_BLOCK\n")
			sys.exit(1)

		# clean up the bundle register
		writetodeamon_s.send("bundle free\n")
		dretval = readfromdeamon_s.readline()
		if "200" in dretval:
			if self.__class__.DEBUG_MSG_ON: sys.stderr.write("[DEBUG] %s\n" % dretval)
		else:
			sys.stderr.write("[ERROR] %s\n" % dretval)
			sys.exit(1)

		return base64.b64decode(the_data)

