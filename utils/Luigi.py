#!/usr/bin/env python
###########################################################################
#    
#    Written in 2010 by Ian Katz <ijk5@mit.edu>         
#    Terms: WTFPL (http://sam.zoy.org/wtfpl/) 
#           See COPYING and WARRANTY files included in this distribution
#
###########################################################################

# Luigi: the Lua GUI
#  this program is a frontend for Ian's MOOS Lua Helm, written for 
#  the Odyssey IV AUV
#
# Optional command line args are the MOOS hostname and port.  
#  They default to localhost and 9000 respectively.

import wxversion
wxversion.select("2.8")

import wx, sys, os, time, pygame
import pyMOOS

class MOOSPanelBase(wx.Panel):
    def OnNewMail(self, mail):
        pass

    def Subscribe(self):
        return True

    def Iterate(self):
        pass


 
class MissionPanel(MOOSPanelBase):
    def __init__(self, *args, **kwargs):
        wx.Panel.__init__(self, *args, **kwargs)
        
        self.CL_image_viewer = "gwenview"
        self.sChart = None
        self.buttons = {}
        self.varlog_target = None

        # rescan reconfigure
        # mission chooser
        # mark activate execute
        # timer
        # repeat stop abort 

        sizer = wx.StaticBoxSizer(wx.StaticBox(self, -1, "Mission Control"), wx.VERTICAL)
        
        row1 = wx.BoxSizer(wx.HORIZONTAL)
        row2 = wx.BoxSizer(wx.HORIZONTAL)
        row3 = wx.BoxSizer(wx.HORIZONTAL)
        row4 = wx.BoxSizer(wx.HORIZONTAL)
        row5 = wx.BoxSizer(wx.HORIZONTAL)

        self.AddButton("rescan",       row1, self.OnRescan)
        self.AddButton("reconfigure",  row1, self.OnReconfigure)

        self.StateText = wx.StaticText(self, -1, "[not running]", style = wx.ALIGN_RIGHT)
        row1.Add(self.StateText, 1, wx.EXPAND)

        sizer.Add(row1, 0, wx.EXPAND)
        
        self.mission_choice = wx.Choice(self,-1)
        row2.Add(self.mission_choice, 1, wx.EXPAND)
        self.Bind(wx.EVT_CHOICE, self.OnMissionSelect, self.mission_choice)

        sizer.Add(row2, 0, wx.EXPAND)
        
        self.AddButton("mark",      row3, self.OnMark)
        self.AddButton("activate",  row3, self.OnActivate)
        self.AddButton("execute",   row3, self.OnExecute)

        sizer.Add(row3, 0, wx.EXPAND)

        self.TimerText = wx.StaticText(self, -1, " Mission Stopped", style = wx.ALIGN_RIGHT)
        row4.Add(self.TimerText, 1, wx.EXPAND)

        sizer.Add(row4, 0, wx.EXPAND)

        self.AddButton("repeat",  row5, self.OnRepeat)
        self.AddButton("stop",    row5, self.OnStop)
        self.AddButton("abort",   row5, self.OnAbort)

        sizer.Add(row5, 0, wx.EXPAND)

        self.Timer = wx.Timer(self, -1)
        self.Bind(wx.EVT_TIMER, self.OnTimer)
        self.TimerStart = -1

        self.SetSizerAndFit(sizer)
        
    def AddButton(self, label, row, click_fn):
        b = wx.Button(self, -1, label.capitalize())
        row.Add(b, 0, wx.EXPAND | wx.BORDER)
        self.Bind(wx.EVT_BUTTON, click_fn, b)
        self.buttons[label] = b
        b.Disable()

    def DoCmd(self, cmd):
        self.GetParent().Comms.Notify("PLUAHELM_CMD", cmd)

    def OnRescan(self, ev):
        self.DoCmd("rescan")

    def OnReconfigure(self, ev):
        self.DoCmd("reconfigure")

    def OnMark(self, ev):
        self.DoCmd("mark")

    def OnActivate(self, ev):
        self.DoCmd("activate")

    def OnExecute(self, ev):
        if self.varlog_target:
            self.varlog_target.Blank()
        self.TimerStart = time.time()
        self.Timer.Start(1000)      
        self.DoCmd("execute")

    def OnRepeat(self, ev):
        self.DoCmd("repeat")

    def OnStop(self, ev):
        self.DoCmd("stop")

    def OnAbort(self, ev):
        self.DoCmd("abort")

    def OnMissionSelect(self, ev):
        next_mission = self.mission_choice.GetStringSelection()
        print next_mission
        if next_mission:
            self.GetParent().Comms.Notify("LUAHELM_NEXTMISSION", str(next_mission))

    def OnRefresh(self, ev):
        self.GetParent().Comms.Notify("RESTART_HELM", "TRUE")
    
    def OnStart(self, ev):
        self.GetParent().Comms.Notify("MOOS_MANUAL_OVERIDE", "FALSE")
        self.TimerStart = time.time()
        self.Timer.Start(1000)        

    def OnPreview(self, ev):
        import pydot
        if self.sChart is None:
            return
        
        sTempfile = pydot.tempfile.mkstemp(".jpg", "pymoos_Cpanel_")
        print sTempfile
        chart = pydot.graph_from_dot_data(self.sChart)
        chart.write_jpeg(sTempfile[1], prog='dot') 
        os.system(self.CL_image_viewer + " " + sTempfile[1] + "&")
        
    def OnTimer(self, ev):
        elapsed = int(time.time() - self.TimerStart)
        text = " Running %d:%02d" % (elapsed/60, elapsed%60)
        self.TimerText.SetLabel(text)
 
    def OnNewMail(self, mail):
        msg = pyMOOS.CMOOSMsg()
        c = self.GetParent().Comms
        if c.PeekMail(mail, "LUAHELM_MISSIONS", msg):
            missions = msg.m_sVal.split(',')
            missions = filter(lambda x: "" != x, missions)
            self.mission_choice.Clear()
            self.mission_choice.AppendItems(missions)

        if c.PeekMail(mail, "LUAHELM_MISSIONCHART", msg):
            self.sChart = msg.m_sVal
           
        if c.PeekMail(mail, "LUAHELM_STATE", msg):
            self.StateText.SetLabel(" St: " + msg.m_sVal)
            if "Idle" == msg.m_sVal:
                self.Timer.Stop()        
                self.TimerText.SetLabel(" Mission Stopped")
            elif not self.Timer.IsRunning():
                # decide whether to start timer
                if False or \
                        "PrepRun"      == msg.m_sVal or \
                        "Run"          == msg.m_sVal or \
                        "PrepSurface"  == msg.m_sVal or \
                        "Surface"      == msg.m_sVal:
                    self.Timer.Start(1000)


        if c.PeekMail(mail, "LUAHELM_NEXTACTIONS", msg):
            actions = msg.m_sVal.split(",")

            #set button states
            for b in self.buttons:
                if b in actions:
                    self.buttons[b].Enable()
                else:
                    self.buttons[b].Disable()


    def SetVarlog(self, target):
        self.varlog_target = target
 
    def Subscribe(self):
        bOk  = self.GetParent().Comms.Register("LUAHELM_MISSIONS", 0.2)
        bOk &= self.GetParent().Comms.Register("LUAHELM_MISSIONCHART", 0.2)        
        bOk &= self.GetParent().Comms.Register("LUAHELM_NEXTACTIONS", 0.2)
        bOk &= self.GetParent().Comms.Register("LUAHELM_STATE", 0.2)
        bOk &= self.GetParent().Comms.Register("LUAMISSION_STATE", 0.2)
        return bOk
	
        
