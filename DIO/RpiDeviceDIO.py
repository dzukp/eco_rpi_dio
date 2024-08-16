from sys import platform
import time
from collections import namedtuple

import gpiozero
from gpiozero import LED, Button
from gpiozero.pins.mock import MockFactory

from Common.LoggerFormat import LoggerFormat
from ObservedEvents.EventTypes import *
from ObservedEvents.Observed import Observed

_I2C_ADDRESS = 0x05
_I2C_DIRECTION_READ = 0x0F
_I2C_DIRECTION_WRITE = 0xF0

# Входа DI в качестве кнопок
DIO_BTN_1 = 1
# Значение сигнала нажатия кнопки
DIO_BTN_PUSH_SIGNAL = 0

# Цвета кнопок
COLOR_NONE = 0
COLOR_BLUE = 2
COLOR_GREEN = 1
COLOR_RED = 3
COLOR_MAGENTA = 4
COLOR_YELLOW = 5
COLOR_LIGHTBLUE = 6
COLOR_WHITE = 7

# Предопределенные цвета
COLOR_BTN_ENABLE = COLOR_BLUE
COLOR_BTN_DISABLE = COLOR_RED
COLOR_BTN_ACTIVE = COLOR_GREEN
COLOR_BTN_PUSH = COLOR_LIGHTBLUE


# порог дребезга
THRESHOLD_BOUNCE = 1

# задержка перед закрытем после открытия замка
# сек
_DELAY_LOCK = 2

# порог залипания
THRESHOLD_STICKY = 100
# количество циклов отключения залипшей кнопки
STICKY_OFF = 10


