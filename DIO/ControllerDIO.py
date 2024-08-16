import time
from sys import platform

from Common.LoggerFormat import LoggerFormat
from Devices.DIO.config_dio import COLOR_NONE, COLOR_GREEN
from ObservedEvents.Observed import *

from Devices.DIO.RpiDeviceDIO import RpiDeviceDIO
from Devices.DIO.ThreadDIO import ThreadDIO


# ======================================================================
# События
# событие нажатия кнопки
# номер кнопки от 1 до 8
# EVNT_DIO_BTN_PUSH
# ======================================================================

# Разъём подключения подсветки NFC
XP_NFC = 7

# задержка перед закрытем после открытия
# сек
_DELAY_CLOSE = 5

# Номера кнопок
MAKET_BTN_1 = 4
MAKET_BTN_2 = 6
MAKET_BTN_3 = 8


class ControllerDIO(Observed):
    def __init__(self, controllerDevices=None, need_connect=True):
        super().__init__()

        if controllerDevices is None:
            self.loggerFormat = LoggerFormat('ControllerDIO')
            self.logger = self.loggerFormat.logger
            self.nfc_backlight = None
        else:
            self.logger = controllerDevices.get_logger()
            self.nfc_backlight = controllerDevices.get_config().nfc_backlight

        self.device = RpiDeviceDIO(controllerDevices, need_connect=need_connect)
        self.thread = None
        if need_connect:
            self.thread = ThreadDIO()
            self.thread.addDevice(self.device)

            self.logger.info(F'ControllerDIO started with nfc_backlight') if self.nfc_backlight else self.logger.info(F'ControllerDIO started without nfc_backlight')
        else:
            self.logger.debug('ControllerDIO was not connected')

        self.running = False

        self.device.observers_add(self)

    def run(self):
        if platform == 'win32':
            self.logger.error('UBrain not supported in windows')
            return

        if self.thread is not None and not self.running:
            self.logger.debug('ControllerDIO run')
            self.thread.start()
            self.running = True

    def stop(self):
        if self.thread is not None:
            self.thread.stop()
            self.running = False

    # запереть замок
    def lock(self, lock):
        self.device.lock(lock)

    # отпререть замок
    def unlock(self, lock):
        self.device.unlock(lock)

    def open_barrier(self):
        self.logger.info('open barrier')

        self.device.set_DO(1, 1)
        # ждать открытия
        # ждать проезда и осовобождения зоны
        time.sleep(_DELAY_CLOSE)
        self.device.set_DO(1, 0)

    # def close_barrier(self):
    #     self.device.set_DO(1, 0)

    # номер кнопки от 1 до 12
    def set_btn_color_exclusive(self, btn):
        self.device.set_btn_active_exclusive(btn)

    # номер кнопки от 1 до 12
    def switch_btn_color_to_enabled(self, btn):
        self.device.switch_btn_color_to_enabled(btn)

    # номер кнопки от 1 до 12
    def switch_btn_color_to_disabled(self, btn):
        self.device.switch_btn_color_to_disabled(btn)

    # номер кнопки от 1 до 12
    def set_btn_color_disabled(self, btn):
        self.device.set_btn_color_disabled(btn)

    # номер кнопки от 1 до 12
    def set_btn_color_active(self, btn):
        self.device.set_btn_color_active(btn)

    def set_btn_color(self, btn, clr):
        self.device.set_btn_color(btn=btn, clr=clr)

    # Подсветить кнопки в диапазоне
    def set_btn_range_colors(self, buttons_colors_1, color_1, buttons_colors_2, color_2):
        self.device.set_btn_range_colors(buttons_colors_1, color_1, buttons_colors_2, color_2)

    # Подсветка NFC
    def set_nfc_color_enabled(self):
        if self.nfc_backlight:
            self.device.set_btn_color_enabled(XP_NFC)

    # Подсветка NFC
    def set_nfc_color_disabled(self):
        if self.nfc_backlight:
            self.device.set_btn_color_disabled(XP_NFC)

    # Подсветка NFC
    def set_nfc_color_active(self):
        if self.nfc_backlight:
            self.device.set_btn_color_active(XP_NFC)

    # включить подсветку кнопок
    def poweron_buttons(self):
        self.device.poweron_buttons()

    # выключить подсветку кнопок
    def poweroff_buttons(self):
        self.device.poweroff_buttons()

    # подсветить кнопки доступных функций
    def set_functions(self, type_card):
        if type_card == 0:
            self.disable_functions()
        else:
            self.enable_functions(type_card)

    # подсветить кнопки доступных функций
    def enable_functions(self, type_card):
        if type_card > 0:
            self.device.set_btn_color(MAKET_BTN_1, COLOR_GREEN)
        if type_card > 1:
            self.device.set_btn_color(MAKET_BTN_2, COLOR_GREEN)
        if type_card > 2:
            self.device.set_btn_color(MAKET_BTN_3, COLOR_GREEN)

    # погасить кнопки функций
    def disable_functions(self):
        self.device.set_btn_color(MAKET_BTN_1, COLOR_NONE)
        self.device.set_btn_color(MAKET_BTN_2, COLOR_NONE)
        self.device.set_btn_color(MAKET_BTN_3, COLOR_NONE)

    # событие нажатия кнопки
    # номер кнопки от 1 до 8
    def on_button(self, btn):
        # self.logger.debug('btnNumber={}'.format(btn))
        self.fire_event(EVNT_DIO_BTN_PUSH, btn)

    # события от device
    def on_event(self, event_type, event_data):
        if event_type is not None:
            if event_type == EVNT_DIO_BTN_PUSH:
                self.on_button(event_data)
