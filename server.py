import threading
import socket
import time
import random

# declare constansts
d24 = [None,-5,-5,-5,-4,-4,-4,-3,-3,-2,-2,-1,-1,0,0,1,2,3,4,5,7,8,10,10,10]
DIE_SIDES = 24
LONGEST_ROLL = 80
DELAY_BETWEEN_ROLLS = 25
CMSG_LEN = 6
PMSG_LEN = 30
EMSG_LEN = CMSG_LEN + 1
NMSG_LEN = 2
FMSG_LEN = 4
PORT = 2727
SOCK_LISTENMAX = 5
DELIMITER = "#"
POLLRATE = .1
# declare constants

class TableThread(threading.Thread):
    """this object is the tabletop, at the moment it
    only tracks our die"""

    def __init__(self):
	self.players = []
	self.roll = 0
	self.rolling = 0
	self.pastrolling = 0
	self.roller = 0
	self.count = 0
	threading.Thread.__init__(self)

    def run(self):
	while True: #TODO: Add server closing in the CLI
	    if self.rolling:
		if self.pastrolling == 0:
		    self.count = 0
		self.pastrolling = 1
        	self.n = random.randint(1,DIE_SIDES-1)
		if self.n >= self.roll:
		    self.n += 1
		self.roll = self.n
		self.count += 1
		print '%s is rolling: %d! [Face %d]' % (self.players[self.roller], d24[self.roll], self.roll)
		if self.count == LONGEST_ROLL:
		    self.rolling = 0
	    if not self.rolling and self.pastrolling == 1:
        	self.roll = random.randint(1,DIE_SIDES)
		self.pastrolling = 0
		print '%s has rolled a %d! [Face %d]' % (self.players[self.roller], d24[self.roll], self.roll)
		self.count = 0
	    if not self.rolling:
		self.count += 1
	    time.sleep(POLLRATE)

class ClientSocketThread(threading.Thread):
    """This class contains the listening and the sending sockets"""

    def __init__(self,clientsocket,address):
        self.channel = clientsocket
	self.details = address
	self.pastrolling = 0
	self.pid = 0
	self.clientrate = POLLRATE
	self.senderloop = 1
	self.listenloop = 1
	threading.Thread.__init__(self)
	
    def run(self):
	self.sendthread1 = threading.Thread(target=self.listen)
	self.sendthread2 = threading.Thread(target=self.sender)
	Table.players.append("New Player")
	self.pid = len(Table.players)-1
	self.sendthread1.start()

    def listen(self):
	print "---[Opening new connection thread: %s]" % self.details[0]
	self.sendthread2.start()
	while self.listenloop: #TODO: Add server closing in the CLI
	    msg = self.irecv ( CMSG_LEN )
	    if msg == "Rollin":
		if self.pid > len(Table.players) or self.pid < 0:
		    print "[Error: An unidentified player tried to roll]"
		    self.isend("error 1",EMSG_LEN)
		elif Table.rolling == 1:
		    if self.pid == Table.roller:
		        Table.rolling = 0
			print "---[Roll Stopped]"
		    else:
		        print "---[Error: Two different people tried to roll]"
			self.isend("error 2",EMSG_LEN)
		elif Table.rolling == 0:
		    if Table.count > DELAY_BETWEEN_ROLLS:
			print "---[Rolling]"
			Table.roller = self.pid
			Table.rolling = 1
		    else:
			print "---[Error: Too early to roll]"
			self.isend("error 3",EMSG_LEN)
		else:
		    print "---[Error: Unknown rolling exception: %s]" % self.details[0]
		    self.isend("error 5",EMSG_LEN)
	    if msg == "Player":
		msg = self.irecv ( PMSG_LEN )
		print "%s has changed name to %s" % (Table.players[self.pid], msg)
		Table.players[self.pid] = msg
	    if msg == "SetPol":
		msg = self.irecv ( FMSG_LEN )
		print "%s has changed poll rate to %s" % (Table.players[self.pid], msg)
		self.clientrate = float(msg)/1000
	    if msg == "Quitin":
		self.listenloop = 0
		if self.senderloop:
		    print "%s is quitting." % (Table.players[self.pid],)
		else:
		# TODO: add server kicking in the CLI
		    print "%s is being kicked." % (Table.players[self.pid],)
		break


    def sender(self):
	while self.senderloop: #TODO: add server closing in the CLI
	    if self.listenloop == 0:
	    # if the client has shut down the listen loop, all
	    # we have yet to do is send confirmation all loops are closed
		self.isend("shutdn",CMSG_LEN)
		self.senderloop = 0
		print "---[Connection closed: %s]" % self.details[0]
	    elif Table.rolling == 1 and self.pastrolling == 0:
		self.isend("player",CMSG_LEN)
		self.isend('%s' % (Table.players[Table.roller],),PMSG_LEN)
		self.pastrolling = 1
	    elif Table.rolling == 1 and self.pastrolling == 1:
		self.isend("number",CMSG_LEN)
		self.isend("%d" % Table.roll,NMSG_LEN)
		time.sleep(self.clientrate)
	    elif self.pastrolling == 1 and Table.pastrolling == 0:
		self.isend("number",CMSG_LEN)
		self.isend("%d" % Table.roll,NMSG_LEN)
		self.isend("finish",CMSG_LEN)
		self.pastrolling = 0
		time.sleep(self.clientrate)
	    else:
		self.isend("CurInf",CMSG_LEN)
		time.sleep(self.clientrate)

    def isend(self, msg,msglen):
        totalsent = 0
	while len(msg) < msglen:
	    msg = msg + DELIMITER
        while totalsent < msglen:
            sent = self.channel.send(msg[totalsent:msglen])
            if sent == 0:
                raise RuntimeError("socket connection broken")
            totalsent = totalsent + sent

    def irecv(self,msglen):
        msg = ''
        while len(msg) < msglen:
            chunk = self.channel.recv(msglen-len(msg))
            if chunk == '':
                raise RuntimeError("socket connection broken")
            msg = msg + chunk
	if DELIMITER in msg:
	    msg = msg[:msg.find(DELIMITER)]
        return msg


ServSocket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
ServSocket.bind(('',PORT))
ServSocket.listen( SOCK_LISTENMAX )


Table = TableThread()
Table.start()

while 1: #TODO: add server closing to CLI
    clientsocket, address = ServSocket.accept()
    print 'Connection opened with', address
    sock = ClientSocketThread(clientsocket,address)
    sock.start()
    
