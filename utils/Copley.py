import serial
###########################################################################
#    
#    Written in 2009 by Ian Katz <ijk5@mit.edu>         
#    Terms: WTFPL (http://sam.zoy.org/wtfpl/) 
#           See COPYING and WARRANTY files included in this distribution
#
###########################################################################

#This class provides a tab-completed command line (through iPython) 
# for a Copley motor controller

class CopleyException(Exception):

    #as defined in the manual
    errorDescriptions = {
        1 : "Too much data passed with command",
        3 : "Unknown command code",
        4 : "Not enough data was supplied with the command",
        5 : "Too much data was supplied with the command",
        9 : "Unknown variable ID",
        10: "Data value out of range",
        11: "Attempt to modify read-only variable",
        14: "Unknown axis state",
        15: "Variable doesn't exist on requested page",
        18: "Illegal attempt to start a move while currently moving",
        19: "Illegal velocity limit for move",
        20: "Illegal acceleration limit for move",
        21: "Illegal deceleration limit for move",
        22: "Illegal jerk limit for move",
        25: "Invalid trajectory mode",
        27: "Command is not allowed while CVM is running",
        31: "Invalid node ID for serial port forwarding",
        32: "CAN Network communications failure",
        33: "ASCII command parsing error",
        }

    def __init__(self, code):
        self.code = code

        def lookup(self, code):
            return self.errorDescriptions[int(code)]

        def __str__(self):
            return repr("Copley error " + str(code) + ": " + self.lookup(code))
        
#this is the base class for all the individual copley commands
class CopleyCommand(object):
    def __init__(self, serialObj):
        #we assume that the port is initialized and opened
        self.serial = serialObj
        self.serial.timeout = 2

    #talk to serial port
    def execute_blind(self):
        self.send(self.makeCommand())

    #talk to serial port and get reponse (even for writes... check for error)
    def execute(self):
        self.execute_blind()

        response = self.getResponse()        

        if "e " == response[0:2]:
            raise CopleyException(response[2:])

        return response[2:-1]

    def send(self, whattosend):
        #FIXME: use self.serialObj
        #print whattosend
        self.serial.timeout = 0
        junk = self.serial.read(1000)
        if False and 0 < len(junk):
            print "Got some junk from the Copley:"
            print junk
        self.serial.write(whattosend)

    def getResponse(self):
        self.serial.timeout = 2
        buf = ""
        while True:
            b = self.serial.read(1)
            buf = buf + b
            if "\r" == b or "" == b:
                return buf

# this class creates an "empty" class representing a node in the tree of 
#      possible copley commands.  when we create an instance of this,
#      whichever child class we use will create the necessary properties
#      using the qp function
class CopleyCommandset(CopleyCommand):
    def __init__(self, serialObj, bank):
        CopleyCommand.__init__(self, serialObj)
        self.bank = bank
        self.cmd = ""

    def hexvar(self, variable):
        return "0x%0.2x" % variable
        #return str(hex(variable))

    def read(self, variable):
        self.cmd = "g %s%s\r" % (self.bank, self.hexvar(variable))
        return self.execute()

    def write(self, variable, value):
        #if is_list(value), convert to space-separated
        self.cmd = "s %s%s %s\r" % (self.bank, self.hexvar(variable), value)
        self.execute()

    def makeCommand(self):
        return self.cmd

#the magic: quick-property.  inserts a property into a command set
def qp(var):
    r = lambda inst: CopleyCommandset.read(inst, var)
    w = lambda inst, val: CopleyCommandset.write(inst, var, val)
    return property(r, w)


