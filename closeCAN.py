from can.interfaces import slcan
try:
 port = slcan.slcanBus("/dev/ttyACM0", bitrate=1000000)
 print("Closing CANBUS on ttyACM0...")
except:
 port = slcan.slcanBus("/dev/ttyACM1", bitrate=1000000)
 print("Can not find ttyACM0, closing ttyACM1...")
 port.close()
 print("CANBUS ttyACM1 Closed")
else:
 port.close()
 print("CANBUS ttyACMO Closed")
