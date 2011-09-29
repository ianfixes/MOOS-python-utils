#!/usr/bin/env python
###########################################################################
#    
#    Written in 2010 by Ian Katz <ijk5@mit.edu>         
#    Terms: WTFPL (http://sam.zoy.org/wtfpl/) 
#           See COPYING and WARRANTY files included in this distribution
#
###########################################################################

# This program attempts to announce vehicle status by reading MOOS 
#  variables and contacting the remote freewave radio modem.
#
# The program takes 3 command line arguments:
#  1. the hostname/IP of the remote freewave modem
#  2. the host of the local (topside) MOOSDB
#  3. the port of the local (topside) MOOSDB
#
# Although it is possible to connect to the remote MOOSDB (on the vehicle),
#  don't.  Learn pMOOSBridge.
#
# For a list of variables to send from the vehicle to topside 
#  via pMOOSBrige, see subscriptionsNeeded

###
#
# note from Ian: 
#
# these spoken phrases were crafted carefully to make good use of the
# digital voice (i.e., not sound too cheesy).  each voice needs its own
# slight tweak of wording to minimize odd-sounding speech.  this script
# was verbally optimized for "voice_nitech_us_slt_arctic_hts".
# 
#
# i installed a bunch of voices as per
#    http://ubuntuforums.org/showthread.php?t=751169
#
# a script called install-speech-software.sh is provided
#  for your convenience
# 
# this is my /etc/festival.scm
#
# (Parameter.set 'Audio_Method 'esdaudio)
# (set! voice_default 'voice_rab_diphone)
# (set! voice_default 'voice_nitech_us_rms_arctic_hts)
# (set! voice_default 'voice_nitech_us_clb_arctic_hts)
# (set! voice_default 'voice_nitech_us_slt_arctic_hts)
#
###



import sys
import os
import subprocess
import time
import pyMOOS

STATE_STARTED = 0
STATE_TIMEOUT = 1
STATE_STOPPED = 2

# simple ping
def ping(ip):
    """pings IP"""
    return 0 == subprocess.call("ping -c 1 -W 1 %s" % ip,
                                shell=True,
                                stdout=open('/dev/null', 'w'),
                                stderr=subprocess.STDOUT)

# use the big boy words... text to speech!
def say(things):
    print time.strftime("%H:%M:%S"), things
    """Speaks words"""
    subprocess.call("echo %s | festival --tts " % things,
                    shell=True,
                    stdout=open('/dev/null', 'w'),
                    stderr=subprocess.STDOUT)



