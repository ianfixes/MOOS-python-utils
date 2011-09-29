#!/usr/bin/env python
###########################################################################
#    
#    Written in 2009 by Ian Katz <ijk5@mit.edu>         
#    Terms: WTFPL (http://sam.zoy.org/wtfpl/) 
#           See COPYING and WARRANTY files included in this distribution
#
###########################################################################

#
#    iMS - ian's uMS clone in TEXTMODE :)
#
# The program takes 2 command line arguments:
#  1. the host of the MOOSDB
#  2. the port of the MOOSDB
#


import pyMOOS
import os
import sys
import time
import subprocess
import traceback
import urwid.curses_display
import urwid


class mDB(object):
    def __init__(self):

        self.MOOSDB_hostname = "localhost"
        self.MOOSDB_port = 9000

        self.DBVars = {}
        self.Comms = pyMOOS.CMOOSCommClient()
        self.ConsecutiveCommsFailures = 0


    def Activate(self, hostname, port):

        self.MOOSDB_hostname = hostname
        self.MOOSDB_port = port

        self.ConnectToDB()

        #self.GetAllMOOSVars()
        
    
    #set our desire to (un)subscribe to vars
    def SetSubscription(self, varname, wantsubscription):
        (subscribed, updated, thevalue) = self.DBVars[varname]

        if subscribed and not wantsubscription:
            print >>sys.stderr, "mDB unsubscribing from " + varname + "...",
            if self.Comms.UnRegister(varname):
                print >>sys.stderr, "unsubscribed :)"
            else:
                print >>sys.stderr, "FAIL"

        if not subscribed and wantsubscription:
            print >>sys.stderr, "mDB subscribing to " + varname + "...",
            if self.Comms.Register(varname, 0.2):
                print >>sys.stderr, "success"
            else:
                print >>sys.stderr, "FAIL"

        self.DBVars[varname] = (wantsubscription, updated, thevalue)

    #post some value to the DB
    def SetDBValue(self, varname, somevalue):
        if pyMOOS.MOOSIsNumeric(somevalue):
            somevalue = float(somevalue)
        self.Comms.Notify(varname, somevalue)


    #get mail from the server manually    
    def FetchMail(self):
        inbox = pyMOOS.MOOSMSG_LIST()
        
        if not self.Comms.Fetch(inbox):
            print >>sys.stderr, "Fetch Failed", time.asctime()
            self.ConsecutiveCommsFailures += 1
            if 0 == self.ConsecutiveCommsFailures % 15:
                print >>sys.stderr, "The Comms situation is unacceptable (~3 seconds), re-registering"
                self.Subscribe() 
            return

        #success in getting vars!
        self.ConsecutiveCommsFailures = 0

        self.ResetUpdateStatus()

        #go through all messages and put them in the local cache
        iter = inbox.iterator()
        try:
            while 1:
                msg = iter.next()
                varname = msg.GetKey()
                #print >>sys.stderr, "Fetched " + varname
                (sub, upd, oldmsg) = self.DBVars[varname]
                self.DBVars[varname] = (sub, True, msg)


        except StopIteration:
            pass

    def ResetUpdateStatus(self):
        for k, v in self.DBVars.items():
            (sub, upd, m) = v
            self.DBVars[k] = (sub, False, m)

    def GetVarList(self):
        return self.DBVars.keys()

    #get the list of variables that we've chosen to care about
    def GetMessages(self):
        d = self.DBVars
        #return dict([(k, d[k]) for (k, (sub, upd, msg)) in d.items() if sub])
        r = {}
        for k, v in d.items():
            (sub, upd, msg) = v
            if sub:
                r[k] = v

        return r

    def IsConnected(self):
        return self.Comms.IsConnected()

    ###### PRIVATE / PROTECTED stuff


    def ConnectToDB(self):
        if self.Comms.IsConnected():
            self.DisconnectFromDB()
            time.sleep(1)

        if not self.Comms.Run(self.MOOSDB_hostname, self.MOOSDB_port, "iMS[" + os.uname()[1] + "]"):
            print "Failed to connect to MOOSDB on ", self.MOOSDB_hostname, ":", self.MOOSDB_port            
            return False

        #time.sleep(1)
        #print "Connected to DB on", self.MOOSDB_hostname, ":", self.MOOSDB_port



    def DisconnectFromDB(self):
        print("Disconnecting from DB...")
        ret = self.Comms.Close()
        print "Closed?", ret
        self.DBVars = {}
        return ret
        


    def GetAllMOOSVars(self):
        mail = pyMOOS.MOOSMSG_LIST()
        if self.Comms.ServerRequest("VAR_SUMMARY", mail):
            varlist = mail[0].m_sVal.split(',')
            for v in varlist:
                if v != "" and v not in self.DBVars:
                    #create new tuple:
                    # whether we're subscribed, (false initially...) 
                    # whether the value has been updated
                    # the latest message
                    print >>sys.stderr, "Adding " + v + " to mDB.DBVars"
                    self.DBVars[v] = (False, False, None)
                    
                    #this will set "subscribed" to true
                    self.SetSubscription(v, True)



    #more like RE-subscribe... subscribe to everything we said we wanted
    def Subscribe(self):
        for varname, (subscribed, updated, thevalue) in self.DBVars.items():
            print >>sys.stderr, "Subscribing to ", varname, "...",
            if self.Comms.Register(varname, 0.2):
                print >>sys.stderr, "Success!"
            else:
                print >>sys.stderr, "FAIL"

        

        

