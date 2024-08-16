"""
Файл конфишурации работы с кнопками и DIO
"""

# количество обслуживаемых кнопок
BTN_QUANTITY = 12


# Цвета кнопок
COLOR_NONE = 0

# # кнопочная плата с wago разъёмами
# COLOR_BLUE = 1
# COLOR_GREEN = 2
# COLOR_RED = 3
# COLOR_MAGENTA = 4
# COLOR_YELLOW = 5
# COLOR_LIGHTBLUE = 6
# COLOR_WHITE = 7

# кнопочная плата с IDC SMD разъёмами
COLOR_BLUE = 2
COLOR_GREEN = 1
COLOR_RED = 3
COLOR_MAGENTA = 4
COLOR_YELLOW = 5
COLOR_LIGHTBLUE = 6
COLOR_WHITE = 7

# # кнопочная плата с IDC SMD разъёмами с кнопками сделанными ЭКО
# COLOR_BLUE = 2
# COLOR_GREEN = 3
# COLOR_RED = 1
# COLOR_MAGENTA = 6
# COLOR_YELLOW = 4
# COLOR_LIGHTBLUE = 5
# COLOR_WHITE = 7


# задержка перед закрытем после открытия замка
# сек
DELAY_LOCK = 2


# порог дребезга
THRESHOLD_BOUNCE = 1


# порог залипания
THRESHOLD_STICKY = 100
# количество циклов отключения залипшей кнопки
STICKY_OFF = 10

# Назначения кнопок, начиная с 1
BTN_UNLOCK = 1  # кнопка отпирания замков
BTN_LOCK = 3  # кнопка запирания замков
BTN_FINISH = 7  # кнопка выхода из режима
BTN_COLLECT = 2  # Кнопка инкассации

# Разрешенные в режиме сервиса кнопки
BTN_SERVICE_ENABLED = [1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, BTN_FINISH]

# Разрешенные в режиме уборки кнопки
BTN_CLEAN_ENABLED = [4, BTN_FINISH]
