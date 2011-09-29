###########################################################################
#    
#    Written in 2010 by Ian Katz <ijk5@mit.edu>         
#    Terms: WTFPL (http://sam.zoy.org/wtfpl/) 
#           See COPYING and WARRANTY files included in this distribution
#
###########################################################################



import pygame

#joystick_handle comes from pygame
def Factory(joystick_handle, settext_fn):
    devicename = joystick_handle.get_name()

    if "Logitech Logitech Dual Action" == devicename:
        return JoystickLogitechDualAction(joystick_handle, settext_fn)

    if "Logitech WingMan Action Pad" == devicename:
        return JoystickLogitechWingman(joystick_handle, settext_fn)

    if "Mad Catz Wired Xbox 360 Controller" == devicename:
        return JoystickMadcatzXbox360(joystick_handle, settext_fn)
    
    if "PLAYSTATION(R)3 Controller" in devicename:
        return JoystickSonyPS3(joystick_handle, settext_fn)

    return Joystick(joystick_handle, settext_fn)
        
        

class Joystick(object):
    def __init__(self, joystick_handle, settext_fn):
        self.joystick_handle = joystick_handle
        self.settext_fn = settext_fn
        self.joystick_handle.init()
        self.initialize()
        
        
    def initialize(self):
        print "Initialized Joystick BASE class: '" + self.joystick_handle.get_name() + "'"
        pygame.event.set_allowed(pygame.JOYBUTTONDOWN)
        pygame.event.set_allowed(pygame.JOYBUTTONUP)
        pygame.event.set_allowed(pygame.JOYAXISMOTION)
        pygame.event.set_allowed(pygame.JOYHATMOTION)
        self.settext_fn("Unknown Joystick")

    def moosSubscriptions(self):
        return []

    def ProcessEvents(self, pygameEvents, moosVars = {}):
        for ev in pygameEvents:
            
            if ev.type == pygame.JOYAXISMOTION:
                print "AXIS: ",ev.axis, ev.value
            elif ev.type == pygame.JOYBUTTONDOWN:
                print "BUTTON DOWN", ev.button
            elif ev.type == pygame.JOYBUTTONUP:
                print "BUTTON UP", ev.button
            elif ev.type == pygame.JOYHATMOTION:
                print "JOYHAT: ", ev.value

        #this is only informative, so don't return anything
        return {}



class JoystickMadcatzXbox360(Joystick):
    def initialize(self):
        self.settext_fn("Xbox 360")
        
        self.allstop = False
        self.heave_step = 10
        self.heading_step_small = 15
        self.heading_step_medium = 90
        self.heading_step_full = 180
        
        self.heading = 0

        self.throttle_ratio = 1

        self.surge = 0
        self.sway = 0
        self.heave = 10

        #this is the latest fetch, not the desired (maintain heading takes care of that)
        self.heading = 0

        self.hat = [0, 0]
        self.buttondown = {
            0:  False, 
            1:  False, 
            2:  False, 
            3:  False, 
            4:  False, 
            5:  False, 
            6:  False, 
            7:  False, 
            8:  False,
            9:  False,
            10: False,
            }


    def moosSubscriptions(self):
        return ["INS_HEADING"]

    def ProcessEvents(self, pygameEvents, moosVars = {}):
        #pick up values
        for k, v in moosVars.iteritems():
            if "INS_HEADING" == k:
                self.heading = v
                
        ret = {}
        for ev in pygameEvents:
            
            if ev.type == pygame.JOYAXISMOTION:
                if 1 == ev.axis:
                    self.surge = -100 * ev.value
                elif 3 == ev.axis:
                    self.sway = 50 * ev.value
                elif 2 == ev.axis and 1.0 == ev.value:
                    ret["MANUAL_HEADING_STEP"] = -self.heading_step_small
                elif 5 == ev.axis and 1.0 == ev.value:
                    ret["MANUAL_HEADING_STEP"] = self.heading_step_small

            elif ev.type == pygame.JOYBUTTONDOWN:
                print "BUTTON DOWN", ev.button
                self.buttondown[ev.button] = True
            elif ev.type == pygame.JOYBUTTONUP:
                print "BUTTON UP", ev.button
                self.buttondown[ev.button] = False
            elif ev.type == pygame.JOYHATMOTION:
                self.hat = ev.value

        #heave
        self.heave = max(0, min(40, self.hat[1] * self.heave_step + self.heave))
        print "Heave now", self.heave

        #BUTTONS
        #
        #pick up current heading on joystick press
        if self.buttondown[6]:
            ret["MANUAL_HEADING"] = self.heading
            print "Heading now", self.heading

        #steps
        elif self.buttondown[4]:
            ret["MANUAL_HEADING_STEP"] = -self.heading_step_medium
        elif self.buttondown[5]:
            ret["MANUAL_HEADING_STEP"] = self.heading_step_medium
        elif self.buttondown[10]:
            ret["MANUAL_HEADING_STEP"] = self.heading_step_full

        if "MANUAL_HEADING_STEP" in ret:
            print "Heading step is", ret["MANUAL_HEADING_STEP"]

        #rtu
        elif self.buttondown[2]:
            ret["RTU_ENABLE"] = "True"
        elif self.buttondown[0]:
            ret["RTU_ENABLE"] = "False"

        #thrusters
        elif self.buttondown[3]:
            ret["THRUSTERS_ENABLE"] = "True"
        elif self.buttondown[1]:
            ret["THRUSTERS_ENABLE"] = "False"

        #allstop
        elif self.buttondown[7]:
            self.allstop = True
        elif self.buttondown[8]:
            self.allstop = False

        #throttle ratio
        if self.buttondown[9]:
            print "BRINGING THE HAMMER DOWN"
            self.throttle_ratio = 1
        else:
            self.throttle_ratio = 0.25

        if self.allstop:
            ret["MANUAL_SURGE"] = 0
            ret["MANUAL_SWAY"] = 0
            ret["MANUAL_HEAVE"] = 0
        else:
            ret["MANUAL_SURGE"] = self.surge * self.throttle_ratio
            ret["MANUAL_SWAY"] = self.sway
            ret["MANUAL_HEAVE"] = self.heave

        return ret
                






