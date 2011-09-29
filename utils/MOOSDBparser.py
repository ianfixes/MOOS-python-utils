#!/usr/bin/env python
###########################################################################
#    
#    Written in 2009 by Ian Katz <ijk5@mit.edu>         
#    Terms: WTFPL (http://sam.zoy.org/wtfpl/) 
#           See COPYING and WARRANTY files included in this distribution
#
###########################################################################

# this function turns HTML from the MOOS HTTP server into a key/val dict

import re
from BeautifulSoup import BeautifulSoup
from urlgrabber.grabber import URLGrabber


def moosWeb2dict(vehicle_host, vehicle_port):

    def moosHTML2dict(data):
        soup = BeautifulSoup(data)
        istrtd = (lambda tag : tag.name == "tr" and len(tag.findAll("td")) > 0)
        ret = {}
        for tr in soup.table.table.findAll(istrtd):
            tds = tr.findAll("td")
            vartag = tds[0].a
            if 0 < len(vartag) and "pending" != tds[2].contents[0]:
                key = vartag.contents[0]
                val = tds[6].contents[0]
                ret[str(key)] = str(val)
        return ret


    UG = URLGrabber()

    #fetch new page
    data = UG.urlread("http://" + remote_vehicle + ":" + str(vehicle_port))

    #paul newman writes shitty HTML; we must fix it
    p = re.compile('<A href = ([^>]*)>')
    fixed_data = p.sub(r'<A href="\1">', data)
                
    return moosHTML2dict(fixed_data)

