from threading import Thread, Event
import time

# Задежка в опросе (сек)
_THREAD_DELAY = 0.02


class ThreadDIO(Thread):
    def __init__(self):
        super().__init__()

        self.__devices = []
        self.event_stop = Event()

    def addDevice(self, dev):
        self.__devices.append(dev)

    def removeDevice(self, dev):
        self.__devices.remove(dev)
        if len(self.__devices) == 0:
            self.event_stop.set()

    def run(self):
        # self.logger.info('ThreadDIO start')
        # print('ThreadDIO start')
        need_stop = False
        while not need_stop:
            for dev in self.__devices:
                dev.poll()
            need_stop = self.event_stop.wait(_THREAD_DELAY)
        print('ThreadDIO finish')

    def stop(self):
        self.event_stop.set()
        # time.sleep(_THREAD_DELAY*2)
        # self.logger.debug('ThreadDIO stop')
