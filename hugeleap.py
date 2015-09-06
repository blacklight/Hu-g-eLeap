#!/usr/bin/python2

import Leap, sys, re
from math import sqrt
from getopt import getopt
from phue import Bridge

config = {}
prevFrame = None

class LeapListener(Leap.Listener):
    def __init__(self, onXYZChange=None):
        super(self.__class__, self).__init__()
        self.onXYZChange = onXYZChange
        self.collectedFrames = 0
        self.framesBufferSize = 3

    def on_init(self, controller):
        print "Leap Motion initialized"

    def on_connect(self, controller):
        print "Leap Motion connected"

    def on_disconnect(self, controller):
        print "Leap Motion disconnected"

    def on_exit(self, controller):
        print "Leap Motion exited"

    def on_frame(self, controller):
        # React after X frames, to prevent flooding the Hue bridge
        if self.collectedFrames < self.framesBufferSize:
            self.collectedFrames += 1
            return

        self.collectedFrames = 0
        frame = controller.frame()

        for hand in frame.hands:
            posX = hand.palm_position[0]
            posY = hand.palm_position[1]
            posZ = hand.palm_position[2]
            print "[%s, %s, %s]" % (posX, posY, posZ)
            if self.onXYZChange:
                self.onXYZChange(posX, posY, posZ)

class Hue():
    def __init__(self, bridge, lightbulb=None):
        self.bridgeAddress = bridge
        self.lightsMap = {}

        if lightbulb:
            m = re.split('\s*,\s*', lightbulb)
            self.lightbulbs = m if m else [lightbulb]

    def connect(self):
        self.bridge = Bridge(self.bridgeAddress)
        self.bridge.connect()
        self.bridge.get_api()

        for light in self.bridge.lights:
            self.lightsMap[light.name] = light

        if not hasattr(self, 'lightbulbs'):
            self.lightbulbs = []
            for light in self.bridge.lights:
                self.lightbulbs.append(light.name)

    def setBri(self, bri):
        if bri == 0:
            for light in self.lightbulbs:
                self.bridge.set_light(light, 'on', False)
        else:
            for light in self.lightbulbs:
                if not self.bridge.get_light(light, 'on'):
                    self.bridge.set_light(light, 'on', True)

        self.bridge.set_light(self.lightbulbs, 'bri', bri)

    def setSat(self, sat):
        self.bridge.set_light(self.lightbulbs, 'sat', sat)

    def setHue(self, hue):
        self.bridge.set_light(self.lightbulbs, 'hue', hue)

def showHelp():
    print "Usage: %s <-b|--bridge> bridge [-l|--lightbulb lighbulb] [--no-sat] [--no-bri] [--no-hue]\n" \
        "  -b|--bridge\tIP address or hostname of the Philips Hue bridge\n" \
        "  -l|--lightbulb\tLightbulbs to control, name or index, or comma separated list (default: all)\n" \
        "  --no-sat\tDon't set the light saturation (Leap X axis) (default: not set)\n" \
        "  --no-bri\tDon't set the light brightness (Leap Y axis) (default: not set)\n" \
        "  --no-bri\tDon't set the light hue (Leap Z axis) (default: not set)\n" \
        % (sys.argv[0])

def initConfig():
    optlist, args = getopt(sys.argv[1:], 'b:l:', ['bridge=', 'lightbulb=', 'no-bri', 'no-sat', 'no-hue'])

    for opt in optlist:
        if opt[0] == '-b' or opt[0] == '--bridge':
            config['bridge'] = opt[1]
        elif opt[0] == '-l' or opt[0] == '--lightbulb':
            config['lightbulb'] = opt[1]
        elif opt[0] == '--no-hue':
            config['nohue'] = True
        elif opt[0] == '--no-sat':
            config['nosat'] = True
        elif opt[0] == '--no-bri':
            config['nobri'] = True

    if 'bridge' not in config:
        showHelp()
        sys.exit(1)

def onPosXYZChangeListener(posX, posY, posZ):
    global prevFrame

    minX = -100
    maxX = 100
    minY = 90
    maxY = 400
    minZ = -20
    maxZ = 200
    maxFrameDist = 20

    minBri = 0
    maxBri = 254
    minSat = 154
    maxSat = 500
    minHue = 0
    maxHue = 65535

    if prevFrame is not None:
        dist = sqrt( \
            (posX-prevFrame[0])*(posX-prevFrame[0]) + \
            (posY-prevFrame[1])*(posY-prevFrame[1]) + \
            (posZ-prevFrame[2])*(posZ-prevFrame[2]) \
        );

        prevFrame = [posX, posY, posZ]
        if dist > maxFrameDist:
            return
    else:
        prevFrame = [posX, posY, posZ]


    if posX > maxX:
        posX = maxX
    elif posX < minX:
        posX = minX
    if posY > maxY:
        posY = maxY
    elif posY < minY:
        posY = minY
    if posZ > maxZ:
        posZ = maxZ
    elif posZ < minZ:
        posZ = minZ

    sat = int((((posX-minX) / (maxX-minX)) * (maxSat-minSat)) + minSat)
    bri = int((((posY-minY) / (maxY-minY)) * (maxBri-minBri)) + minBri)
    hue = int((((posZ-minZ) / (maxZ-minZ)) * (maxHue-minHue)) + minHue)

    if not 'nosat' in config:
        config['hue'].setSat(sat)

    if not 'nobri' in config:
        config['hue'].setBri(bri)

    if not 'nohue' in config:
        config['hue'].setHue(hue) # WTF? Setting the "hue" on a "Hue" lightbulb? Name clash?

def main():
    initConfig()

    print "Initializing Philips Hue connection"
    config['hue'] = Hue(bridge=config['bridge'], lightbulb = (config['lightbulb'] if 'lightbulb' in config else None))
    config['hue'].connect()

    print "Initializing Leap Motion connection"
    listener = LeapListener(onXYZChange = onPosXYZChangeListener)
    controller = Leap.Controller()
    controller.add_listener(listener)

    # Keep this process running until Enter is pressed
    print "Press Enter to quit..."
    sys.stdin.readline()

    # Remove the sample listener when done
    controller.remove_listener(listener)

if __name__ == "__main__":
    main()

