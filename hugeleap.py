#!/usr/bin/python2

import Leap, sys, re
from getopt import getopt
from phue import Bridge

config = {}

class LeapListener(Leap.Listener):
    def __init__(self, onYChange=None):
        super(self.__class__, self).__init__()
        self.onYChange = onYChange
        self.collectedFrames = 0
        self.framesBufferSize = 10

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
            posY = hand.palm_position[1]
            if self.onYChange:
                self.onYChange(posY)

class Hue():
    def __init__(self, bridge, lightbulb=None):
        self.bridgeAddress = bridge

        if lightbulb:
            m = re.split('\s*,\s*', lightbulb)
            self.lightbulbs = m if m else [lightbulb]

    def connect(self):
        self.bridge = Bridge(self.bridgeAddress)
        self.bridge.connect()
        self.bridge.get_api()

        if not hasattr(self, 'lightbulbs'):
            self.lightbulbs = []
            for light in self.bridge.lights:
                self.lightbulbs.append(light.name)

    def setBrightness(self, brightness):
        if brightness == 0:
            for light in self.lightbulbs:
                self.bridge.set_light(light, 'on', False)
        else:
            for light in self.lightbulbs:
                if not self.bridge.get_light(light, 'on'):
                    self.bridge.set_light(light, 'on', True)

        self.bridge.set_light(self.lightbulbs, 'bri', brightness)

def showHelp():
    print "Usage: %s <-b|--bridge> bridge [-l|--lightbulb lighbulb]\n" \
        "  -b|--bridge\tIP address or hostname of the Philips Hue bridge\n" \
        "  -l|--lightbulb\tLightbulbs to control, name or index, or comma separated list (default: all)\n" \
        % (sys.argv[0])

def initConfig():
    optlist, args = getopt(sys.argv[1:], 'b:l:', ['bridge=', 'lightbulb='])

    for opt in optlist:
        if opt[0] == '-b' or opt[0] == '--bridge':
            config['bridge'] = opt[1]
        elif opt[0] == '-l' or opt[0] == '--lightbulb':
            config['lightbulb'] = opt[1]

    if 'bridge' not in config:
        showHelp()
        sys.exit(1)

def onPosYChangeListener(posY):
    minY = 90
    maxY = 400
    minBright = 0
    maxBright = 254

    if posY > maxY:
        posY = maxY
    elif posY < minY:
        posY = minY

    brightness = int((((posY-minY) / (maxY-minY)) * (maxBright-minBright)) + minBright)
    config['hue'].setBrightness(brightness)

def main():
    initConfig()

    print "Initializing Philips Hue connection"
    config['hue'] = Hue(bridge=config['bridge'], lightbulb = (config['lightbulb'] if 'lightbulb' in config else None))
    config['hue'].connect()

    print "Initializing Leap Motion connection"
    listener = LeapListener(onYChange = onPosYChangeListener)
    controller = Leap.Controller()
    controller.add_listener(listener)

    # Keep this process running until Enter is pressed
    print "Press Enter to quit..."
    sys.stdin.readline()

    # Remove the sample listener when done
    controller.remove_listener(listener)

if __name__ == "__main__":
    main()

