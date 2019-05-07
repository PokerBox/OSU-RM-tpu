from connection import SerialThread
from detect import main

try:
    serial = SerialThread(port="/dev/ttyACM0", connect=True,
                          fps=10000, buffer_size=0, debug=True)
except:
    serial = SerialThread(port="/dev/ttyACM1", connect=True,
                          fps=10000, buffer_size=0, debug=True)

# connection
serial.start()

main(serial)