class JoystickSonyPS3(Joystick):
    
    def initialize(self):
        pygame.event.set_allowed(pygame.JOYBUTTONDOWN)
        pygame.event.set_allowed(pygame.JOYBUTTONUP)
        pygame.event.set_allowed(pygame.JOYAXISMOTION)
        pygame.event.set_allowed(pygame.JOYHATMOTION)
        self.settext_fn("Sony PS3")
        self.buttondown = {
            0 : False,
            1 : False, 
            2 : False, 
            3 : False, 
            4 : False, 
            5 : False, 
            6 : False,
            7 : False,
            8 : False,
            9 : False,
            10: False,
            11: False,
            12: False,
            13: False,
            14: False,
            15: False,
            }
        
        self.joyaxismap = {
            0:("MANUAL_SWAY", 100.0), 
            1:("MANUAL_SURGE", -100.0),
            2:("MANUAL_YAW", -100.0),
            #3:("MANUAL_HEAVE", -100.0),
            }

        self.force = {"MANUAL_SWAY": 0, "MANUAL_SURGE": 0, "MANUAL_YAW": 0}

    def processDigiAnalog(self, dict, forcename, buttonmin, buttonmax, digimin, digimax):            
        if self.buttondown[buttonmax]:
            dict[forcename] = digimax
        elif self.buttondown[buttonmin]:
            dict[forcename] = digimin
        else:
            dict[forcename] = self.force[forcename]
            
            
    def ProcessEvents(self, pygameEvents, moosVars = {}):
        ret = {}
        
        
        for ev in pygameEvents:
            
            if ev.type == pygame.JOYAXISMOTION:
                try:
                    (varname, scalefactor) = self.joyaxismap[ev.axis]
                    self.force[varname] = scalefactor * ev.value
                except KeyError:
                    pass
            elif ev.type == pygame.JOYBUTTONDOWN:
                self.buttondown[ev.button] = True
                print "BUTTON DOWN", ev.button
            elif ev.type == pygame.JOYBUTTONUP:
                self.buttondown[ev.button] = False
                print "BUTTON UP", ev.button
            elif ev.type == pygame.JOYHATMOTION:
                print "JOYHAT: ", ev.value
        """
            
        for k, dontcare in self.buttondown.items():
            self.buttondown[k] = self.joystick_handle.get_button(k)
        
        for k, (var, scalefactor) in self.joyaxismap.items():
            self.force[var] = scalefactor * self.joystick_handle.get_axis(k)

        self.processDigiAnalog(ret, "MANUAL_SURGE", 6, 4, -50, 50)
        self.processDigiAnalog(ret, "MANUAL_SWAY",  7, 5, -50, 50)
        #self.processDigiAnalog(ret, "MANUAL_YAW", -50, 50)
        print ret
         """
        return ret



