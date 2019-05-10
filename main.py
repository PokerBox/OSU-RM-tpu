# Copyright 2019 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""A demo which runs object detection on camera frames.

export TEST_DATA=/usr/lib/python3/dist-packages/edgetpu/test_data

Run face detection model:
python3 -m edgetpuvision.detect \
  --model ${TEST_DATA}/mobilenet_ssd_v2_face_quant_postprocess_edgetpu.tflite

Run coco model:
python3 -m edgetpuvision.detect \
  --model ${TEST_DATA}/mobilenet_ssd_v2_coco_quant_postprocess_edgetpu.tflite \
  --labels ${TEST_DATA}/coco_labels.txt
"""
import argparse
import time
import datetime
import re
import svgwrite
import imp
import os
from edgetpu.detection.engine import DetectionEngine
import gstreamer
import math
from can.interfaces import slcan
from can import Message

YAW_MID = 900
PITCH_MID = 300
X_PIXEL = 320
Y_PIXEL = 240

# LOGITECH: 765
# BLACK GLOBLE SHUTTER: 416
CAMREA_PARAM = 400

# Choose among 0(red), 1(blue), or 'None'
ENEMY_COLOR = 1

PORT = ["/dev/ttyACM0", "/dev/ttyACM1"]
DEBUG = True
LOG_PATH = '~/OSU_RM_tpu/log/{date}'


def load_labels(path):
    p = re.compile(r'\s*(\d+)(.+)')
    with open(path, 'r', encoding='utf-8') as f:
        lines = (p.match(line).groups() for line in f.readlines())
        return {int(num): text.strip() for num, text in lines}


def shadow_text(dwg, x, y, text, font_size=20):
    dwg.add(dwg.text(text, insert=(x+1, y+1), fill='black', font_size=font_size))
    dwg.add(dwg.text(text, insert=(x, y), fill='white', font_size=font_size))


def generate_svg(dwg, objs, labels, text_lines):
    width, height = dwg.attribs['width'], dwg.attribs['height']
    for y, line in enumerate(text_lines):
        shadow_text(dwg, 10, y*20, line)
    for obj in objs:
        x0, y0, x1, y1 = obj.bounding_box.flatten().tolist()
        x, y, w, h = x0, y0, x1 - x0, y1 - y0
        x, y, w, h = int(x * width), int(y *
                                         height), int(w * width), int(h * height)
        percent = int(100 * obj.score)
        label = '%d%% %s' % (percent, labels[obj.label_id])
        shadow_text(dwg, x, y - 5, label)
        dwg.add(dwg.rect(insert=(x, y), size=(w, h),
                         fill='red', fill_opacity=0.3, stroke='white'))


def hexToNumArray(data):
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


def numToHex(num):
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


def sendMessage(dev, yaw, pitch):
    send_yaw = int(yaw)
    send_pitch = int(pitch)
    x = numToHex(send_yaw)
    y = numToHex(send_pitch)
    send_data = [x[0], x[1], y[0], y[1], 0x00, 0x00, 0x00, 0x00]

    if len(send_data) == 8:
        dev.send(Message(arbitration_id=0x300, dlc=8,
                         data=send_data, extended_id=False))
        print('Send: ', send_yaw, send_pitch)


# Return a distance parameter (not actual distance) to be compared
def distance_to_center(obj):
    [x1, y1, x2, y2] = obj.bounding_box.flatten().tolist()
    # squre of ((distance of x coord to center) * (xy pixel ratio)) + squre of (distance of x coord to center)
    distance = (((x1+x2)/2-0.5)*(X_PIXEL/Y_PIXEL))**2+((y1+y2)/2-0.5)**2
    return distance


# Choose the object with the enemy color closest to the center
def choose_obj(objs, start_time):
    if objs == []:
        return None
    enemy_objs = []
    if ENEMY_COLOR == None:
        enemy_objs = objs
    else:
        for obj in objs:
            if obj.label_id == ENEMY_COLOR:
                enemy_objs.append(obj)
    if enemy_objs == []:
        return None
    chosen_obj = enemy_objs[0]
    if len(enemy_objs) > 1:
        for obj in objs:
            if distance_to_center(obj) < distance_to_center(chosen_obj):
                chosen_obj = obj
    return chosen_obj


def main():
    default_model_dir = 'models'
    # default_model = '2019_05_10/output_tflite_graph_1557521764_edgetpu.tflite'
    # default_labels = 'armor_plate_labels.txt'
    default_model = 'mobilenet_ssd_v2_face_quant_postprocess_edgetpu.tflite'
    default_labels = 'face_labels.txt'
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', help='.tflite model path',
                        default=os.path.join(default_model_dir, default_model))
    parser.add_argument('--labels', help='label file path',
                        default=os.path.join(default_model_dir, default_labels))
    parser.add_argument('--top_k', type=int, default=5,
                        help='number of classes with highest score to display')
    parser.add_argument('--threshold', type=float, default=0.05,
                        help='class score threshold')

    args = parser.parse_args()

    print("Loading %s with %s labels." % (args.model, args.labels))
    engine = DetectionEngine(args.model)
    labels = load_labels(args.labels)

    last_time = time.monotonic()

    try:
        dev = slcan.slcanBus(PORT[0], bitrate=1000000)
        dev.open()
        print('Connection found at port ', PORT[0])
    except:
        dev = slcan.slcanBus(PORT[1], bitrate=1000000)
        dev.open()
        print('Connection found at port ', PORT[1])

    yaw = YAW_MID
    pitch = PITCH_MID

    def user_callback(image, svg_canvas):
        nonlocal last_time
        start_time = time.monotonic()
        objs = engine.DetectWithImage(image, threshold=args.threshold,
                                      keep_aspect_ratio=True, relative_coord=True,
                                      top_k=args.top_k)
        end_time = time.monotonic()

        obj = choose_obj(objs, start_time)
        if obj:
            # if labels:
            #     print(labels[obj.label_id], 'score = ', obj.score)
            # else:
            #     print('score = ', obj.score)
            [x1, y1, x2, y2] = obj.bounding_box.flatten().tolist()
            # print(x1, y1, x2, y2)
            # calculate pixel coords
            pix_x = (x1 + x2) * X_PIXEL/2  # 640/2 = 320
            pix_y = (y1 + y2) * Y_PIXEL/2  # 480/2 = 240
            # calculate angles with respect to center
            # TODO: an accurate parameter replacing 480 needs to be calculated
            yaw = math.atan((pix_x - X_PIXEL/2) / CAMREA_PARAM) * \
                1800 / math.pi + YAW_MID
            pitch = math.atan((pix_y - Y_PIXEL/2) / CAMREA_PARAM) * \
                1800 / math.pi + PITCH_MID
            sendMessage(dev, yaw, pitch)
        else:
            print('No object detected!')

        text_lines = [
            'Inference: %.2f ms' % ((end_time - start_time) * 1000),
            'FPS: %.2f fps' % (1.0/(end_time - last_time)),
        ]
        # print(' '.join(text_lines))
        last_time = end_time
        generate_svg(svg_canvas, objs, labels, text_lines)

    result = gstreamer.run_pipeline(user_callback)


if __name__ == '__main__':
    main()