class InitPanel(MOOSPanelBase):
    def __init__(self, *args, **kwargs):
        wx.Panel.__init__(self, *args, **kwargs)
        
        sizer = wx.StaticBoxSizer(wx.StaticBox(self,-1, "Quick Init"),wx.VERTICAL)
        
        row_1 = wx.BoxSizer(wx.HORIZONTAL)
        row_2 = wx.BoxSizer(wx.HORIZONTAL)
        row_3 = wx.BoxSizer(wx.HORIZONTAL)
        row_4 = wx.BoxSizer(wx.HORIZONTAL)
        
        b1 = wx.Button(self,-1,"Set Camera")
        row_1.Add(b1, 0, wx.EXPAND|wx.BORDER)
        self.Bind(wx.EVT_BUTTON, lambda x: self.OnEvent(\
                {"ICAMERA_BRIGHTNESS" : 89,
                 "ICAMERA_SHUTTER"    : 1117,
                 "ICAMERA_GAIN"       : 512,
                 }\
                    ), b1)
        
        b1a = wx.Button(self,-1,"Zero Depth")
        row_1.Add(b1a, 0, wx.EXPAND|wx.BORDER)
        self.Bind(wx.EVT_BUTTON, 
                  lambda x: self.OnEvent({"ZERO_DEPTH" : "True"}), b1a)

        b2 = wx.Button(self,-1,"Actuators ON")
        row_2.Add(b2, 0, wx.EXPAND|wx.BORDER)
        self.Bind(wx.EVT_BUTTON, lambda x: self.OnEvent(\
                {"RTU_ENABLE"       : "True",
                 "THRUSTERS_ENABLE" : "True",
                 }\
                    ), b2)

        b2b = wx.Button(self,-1,"Actuators Off")
        row_2.Add(b2b, 0, wx.EXPAND|wx.BORDER)
        self.Bind(wx.EVT_BUTTON, lambda x: self.OnEvent(\
                {"RTU_ENABLE"       : "False",
                 "THRUSTERS_ENABLE" : "False",
                 }\
                    ), b2b)


        b3 = wx.Button(self,-1,"Grab/2")
        row_3.Add(b3, 0, wx.EXPAND|wx.BORDER)
        self.Bind(wx.EVT_BUTTON, 
                  lambda x: self.OnEvent({"ICAMERA_CMD" : "GrabEvery=2"}), b3)


        b4 = wx.Button(self,-1,"Stopgrab")
        row_3.Add(b4, 0, wx.EXPAND|wx.BORDER)
        self.Bind(wx.EVT_BUTTON, 
                  lambda x: self.OnEvent({"ICAMERA_CMD" : "StopGrabbing"}), b4)


        b5 = wx.Button(self,-1,"CV PIPE")
        row_4.Add(b5, 0, wx.EXPAND|wx.BORDER)
        self.Bind(wx.EVT_BUTTON, 
                  lambda x: self.OnEvent({"CV_CMD" : "start:pipe"}), b5)

        b5b = wx.Button(self,-1,"CV PIPE2")
        row_4.Add(b5b, 0, wx.EXPAND|wx.BORDER)
        self.Bind(wx.EVT_BUTTON, 
                  lambda x: self.OnEvent({"CV_CMD" : "start:pipe2"}), b5b)


        b6 = wx.Button(self,-1,"CV STOP")
        row_4.Add(b6, 0, wx.EXPAND|wx.BORDER)
        self.Bind(wx.EVT_BUTTON, 
                  lambda x: self.OnEvent({"CV_CMD" : "stop"}), b6)

        

        sizer.Add(row_1,0, wx.EXPAND)
        sizer.Add(row_2,0, wx.EXPAND)
        sizer.Add(row_3,0, wx.EXPAND)
        sizer.Add(row_4,0, wx.EXPAND)
        self.SetSizerAndFit(sizer)
        
    def OnEvent(self, pairs):
        for var, val in pairs.iteritems():
            print "Setting", var, "to", val
            self.GetParent().Comms.Notify(var, val)
    
	
        


        
