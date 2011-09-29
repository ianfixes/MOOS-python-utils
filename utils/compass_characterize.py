#!/usr/bin/env python
###########################################################################
#    
#    Written in 2010 by Ian Katz <ijk5@mit.edu>         
#    Terms: WTFPL (http://sam.zoy.org/wtfpl/) 
#           See COPYING and WARRANTY files included in this distribution
#
###########################################################################

###
#
# note from Ian: 
# 
# this program reads a mysql database of missions and characterizes the
#  compass (INS_HEADING) error by comparing it to headings calculated from 
#  GPS.  in other words, use this with surface missions ONLY.  the output
#  is average error vs degree, with a count of how many points are in the 
#  average.
#  
# typical use of this program: compass_characterize.py < input > output.csv
#
###


   
import sys, os, time 
import math, numpy, scipy, scipy.interpolate
import MySQLdb

#put together a var-retrieval query
def get_query(mission_id, var):
    return """
        select elapsed_time, value 
        from app_data 
        where mission_id = %d 
          and varname='%s' 
        order by elapsed_time asc""" % (mission_id, var)

#get an array of (time, val)
def get_dataset(db, mission_id, var):
    sys.stderr.write("Getting %s from mission %d..." % (var, mission_id))
    c = db.cursor()
    c.execute(get_query(mission_id, var))
    results = c.fetchall()
    c.close()
    sys.stderr.write("Done\n")
    
    return results

#interpolate points.  we cache the matrix of values that get used for the spline
interp_cache = {}
def my_interp(val, xset, yset):
    #return numdpy.interp(val, xset, yset)
    if (xset, yset) in interp_cache:
        tck = interp_cache[(xset, yset)]
    else:
        tck = scipy.interpolate.splrep(xset, yset, s=0)
        interp_cache[(xset, yset)] = tck

    return scipy.interpolate.splev(val, tck, der=0)  

def rad2deg(angle):
    return angle * 180 / math.pi

        
def my_atan2(y, x):
    return ((rad2deg(math.atan2(x, y)) + 180) % 360) - 180
        

#calculate angles from gps and dvl
def make_angles(db, mission_id, stepsize):
    def sgn(a):
        if a == 0: return 0
        if a > 0:  return 1
        return -1

    def normalize(angle):
        return ((270 - angle) % 360) - 180

    #get all lines... 
    heading_set = get_dataset(db, mission_id, "INS_HEADING")
    gps_x_set   = get_dataset(db, mission_id, "GPS_X")
    gps_y_set   = get_dataset(db, mission_id, "GPS_Y")


    #split into x/y
    head_time, heading  = zip(*heading_set)
    gps_xtime, gps_x    = zip(*gps_x_set)
    gps_ytime, gps_y    = zip(*gps_y_set)


    #get maxes and mins
    max_time_gps_x  = gps_xtime[-1:][0]
    max_time_gps_y  = gps_ytime[-1:][0]
    max_time = min(max_time_gps_x, max_time_gps_y) - stepsize

    (min_time1, initial_x) = gps_x_set[0]
    (min_time2, initial_y) = gps_y_set[0]
    min_time = max(min_time1, min_time2)

    #set initial conditions for while loop
    time_count = min_time
    current_x = initial_x
    current_y = initial_y
    out = []
    doneflag = True
    
    #calculate directions from GPS and pair with INS heading
    while True:
        if time_count > max_time:
            break

        #progress to stderr
        doneness = round(time_count / max_time * 100.0, 1)
        if (math.floor(doneness) == doneness):
            if doneflag:
                sys.stderr.write("Processing points: %02d%%\n" % math.floor(doneness))
                doneflag = False
        else:
            doneflag = True


        #pick up the next locations
        next_time  = time_count + stepsize
        next_x     = my_interp(next_time, gps_xtime, gps_x)
        next_y     = my_interp(next_time, gps_ytime, gps_y)

        #calculate delta distances
        dy = next_y - current_y
        dx = next_x - current_x

        #calculate headings
        ins_heading = my_interp(time_count, head_time, heading)
        gps_heading = my_atan2(dy, dx)

        #move the INS value within the range of GPS value
        if 180 <= abs(ins_heading - gps_heading):
            if ins_heading < gps_heading:
                ins_heading = ins_heading + 360
            else:
                ins_heading = ins_heading - 360


        #add to output array
        out.append((gps_heading, ins_heading))

        #values for next iteration
        current_x   = next_x
        current_y   = next_y
        time_count  = next_time
          

    #create initial dict of output degrees
    degs = {}    
    for r in range(-180, 181):
        degs[r] = (0, 0)


    #build error averages
    for gps, ins in out:
        key = int(round(gps, 0))
        
        #average, count become newaverage, newcount
        (a, c) = degs[key]
        newc = c + 1
        newa = ((c * a) + (ins - gps)) / newc

        degs[key] = (newa, newc)

    #calculate average error
    tot_err = 0
    avg_err = 0
    for d, (a, _) in degs.iteritems():
        tot_err = tot_err + a - d

    avg_err = tot_err / len(degs)

    print "\nHeading,Error, Num_pts"
    k = degs.keys()
    k.sort()
    for d in k:
        (a, c) = degs[d]
        print d, ",", (a - avg_err), ",", c
        


def DoAwesome():
    #solicit db information, mission id from user

    db = MySQLdb.Connection(
        host    = raw_input("DB host: "),
        db      = raw_input("DB name: "),
        user    = raw_input("DB user: "),
        passwd  = raw_input("DB pass: "),
        )

    mission_id = int(raw_input("Mission ID: "))

    make_angles(db, mission_id, 0.2)



if __name__ == "__main__":
    DoAwesome()
