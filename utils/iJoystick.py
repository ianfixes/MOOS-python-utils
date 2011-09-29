#!/usr/bin/env python
###########################################################################
#    
#    Written in 2010 by Ian Katz <ijk5@mit.edu>         
#    Terms: WTFPL (http://sam.zoy.org/wtfpl/) 
#           See COPYING and WARRANTY files included in this distribution
#
###########################################################################


# This program attempts to locate a joystick and feed its input into a
#  MOOS DB
#
# The program takes 2 command line arguments:
#  1. the host of the local (topside) MOOSDB
#  2. the port of the local (topside) MOOSDB
#
# Although it is possible to connect to the remote MOOSDB (on the vehicle),
#  don't.  Learn pMOOSBridge.
#

import os
import sys
import time
import pyMOOS
import pygame
import Joystick



class JoystickApp(object):

    def __init__(self, mooshost, moosport, joystick):

        self.mooshost = mooshost
        self.moosport = moosport
        self.joystick = joystick
        self.comms = None
        self.time = 0

    def MainLoop(self):

        # instantiate a new Comm Client object
        self.comms = pyMOOS.CMOOSCommClient()

        # open a connection to the server & start the mail thread
        # (server hostname, port, your app name, mail frequency)
        if not self.comms.Run(self.mooshost, self.moosport, "iJoystick[" + os.uname()[1] + "]", 5):
            return

        while not self.comms.IsConnected():
            print("Waiting for connect")
            time.sleep(5)

        # Register for variables
        for k in self.joystick.moosSubscriptions():
            print "Registering for", k, self.comms.Register(k, 0.1)

        try:
            # Now, Loop
            while(True):
                mail = self.GetMail()
                print "tick. ", len(mail), "messages fetched"

                #process joystick events
                if None != self.joystick:
                    todo = self.joystick.ProcessEvents(pygame.event.get(), mail)
                    for key, val in todo.items():
                        self.comms.Notify(key, val)

                # pause for a moment
                time.sleep(0.2)
                
        except(KeyboardInterrupt):
            # No need to explicitly close, in destructor of comms client.
            print "interrupted by user, quitting"
            return


    def GetMail(self):
        # Create our inbox
        inbox = pyMOOS.MOOSMSG_LIST()
        ret = {}

        # Fetch New Mail
        if self.comms.Fetch(inbox):
            now = pyMOOS.MOOSTime()
            for mail in inbox:
                k = mail.GetKey()
                if mail.IsString():
                    ret[k] = mail.m_sVal
                else:
                    ret[k] = mail.m_dfVal
        

        return ret


if __name__ == "__main__":

    if len(sys.argv) != 3:
        print "Usage: " + sys.argv[0] + " <mooshost> <moosport>"
        exit(1)

    def printJoy(type):
        print "Found joystick:", type


    pygame.init()

    try:
        print "Finding joystick...",
        joystick = Joystick.Factory(pygame.joystick.Joystick(0), printJoy)
    except:
        print("No Joystick, exiting")
            

    j = JoystickApp(sys.argv[1], int(sys.argv[2]), joystick)
    j.MainLoop()

