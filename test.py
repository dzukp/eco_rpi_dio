import sys
import time

sys.path.append('../..')

from Devices.DIO.ControllerDIO import  ControllerDIO


if __name__ == '__main__':
    controller = ControllerDIO()
    controller.run()

    step = 0
    while True:
        time.sleep(3)
        if step == 0:
            controller.switch_btn_color_to_enabled(0)
            controller.switch_btn_color_to_disabled(1)
            print('-> DO:', 0, 1)
        else:
            controller.switch_btn_color_to_disabled(0)
            controller.switch_btn_color_to_enabled(1)
            print('-> DO:', 1, 0)
        step = (step + 1) % 2