class RpiDeviceDIO(Observed):
    def __init__(self, controllerDevices=None, need_connect=True):
        super().__init__()

        if controllerDevices is None:
            self.loggerFormat = LoggerFormat('RpiDeviceDIO')
            self.logger = self.loggerFormat.logger
        else:
            self.logger = controllerDevices.get_logger()

        self.need_connect = need_connect

        # self.logger.info('DeviceDIO start')

        self.buttons = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        self.btn_anti_bounce = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

        self.di = 0b11111111
        # self.di = 0b00000000

        self.btncollors = [COLOR_BTN_ENABLE, COLOR_BTN_ENABLE, COLOR_BTN_ENABLE, COLOR_BTN_ENABLE, COLOR_BTN_ENABLE, COLOR_BTN_ENABLE, COLOR_BTN_ENABLE, COLOR_BTN_ENABLE, COLOR_BTN_ENABLE, COLOR_BTN_ENABLE, COLOR_BTN_ENABLE, COLOR_BTN_ENABLE]
        self.do = 0b00000000

        # массив  срабатываний
        self.btntriggered = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        self.btn_previose_color = self.btncollors.copy()
        self.btn_off = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

        self.rpi_leds = [LED(26), LED(29)]
        self.rpi_buttons = [Button(19), Button(16)]

        self.running = False

    def init(self, need_connect):
        if platform == 'win32':
            self.logger.error('RPI IO not supported in windows')
            return

        if not need_connect:
            return

        self.running = True
        self.logger.debug(F'RPI IO successful init.')

    def poll(self):
        if not self.running:
            self.init(self.need_connect)

        if not self.running:
            print('is_not_running. Exit...')
            return

        result = self.dio_read()

        if result.status == 1:
            # реагировать на нажатие кнопок
            self._check_buttons_8(result.buttons & 0xFF)

            # реагировать на изменения входов
            # self._check_di(self.di, result.di)
            self.di = result.di

        # time.sleep(0.005)

        self.dio_write(self.do)

    def _check_di(self, old, new):
        # self.logger.debug("old di={}".format(bin(old)))
        # self.logger.debug("new di={}".format(bin(new)))
        for i in range(8):
            if old >> i & 1 != new >> i & 1:
                # self.logger.debug("old di={}".format(bin(old)))
                # self.logger.debug("new di={}".format(bin(new)))
                # self.logger.info("di{0} = {1}".format(i+1, new >> i & 1))
                self.on_DI(i + 1, new >> i & 1)

    def _check_buttons_8(self, fbuttons):
        for i in range(8):
            # антидребезг и залипание
            if fbuttons >> i & 1:
                self.btn_anti_bounce[i] += 1
                self.btntriggered[i] += 1
            else:
                self.btn_anti_bounce[i] = 0
                self.btntriggered[i] = 0

            # очистка залипших кнопок
            if self.btn_off[i] > 0:
                self.btn_off[i] -= 1
                if self.btn_off[i] == 0:
                    self.btncollors[i] = self.btn_previose_color[i]
                    # self.logger.debug('Power button {0}'.format(i+1))
            # проверить залипание кнопок
            elif self.btntriggered[i] > THRESHOLD_STICKY:
                self.logger.debug('Sticky button {0}'.format(i+1))
                self.btn_previose_color[i] = self.btncollors[i]
                self.btncollors[i] = COLOR_NONE
                self.btn_off[i] = STICKY_OFF

        # проверить на мусорную посылку из нескольких единиц
        bb = self.CountBits8(fbuttons)
        if bb > 1:
            # self.logger.debug('В кнопках много нажатий {}: {:04b} {:04b} {:04b}'.format(bb, (0xF00 & fbuttons) >> 8, (0xF0 & fbuttons) >> 4, 0x0F & fbuttons))

            # все нажатые кнопки пометить залипшими
            for i in range(8):
                if fbuttons >> i & 1 and self.btn_off[i] == 0:
                    # self.logger.debug('MultiSticky button {0}'.format(i + 1))
                    self.btn_previose_color[i] = self.btncollors[i]
                    self.btncollors[i] = COLOR_NONE
                    self.btn_off[i] = STICKY_OFF

            return

        for i in range(8):
            # проверить смену состояния кнопки и признак нажатия кнопки
            if self.btn_anti_bounce[i] > THRESHOLD_BOUNCE:
                if self.buttons[i] == 0:
                    # послать событие реакции на нажатие кнопки
                    self.logger.debug('Push button {0}'.format(i+1))
                    self.on_button(i + 1)

                self.buttons[i] = 1
                # self.set_btn_color(i+1, COLOR_BTN_PUSH)
            elif self.buttons[i] == 1:
                # self.logger.debug('Unpush button {0}'.format(i + 1))
                self.buttons[i] = 0
                # self.set_btn_color(i+1, COLOR_BTN_ENABLE)
                # # послать событие реакции на нажатие и отпускание кнопки
                # self.on_button(i + 1)

    # событие появления входа на пине DI
    # pin on 1 до 8
    def on_DI(self, pin, val):
        # self.logger.debug(F"On change DI {pin} = {val}")
        if pin == DIO_BTN_1 and val == DIO_BTN_PUSH_SIGNAL:
            self.on_button(DIO_BTN_1)

    # событие нажатия кнопки
    # номер кнопки от 1 до 12
    def on_button(self, btn):
        self.logger.debug(F"push button {btn}")
        self.fire_event(EVNT_DIO_BTN_PUSH, btn)

    # pin on 1 до 8
    def set_DO(self, pin, val):
        pin -= 1
        if val == 1:
            self.do |= (1 << pin)
        else:
            self.do &= ~(1 << pin)

    # номер кнопки от 1 до 12
    def set_btn_color(self, btn, clr):
        if 1 <= btn <= 12 and COLOR_NONE <= clr <= COLOR_WHITE:
            self.btncollors[btn-1] = clr
        self.dio_write(self.do)

    # номер кнопки от 1 до 8
    def set_btn_active_exclusive(self, btn):
        # здесь работаем только с 8 кнопками функций
        for i in range(8):
            if i == btn-1:
                self.btncollors[i] = COLOR_BTN_ACTIVE
            elif self.btncollors[i] == COLOR_BTN_ACTIVE:
                self.btncollors[i] = COLOR_BTN_ENABLE

        self.dio_write(self.do)
        # self.logger.debug('Exclusive button {0}'.format(btn))

    # номер кнопки от 1 до 8
    def set_btn_active_exclusive_in_range(self, btn, btn_range_1=1, btn_range_2=8):
        # здесь работаем только с 8 кнопками функций
        for i in range(btn_range_1-1, btn_range_2):
            if i+1 == btn:
                self.btncollors[i] = COLOR_BTN_ACTIVE
            elif self.btncollors[i] == COLOR_BTN_ACTIVE:
                self.btncollors[i] = COLOR_BTN_ENABLE

        self.dio_write(self.do)
        # self.logger.debug('Exclusive button {0}'.format(btn))

    def switch_btn_color_to_enabled(self, btn):
        try:
            led = self.rpi_leds[btn]
            led.on()
        except IndexError:
            pass

    def set_btn_color_enabled(self, btn):
        pass

    def set_btn_color_disabled(self, btn):
        try:
            led = self.rpi_leds[btn]
            led.off()
        except IndexError:
            pass

    def set_btn_color_active(self, btn):
        pass

    # выключить подсветку кнопок
    def poweroff_buttons(self):
        pass

    # запереть замок
    def lock(self, lock):
        pass

        # self.logger.debug('Lock {0}'.format(lock))

    # отпререть замок
    def unlock(self, lock):
        pass

        # self.logger.debug('Unlock {0}'.format(lock))

    # Открыть шлагбаум через 5 канал моторной платы
    def open_barrier(self):
        pass

    # pin on 1 до 8
    def dio_set_do(self, d_o, pin, val):
        pin -= 1
        if val == 1:
            d_o |= (1 << pin)
        else:
            d_o &= ~(1 << pin)

        return d_o

    def dio_write(self, d_o):
        pass

    def dio_read(self):
        Result = namedtuple('Result', [
            'status',
            'di',
            'buttons'
        ])
        buttons = 0
        for i, button in enumerate(self.rpi_buttons):
            if button.is_pressed:
                buttons |= (1 << i)
        print('dio_read', buttons)
        return Result(status=1, di=0, buttons=buttons)

    def CountBits16(self, n):
        return self.CountBits8(n & 0xFF) + self.CountBits8(n >> 8)

    def CountBits8(self, n):
        if n == 0:
            return 0  # Единственный случай, когда ответ 0.
        if n == 0xFF:
            return 8  # Единственный случай, когда ответ 8.

        n = (0x010101*n & 0x249249) % 7  # Считаем число бит по модулю 7.
        if n == 0:
            return 7  # Гарантированно имеем 7 единичных битов.
        return n  # Случай, когда в числе от 1 до 6 единичных битов.