class VarLog(MOOSPanelBase):

    def __init__(self, *args, **kwargs):
        self.vars = kwargs["varnames"]
        del kwargs["varnames"]

        title = kwargs["boxtitle"]
        del kwargs["boxtitle"]

        wx.Panel.__init__(self, *args, **kwargs)
        sizer = wx.StaticBoxSizer(wx.StaticBox(self, -1, label = title), wx.VERTICAL)
        self.log = wx.TextCtrl(self, -1, style = wx.TE_MULTILINE | wx.TE_READONLY)
        sizer.Add(self.log, 1, wx.EXPAND)
        self.SetSizerAndFit(sizer)

    def CheckFor(self, label, mail):
        msg = pyMOOS.CMOOSMsg()
        if self.GetParent().Comms.PeekMail(mail, label, msg):
            if not msg.IsSkewed(pyMOOS.MOOSTime()):
                self.log.AppendText(time.strftime("(%H:%M:%S) ") 
                                    + label + ": " 
                                    + msg.m_sVal + os.linesep)
        
    def Blank(self):
        self.log.AppendText(os.linesep)

    def OnNewMail(self, mail):
        for v in self.vars:
            self.CheckFor(v, mail)
                
    def Subscribe(self):
        bOk  = True
        for v in self.vars:
            bOk &= self.GetParent().Comms.Register(v, 0.2)

        return bOk

    

