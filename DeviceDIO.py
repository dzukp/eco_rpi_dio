from sys import platform
import time
from collections import namedtuple

from Devices.DIO.quick2wire.i2c import I2CMaster, writing, writing_bytes, reading, reading_into

from Common.LoggerFormat import LoggerFormat
from ObservedEvents.Observed import *

from .config_dio import *

_I2C_ADDRESS = 0x05
_I2C_DIRECTION_READ = 0x0F
_I2C_DIRECTION_WRITE = 0xF0

# Предопределенные цвета
COLOR_BTN_ENABLE = COLOR_BLUE
COLOR_BTN_DISABLE = COLOR_RED
COLOR_BTN_ACTIVE = COLOR_GREEN
COLOR_BTN_PUSH = COLOR_MAGENTA


class DeviceDIO(Observed):
    def __init__(self, controllerDevices=None, need_connect=True):
        super().__init__()

        if controllerDevices is None:
            self.loggerFormat = LoggerFormat('DeviceDIO')
            self.logger = self.loggerFormat.logger
        else:
            self.logger = controllerDevices.get_logger()

        self.need_connect = need_connect

        # self.logger.info('DeviceDIO start')

        self.buttons = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        self.btn_anti_bounce = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

        self.di = 0b00000000

        self.btncollors = [COLOR_BTN_ENABLE, COLOR_BTN_ENABLE, COLOR_BTN_ENABLE, COLOR_BTN_ENABLE, COLOR_BTN_ENABLE, COLOR_BTN_ENABLE, COLOR_BTN_ENABLE, COLOR_BTN_ENABLE, COLOR_BTN_ENABLE, COLOR_BTN_ENABLE, COLOR_BTN_ENABLE, COLOR_BTN_ENABLE]
        self.do = 0b00000000
        self.do_debug = 0

        # массив  срабатываний
        self.btntriggered = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        self.btn_previose_color = self.btncollors.copy()
        self.btn_off = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

        self.i2c_lock = controllerDevices.get_i2c_lock()

        self.running = False

    def init(self, need_connect):
        if platform == 'win32':
            self.logger.error('UBrain not supported in windows')
            return

        if not need_connect:
            return

        # попробовать прочитать из I2C
        # self.logger.debug('test I2C reading address {0}'.format(_I2C_ADDRESS))

        self.i2c_lock.acquire()
        try:
            with I2CMaster(1) as i2c:
                i2c.transaction(writing_bytes(_I2C_ADDRESS, _I2C_DIRECTION_READ))
                response = i2c.transaction(reading(_I2C_ADDRESS, 2))

                self.running = True
                self.logger.debug(F'UBrain I2C {_I2C_ADDRESS} successful connect. {BTN_QUANTITY} buttons')
        except Exception as ex:
            self.logger.error(F'UBrain I2C {_I2C_ADDRESS} connect error')
            self.logger.error(ex)
        finally:
            self.i2c_lock.release()

    def poll(self):
        if not self.running:
            self.init(self.need_connect)

        if not self.running:
            return

        time.sleep(0.02)
        result = self.dio_read()

        if result.status == 1:
            # реагировать на нажатие кнопок
            self._check_buttons(result.buttons & 0xFFF)

            # # реагировать на изменения входов
            # self._check_di(self.di, result.di)
            # self.di = result.di

        # time.sleep(0.005)
        time.sleep(0.02)

        self.dio_write(self.do)
        # time.sleep(0.02)

    def dio_read(self):
        Result = namedtuple('Result', [
            'status',
            'di',
            'buttons'
        ])
        self.i2c_lock.acquire()

        try_max = 15
        try_count = 0
        flag = 'flag write ...'

        try:
            with I2CMaster(1) as i2c:
                # self.di, self.buttons = i2c.transaction(
                #     writing_bytes(_I2C_ADDRESS, _I2C_DIRECTION_READ),
                #     reading(_I2C_ADDRESS, 2))[0]

                # Чтение нажатия кнопок
                old_di = self.di

                t_start = time.perf_counter()

                while flag == 'flag write ...' and try_count < try_max:
                    try:
                        i2c.transaction(writing_bytes(_I2C_ADDRESS, _I2C_DIRECTION_READ))
                        flag = 'data read ...'
                    except:
                        try_count += 1
                        time.sleep(0.002)

                if flag == 'data read ...':
                    time.sleep(0.002)
                    response = i2c.transaction(reading(_I2C_ADDRESS, 3))
                    flag = 'data readed'
                    # self.logger.info(F"Запись 1 байт + Чтение 3 байт {time.perf_counter() - t_start}, {flag}")

                    di, btns1, btns2 = response[0]
                    buttons = (btns2 << 8) | btns1

                    # todo Маску делать на основе используемых кнопок
                    mask_used_buttons = 0xFFF
                    response_sequence = buttons & mask_used_buttons
                    if bin(response_sequence).count('1') == bin(mask_used_buttons).count('1'):
                        # self.logger.debug('Мусорная посылка')
                        return Result(status=0, di=0, buttons=0)
                    else:
                        # self.logger.debug(F'кнопки {buttons}={buttons:012b}, response {response_sequence}={response_sequence:012b}')
                        return Result(status=1, di=di, buttons=buttons)
                    # self.logger.debug('I2C read OK')
                else:
                    self.logger.error(F"DIO I2C read timeout error")
        except Exception as ex:
            # self.logger.error(F"DIO I2C read error. Время={time.perf_counter() - t_start:.4}, {flag}: {ex}")
            # time.sleep(0.01)
            # self.logger.error(F"{ex}")

            # self.running = False
            return Result(status=0, di=0, buttons=0)
        finally:
            self.i2c_lock.release()

    def dio_write(self, d_o):
        self.i2c_lock.acquire()

        try_max = 15
        try_count = 0
        flag = 'flag write ...'

        try:
            # t_start = time.perf_counter()
            with I2CMaster(1) as i2c:
                # self.logger.info(F"Открытие i2c dio: {time.perf_counter() - t_start}")
                # Запись цветов кнопок
                # i2c.transaction(
                #     writing(_I2C_ADDRESS, bytes([_I2C_DIRECTION_WRITE])))
                t_start = time.perf_counter()
                while flag == 'flag write ...' and try_count < try_max:
                    try:
                        i2c.transaction(writing_bytes(_I2C_ADDRESS, _I2C_DIRECTION_WRITE))
                        flag = 'data write ...'
                    except:
                        try_count += 1
                        time.sleep(0.002)

                if flag == 'data write ...':
                    time.sleep(0.0005)
                    i2c.transaction(writing(_I2C_ADDRESS, bytes([self.btncollors[2], self.btncollors[3], self.btncollors[0],
                                                                 self.btncollors[1], self.btncollors[7], self.btncollors[6],
                                                                 self.btncollors[5], self.btncollors[4], self.btncollors[8],
                                                                 self.btncollors[9], self.btncollors[10], self.btncollors[11],
                                                                 d_o])))
                    flag = 'data writed'
                    # self.logger.info(F"Запись 1 байт + Запись 13 байт {time.perf_counter() - t_start}, {flag}")
                    # self.logger.debug('>')

                    # if d_o != self.do_debug:
                    #     self.logger.debug(F'DO {d_o:08b}')
                    #     self.do_debug = d_o

                    # self.logger.debug('DIO I2C write OK')
                else:
                    self.logger.error(F"DIO I2C write timeout error")
        except Exception as ex:
            # self.logger.error(F"DIO I2C write error. Время={time.perf_counter() - t_start:.4}, {flag}: {ex}")
            # time.sleep(0.01)
            # self.logger.error(F"Error: {ex}")

            # self.running = False
            pass
        finally:
            self.i2c_lock.release()

    def _check_di(self, old, new):
        # self.logger.debug("old di={}".format(bin(old)))
        # self.logger.debug("new di={}".format(bin(new)))
        for i in range(8):
            if old >> i & 1 != new >> i & 1:
                self.logger.debug("old di={}".format(bin(old)))
                self.logger.debug("new di={}".format(bin(new)))
                # self.logger.info("di{0} = {1}".format(i+1, new >> i & 1))
                self.on_DI(i + 1, new >> i & 1)

    def _check_buttons(self, fbuttons):
        for i in range(BTN_QUANTITY):
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

                # clr = self.btncollors[i]
                # self.set_btn_color(btn=i+1, clr=COLOR_NONE)
                # time.sleep(0.4)
                # self.set_btn_color(btn=i+1, clr=clr)

                # # сбросить нажатие залипшей кнопки
                # fbuttons &= ~(1 >> i)

        # проверить на мусорную посылку из нескольких единиц
        bb = self.CountBits(fbuttons)
        if bb > 1:
            self.logger.debug('В кнопках много нажатий {}: {:04b} {:04b} {:04b}'.format(bb, (0xF00 & fbuttons) >> 8, (0xF0 & fbuttons) >> 4, 0x0F & fbuttons))

            # все нажатые кнопки пометить залипшими
            for i in range(BTN_QUANTITY):
                if fbuttons >> i & 1 and self.btn_off[i] == 0:
                    # self.logger.debug('MultiSticky button {0}'.format(i + 1))
                    self.btn_previose_color[i] = self.btncollors[i]
                    self.btncollors[i] = COLOR_NONE
                    self.btn_off[i] = STICKY_OFF

            return

        for i in range(BTN_QUANTITY):
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

    # def _check_buttons_8(self, fbuttons):
    #     for i in range(8):
    #         # антидребезг и залипание
    #         if fbuttons >> i & 1:
    #             self.btn_anti_bounce[i] += 1
    #             self.btntriggered[i] += 1
    #         else:
    #             self.btn_anti_bounce[i] = 0
    #             self.btntriggered[i] = 0
    #
    #         # очистка залипших кнопок
    #         if self.btn_off[i] > 0:
    #             self.btn_off[i] -= 1
    #             if self.btn_off[i] == 0:
    #                 self.btncollors[i] = self.btn_previose_color[i]
    #                 # self.logger.debug('Power button {0}'.format(i+1))
    #         # проверить залипание кнопок
    #         elif self.btntriggered[i] > THRESHOLD_STICKY:
    #             self.logger.debug('Sticky button {0}'.format(i+1))
    #             self.btn_previose_color[i] = self.btncollors[i]
    #             self.btncollors[i] = COLOR_NONE
    #             self.btn_off[i] = STICKY_OFF
    #
    #             # clr = self.btncollors[i]
    #             # self.set_btn_color(btn=i+1, clr=COLOR_NONE)
    #             # time.sleep(0.4)
    #             # self.set_btn_color(btn=i+1, clr=clr)
    #
    #             # # сбросить нажатие залипшей кнопки
    #             # fbuttons &= ~(1 >> i)
    #
    #     # проверить на мусорную посылку из нескольких единиц
    #     bb = self.CountBits(fbuttons)
    #     if bb > 1:
    #         self.logger.debug('В кнопках много нажатий {}: {:04b} {:04b} {:04b}'.format(bb, (0xF00 & fbuttons) >> 8, (0xF0 & fbuttons) >> 4, 0x0F & fbuttons))
    #
    #         # все нажатые кнопки пометить залипшими
    #         for i in range(8):
    #             if fbuttons >> i & 1 and self.btn_off[i] == 0:
    #                 # self.logger.debug('MultiSticky button {0}'.format(i + 1))
    #                 self.btn_previose_color[i] = self.btncollors[i]
    #                 self.btncollors[i] = COLOR_NONE
    #                 self.btn_off[i] = STICKY_OFF
    #
    #         return
    #
    #     for i in range(8):
    #         # проверить смену состояния кнопки и признак нажатия кнопки
    #         if self.btn_anti_bounce[i] > THRESHOLD_BOUNCE:
    #             if self.buttons[i] == 0:
    #                 # послать событие реакции на нажатие кнопки
    #                 self.logger.debug('Push button {0}'.format(i+1))
    #                 self.on_button(i + 1)
    #
    #             self.buttons[i] = 1
    #             # self.set_btn_color(i+1, COLOR_BTN_PUSH)
    #         elif self.buttons[i] == 1:
    #             # self.logger.debug('Unpush button {0}'.format(i + 1))
    #             self.buttons[i] = 0
    #             # self.set_btn_color(i+1, COLOR_BTN_ENABLE)
    #             # # послать событие реакции на нажатие и отпускание кнопки
    #             # self.on_button(i + 1)

    # событие появления входа на пине DI
    # pin on 1 до 8
    def on_DI(self, pin, val):
        self.logger.debug('On change DI {0} = {1}'.format(pin, val))

    # событие нажатия кнопки
    # номер кнопки от 1 до 12
    def on_button(self, btn):
        # self.logger.debug('btn={}'.format(btn))
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

    # номер кнопки от 1 до BTN_QUANTITY
    def set_btn_active_exclusive(self, btn):
        # здесь работаем только с BTN_QUANTITY кнопками функций
        for i in range(BTN_QUANTITY):
            if i == btn-1:
                self.btncollors[i] = COLOR_BTN_ACTIVE
            elif self.btncollors[i] == COLOR_BTN_ACTIVE:
                self.btncollors[i] = COLOR_BTN_ENABLE

        self.dio_write(self.do)
        # self.logger.debug('Exclusive button {0}'.format(btn))

    def switch_btn_color_to_enabled(self, btn):
        if self.btncollors[btn-1] == COLOR_BTN_DISABLE:
            self.set_btn_color(btn, COLOR_BTN_ENABLE)

    def switch_btn_color_to_disabled(self, btn):
        if self.btncollors[btn-1] != COLOR_NONE:
            self.set_btn_color(btn, COLOR_BTN_DISABLE)

    def set_btn_color_enabled(self, btn):
        self.set_btn_color(btn, COLOR_BTN_ENABLE)

    def set_btn_color_disabled(self, btn):
        self.set_btn_color(btn, COLOR_BTN_DISABLE)

    def set_btn_color_active(self, btn):
        self.set_btn_color(btn, COLOR_BTN_ACTIVE)

    # номер кнопки от 1 до BTN_QUANTITY
    def set_btn_range_colors(self, buttons_colors_1, color_1, buttons_colors_2, color_2):
        # здесь работаем только с кнопками функций
        for i in range(BTN_QUANTITY):
            if (i+1) in buttons_colors_1:
                self.btncollors[i] = color_1
            elif (i+1) in buttons_colors_2:
                self.btncollors[i] = color_2

        self.dio_write(self.do)
        # self.logger.debug('Exclusive button {0}'.format(btn))

    # запереть замок
    def lock(self, lock):
        d_o = self.do
        # self.set_DO(2, 0)
        # self.set_DO(1, 1)
        #
        # # выждать паузу
        # time.sleep(DELAY_LOCK)

        d_o = self.dio_set_do(d_o, 1, 0)
        d_o = self.dio_set_do(d_o, 2, 1)
        d_o = self.dio_set_do(d_o, 3, 0)
        d_o = self.dio_set_do(d_o, 4, 1)
        d_o = self.dio_set_do(d_o, 5, 0)
        d_o = self.dio_set_do(d_o, 6, 1)
        self.do = d_o

        self.dio_write(d_o)

        # выждать паузу
        time.sleep(DELAY_LOCK)

        d_o = self.dio_set_do(d_o, 1, 0)
        d_o = self.dio_set_do(d_o, 2, 0)
        d_o = self.dio_set_do(d_o, 3, 0)
        d_o = self.dio_set_do(d_o, 4, 0)
        d_o = self.dio_set_do(d_o, 5, 0)
        d_o = self.dio_set_do(d_o, 6, 0)

        self.do = d_o
        self.dio_write(d_o)

        # self.logger.debug('Lock {0}'.format(lock))

    # отпререть замок
    def unlock(self, lock):
        d_o = self.do
        # self.set_DO(2, 0)
        # self.set_DO(1, 1)
        #
        # # выждать паузу
        # time.sleep(DELAY_LOCK)

        d_o = self.dio_set_do(d_o, 1, 1)
        d_o = self.dio_set_do(d_o, 2, 0)
        d_o = self.dio_set_do(d_o, 3, 1)
        d_o = self.dio_set_do(d_o, 4, 0)
        d_o = self.dio_set_do(d_o, 5, 1)
        d_o = self.dio_set_do(d_o, 6, 0)

        self.do = d_o
        self.dio_write(d_o)

        # выждать паузу
        time.sleep(DELAY_LOCK)

        d_o = self.dio_set_do(d_o, 1, 0)
        d_o = self.dio_set_do(d_o, 2, 0)
        d_o = self.dio_set_do(d_o, 3, 0)
        d_o = self.dio_set_do(d_o, 4, 0)
        d_o = self.dio_set_do(d_o, 5, 0)
        d_o = self.dio_set_do(d_o, 6, 0)

        self.do = d_o
        self.dio_write(d_o)

        # self.logger.debug('Unlock {0}'.format(lock))

    # pin on 1 до 8
    def dio_set_do(self, d_o, pin, val):
        pin -= 1
        if val == 1:
            d_o |= (1 << pin)
        else:
            d_o &= ~(1 << pin)

        return d_o

    def CountBits(self, n):
        return bin(n).count('1')

    # def CountBits16(self, n):
    #     return self.CountBits8(n & 0xFF) + self.CountBits8(n >> 8)
    #
    # def CountBits8(self, n):
    #     if n == 0:
    #         return 0  # Единственный случай, когда ответ 0.
    #     if n == 0xFF:
    #         return 8  # Единственный случай, когда ответ 8.
    #
    #     n = (0x010101*n & 0x249249) % 7  # Считаем число бит по модулю 7.
    #     if n == 0:
    #         return 7  # Гарантированно имеем 7 единичных битов.
    #     return n  # Случай, когда в числе от 1 до 6 единичных битов.

    # выключить подсветку кнопок
    def poweron_buttons(self):
        self.btncollors = [COLOR_BTN_ENABLE]*BTN_QUANTITY

        self.dio_write(self.do)

    # выключить подсветку кнопок
    def poweroff_buttons(self):
        self.btncollors = [COLOR_NONE]*BTN_QUANTITY

        self.dio_write(self.do)
