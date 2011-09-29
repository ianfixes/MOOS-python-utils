#!/usr/bin/env python
###########################################################################
#    
#    Written in 2010 by Ian Katz <ijk5@mit.edu>         
#    Terms: WTFPL (http://sam.zoy.org/wtfpl/) 
#           See COPYING and WARRANTY files included in this distribution
#
###########################################################################

# this program is meant to drive the AUV PlanIt web / Google Earth app
# it takes GPS data from a MOOS DB and puts it in a MySQL db
#
# The program takes 4 command line arguments:
#  1. the host of the MOOSDB
#  2. the port of the MOOSDB
#  3. the entity ID corresponding to the icon in AUV PlanIt
#  4. the mysql db connection string

import os
import sys
import time
import traceback
import MySQLdb
import random
import pyMOOS

class fakedb(object):
    def execute(self, q):
        print q

    def close(self):
        pass

class trackGPSmoos(object):

    def __init__(self):
        self.relevant_data = {}

        # instantiate a new Comm Client object
        self.comms = pyMOOS.CMOOSCommClient()


    def main(self, mooshost, moosport, db, entity_id):

        self.db = db
        self.entity_id = entity_id
        self.mooshost = mooshost
        self.moosport = moosport

        #readline & parse from serial port until we get a repeat command
        self.moos_output = {}
        self.debug_output = "debug output goes here"

        c = self.db.cursor()
        c.execute("select name from entity where entity_id=%d" % self.entity_id)
        self.entity_name = c.fetchall()[0][0]
        c.close()

        print "Going to track", self.entity_name

        # open a connection to the server & start the mail thread
        # (server hostname, port, your app name, mail frequency)
        if not self.comms.Run(mooshost, moosport, "TopsideTracker[" + os.uname()[1] + "]", 1):
            print "Could not run the MOOS comms client.... so quitting"
            return


        #while not self.comms.IsConnected():
        #    print "Waiting for initial connect"
        #    time.sleep(1)


        # Register for a variable (variable name, frequency)
        self.relevant_data = ["GPS_SAT", "GPS_LAT", "GPS_LON", "INS_HEADING"]

        #for k in self.relevant_data:
        #    self.comms.Register(k, 0.5)
        self.need_reregister = True

        while True:

            # if not connected, wait for connect
            if not self.comms.IsConnected():
                print "Waiting for reconnect"
                self.need_reregister = True
                time.sleep(1)
            else:
                if self.need_reregister:
                    print "Reregistering:"
                    for k in self.relevant_data:
                        print "  ", k, self.comms.UnRegister(k), ",", self.comms.Register(k, 0.5)
                    self.need_reregister = False
                print "Iteration!"

                try:
                    self.moos2mysql()
                    time.sleep(3)
                except(KeyboardInterrupt):
                    return


    def moos2mysql(self):
        # fetch db
        # print extracted data to screen
        # write vars to database
            
        self.moos_output = {}

        inbox = pyMOOS.MOOSMSG_LIST()

        print "Checking mail...",
        # Fetch New Mail
        if not self.comms.Fetch(inbox):
            print "FAIL"
            return
        else:
            print "OK"
            for mail in inbox:
                key = mail.GetKey()
                if mail.IsString():
                    self.moos_output[key] = mail.m_sVal
                else:
                    self.moos_output[key] = mail.m_dfVal


        #write vars in database
        if ("GPS_SAT" in self.moos_output 
            and float(self.moos_output["GPS_SAT"]) >= 3
            and "GPS_LAT" in self.moos_output
            and "GPS_LON" in self.moos_output
            ):

            self.doInsert()
        elif "GPS_SAT" in self.moos_output and 3 <= float(self.moos_output["GPS_SAT"]):
            self.need_reregister = True
        else:
            print "insufficient data for insert\n    ",
            print self.moos_output


    def doInsert(self):
        
        c = self.db.cursor()
        #c = fakedb()

        if "INS_HEADING" in self.moos_output and "pending" != self.moos_output["INS_HEADING"]:
            q = "insert into entity_location(entity_id, lat, lng, heading) values(%d, %f, %f, %f)"
            c.execute(q % (self.entity_id, 
                           float(self.moos_output["GPS_LAT"]), 
                           float(self.moos_output["GPS_LON"]), 
                           float(self.moos_output["INS_HEADING"]))
                      )
            
        else:
            q = "insert into entity_location(entity_id, lat, lng) values(%d, %f, %f)"
            c.execute(q % (self.entity_id, 
                           float(self.moos_output["GPS_LAT"]), 
                           float(self.moos_output["GPS_LON"]))
                      )

            c.close()
            


if __name__ == "__main__":

    if len(sys.argv) != 5:
        print "Usage: " + sys.argv[0] + " <mooshost> <moosport> <db connection str> <entity #>"
        print "    <db connection str> is in the form mysql://user:pass@host/db"
        exit(1)

    for arg in sys.argv:
        print "arg is", arg
    
    (_, __, tmp1) = sys.argv[3].partition("://")
    (tmp1, _, tmp2) = tmp1.partition("@")
    
    (db_user, _, db_pass) = tmp1.partition(":")
    (db_host, _, db_name) = tmp2.partition("/")
    db = MySQLdb.Connection(
        host    = db_host,
        db      = db_name,
        user    = db_user,
        passwd  = db_pass,
        )

    tGS = trackGPSmoos()

    tGS.main(sys.argv[1], int(sys.argv[2]), db, int(sys.argv[4]))
    print "\n\n\nexited cleanly!\n\n"