class SummaryPanel(MOOSPanelBase):
    def __init__(self, *args, **kwargs):
        #read the args & get rid of them.
        names = kwargs["varnames"]
        del kwargs["varnames"]
        
        wx.Panel.__init__(self, *args, **kwargs)
        
        sizer=wx.StaticBoxSizer(wx.StaticBox(self,-1, label=self.Name),wx.VERTICAL)
        self.summary_items = {}
        for n in names:
            new_sizer=wx.BoxSizer(wx.HORIZONTAL)
            new_sizer.Add(wx.StaticText(self, -1, n, style=wx.ALIGN_LEFT),1, wx.EXPAND)
            self.summary_items[n] = wx.TextCtrl(self, -1, "",style=wx.TE_READONLY | wx.ALIGN_RIGHT) #wx.StaticText(self, -1, "",style=wx.ALIGN_RIGHT)
            new_sizer.Add(self.summary_items[n],1, wx.EXPAND | wx.ALIGN_RIGHT)
            sizer.Add(new_sizer,0, wx.EXPAND)
        self.SetSizerAndFit(sizer)
        
    def OnNewMail(self, mail):
        msg = pyMOOS.CMOOSMsg()
        for key, txt in self.summary_items.iteritems():
            if self.GetParent().Comms.PeekMail(mail,key,msg):
                #txt.SetLabel(msg.GetAsString())
                
                #make a reasonable looking float by trimming trailing 0s
                value = str(msg.GetDouble()).rstrip("0")

                #txt.SetValue("%0.2f" % (msg.GetDouble(),))
                txt.SetValue(value)
#                txt.Enable(True)
                txt.SetForegroundColour("RED")
            else:
#                txt.Enable(False)
                txt.SetForegroundColour("BLACK")
                
    def Subscribe(self):
        success = True
        for key in self.summary_items.keys():
            success &= self.GetParent().Comms.Register(key, 0.2)
        return success

