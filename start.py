from connection import SerialThread
import detect_test

try:
    serial = SerialThread(port="/dev/ttyACM0", connect=True,
                          fps=10000, buffer_size=0, debug=True)
except:
    serial = SerialThread(port="/dev/ttyACM1", connect=True,
                          fps=10000, buffer_size=0, debug=True)

# connection
serial.start()

detect_test.main(serial)