# the operational mode is a command set 
class CopleyMode(CopleyCommandset):
    label = {
        0 : "Amplifier disabled",
        1 : "Programmed Current Mode",
        2 : "Analog Current Mode",
        3 : "PWM Current Mode",
        11: "Programmed Velocity Mode",
        12: "Analog Velocity Mode",
        13: "PWM Velocity Mode",
        21: "Programmed Position (Trajectory Generator) Mode",
        22: "Analog Position Mode",
        23: "Digital Input Position Mode",
        31: "Programmed Position Mode, Stepper",
        33: "Digital Input Position Mode, Stepper",
        }

    def Enable(self):
        self.write(0x24, self.modenumber())

# command sets based on mode
class CopleyModeProgrammedCurrent(CopleyMode):

    def modenumber(self):
        return 1

    def setcurrent(self, s):
        self.write(0x20, s)

    def getcurrent(self):
        return self.read(0x20)

    Current_x10mA        = qp(0x20)
    Ramprate_x1mA_per_s  = qp(0x6a)


class CopleyModeAnalogCurrent(CopleyMode):
    def modenumber(self):
        return 2

    Input_scalefactor_x10mA  = qp(0x19)
    Input_deadband_x1mV      = qp(0x26)
    Input_offset_x1mV        = qp(0x1a)


class CopleyModePWMCurrent(CopleyMode):
    def modenumber(self):
        return 3

    Input_scalefactor_x10mA  = qp(0xa9)
    Input_command_code       = qp(0xa8)


class CopleyModeProgrammedVelocity(CopleyMode):
    def modenumber(self):
        return 11
    
    Velocity_x100mCounts_per_s            = qp(0x2f)
    Velocity_accel_limit_x1kCount_per_s2  = qp(0x36)
    Velocity_decel_limit_x1kCount_per_s2  = qp(0x37)
    Fast_stop_ramp_x1kCount_per_s2        = qp(0x39)

class CopleyModeAnalogVelocity(CopleyMode):
    def modenumber(self):
        return 12

    #stuff from modes 2 and 11
    Input_scalefactor_x10mA  = qp(0x19)
    Input_deadband_x1mV      = qp(0x26)
    Input_offset_x1mV        = qp(0x1a)

    Velocity_accel_limit_x1kCount_per_s2  = qp(0x36)
    Velocity_decel_limit_x1kCount_per_s2  = qp(0x37)
    Fast_stop_ramp_x1kCount_per_s2        = qp(0x39)
    

class CopleyModePWMVelocity(CopleyMode):
    def modenumber(self):
        return 13

    #stuff from modes 3 and 11
    Input_scalefactor_x10mA  = qp(0xa9)
    Input_command_code       = qp(0xa8)

    Velocity_accel_limit_x1kCount_per_s2  = qp(0x36)
    Velocity_decel_limit_x1kCount_per_s2  = qp(0x37)
    Fast_stop_ramp_x1kCount_per_s2        = qp(0x39)


class CopleyModeProgrammedPosition(CopleyMode):
    
    Profile_code                   = qp(0xc8)
    Position_cmd_count             = qp(0xca)
    Max_velocity_x100mCount_per_s  = qp(0xcb)
    Max_accel_x10count_per_s2      = qp(0xcc)
    Max_decel_x10count_per_s2      = qp(0xcd)
    Max_jerk_x100count_per_s3      = qp(0xce)
    Abort_decel_x10count_per_s     = qp(0xcf)

class CopleyModeProgrammedPositionServo(CopleyModeProgrammedPosition):
    def modenumber(self):
        return 21
                                       

class CopleyModeProgrammedPositionStepper(CopleyModeProgrammedPosition):
    def modenumber(self):
        return 31
                                       

class CopleyModeAnalogPosition(CopleyMode):
    def modenumber(self):
        return 22

    #stuff from modes 2 and 21/31
    Input_scalefactor_x10mA  = qp(0x19)
    Input_deadband_x1mV      = qp(0x26)
    Input_offset_x1mV        = qp(0x1a)

    Max_velocity_x100mCount_per_s  = qp(0xcb)
    Max_accel_x10count_per_s2      = qp(0xcc)
    Max_decel_x10count_per_s2      = qp(0xcd)
    Abort_decel_x10count_per_s     = qp(0xcf)