class AppMonitorPanel(MOOSPanelBase):
    def __init__(self, *args, **kwargs):
        #read the args & get rid of them.
        names = kwargs["AppList"]
        del kwargs["AppList"]
        self.expected = set(names)

        wx.Panel.__init__(self, *args, **kwargs)
        sizer=wx.StaticBoxSizer(wx.StaticBox(self,-1, label="App Monitor"), wx.VERTICAL)
        self.appText=wx.TextCtrl(self, -1, 
                                 "App Status Unknown",
                                 style = wx.TE_READONLY | wx.ALIGN_LEFT | wx.TE_MULTILINE)
        sizer.Add(self.appText, 1, wx.EXPAND)
        self.SetSizerAndFit(sizer)

    def OnNewMail(self, mail):
        msg = pyMOOS.CMOOSMsg()
        if self.GetParent().Comms.PeekAndCheckMail(mail,"OIV_DB_CLIENTS",msg):
            self.appText.Clear()
            CurrentAppSet = set(msg.m_sVal.split(",")[:-1])
            additional=CurrentAppSet-self.expected
            missing=self.expected-CurrentAppSet
            self.appText.Clear()
            if len(additional | missing) == 0:
                self.appText.AppendText("Running Normally")
            else:
                if len(additional) > 0:
                    self.appText.AppendText("Also running:\n")
                    for a in additional:
                        self.appText.AppendText("  "+a+"\n")
                if len(missing) > 0:
                    self.appText.AppendText("Missing:\n")
                    for m in missing:
                        self.appText.AppendText("  "+m+"\n")

    def Subscribe(self):
        return self.GetParent().Comms.Register("DB_CLIENTS", 0.2)
    