class StateMachine(object):
    def __init__(self):
        self.state = None

    def Start(self, state):
        self.state = state

    def Iterate(self, event):
        self.state.HandleEvent(event)
        self.state = self.state.NextState(event)
 
    def CurrentState(self):
        return self.state.GetName()

    class State(object):
        def __init__(self, name = "unnamed state", default_action = None, default_transition_state = None):
            self.transitions = {}
            self.name = name
            self.default_action = lambda event_arg : ()
            self.default_transition_state = self

        def AddDefaults(self, default_action, default_transition_state):
            #default action takes 1 argument: the event.
            self.default_action = default_action
            self.default_transition_state = default_transition_state
            
        def AddTransition(self, event, action, nextstate):
            self.transitions[event] = (action, nextstate)
            
        def GetName(self):
            return self.name

        #PROTECTED STUFF ##############

        def HandleEvent(self, event):
            if not self.transitions.has_key(event):
                self.default_action(event)
            else:
                (action, nextstate) = self.transitions[event]
                #execute action if we have it
                if action:
                    action()


        def NextState(self, event):
            if not self.transitions.has_key(event):
                return self.default_transition_state
            else:
                (action, nextstate) = self.transitions[event]
                return nextstate
                    




class iMS(object):

    class ExitFromUser(Exception):
        pass



    def __init__(self):

        #hold the various variables of interest in their own pages
        self.pages = [[], [], [], [], [], [], [], [], [], [], []]
        self.current_page = 1
   
        #column and row (listbox) in focus
        self.focus_col = 0
        self.focus_row = 0
        self.screen_size = (0, 0)

        #for noticing when new vars have been added
        #for keeping track of val being edited
        self.master_varlist = {}

        #related to debug output
        self.logfile_path = None
        self.show_log = True
        self.override_log = False
        self.override_normalview = False

        self.states = []
        self.statemachine = self.MakeStateMachine()

        #we want to update the var list every so often... keep track of time
        self.time_ticks = 0



    def main(self, hostname, port, logfile_path):
        self.ui = urwid.curses_display.Screen()
        self.ui.register_palette([
                ("header",    "black", "dark cyan", "standout"),
                ("footer",    "black", "brown", "bold"),
                ("Cell",      "default", "default", "bold"),
                ("Cell grey", "dark gray", "default"),
                ("Cell upd",  "yellow", "default"),
                ])

        self.logfile_path = logfile_path

        print >>sys.stderr, "iMS Initializing local DB via MOOS Comm Client..."
        self.db = mDB()
        print >>sys.stderr, "Done\n"

        print >>sys.stderr, "iMS activating connection to DB\n"
        self.db.Activate(hostname, port)

        self.db.GetAllMOOSVars()

        self.MakeScreen("Startup")

        self.ui.run_wrapper(self.run)



    def run(self):
        self.screen_size = self.ui.get_cols_rows()
        
        while True:
            self.time_ticks += 1

            #pick up any new variables
            if 0 == len(self.master_varlist) or 0 == self.time_ticks % 50:
                self.db.GetAllMOOSVars()
                

            for v in self.db.GetVarList():
                #look for variables we don't know about yet
                if not self.master_varlist.has_key(v):
                    print >>sys.stderr, "Adding " + v + " to page 1"
                    #put on first virtual page, subscribe, indicate that we've seen it
                    self.pages[1] += [v]
                    self.master_varlist[v] = None 
                    self.db.SetSubscription(v, True)

            #fetch mail if connected, otherwise print to stderr to help user
            if self.db.IsConnected():
                self.db.FetchMail()
            else:
                print >>sys.stderr, "Waiting for DB connect..."
            self.draw_screen()

            #get input until user exits
            try:
                self.HandleKeys()
            except iMS.ExitFromUser:
                break


    def HandleKeys(self):

        keys = self.ui.get_input()
        

        #DEBUG INFORMATION REMOVEME WHEN FINISHED
        s = ""
        if 0 == len(keys):
            s = " *tick*"    
            for k in keys:
                s += "'" + k + "', "
            s += "size=" + str(self.screen_size[1] / 2)
                
        self.MakeScreen("")#"key=" + s)
                
        #precedence above all others
        if "ctrl w" in keys:
            self.user_exit()
        
        #handle other globals
        for k in keys:
            if k == "window resize":
                self.screen_size = self.ui.get_cols_rows()
            elif k == "crtl l":
                self.ui.s.clear() # refresh screen
                self.MakeScreen("key=ctrl l")
            else:
                #self.keypress(k) #non-globals
                if self.db.IsConnected():
                    self.statemachine.Iterate(k)
                    self.MakeScreen("")#"key=" + k + " State='" + self.statemachine.CurrentState() + "'")




    def MakeStateMachine(self):
        varlist = StateMachine.State("Var List")
        vallist = StateMachine.State("Value List")
        newvar  = StateMachine.State("New Variable")
        editval = StateMachine.State("Edit Value")

        #varlist.AddDefaults(lambda k: self.top.keypress(self.screen_size, k), varlist)

        def half():
            return self.screen_size[1] / 2
        
        #variable list
        #event, action, nextate
        varlist.AddTransition("up", lambda : self.movefocus_vertical(-1), varlist)
        varlist.AddTransition("down", lambda : self.movefocus_vertical(1), varlist)
        varlist.AddTransition("delete", self.dropvar, varlist)
        varlist.AddTransition("page up", lambda : self.movefocus_vertical(half() * -1), varlist)
        varlist.AddTransition("page down", lambda : self.movefocus_vertical(half()), varlist)
        varlist.AddTransition("home", lambda : self.movefocus_vertical(self.focus_row * -1), varlist)
        varlist.AddTransition("end", lambda : self.movefocus_vertical(len(self.pages[self.current_page])), varlist)
        varlist.AddTransition("k", lambda : self.swap(-1), varlist)
        varlist.AddTransition("j", lambda : self.swap(1), varlist)
        varlist.AddTransition("K", lambda : self.swap(half() * -1), varlist)
        varlist.AddTransition("J", lambda : self.swap(half()), varlist)
        varlist.AddTransition("meta up", lambda : self.swap(-1), varlist)
        varlist.AddTransition("meta down", lambda : self.swap(1), varlist)
        varlist.AddTransition("meta page up", lambda : self.swap(half() * -1), varlist)
        varlist.AddTransition("meta page down", lambda : self.swap(half()), varlist)
        varlist.AddTransition("tab", lambda : self.gotopage(((self.current_page) % 10) + 1), varlist)
        varlist.AddTransition("shift tab", lambda : self.gotopage(((self.current_page - 2) % 10) + 1), varlist)
        varlist.AddTransition("o", self.sort_current_page, varlist)
        varlist.AddTransition("1", lambda : self.gotopage(1), varlist)
        varlist.AddTransition("2", lambda : self.gotopage(2), varlist)
        varlist.AddTransition("3", lambda : self.gotopage(3), varlist)
        varlist.AddTransition("4", lambda : self.gotopage(4), varlist)
        varlist.AddTransition("5", lambda : self.gotopage(5), varlist)
        varlist.AddTransition("6", lambda : self.gotopage(6), varlist)
        varlist.AddTransition("7", lambda : self.gotopage(7), varlist)
        varlist.AddTransition("8", lambda : self.gotopage(8), varlist)
        varlist.AddTransition("9", lambda : self.gotopage(9), varlist)
        varlist.AddTransition("0", lambda : self.gotopage(10), varlist)
        varlist.AddTransition("d", lambda : self.gotopage(0), varlist)
        varlist.AddTransition("!", lambda : self.movevar(1), varlist)
        varlist.AddTransition("@", lambda : self.movevar(2), varlist)
        varlist.AddTransition("#", lambda : self.movevar(3), varlist)
        varlist.AddTransition("$", lambda : self.movevar(4), varlist)
        varlist.AddTransition("%", lambda : self.movevar(5), varlist)
        varlist.AddTransition("^", lambda : self.movevar(6), varlist)
        varlist.AddTransition("&", lambda : self.movevar(7), varlist)
        varlist.AddTransition("*", lambda : self.movevar(8), varlist)
        varlist.AddTransition("(", lambda : self.movevar(9), varlist)
        varlist.AddTransition(")", lambda : self.movevar(10), varlist)
        varlist.AddTransition("f", self.force_update, varlist)
        varlist.AddTransition("r", lambda : self.db.GetAllMOOSVars(), varlist)

        varlist.AddTransition("right", lambda : self.movefocus_horizontal(1), vallist)
        varlist.AddTransition("u", lambda : (self.movefocus_horizontal(1), self.startEdit()), editval)
        varlist.AddTransition("ctrl u", lambda : (self.movefocus_horizontal(1), self.startEdit()), editval)
        varlist.AddTransition("q", self.user_exit, None)

        #value list
        vallist.AddTransition("up", lambda : self.movefocus_vertical(-1), vallist)
        vallist.AddTransition("down", lambda : self.movefocus_vertical(1), vallist)
        vallist.AddTransition("delete", self.dropvar, vallist)
        vallist.AddTransition("page up", lambda : self.movefocus_vertical(half() * -1), vallist)
        vallist.AddTransition("page down", lambda : self.movefocus_vertical(half()), vallist)
        vallist.AddTransition("home", lambda : self.movefocus_vertical(self.focus_row * -1), vallist)
        vallist.AddTransition("end", lambda : self.movefocus_vertical(len(self.pages[self.current_page])), vallist)
        vallist.AddTransition("k", lambda : self.swap(-1), vallist)
        vallist.AddTransition("j", lambda : self.swap(1), vallist)
        vallist.AddTransition("K", lambda : self.swap(half() * -1), vallist)
        vallist.AddTransition("J", lambda : self.swap(half()), vallist)
        vallist.AddTransition("meta up", lambda : self.swap(-1), vallist)
        vallist.AddTransition("meta down", lambda : self.swap(1), vallist)
        vallist.AddTransition("meta page up", lambda : self.swap(half() * -1), vallist)
        vallist.AddTransition("meta page down", lambda : self.swap(half()), vallist)
        vallist.AddTransition("tab", lambda : self.gotopage(((self.current_page) % 10) + 1), vallist)
        vallist.AddTransition("shift tab", lambda : self.gotopage(((self.current_page - 2) % 10) + 1), vallist)
        vallist.AddTransition("1", lambda : self.gotopage(1), vallist)
        vallist.AddTransition("2", lambda : self.gotopage(2), vallist)
        vallist.AddTransition("3", lambda : self.gotopage(3), vallist)
        vallist.AddTransition("4", lambda : self.gotopage(4), vallist)
        vallist.AddTransition("5", lambda : self.gotopage(5), vallist)
        vallist.AddTransition("6", lambda : self.gotopage(6), vallist)
        vallist.AddTransition("7", lambda : self.gotopage(7), vallist)
        vallist.AddTransition("8", lambda : self.gotopage(8), vallist)
        vallist.AddTransition("9", lambda : self.gotopage(9), vallist)
        vallist.AddTransition("0", lambda : self.gotopage(10), vallist)
        vallist.AddTransition("d", lambda : (self.movefocus_horizontal(-1), self.gotopage(0)), vallist)
        vallist.AddTransition("!", lambda : self.movevar(1), vallist)
        vallist.AddTransition("@", lambda : self.movevar(2), vallist)
        vallist.AddTransition("#", lambda : self.movevar(3), vallist)
        vallist.AddTransition("$", lambda : self.movevar(4), vallist)
        vallist.AddTransition("%", lambda : self.movevar(5), vallist)
        vallist.AddTransition("^", lambda : self.movevar(6), vallist)
        vallist.AddTransition("&", lambda : self.movevar(7), vallist)
        vallist.AddTransition("*", lambda : self.movevar(8), vallist)
        vallist.AddTransition("(", lambda : self.movevar(9), vallist)
        vallist.AddTransition(")", lambda : self.movevar(10), vallist)
        vallist.AddTransition("f", self.force_update, vallist)
        vallist.AddTransition("r", lambda : self.db.GetAllMOOSVars(), vallist)

        vallist.AddTransition("left", lambda : self.movefocus_horizontal(-1), varlist)
        vallist.AddTransition("u", self.startEdit, editval)
        vallist.AddTransition("ctrl u", self.startEdit, editval)
        vallist.AddTransition("q", self.user_exit, None)

        #add new variable
        #newvar
        

        #edit value
        editval.AddDefaults(lambda k : self.top.keypress(self.screen_size, k), editval)

        editval.AddTransition("esc", self.stopEdit, vallist)
        editval.AddTransition("enter", lambda : (self.saveEdit(), self.stopEdit()), vallist)
        editval.AddTransition("ctrl u", self.clearEdit, editval) #compatiblity with readline's "clear"


        s = StateMachine()
        s.Start(varlist)

        self.states = [varlist, vallist]
        return s

    def MakeScreen(self, banner):
        msgs = self.db.GetMessages()
        msg_maxlen = self.ValColMaxWidth()

            
        def getValAndClass(varname, truncate):
            #"deleted" vars won't be in the message list, so print special message
            if not msgs.has_key(varname):
                return ("Cell grey", "<ignoring>")

            (sub, upd, msg) = msgs[varname]
    
            #default formatting
            if upd:
                c = "Cell upd"
            else:
                c = "Cell"

            #cell content
            if not msg:
                c = "Cell grey"
                s = "<not set>"

            elif msg.IsDouble():
                s = str(msg.GetDouble())

            else:
                s = msg.GetString()
                if truncate:
                    s = s.replace("\n", "")
                    s = s.replace("\r", "")
                    if len(s) > msg_maxlen:
                        s = s[:msg_maxlen]
            
            return (c, s)
            

        def getVal(varname, truncate):
            (foo, ret) = getValAndClass(varname, truncate)
            return ret


        
        def makeValBox(varname):
            if self.master_varlist[varname]:
                return self.master_varlist[varname]
            else:
                return urwid.Edit(getValAndClass(varname, True))
        
        
        #make the boxes for var names
        nameboxes = map(lambda x: urwid.Edit(("Cell", x)), self.pages[self.current_page])
        self.items_varnames = urwid.SimpleListWalker(nameboxes)

        #make the boxes for values
        editboxes = map(lambda x: makeValBox(x), self.pages[self.current_page])
        self.items_values = urwid.SimpleListWalker(editboxes)

        #create a listbox with items
        self.listbox_names = urwid.ListBox(self.items_varnames)
        self.listbox_vals  = urwid.ListBox(self.items_values)

        self.columns = urwid.Columns(
            [
                ('fixed',  self.VarColMinWidth(), self.listbox_names),
                ('weight', 1,                     self.listbox_vals),
                ], 
            dividechars=2, 
            focus_column=0)
 

        #create filler with log text
        logtext = tail_file(self.logfile_path, self.screen_size[1])
        txt = urwid.Text(logtext, align="left")
        
        #this might only work on text objects...
        self.fill_errlog = urwid.Filler(txt, valign="top")
        
        self.show_log = not self.db.IsConnected()

        #create header and frame
        instruct = urwid.Text("Press ctrl-w to quit " + banner)
        header = urwid.AttrWrap(instruct, 'header')

        if self.show_log:
            longmsg = urwid.Text("MOOSDB connection has dropped!  Reconnecting...")
            footer = urwid.AttrWrap(longmsg, 'footer')
            self.top = urwid.Frame(self.fill_errlog, header, footer)
        else:
            if 0 < len(self.pages[self.current_page]):
                longmsg = urwid.Text(getVal(self.pages[self.current_page][self.focus_row], False))
                footer = urwid.AttrWrap(longmsg, 'footer')
                self.top = urwid.Frame(self.columns, header, footer)
            else:
                self.top = urwid.Frame(self.columns, header)

            if 0 < len(self.pages[self.current_page]):
                #set the row of the unwanted column first (for scrolling purposes)
                if 0 == self.focus_col:
                    othercol = 1
                else:
                    othercol = 0
                self.columns.set_focus_column(othercol)
                self.columns.get_focus().set_focus(self.focus_row)
            
                #now set the actual focused column
                self.columns.set_focus_column(self.focus_col)
                self.columns.get_focus().set_focus(self.focus_row)
        

        
    #figure out what variable name is the longest
    def VarColMinWidth(self):
        #function to get the max length of a var name
        def maxlen (acc, x):
            return max(acc, len(x))

        #add 1 for cursor
        return reduce(maxlen, self.pages[self.current_page], 0) + 1


    #figure out the max size of a value string
    def ValColMaxWidth(self):
        (cols, rows) = self.screen_size
        return (cols - self.VarColMinWidth()) - 3
        
            

    def user_exit(self):
        raise iMS.ExitFromUser()

    def sort_current_page(self):
        varname = self.pages[self.current_page][self.focus_row]
        self.pages[self.current_page].sort()
        self.focus_row = self.pages[self.current_page].index(varname)

    def force_update(self):
        #no updates for deleted vars
        if self.current_page == 0:
            return

        varname = self.pages[self.current_page][self.focus_row]
        self.db.SetSubscription(varname, False)
        self.db.SetSubscription(varname, True)


    def startEdit(self):
        #create an editbox object and save it so that it persists across refreshes
        varname = self.pages[self.current_page][self.focus_row]
        newbox = urwid.Edit(("Cell grey", ">> "))

        newbox.set_edit_text(self.get_current_value(varname))

        self.master_varlist[varname] = newbox

    def saveEdit(self):
        varname = self.pages[self.current_page][self.focus_row]
        self.db.SetDBValue(varname, self.master_varlist[varname].get_edit_text())

    def stopEdit(self):
        varname = self.pages[self.current_page][self.focus_row]
        self.master_varlist[varname] = None

    def clearEdit(self):
        varname = self.pages[self.current_page][self.focus_row]
        self.master_varlist[varname].set_edit_text("")

    def get_current_value(self, varname):
        msgs = self.db.GetMessages()
        (sub, upd, msg) = msgs[varname]
        
        if not msg:
            return ""
        if not msg.IsDouble():
            return msg.GetString()
        #else
        return str(msg.GetDouble())


    #modify the order of the list
    def swap(self, offset):
        #get current position
        listbox = self.columns.get_focus()
        widget, pos = listbox.get_focus()

        p = self.current_page

        #range limit the offset
        if 0 < offset:
            maxitem = len(self.pages[p]) - 1
            start = 0
            stop = offset = min(maxitem - pos, offset)
            step = 1
        else:
            start = 0
            stop = offset = max(-1 * pos, offset)
            step = -1

        for i in range(start, stop, step):
            a = pos + i
            b = pos + i + step

            #in-place swap
            self.pages[p][a], self.pages[p][b] = self.pages[p][b], self.pages[p][a]

        #set the cursor to where we just moved
        self.focus_row += offset

    #for moving the cursor vertically
    def movefocus_vertical(self, offset):
        if offset < 0:
            self.focus_row = max(self.focus_row + offset, 0)
        else:
            maxlen = len(self.pages[self.current_page])
            self.focus_row = min(self.focus_row + offset, maxlen - 1)

    #moving between columns
    def movefocus_horizontal(self, offset):
        if offset < 0:
            self.focus_col = max(self.focus_col + offset, 0)
        else:
            self.focus_col = min(self.focus_col + offset, 1)

    #move a var to the "dont watch" list
    def dropvar(self):
        self.movevar(0)

    def movevar(self, destination):
        cp = self.current_page

        #don't move to own page
        if destination == cp:
            return

        #can't delete from an empty page
        if 0 == len(self.pages[cp]):
            return

        #move to dest page
        x = self.pages[cp][self.focus_row]
        del self.pages[cp][self.focus_row]
        self.pages[destination] += [x]

        #stop listening on delete, start on undelete
        self.db.SetSubscription(x, 0 != destination)


        self.focus_row = min(self.focus_row, len(self.pages[cp]) - 1)


    def gotopage(self, pagenum):
        self.current_page = pagenum
        self.focus_row = 0

    def draw_screen(self):   
        canvas = self.top.render(self.screen_size, focus=True)
        self.ui.draw_screen(self.screen_size, canvas)



def tail_file(path, lines):
    return subprocess.Popen(
        ["tail", "-n", str(lines), path], 
        stdout=subprocess.PIPE,
        universal_newlines=True,
        ).communicate()[0]


#we need an environment variable to work the logging properly
if not os.environ.has_key("IMS_LOGFILE"):
    print "Do not run this python script directly; use the iMS shell script wrapper!"
    exit(1)

if len(sys.argv) != 3:
    print "Usage: " + sys.argv[0] + " <MOOSDB hostname> <MOOSDB TCP/IP port>"
    exit(1)

myMS = iMS()
try:
    myMS.main(sys.argv[1], long(sys.argv[2]), os.environ["IMS_LOGFILE"])
    print "\n\n\niMS has exited cleanly!\n\n"
except:
    exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
    traceback.print_tb(exceptionTraceback, None, sys.stdout)