class CopleyModeDigitalInputPosition(CopleyMode):
    
    #stuff from modes 3 and 21/31
    Input_scalefactor_x10mA  = qp(0xa9)
    Input_command_code       = qp(0xa8)

    Max_velocity_x100mCount_per_s  = qp(0xcb)
    Max_accel_x10count_per_s2      = qp(0xcc)
    Max_decel_x10count_per_s2      = qp(0xcd)
    Abort_decel_x10count_per_s     = qp(0xcf)


class CopleyModeDigitalInputPositionServo(CopleyModeDigitalInputPosition):
    def modenumber(self):
        return 23


class CopleyModeDigitalInputPositionStepper(CopleyModeDigitalInputPosition):
    def modenumber(self):
        return 33

    
class CopleyLoopCurrentLimits(CopleyCommandset):
    Current_peak_x10mA         = qp(0x21)
    Current_continuous_x10mA   = qp(0x22)
    I2t_limit_x1ms             = qp(0x23)
    Current_loop_offset_x10mA  = qp(0xae)
    

class CopleyLoopCurrentGains(CopleyCommandset):
    Proportional  = qp(0x00)
    Integral      = qp(0x01)


class CopleyLoopVelocityLimits(CopleyCommandset):
    Velocity_x10mCounts_per_s       = qp(0x3a)
    Acceleration_x1kCount_per_s2    = qp(0x36)
    Deceleration_x1kCount_per_s2    = qp(0x37)
    Fast_stop_ramp_x10count_per_s2  = qp(0xcf)

class CopleyLoopVelocityGains(CopleyCommandset):
    Proportional  = qp(0x27)
    Integral      = qp(0x28)

class CopleyLoopVelocityFilters(CopleyCommandset):
    Command_coefficients  = qp(0x6b)
    Output_coefficients   = qp(0x5f)

class CopleyLoopPositionGains(CopleyCommandset):
    Proportional              = qp(0x30)
    Velocity_feedforward      = qp(0x33)
    Acceleration_feedforward  = qp(0x34)
    Multiplier_percent        = qp(0xe3)


class CopleyLoopCurrent(CopleyCommandset):
    Limits = property(lambda self: CopleyLoopCurrentLimits(self.serial, self.bank))
    Gains  = property(lambda self: CopleyLoopCurrentGains(self.serial, self.bank))


class CopleyLoopVelocity(CopleyCommandset):
    Limits  = property(lambda self: CopleyLoopVelocityLimits(self.serial, self.bank))
    Gains   = property(lambda self: CopleyLoopVelocityGains(self.serial, self.bank))
    Filters = property(lambda self: CopleyLoopVelocityFilters(self.serial, self.bank))
        

class CopleyLoopPosition(CopleyCommandset):
    Gains = property(lambda self: CopleyLoopPositionGains(self.serial, self.bank))

class CopleyFlashset(CopleyCommandset):
    def __init__(self, serialObj):
        CopleyCommandset.__init__(self, serialObj, "f")

    def Amplifier_disable(self):
        self.write(0x24, "0")

    Mode = property(lambda self: CopleyMode.label[int(self.read(0x24))])

    Mode_programmed_curent = \
        property(lambda self: CopleyModeProgrammedCurrent(self.serial, self.bank))

    Mode_analog_current = \
        property(lambda self: CopleyModeAnalogCurrent(self.serial, self.bank))

    Mode_pwm_current = \
        property(lambda self: CopleyModePWMCurrent(self.serial, self.bank))

    Mode_programmed_velocity = \
        property(lambda self: CopleyModeProgrammedVelocity(self.serial, self.bank))

    Mode_analog_velocity = \
        property(lambda self: CopleyModeAnalogVelocity(self.serial, self.bank))

    Mode_pwm_velocity = \
        property(lambda self: CopleyModePWMelocity(self.serial, self.bank))

    Mode_programmed_position_servo = \
        property(lambda self: CopleyModeProgrammedPositionServo(self.serial, self.bank))

    Mode_programmed_position_stepper = \
        property(lambda self: CopleyModeProgrammedPositionStepper(self.serial, self.bank))

    Mode_analog_position = \
        property(lambda self: CopleyModeAnalogPosition(self.serial, self.bank))

    Mode_digital_input_position_servo = \
        property(lambda self: CopleyModeDigitalInputPositionServo(self.serial, self.bank))

    Mode_digital_input_position_stepper = \
        property(lambda self: CopleyModeDigitalInputPositionStepper(self.serial, self.bank))


    Loop_current = \
        property(lambda self: CopleyLoopCurrent(self.serial, self.bank))

    Loop_velocity = \
        property(lambda self: CopleyLoopVelocity(self.serial, self.bank))

    Loop_position = \
        property(lambda self: CopleyLoopPosition(self.serial, self.bank))
    

