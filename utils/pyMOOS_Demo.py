#!/usr/bin/env python
###########################################################################
#    
#    Written in 2009 by Ian Katz <ijk5@mit.edu>         
#    Terms: WTFPL (http://sam.zoy.org/wtfpl/) 
#           See COPYING and WARRANTY files included in this distribution
#
###########################################################################

# this is a brief example of how to use the pyMOOS library
#
# The program takes 2 command line arguments:
#  1. the host of the MOOSDB
#  2. the port of the MOOSDB
#


import pyMOOS, time, sys

def MainLoop(host, port):

    # instantiate a new Comm Client object
    comms = pyMOOS.CMOOSCommClient()

    # open a connection to the server & start the mail thread
    # (server hostname, port, your app name, mail frequency)
    if not comms.Run(host, port, "DemoApp", 5):
        return

    while not comms.IsConnected():
        print("Waiting for connect")
        time.sleep(5)

    # Register for a variable (variable name, frequency)
    comms.Register("DB_TIME", 0.5)

    # Create our inbox
    inbox = pyMOOS.MOOSMSG_LIST()

    # Now, Loop
    try:
        while(True):
            print "Checking mail...",
            # Fetch New Mail
            if not comms.Fetch(inbox):
                print "FAIL"
            else:
                print "OK"
                for mail in inbox:
                    print "Got Message: ",
                    # here's how you access string vs. numeric data:
                    if mail.IsString():
                        print mail.m_sVal
                    else:
                        print mail.m_dfVal
            
            # Let's post a value as well (variable_name, value (numeric or string) [, time])
            comms.Notify("TEST_VAR", "HelloWorld", pyMOOS.MOOSTime())

            # pause for a moment
            print "Pause...",
            time.sleep(1)
            print "done"

    except(KeyboardInterrupt):
        # No need to explicitly close, in destructor of comms client.
        print "interrupted by user, quitting"
        return

if __name__ == "__main__":
    
    if len(sys.argv) != 3:
        print "Usage: " + sys.argv[0] + " <MOOSDB hostname> <MOOSDB TCP/IP port>"
        exit(1)

        MainLoop(sys.argv[1], sys.argv[2])
