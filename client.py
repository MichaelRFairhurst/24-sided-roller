import socket
import threading
from Tkinter import *
from itertools import count
import Queue
import time
import tkMessageBox


root = Tk()

d24 = [None,-5,-5,-5,-4,-4,-4,-3,-3,-2,-2,-1,-1,0,0,1,2,3,4,5,7,8,10,10,10]

class App:

    def __init__(self, master, queue):

        frame = Frame(master,)
        frame.pack()

	root.protocol("WM_DELETE_WINDOW", self.quit)
	root.wm_title("Mike Is Sooo Cool")

	global rollphoto
	rollphoto = [None]
	for x in xrange(1,25):
	    rollphoto.append(PhotoImage(file="Random/%d.gif" % x))
	    #print x

	global landphoto
	landphoto = [None]
	for x in xrange(1,25):
	    landphoto.append(PhotoImage(file="Landed/%d.gif" % x))
	    #print x

	self.queue = queue
	self.roll = 0
	self.quittimer = 0
	self.playername = ''
	self.err = ["", "You don't exist on the server", "Another player is already rolling", "Please wait between rolls", "Bitch you can't steal my name.", "Fatal error"]

	self.nickframe = Frame(frame,)
	self.nickframe.pack(side=TOP,fill=X)
	self.controlframe = Frame(self.nickframe,)
	self.controlframe.pack(side=RIGHT,fill=X)
	self.statusframe = Frame(frame,)
	self.statusframe.pack(side=BOTTOM,fill=X)

	self.picframe = Button(self.statusframe,image=landphoto[1],command=self.Roll)
	self.picframe.pack(side=TOP)

        #self.RollButton = Button(self.controlframe, text="Roll", fg="red",command=self.Roll)
        #self.RollButton.pack(side=TOP,fill=BOTH)

        #self.QuitButton = Button(self.controlframe, text="Quit",command=self.quit)
        #self.QuitButton.pack(side=TOP)

	self.myname = Entry(self.nickframe,)
        self.myname.pack(fill=X)

	self.NickButton = Button(self.nickframe, text="Set Nick", fg="red",command=self.setName)
        self.NickButton.pack(fill=X)

	self.whatisay = StringVar()
	self.message = Label(self.statusframe, textvariable=self.whatisay)
        self.message.pack()

    def Roll(self):
	Clocket.action = "roll"

    def setName(self):
	Clocket.ResetPlayer(self.myname.get())

    def quit(self):
	Clocket.action = "quit"

    def processIncoming(self):
        """
        Handle all the messages currently in the queue (if any).
        """
        while self.queue.qsize():
            try:
                qmsg = self.queue.get(0)
		self.quittimer = 0
                # Check contents of message and do what it says
		if qmsg[:6] == "player":
		    self.playername = qmsg[6:]
                    self.whatisay.set("%s is rolling " % self.playername)
		elif qmsg[:6] == "finish":
                    self.whatisay.set("%s has rolled a %d" % (self.playername,d24[self.roll]))
		    self.picframe.configure(image=landphoto[self.roll])
		elif qmsg[:6] == "number":
		    self.roll = int(qmsg[6:])
		    self.picframe.configure(image=rollphoto[self.roll])
		elif qmsg[:6] == "error ":

		    tkMessageBox.showinfo("Error", self.err[int(qmsg[6:])])
		elif qmsg[:6] != "CurInf":

		    tkMessageBox.showinfo("Error", "Unknown data recieved '%s'" % qmsg)
		    Clocket.action = "quit"
            except Queue.Empty:
		pass
	self.quittimer += 1
	if self.quittimer == 10:
	    tkMessageBox.showinfo("Error", "Connection lost")
	    Clocket.running = 0



class ClientSocket():

    def __init__(self, master):

	self.action = '' 
	# Holds commands from GUI

	self.pid = '0'
	#tells server the player number

	self.master = master
	self.queue = Queue.Queue()
	self.app = App(root,self.queue)

	self.running = 1
	self.socksender = threading.Thread(target=self.sender)
	self.socklisten = threading.Thread(target=self.listen)
        self.socklisten.start()
	self.periodicCall()


    def periodicCall(self):
        """
        Check every 100 ms if there is something new in the queue.
        """
        self.app.processIncoming()
        if not self.running:
            # This is the brutal stop of the system. You may want to do
            # some cleanup before actually shutting it down.
	    self.Sock.close()
            import sys
	    #time.sleep(2)
            sys.exit(1)
        self.master.after(80, self.periodicCall)
	

    def listen(self):
        self.Sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.Sock.connect(("wikifightgame.com",2727))
	# Connect to socket in this thread

	#if not self.Sock:
	#    self.running = 0
	#    return false

	self.action = "setp"
        self.socksender.start()

	# start the socket sending thread

	while self.running:
	    #print "client listening loop restarting"
	    msg = self.irecv(6)

	# These below add to the queue

	    if msg == "number":
		msg += self.irecv(2)
		#update number
	    elif msg == "player":
		msg += self.irecv(30)
		#update name of player rolling
	    elif msg == "shutdn":
		#self.running = 0
		pass 
	    elif msg == "error ":
		msg += self.irecv(1)
		#read error 
	    elif msg == "finish":
		#the roll is done
		pass
	    elif msg == "CurInf":
	        time.sleep(.1)

	# These below don't add to the queue 

	    if msg == "yourid":
		self.pid = self.irecv(2)
		#print "Dude my ID is totally %s" % self.pid

	# If it wasn't one of those, add it to the queue
	    else:
		self.queue.put(msg)

    def sender(self):
	while self.running:
	    #print "client sender loop restarting"
	    if self.action == "roll":
		threadsend = threading.Thread(target=self.roll())
		threadsend.start()
	    elif self.action == "setp":
		self.SetPlayer()
		#threadsend.start()
	    elif self.action == "name":
		threadsend = threading.Thread(target=self.ResetPlayer())
		threadsend.start()
	    elif self.action == "quit":
		self.quit()
	    self.action = ''
	    time.sleep(.1)

    def SetPlayer(self):
	self.isend("Player",6)
	self.isend("Mike",30)

    def ResetPlayer(self,name):
	self.isend("chName",6)
	self.isend(self.pid,2)
	self.isend(name,30)

    def roll(self):
	self.isend("Rollin",6)
	self.isend(self.pid,2)

    def quit(self):
	#self.isend("Quitin",6)
	#self.Sock.close()
	self.running = 0

    def isend(self, msg,msglen):
        totalsent = 0
	while len(msg) < msglen:
	    msg = msg + "#"
        while totalsent < msglen:
            sent = self.Sock.send(msg[totalsent:])
            if sent == 0:
                raise RuntimeError("socket connection broken")
            totalsent = totalsent + sent
	    #print msg

    def irecv(self,msglen):
        msg = ''
        while len(msg) < msglen:
            chunk = self.Sock.recv(msglen-len(msg))
            if chunk == '':
                raise RuntimeError("socket connection broken")
            msg = msg + chunk
	if "#" in msg:
	    msg = msg[:msg.find("#")]
	#print msg
        return msg



Clocket = ClientSocket(root)
root.mainloop()