class DiveOfficer(object):

    
    def __init__(self):
        self.comms = None


    def needUpdate(self):
        return self.need_batteryupdate or 0 < self.need_gpsupdate

    # try to infer the mission state
    def determineState(self):
        if "ALLDONE" == self.moosvars["DESIRED_YAW_TASK"]:
            print "\tstate is TIMEOUT"
            return STATE_TIMEOUT

        if "TRUE" == self.moosvars["MOOS_MANUAL_OVERIDE"]:
            print "\tstate is STOP"
            return STATE_STOPPED

        print "\tstate is STARTED"
        return STATE_STARTED



    def main(self, remote_freewave, local_moosdb_host, local_moosdb_port):
        self.remote_freewave = remote_freewave
        self.local_moosdb_host = local_moosdb_host
        self.local_moosdb_port = local_moosdb_port

        #flags, states, and counters
        self.i = 0
        self.was_down = 61 #so we assume down
        self.need_init = True
        self.need_subscribe = True
        self.need_batteryupdate = False
        self.need_gpsupdate = 0
        
        self.moosvars = {}

        say("Dive officer on line")
        #say("on")

        self.comms = pyMOOS.CMOOSCommClient()
        self.comms.Run(self.local_moosdb_host, 
                       local_moosdb_port, 
                       "DiveOfficer[" + os.uname()[1] + "]", 1)

        while not self.comms.IsConnected():
            print "Waiting for connect"
            time.sleep(0.5)
        
        print "Registering for:"
        for v in self.subscriptionsNeeded():
            print "\t", v, "\t", self.comms.Register(v, 0.5)

        time.sleep(1)
        self.processFetch()
        self.last_mission_state = None #self.determineState()

        #clear out junk vars
        #time.sleep(1)
        #self.processFetch()


        # main mega loop
        while (True):
            print "\n", self.i
            is_down = not ping(remote_freewave)
            print "\t", remote_freewave, "state is", (not is_down)
    
            if is_down:
                self.processDown()
            else: #OH GOOD
                self.processUp()

            self.i = self.i + 1


    def subscriptionsNeeded(self):
        ret = []
        ret.append("BATTERY_VOLTAGES")
        ret.append("GPS_SAT")
        ret.append("MOOS_MANUAL_OVERIDE")
        ret.append("DESIRED_YAW_TASK")

        return ret


    def processFetch(self):
        inbox = pyMOOS.MOOSMSG_LIST()

        if self.comms.IsConnected() and self.comms.Fetch(inbox):
            for mail in inbox:
                key = mail.GetKey()
                if mail.IsString():
                    self.moosvars[key] = mail.m_sVal
                else:
                    self.moosvars[key] = mail.m_dfVal


    def processDown(self):
        #set flags
        self.was_down = self.was_down + 1
        
        #alerts for various moments; just a dip in the wave, or a submerge?
        if (self.was_down == 5):
            say("oops")
        if (self.was_down == 15):
            say("no signal")

    def processUp(self):
        if self.need_init:
            self.need_init = False

        #hack to get the override state in each iteration
        newvars = {}
        if "MOOS_MANUAL_OVERIDE" in self.moosvars:
            newvars["MOOS_MANUAL_OVERIDE"] = self.moosvars["MOOS_MANUAL_OVERIDE"]

        if "DESIRED_YAW_TASK" in self.moosvars:
            newvars["DESIRED_YAW_TASK"] = self.moosvars["DESIRED_YAW_TASK"]

        self.moosvars = newvars
        self.processFetch()
        print "\t", self.moosvars

        if self.was_down >= 15:
            say("radio contact")

        #detailed report if we have been down for a while
        if self.was_down > 60:
            self.need_batteryupdate = True
            self.need_gpsupdate = 3


        #check mission status
        if self.canMissionupdate():
            mission_state = self.determineState()

            if self.last_mission_state != mission_state:
                if STATE_TIMEOUT == mission_state:
                    say("mission timed out")
                elif STATE_STOPPED == mission_state:
                    say("mission stopped")
                elif STATE_STARTED == mission_state:
                    say("mission under way")
                
            self.last_mission_state = mission_state

        #check battery
        if self.canBatteryupdate():
            mincell = self.getMinCell(self.moosvars["BATTERY_VOLTAGES"])
            if not self.need_batteryupdate:
                print "\tMin cell is", mincell
            else:
                say("min cell " + mincell)
                self.need_batteryupdate = False

        #check GPS
        if 0 < self.need_gpsupdate and self.canGpsupdate():
            sats = int(self.moosvars["GPS_SAT"])
            
            # vehicle surfaces thinking that it has GPS... check 3 times to be sure
            if 0 >= sats:
                self.need_gpsupdate = 3
            else:
                if 3 < sats:
                    self.need_gpsupdate = self.need_gpsupdate - 1

                if 0 >= self.need_gpsupdate:
                    say("active gps with " + str(sats) + " satellites")


        self.was_down = 0
        time.sleep(1)

        
    def canMissionupdate(self):
        return "MOOS_MANUAL_OVERIDE" in self.moosvars and "DESIRED_YAW_TASK" in self.moosvars

    def canBatteryupdate(self):
        return "BATTERY_VOLTAGES" in self.moosvars

    def canGpsupdate(self):
        return "GPS_SAT" in self.moosvars

    def getMinCell(self, cells):
        voltstrs = cells.split(" ")
        bs = {}
        for v in voltstrs:
            bs[v] = float(v)

        min = 10
        ret = ""
        for v, val in bs.iteritems():
            if 0.0 < val and val < min:
                min = val
                ret = v
        return ret

######################################################################3
#run it

if __name__ == "__main__":

    if len(sys.argv) != 4:
        print "\nUsage: " + sys.argv[0] + \
            " <Remote freewave hostname>" + \
            " <local MOOSDB host>" + \
            " <local MOOSDB port>\n"

        exit(1)

    officer = DiveOfficer()

    officer.main(sys.argv[1], sys.argv[2], sys.argv[3])
    print "\n\n\nexited cleanly!\n\n"
