#!/usr/bin/env python
###########################################################################
#    
#    Written in 2009 by Ian Katz <ijk5@mit.edu>         
#    Terms: WTFPL (http://sam.zoy.org/wtfpl/) 
#           See COPYING and WARRANTY files included in this distribution
#
###########################################################################

# this program provides an audible alert for any change in the 
#  connected/disconnected state of a named host
#
# It takes 2 command line arguments:
#  1. the hostname/IP
#  2. the name to be spoken by the program as up/down

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



class PingMonitor(object):

    
    def __init__(self):
        pass

    def main(self, remote_ip, name):
        self.remote_ip = remote_ip
        self.name = name

        #flags, states, and counters
        self.laststate = True
        self.i = 0
        
        # main mega loop
        while (True):
            is_up = ping(self.remote_ip)
            print remote_ip, self.i, "state is", is_up
    
            if not is_up:
                self.processDown()
            else: #OH GOOD
                self.processUp()

            self.laststate = is_up
            self.i = self.i + 1


    def processDown(self):
        #alerts for various moments; just a dip in the wave, or a submerge?
        if (self.laststate):
            say(self.name + " is down")

    def processUp(self):
        if not self.laststate:
            say(self.name + " is up")


######################################################################3
#run it

if __name__ == "__main__":

    if len(sys.argv) != 3:
        print "Usage: " + sys.argv[0] + "<IP> <name>"

        exit(1)

    monitor = PingMonitor()

    monitor.main(sys.argv[1], sys.argv[2])
    print "\n\n\nexited cleanly!\n\n"