class MainWindow(wx.Frame):
    def __init__(self, *args, **kwargs):
        wx.Frame.__init__(self, *args, **kwargs)

        ## Set Up The Menu
        menu = wx.Menu()
        # information string shows up in statusbar
        menu.Append(wx.ID_NEW, "New Connection", "Connect to a MOOS Community")
        menu.AppendSeparator()
        menu.Append(wx.ID_EXIT, "Exit", "Quit the program")
        menuBar = wx.MenuBar()
        menuBar.Append(menu, "File")
        self.SetMenuBar(menuBar)
        self.Bind(wx.EVT_MENU, self.menuNewConnection, id=wx.ID_NEW)
        self.Bind(wx.EVT_MENU, self.menuExit, id=wx.ID_EXIT)
        ## End Menu


        main_sizer=wx.BoxSizer(wx.HORIZONTAL)        

        column1 = wx.BoxSizer(wx.VERTICAL)
        column2 = wx.BoxSizer(wx.VERTICAL)
        column3 = wx.BoxSizer(wx.VERTICAL)


        column3.Add(VarLog(self, -1, 
                            boxtitle="Helm Messages", 
                            varnames=["LUAHELM_LOADERMESSAGE",
                                      "LUAHELM_MESSAGE",
                                      "MOOS_DEBUG"]), 
                    1, 
                    wx.EXPAND | wx.BORDER)


        mission_msgs = VarLog(self, -1, 
                              boxtitle="Mission Messages", 
                              varnames=["LUAMISSION_MESSAGE"])
        column3.Add(mission_msgs, 1, wx.EXPAND | wx.BORDER)
        

        mission_summary = SummaryPanel(self, 1, 
                                       name="Mission", 
                                       varnames=["WAYPOINT_X",
                                                 "WAYPOINT_Y",
                                                 "WAYPOINT_DISTANCE",
                                                 "DESIRED_HEADING",
                                                 "DESIRED_DEPTH",
                                                 "DESIRED_ALTITUDE"])
        column2.Add(mission_summary, 0, wx.EXPAND | wx.BORDER)
        
        column2.Add(SummaryPanel(self, 1,
                                 name = "Navigation",
                                 varnames=["GPS_SAT",
                                           "GPS_LAT",
                                           "GPS_LON",
                                           "NAV_X",
                                           "NAV_Y",
                                           "INS_HEADING",
                                           "NAV_ALTITUDE",
                                           "NAV_DEPTH"]),
                    0, wx.EXPAND | wx.BORDER)
        
        column2.Add(SummaryPanel(self, 1, 
                                 name="Battery", 
                                 varnames=["BATTERY_VOLTAGE",
                                           "BATTERY_MIN_CELL", 
                                           "BATTERY_MAX_CELL"]), 
                    0, wx.EXPAND | wx.BORDER)
        
        
        column2.Add(SummaryPanel(self, 1, 
                                 name="Health", 
                                 varnames=["DB_UPTIME", 
                                           "OIV_DB_UPTIME", 
                                           "ICAMERA_FRAMENUMBER"]),
                    0, wx.EXPAND | wx.BORDER)
        



        mp = MissionPanel(self, -1)
        mp.SetVarlog(mission_msgs)

        column1.Add(mp, 0, wx.EXPAND | wx.BORDER)
        #column1.Add(JoystickPanel(self,-1),0, wx.EXPAND | wx.BORDER)
        column1.Add(InitPanel(self,-1),0, wx.EXPAND | wx.BORDER)
        column1.Add(AppMonitorPanel(self, -1, 
                                    AppList = ["iGPS",
                                               "iDVL",
                                               "iINS",
                                               "CTD",
                                               "iRange",
                                               "iDepth",
                                               "Thrusters",
                                               "RTU",
                                               "Battery",
                                               "pHelm",
                                               "pNav",
                                               "pLogMySQL",
                                               "iCamera",
                                               "pSystemHealth[oiv]",
                                               "pSystemHealth[camera]"
                                               ]
                                    ),
                    1, 
                    wx.EXPAND | wx.BORDER)




        main_sizer.Add(column1, 1, wx.EXPAND | wx.BORDER)        
        main_sizer.Add(column2, 1, wx.EXPAND | wx.BORDER)
        main_sizer.Add(column3, 1, wx.EXPAND | wx.BORDER)

        self.SetSizerAndFit(main_sizer)
        self.SetSize((600,450))
        self.Show(1)
        
        self.Comms = pyMOOS.CMOOSCommClient()
        
        self.IterationTimer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.OnIterate, self.IterationTimer)

        self.ConsecutiveCommsFailures = 0
   

        self.hostname = "localhost"
        self.port = 9000

        if len(sys.argv) == 1:
            print "Usage:", sys.argv[0], "<hostname> <port>"

        if len(sys.argv) > 1:
	    self.hostname = sys.argv[1]

        if len(sys.argv) > 2:
            self.port = long(sys.argv[2])

            
    def menuNewConnection(self,e):
        self.ConnectToDB()
        
    def menuExit(self,e):
        print "Exit"
        self.Close()
        
    def OnIterate(self,e):
        inbox = pyMOOS.MOOSMSG_LIST()

        if self.Comms.Fetch(inbox):
            self.ConsecutiveCommsFailures = 0
            for child in self.GetChildren():
                child.OnNewMail(inbox)
                child.Iterate()
        else:
            #print "Fetch Failed", time.asctime()
            self.ConsecutiveCommsFailures = self.ConsecutiveCommsFailures + 1
            if self.ConsecutiveCommsFailures % 25 == 0:
                print("No MOOS messages since ~5 seconds ago, re-registering")
                self.Subscribe()
        
        for child in self.GetChildren():
            child.Iterate()
            
    def ConnectToDB(self):
        if self.Comms.IsConnected():
            self.DisconnectFromDB()
            time.sleep(1)
            

        if self.Comms.Run(self.hostname,self.port,"Luigi[" + os.uname()[1] + "]"):
            time.sleep(1)
            self.Subscribe()
            
            self.IterationTimer.Start(200)
            print "Connected to DB on", self.hostname
        else:
            print("Failed to connect to DB")

    def DisconnectFromDB(self):
        print("Disconnecting from DB...")
        self.IterationTimer.Stop()
        print "Closed?", self.Comms.Close()
    
    def Subscribe(self, ):
        print "Subscribing to variables...",

        #keep us fresh
        self.Comms.Register("DB_TIME", 0.2)

        success = True
        for child in self.GetChildren():
            success &= child.Subscribe()
        
        if success:
            print "succeeded."
        else:
            print "failed."
            
        return success
        
    #def Reregister(self):
        #requires a re-registration
        #for var in self.Comms.GetRegistered():
            #print "Reregistering for ", var
            
def LuigiMain():
    app = wx.App()
    frame = MainWindow(None, -1, "Luigi: The Lua helm GUI")
    app.MainLoop()

if __name__ == "__main__":
    LuigiMain()
