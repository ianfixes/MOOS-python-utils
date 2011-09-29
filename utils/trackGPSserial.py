#!/usr/bin/env python
###########################################################################
#    
#    Written in 2010 by Ian Katz <ijk5@mit.edu>         
#    Terms: WTFPL (http://sam.zoy.org/wtfpl/) 
#           See COPYING and WARRANTY files included in this distribution
#
###########################################################################

# this program is meant to drive the AUV PlanIt web / Google Earth app
# it takes data from a serially-connected GPS and puts it in a MySQL db
#
# The program takes 4 command line arguments:
#  1. the serial port (in the form /dev/ttyXXX)
#  2. the baud rate
#  3. the mysql db connection string
#  4. the entity ID corresponding to the icon in AUV PlanIt


import os
import sys
import time
import serial
import subprocess
import traceback
import MySQLdb


def parseGPS(line):
    (cmd, _, data) = line.partition(",")
    return (cmd, data)

def parseGPScmd((cmd, data)):

    #turn GPS-formatted degree measurements into decimal
    def realdegrees(degmin, direction):

        #determine if we have 2 or 3 digits for the degrees
        if "E" == direction or "W" == direction:
            digits = 3
        else:
            digits = 2

        deg = degmin[0:digits]
        min = degmin[digits:]

        #this will fail if inputs are bad
        ret = float(deg) + (float(min) / 60.)

        #calculate sign
        if "S" == direction or "W" == direction:
            ret = ret * -1

        return ret

    #make the input useful
    fields = data.split(",")

    ret = {}

    if   "$GPRMC" == cmd:
        if "A" == fields[1]:
            ret["latitude"] = realdegrees(fields[2], fields[3])
            ret["longitude"] = realdegrees(fields[4], fields[5])
    elif "$GPGGA" == cmd:
        if "0" != fields[5]:
            ret["latitude"] = realdegrees(fields[1], fields[2])
            ret["longitude"] = realdegrees(fields[3], fields[4])
    elif "$GPGSA" == cmd:
        ret["fix"] = fields[1]
    elif "$GPGSV" == cmd:
        ret["satellites"] = fields[2]
    elif "$GPGLL" == cmd:
        if "A" == fields[5]:
            ret["latitude"] = realdegrees(fields[0], fields[1])
            ret["longitude"] = realdegrees(fields[2], fields[3])
    elif "$HCHDG" == cmd:
        ret["heading"] = float(fields[0])

    return ret


class trackGPSserial(object):

    class ExitFromUser(Exception):
        pass

    def __init__(self):
        self.maxlen = 0


    def main(self, serialport, db, entity_id):

        self.comm = serialport
        self.db = db
        self.entity_id = entity_id

        #readline & parse from serial port until we get a repeat command
        self.gps_output = []
        self.gps_data = {}


        c = self.db.cursor()
        c.execute("select name from entity where entity_id=%d" % self.entity_id)
        self.entity_name = c.fetchall()[0][0]
        c.close()

        while(True):
            try:
                if self.run():
                    return
            except(KeyboardInterrupt):
                return


    def run(self):
        
        #do something serial porty
            
        #foreach GPS command we expect to get
        # readline()
        # parse line, add vars to overall extracted data
        # print extracted data to screen
        # write vars to database
            
        self.gps_data = {}
        self.gps_output = []

        try:
            self.gps_output = self.comm.readlines()

            for line in self.gps_output:
                parsed = parseGPScmd(parseGPS(line))

                for label, data in parseGPScmd(parseGPS(line)).items():
                    self.gps_data[label] = data
        except(KeyboardInterrupt):
            return True
        except:
            pass

        #write vars in database
        if ("fix" in self.gps_data 
            and 1 < self.gps_data["fix"] 
            and "latitude" in self.gps_data
            and "longitude" in self.gps_data):

            print "Lat =", self.gps_data["latitude"], "\t"
            print "Lon =", self.gps_data["longitude"], "\t"
                
            c = self.db.cursor()

            if "heading" in self.gps_data:
                print "Hed =", self.gps_data["heading"],
                q = "insert into entity_location(entity_id, lat, lng, heading) values(%d, %f, %f, %f)"
                c.execute(q % (self.entity_id, 
                               self.gps_data["latitude"], 
                               self.gps_data["longitude"], 
                               self.gps_data["heading"])
                          )

            else:
                q = "insert into entity_location(entity_id, lat, lng) values(%d, %f, %f)"
                c.execute(q % (self.entity_id, 
                               self.gps_data["latitude"], 
                               self.gps_data["longitude"])
                          )
                    
            c.close()

            print "\n\n"

        return False
            

# for the GPS program, we are going to need an entity ID, a serial port, and a baud rate
if len(sys.argv) != 5:
    print "Usage: " + sys.argv[0] + " <serial port> <baud> <db connection str> <entity #>"
    print "    <serial port> is in the form /dev/ttyXXX"
    print "    <db connection str> is in the form mysql://user:pass@host/db"
    exit(1)
    
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



serialport = serial.Serial()
serialport.portstr  = sys.argv[1]
serialport.baudrate = int(sys.argv[2])
serialport.timeout  = 0.25
print serialport

serialport.port = serialport.portstr
serialport.baud = serialport.baudrate

serialport.open()

tGS = trackGPSserial()


tGS.main(serialport, db, int(sys.argv[4]))
serialport.close()
print "\n\n\nexited cleanly!\n\n"
