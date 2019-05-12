# Copyright 2019 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from PIL import Image
from gi.repository import GLib, GObject, Gst, GstBase
import sys
from functools import partial
import svgwrite
import time

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstBase', '1.0')

X_PIXEL = 640
Y_PIXEL = 480
ROTATE_180 = False

GObject.threads_init()
Gst.init(None)


def on_bus_message(bus, message, loop):
    t = message.type
    if t == Gst.MessageType.EOS:
        loop.quit()
    elif t == Gst.MessageType.WARNING:
        err, debug = message.parse_warning()
        sys.stderr.write('Warning: %s: %s\n' % (err, debug))
    elif t == Gst.MessageType.ERROR:
        err, debug = message.parse_error()
        sys.stderr.write('Error: %s: %s\n' % (err, debug))
        loop.quit()
    return True


def on_new_sample(sink, screen_size, appsink_size, user_function):
    start = time.monotonic()
    sample = sink.emit('pull-sample')
    buf = sample.get_buffer()
    result, mapinfo = buf.map(Gst.MapFlags.READ)
    if result:
        img = Image.frombytes(
            'RGB', (appsink_size[0], appsink_size[1]), mapinfo.data, 'raw')
        if ROTATE_180:
            img = img.rotate(180)
        # svg_canvas = svgwrite.Drawing(
        #     '', size=(screen_size[0], screen_size[1]))

        # overlay.set_property('data', svg_canvas.tostring())
        user_function(img)
    buf.unmap(mapinfo)
    end = time.monotonic()
    print('decode time', (end-start)*1000, 'ms')
    return Gst.FlowReturn.OK


def detectCoralDevBoard():
    try:
        if 'MX8MQ' in open('/sys/firmware/devicetree/base/model').read():
            print('Detected Edge TPU dev board.')
            return True
    except:
        pass
    return False


def run_pipeline(user_function,
                 src_size=(X_PIXEL, Y_PIXEL),
                 appsink_size=(320, 180)):
    PIPELINE = 'v4l2src device=/dev/video1 ! {src_caps} ! {leaky_q} '
    SRC_CAPS = 'video/x-raw,format=YUY2,width={width},height={height},framerate=60/1'
    PIPELINE += """ ! glupload ! tee name=t
        t. ! {leaky_q} ! glfilterbin filter=glcolorscale
            ! videoconvert n-threads=3 ! {sink_caps} ! {sink_element}
    """

    SINK_ELEMENT = 'appsink name=appsink sync=false emit-signals=true max-buffers=0 drop=true'
    SINK_CAPS = 'video/x-raw,format=RGB,width={width},height={height}'
    LEAKY_Q = 'queue max-size-buffers=0 leaky=downstream'

    src_caps = SRC_CAPS.format(width=src_size[0], height=src_size[1])
    sink_caps = SINK_CAPS.format(width=appsink_size[0], height=appsink_size[1])
    pipeline = PIPELINE.format(leaky_q=LEAKY_Q,
                               src_caps=src_caps, sink_caps=sink_caps,
                               sink_element=SINK_ELEMENT)

    print('Gstreamer pipeline: ', pipeline)
    pipeline = Gst.parse_launch(pipeline)

    appsink = pipeline.get_by_name('appsink')
    appsink.connect('new-sample', partial(on_new_sample,
                                          screen_size=src_size,
                                          appsink_size=appsink_size, user_function=user_function))
    loop = GObject.MainLoop()

    # Set up a pipeline bus watch to catch errors.
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect('message', on_bus_message, loop)

    # Run pipeline.
    pipeline.set_state(Gst.State.PLAYING)
    try:
        loop.run()
    except:
        pass

    # Clean up.
    pipeline.set_state(Gst.State.NULL)
    while GLib.MainContext.default().iteration(False):
        pass