class CopleyStatusBase(CopleyCommandset):
    def __init__(self, serialObj, bank):
        CopleyCommandset.__init__(self, serialObj, bank)
        
    #FIXME, get 
    def Report(self):
        return self.int2statuslist(int(self.read(self.varname())))

    def int2statuslist(self, anInt):
        if anInt < 0: 
            raise ValueError, "Can't get bits of negative number"

        ret = []
        i = 0
        while anInt > 0:
            if 0 < (anInt % 2):
                try:
                    ret.append(self.bitVal(i))
                except KeyError:
                    ret.append("UNKNOWN FLAG (" + str(i) + ")")
            anInt = anInt >> i
            i = i + 1
            
        return ret

    def bitVal(self, pos):
        return "ERROR, self.bitVal not defined!"

    def varname(self):
        pass

class CopleyStatusAmplifier(CopleyStatusBase):
        
    statusCodes = {
        0 : "Short Circuit",
        1 : "Amp Over Temperature",
        2 : "Over Voltage",
        3 : "Under Voltage",
        4 : "Motor Over Temperature",
        5 : "Feedback Error",
        6 : "Motor Phasing Error",
        7 : "Current Limited",
        8 : "Voltage Limited",
        9 : "Positive Limit Switch",
        10: "Negative Limit Switch",
        11: "Amp Disabled by Hardware",
        12: "Amp Disabled by Software",
        13: "Attempting to Stop Motor",
        14: "Motor Brake Active",
        15: "PWM Outputs Disabled",
        16: "Positive Software Limit",
        17: "Negative Software Limit",
        18: "Following Error",
        19: "Following Warning",
        20: "Amplifier has been reset",
        21: "Encoder position wrapped (rotary) or hit limit (linear)",
        22: "Amplifier Fault",
        23: "Velocity Limited",
        24: "Acceleration Limited",
        25: "Pos Outside of Tracking Window",
        26: "Home Switch Active",
        27: "In Motion",
        28: "Velocity Outside of Tracking Window",
        29: "Phase not Initialized",
        }

    def bitVal(self, pos):
        return self.statusCodes[pos]

    def varname(self):
        return 0xa0

class CopleyStatusTrajectory(CopleyStatusBase):
    statusCodes = {
        11: "Homing error",
        12: "Referenced (Homing successful)",
        13: "Homing in progress",
        14: "Move aborted",
        15: "In motion",
        }

    def bitVal(self, pos):
        return self.statusCodes[pos]

    def varname(self):
        return 0xc9

