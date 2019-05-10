import math
import threading
import time
from can.interfaces import slcan
from can import Message
import numpy as np

YAW_MID = 900
PITCH_MID = 300


class SerialThread(threading.Thread):
    def __init__(self, connect=True, fps=3000, port='/dev/ttyACM0', buffer_size=20, debug=True):
        super(SerialThread, self).__init__()
        self.fps = fps
        self.connect = connect
        self.debug = debug

        if self.connect:
            self.dev = slcan.slcanBus(port, bitrate=1000000)
            self.dev.open()
            print('Connection found!')

        self.yaw = YAW_MID
        self.pitch = PITCH_MID
        self.send_yaw = 123
        self.send_pitch = 123

        self.sendData = []

    def hexToNumArray(self, data):
        nums = []
        for i in range(4):
            a = data[2*i: 2*i+2]
            num1 = bin(a[0])[2:10]
            num2 = bin(a[1])[2:10]
            for i in range(8-len(num1)):
                num1 = '0' + num1
            for i in range(8-len(num2)):
                num2 = '0' + num2
            nums.append(int(num1 + num2, 2))
        return nums

    def numToHex(self, num):
        if(num < 0):
            num = 0
        num = bin(num)
        num = num[2: len(num)]
        data = []
        for i in range(16-len(num)):
            num = '0' + num
        data.append(int(num[0:8], 2))
        data.append(int(num[8:16], 2))
        return data

    def sendMessage(self):

        self.send_yaw = int(self.yaw)
        self.send_pitch = int(self.pitch)
        x = self.numToHex(self.send_yaw)
        y = self.numToHex(self.send_pitch)
        self.sendData = [x[0], x[1], y[0], y[1], 0x00, 0x00, 0x00, 0x00]

        # if self.debug:
        #     with open('data.txt', 'a') as f:
        #         f.write('%d %d %d\n' % (int(x_num), int(y_num), int(self.yaw)))

        if len(self.sendData) == 8:
            self.dev.send(Message(arbitration_id=0x300, dlc=8,
                                  data=self.sendData, extended_id=False))
            # print('Send: %d %d Raw: %d %d Recieve: %d %d' %
            #           (self.send_x, self.send_y, self.x, self.y, self.yaw, self.pitch))

#    def recvMessage(self):
        # frame = self.dev.recv()
#        if frame.arbitration_id == 0x210:
#           self.yaw = self.hexToNumArray(frame.data)[0]
#            if(self.yaw < 1500):
#                self.yaw = self.yaw + 8192
#            self.yaw = (7210 - self.yaw) * 3600 / 8192
#
#            self.yaw_buffer.append(self.yaw)
#            if len(self.yaw_buffer) > self.buffer_size:
#                del(self.yaw_buffer[0])

#       if frame.arbitration_id == 0x211:
#            self.pitch = self.hexToNumArray(frame.data)[0]
#            self.pitch = self.pitch - 2450
#            self.pitch = self.pitch * 3600 / 8192

#            self.pitch_buffer.append(self.pitch)
#            if len(self.pitch_buffer) > self.buffer_size:
#                del(self.pitch_buffer[0])

    def run(self):
        count_plot = 0
        count_can = 0
        filter_time = time.time()
        while(True):
            prevTime = time.time()
            count_plot += 1
            count_can += 1

            if count_plot >= int(self.fps/300):
                count_plot = 0
                if self.debug:
                    print('Send: %d %d' % (self.send_yaw, self.send_pitch))

            if self.connect:
                self.sendMessage()

            # if count_can % int(self.fps/500) == 0:
            #     count_can = 0
            #     # _, _ = self.filter.getPredictionAbsolute(10)
            #     # self.updateData(x, y)
            #     # if self.debug:
            #     #    print('Send FPS: %d' % (1./(time.time()-filter_time)))

            # if self.connect:
            #     pass

                # self.recvMessage()
                # if self.debug:
                #     print('Recieve FPS: %d' % (1./(time.time()-filter_time)))
                # filter_time = time.time()
'''
            currentTime = time.time()
            runTime = currentTime - prevTime
            waitTime = 1./(self.fps) - runTime

            if waitTime > 0:
                time.sleep(waitTime*0.98)
'''
