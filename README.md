# OSU-RM-tpu
This is an auto detection project running on google coral tpu. It is supported by python API. The goal of this project is to get high performance detection for armor boards in the RoboMaster competition. The project is tested on a coral tpu and achieved 40-50 fps. The models provided in ```/models``` are not garanteed to run on any camera. Should try to create your own dataset using your camera and train a model to achieve higher accuracy.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development. For more information, check [instructions from google](https://coral.withgoogle.com/docs/dev-board/get-started/).

### Prerequisites

- Google tpu dev board with system installed
- Trained model
- Camera supporting high frame rate YUY2 output
- Clone the project into a local directory in tpu
```
git clone https://github.com/PokerBox/OSU-RM-tpu.git
```

### Configurations

- All parameters are located in ```detect.py``` and ```gstreamer.py```

## Running detection

- Enter the project folder and run the detection program
```
python3 detect.py
```

- You can enable debug mode by
```
python3 detect.py debug
```
This will render a video stream with the detected object on your screen but the performance will be suppressed. 

## Submodules

- Check how the models are trained in another repository to be put here.

## Lisence

- TODO
