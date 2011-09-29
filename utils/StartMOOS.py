#!/usr/bin/env python
###########################################################################
#    
#    Written in 2009 by Ian Katz <ijk5@mit.edu>         
#    Terms: WTFPL (http://sam.zoy.org/wtfpl/) 
#           See COPYING and WARRANTY files included in this distribution
#
###########################################################################

# this program launches MOOS processes and verifies that they're up.
#  this sequential launch method is gentler to low-horsepower CPUs.
#
# It takes 2 command line arguments:
#  1. the MOOS config file to be used
#  2. OPTIONALLY the working directory that all apps should launch from


import os
import sys
import time

#MAKE ANY CHANGES HERE
def desired_MOOS_procs():    
    #The app name, and -- optionally -- its ID string.  
    # use a comma in the tupleeither way
    return [
        ("pMOOSBridge",),
        ("iBatterySG", "Battery"),
        ("iDepth",),
        ("pSystemHealth", "pSystemHealth[oiv]"),
        ("iDVL_SG","iDVL"),
        ("iINS_SG","iINS",),
        ("iGPS_SG", "iGPS"),
        ("iRange",),
        ("iMultisonde", "CTD"),
        ("iActuationSG", "Thrusters"),
        ("iMotor", "RTU"),
#        ("pLogMySQL",),
        ("pNav",),
        ("pHelmSG","pHelm"),
        ]
    

def tick():
    sys.stdout.write(".")
    sys.stdout.flush()
    time.sleep(0.2)

def start_MOOS_process_in_new_screen(app_name, config_file, app_id_string=None):
    
    #start in "detatched mode" using a string identifier
    command_line = "screen -dmS "
    
    if(app_id_string is None):
        command_line += app_name
    else:
        command_line += app_id_string
    
    command_line += " " + app_name + " " + config_file
    
    if(app_id_string is not None):
        command_line += " " + app_id_string

    #print command_line
    return os.system(command_line)


def start_all_MOOSProcesses(process_list, config_file, time_between_starts=2.0):
    import time    for p in process_list:
                
        appname = p[0]
        args = (appname, config_file)
        if len(p) > 1:
            appname = p[1]
            args = args + (p[1],)

        print "Starting", appname.ljust(20), "in new screen...",
        start_MOOS_process_in_new_screen(*args)
        print "OK"
        time.sleep(time_between_starts)


def start_MOOS_processes_sequentially(process_list, config_file, moosComms):

    #get mail from the server manually    
    def FetchClients():
        inbox = pyMOOS.MOOSMSG_LIST()
        
        if not moosComms.Fetch(inbox):
            return None

        #go through all messages and put them in the local cache
        iter = inbox.iterator()
        try:
            while 1:
                msg = iter.next()
                varname = msg.GetKey()
                if varname == "DB_CLIENTS":
                    return msg.GetString()
        except StopIteration:
            return 0

    #find out if we successfully fetched
    def FetchSuccess(result):
        if result == None: #fetch error
            return False
        if result == 0:    #message DNE
            return False
        return True

    
    print "Registering for DB_CLIENTS...",
    moosComms.Register("DB_CLIENTS", 0.2)

    #wait for registration confirmation
    while not FetchSuccess(FetchClients()):
        tick()
    
    print "Done!"

    for p in process_list:
        
        appname = p[0]
        args = (appname, config_file)
        if len(p) > 1:
            appname = p[1]
            args = args + (p[1],)

        print "Starting", appname.ljust(20, "."), 
        start_MOOS_process_in_new_screen(*args)
        while True:
            tick()
            clientstring = FetchClients()
            if FetchSuccess(clientstring):
                clientset = set(clientstring.split(","))
                if appname in clientset:
                    break
        print "Done!"

    print "Unregistering...",
    moosComms.UnRegister("DB_CLIENTS")
    print "Done!"



        
if __name__ == "__main__":


    if len(sys.argv) < 2:
        print "Usage: " + sys.argv[0] + "<MOOS config file name> [working directory]"

        exit(1)

    
    #The app name, and -- optionally -- its ID string
    moosProcList = desired_MOOS_procs()

    moosConfigFile = sys.argv[1]

    if len(sys.argv) == 3:
         #we want to run all processes in this directory
        os.chdir(sys.argv[2])



    print "Starting MOOSDB...",
    start_MOOS_process_in_new_screen("MOOSDB", moosConfigFile)

    
    #see if we can use pyMOOS to intelligently launch processes
    try:
        import pyMOOS
        pi = pyMOOS.PI # force an error
    except:
        #fall back on basic implementation
        print "Done"
        print "\nNo pyMOOS detected... falling back on timed launch sequence\n"
        start_all_MOOSProcesses(moosProcList, moosConfigFile, 5.0)
        exit(0)


    #wait for connect
    myComms = pyMOOS.CMOOSCommClient()
    if myComms.Run("localhost", 9000, "StartMOOS.py[" + os.uname()[1] + "]"):
        print "Done!"
        print "\n\nStarting MOOS processes the SCHMANCY way!\n"
    else:
        print "Failed to connect to local MOOSDB."
        print "You may want to 'killall screen' and try again."
        exit(1)




    print "Connecting to MOOSDB...",
    while not myComms.IsConnected():
        tick()

    print "Done!"


    #start each process and wait for it to connect
    start_MOOS_processes_sequentially(moosProcList, moosConfigFile, myComms)

    print "\nAll MOOS processes successfully launched!"