class CopleyStatusFault(CopleyStatusBase):
    statusCodes = {
        0 : "Fatal: flash data corrupt",
        1 : "Fatal: A/D offset out of range",
        2 : "Short Circuit",
        3 : "Amp Over Temperature",
        4 : "Motor Over Temperature",
        5 : "Over Voltage",
        6 : "Under Voltage",
        7 : "Feedback Error",
        8 : "Motor Phasing Error",
        9 : "Following Error",
        10: "OVer Current (Latched)",
        }

    def bitVal(self, pos):
        return self.statusCodes[pos]
    
    def varname(self):
        return 0xa4

    #clear a latched error by writing a 1 to the associated bit of the register
    def Clear(self, bit_pos):
        if bit_pos < 0: 
            raise ValueError, "Can't reset a bit in a negative position"
        
        mask = 1
        while bit_pos > 0:
            mask = mask << 1
            bit_pos = bit_pos - 1

        self.write(self.varname(), mask)
        

class CopleyStatus(CopleyCommandset):
    def __init__(self, serialObj, bank):
        CopleyCommandset.__init__(self, serialObj, bank)

    Amplifier = property(lambda self: CopleyStatusAmplifier(self.serial, self.bank))
    Trajectory = property(lambda self: CopleyStatusTrajectory(self.serial, self.bank))
    Fault = property(lambda self: CopleyStatusFault(self.serial, self.bank))
                                                                      
class CopleyRuntimeCurrent(CopleyCommandset):
    def __init__(self, serialObj, bank):
        CopleyCommandset.__init__(self, serialObj, bank)

    Desired_x10mA  = qp(0x15)
    Actual_x10mA   = qp(0x0c)
    Limited_x10mA  = qp(0x25)

class CopleyRuntimeVelocity(CopleyCommandset):
    def __init__(self, serialObj, bank):
        CopleyCommandset.__init__(self, serialObj, bank)

    Desired_x100mCount_per_s     = qp(0x2c)
    Limited_x100mCount_per_s     = qp(0x29)
    Actual_x100mCount_per_s      = qp(0x18)
    Load_x100mCount_per_s        = qp(0x5e)
    Loop_error_x100mCount_per_s  = qp(0x2a)


class CopleyRuntimePosition(CopleyCommandset):
    def __init__(self, serialObj, bank):
        CopleyCommandset.__init__(self, serialObj, bank)
    
    Motor_x1count            = qp(0x32)
    Load_x1count             = qp(0x17)
    Following_error_x1count  = qp(0x35)
        

class CopleyRuntimeTrajectory(CopleyCommandset):
    def __init__(self, serialObj, bank):
        CopleyCommandset.__init__(self, serialObj, bank)

    Position_desired_x1count              = qp(0x3d)
    Position_limited_x1count              = qp(0x2d)
    Profile_velocity_x100mCount_per_s     = qp(0x3b)
    Profile_acceleration_x10count_per_s2  = qp(0x3c)

class CopleyRuntime(CopleyCommandset):
    def __init(self, serialObj, bank):
        CopleyCommandset.__init__(self, serialObj, bank)

    Current = property(lambda self: CopleyRuntimeCurrent(self.serial, self.bank))
    Velocity = property(lambda self: CopleyRuntimeVelocity(self.serial, self.bank))
    Position = property(lambda self: CopleyRuntimePosition(self.serial, self.bank))
    Trajectory = property(lambda self: CopleyRuntimeTrajectory(self.serial, self.bank))


class CopleyRamset(CopleyFlashset):
    def __init__(self, serialObj):
        CopleyCommandset.__init__(self, serialObj, "r")

    Status = property(lambda self: CopleyStatus(self.serial, self.bank))
    Runtime = property(lambda self: CopleyRuntime(self.serial, self.bank))

class CopleyCommandReset(CopleyCommand):
    def __init__(self, serialObj):
        CopleyCommand.__init__(self, serialObj)

    def makeCommand(self):
        return "r\r"

class CopleyController(object):
    def __init__(self, serialObj):
        self.serial = serialObj
        
    def Reset(self):
        CopleyCommandReset(self.serial).execute_blind()

    Ram = property(lambda self: CopleyRamset(self.serial))
    Flash = property(lambda self: CopleyFlashset(self.serial))
    

        
        
        