class JoystickLogitechWingman(Joystick):
    def initialize(self):
        self.settext_fn("Wingman")
        
        self.allstop = False
        self.throttle = 50
        self.surge = 0
        self.sway = 0
        self.hat = [0, 0]
        self.buttondown = {
            0: False, 
            1: False, 
            2: False, 
            3: False, 
            4: False, 
            5: False, 
            6: False, 
            7: False, 
            8: False}
        self.yaw = 0
        self.heave = 10

    #convert -1.00003051851 to +1 to a ratio
    def axis2throttle(self, zaxis, opposite = False):
        max_val = 1
        min_val = -1.00003051851
        
        ret = (zaxis - min_val) / (max_val - min_val)
        
        if opposite:
            return 1 - ret
        else:
            return ret

    def ProcessEvents(self, pygameEvents, moosVars = {}):
        ret = {}
        for ev in pygameEvents:
            
            if ev.type == pygame.JOYAXISMOTION:
                if 2 == ev.axis:
                    self.throttle = self.axis2throttle(ev.value, True)
                if 0 == ev.axis:
                    self.yaw = -100 * ev.value
                        
                print "AXIS: ",ev.axis, ev.value

            elif ev.type == pygame.JOYBUTTONDOWN:
                print "BUTTON DOWN", ev.button
                self.buttondown[ev.button] = True
            elif ev.type == pygame.JOYBUTTONUP:
                print "BUTTON UP", ev.button
                self.buttondown[ev.button] = False
            elif ev.type == pygame.JOYHATMOTION:
                self.hat = ev.value

        #calculate yaw based on button states
        if self.buttondown[6]:
            ret["MANUAL_YAW"] = 50
        elif self.buttondown[7]:
            ret["MANUAL_YAW"] = -50
        else:
            ret["MANUAL_YAW"] = self.yaw

        #rtu
        if self.buttondown[3]:
            ret["RTU_ENABLE"] = "True"
        elif self.buttondown[0]:
            ret["RTU_ENABLE"] = "False"

        #thrusters
        if self.buttondown[4]:
            ret["THRUSTERS_ENABLE"] = "True"
        elif self.buttondown[1]:
            ret["THRUSTERS_ENABLE"] = "False"

        #heave
        if self.buttondown[5] and self.heave < 40:
            self.heave = self.heave + 10
            self.allstop = False
        elif self.buttondown[2]:
            self.heave = 0


        if self.buttondown[8]:
            self.heave = 0
            self.allstop = True

        x = self.hat[0]
        y = self.hat[1]

        if self.allstop:
            ret["MANUAL_SURGE"] = 0
            ret["MANUAL_SWAY"] = 0
            ret["MANUAL_HEAVE"] = 0
            ret["MANUAL_YAW"] = 0
        else:
            ret["MANUAL_SURGE"] = y * self.throttle * 100
            ret["MANUAL_SWAY"] = x * self.throttle * 50 #vehicle is unstable in sway
            ret["MANUAL_HEAVE"] = self.heave

        return ret
                


class JoystickLogitechDualAction(Joystick):
    def initialize(self):
        self.settext_fn("Dual Action")

        self.do_analog = True
        self.increment = 1.0
        self.yaw_increment = 10.0
        
        self.joybuttonmap = {

            4:("MANUAL_HEADING_STEP",-self.yaw_increment),
            5:("MANUAL_HEADING_STEP",self.yaw_increment),
            #4:("MANUAL_MOVE_WAYPOINT_STARBOARD", self.increment),
            #5:("MANUAL_MOVE_WAYPOINT_FORWARD", -self.increment),
            }
        
        self.joyaxismap = {
            0:("MANUAL_SWAY", 100.0), 
            1:("MANUAL_SURGE", -100.0),
            2:("MANUAL_YAW", -100.0),
            #3:("MANUAL_HEAVE", -100.0),
            }

        #these are the events we expect
        pygame.event.set_allowed(None)
        pygame.event.set_allowed(pygame.JOYBUTTONDOWN)
        pygame.event.set_allowed(pygame.JOYHATMOTION)


    def ToggleAnalog(self):
        self.do_analog = not self.do_analog
        
        if self.do_analog:
            pygame.event.set_allowed(pygame.JOYAXISMOTION)
        else:
           pygame.event.set_allowed(pygame.JOYAXISMOTION)
        
        text = "Analog: "
        if self.do_analog: text+="ON"
        else: text+="OFF"
        print text
        self.settext_fn(text)
        #self.AnalogText.SetLabel(text)

    
    def ProcessEvents(self, pygameEvents, moosVars = {}):
        ret = {}
        for ev in pygameEvents:
        
            if ev.type == pygame.JOYAXISMOTION:
                try:
                    (varname, scalefactor) = self.joyaxismap[ev.axis]
                    ret[varname] = scalefactor * ev.value
                except(KeyError):
                    pass
                print "AXIS: ",ev.axis, ev.value
            elif ev.type == pygame.JOYBUTTONDOWN:
                try:
                    (varname, avalue) = self.joybuttonmap[ev.button]
                    ret[varname] = avalue
                except(KeyError):
                    if ev.button == 9:
                        self.ToggleAnalog()
                    else:
                        print "BUTTON",ev.button
            elif ev.type == pygame.JOYHATMOTION:
                try:
                    if ev.value[0] != 0:
                        ret["MANUAL_MOVE_WAYPOINT_STARBOARD"] = ev.value[0] * self.increment
                        print "JOYHAT... moving waypoint starboard"
                    if ev.value[1] != 0:
                        ret["MANUAL_MOVE_WAYPOINT_FORWARD"] = ev.value[1] * self.increment
                        print "JOYHAT... moving waypoint forward"
                except(KeyError):
                    pass

        return ret
            

