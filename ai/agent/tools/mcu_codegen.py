# -*- coding: utf-8 -*-
"""
Инструменты генерации шаблонов кода периферии микроконтроллеров STM32.

Формируют заготовки кода инициализации на основе HAL (Hardware Abstraction
Layer) по параметрам, полученным от агента. Генерация выполняется по
параметризованным шаблонам, что гарантирует синтаксическую корректность
структур инициализации и освобождает языковую модель от воспроизведения
кода по памяти.
"""
import re

from ai.agent.tool_base import Tool, ToolResult, ToolContext

_GPIO_MODES = {
    'output': 'GPIO_MODE_OUTPUT_PP',
    'output_open_drain': 'GPIO_MODE_OUTPUT_OD',
    'input': 'GPIO_MODE_INPUT',
    'analog': 'GPIO_MODE_ANALOG',
    'alternate': 'GPIO_MODE_AF_PP',
}

_GPIO_PULLS = {
    'none': 'GPIO_NOPULL',
    'up': 'GPIO_PULLUP',
    'down': 'GPIO_PULLDOWN',
}

_GPIO_SPEEDS = {
    'low': 'GPIO_SPEED_FREQ_LOW',
    'medium': 'GPIO_SPEED_FREQ_MEDIUM',
    'high': 'GPIO_SPEED_FREQ_HIGH',
    'very_high': 'GPIO_SPEED_FREQ_VERY_HIGH',
}


def _split_peripheral(peripheral: str) -> tuple[str, str]:
    """Разбирает имя периферии ('USART1', 'I2C1') на тип ('USART', 'I2C') и номер ('1')."""
    match = re.fullmatch(r'(.+?)(\d+)', peripheral.strip())
    if match is None:
        raise ValueError(f'Некорректное имя периферии: "{peripheral}". Пример: USART1, SPI1, I2C1.')
    return match.group(1).upper(), match.group(2)


class GpioCodeTool(Tool):
    """Генерация шаблона кода инициализации GPIO."""
    name = 'generate_gpio_code'
    description = (
        'Генерирует шаблон C-кода инициализации вывода GPIO микроконтроллера STM32 (HAL). '
        'Используй при настройке входов, выходов и аналоговых выводов.')
    parameters = {
        'port': {'type': 'string', 'required': True,
                 'description': 'буква порта, например "A" для GPIOA'},
        'pin': {'type': 'integer', 'required': True,
                'description': 'номер вывода, например 5 для PA5'},
        'mode': {'type': 'string', 'required': False,
                 'description': 'режим работы вывода',
                 'enum': list(_GPIO_MODES.keys())},
        'pull': {'type': 'string', 'required': False,
                 'description': 'подтяжка вывода',
                 'enum': list(_GPIO_PULLS.keys())},
        'speed': {'type': 'string', 'required': False,
                  'description': 'скорость фронта вывода',
                  'enum': list(_GPIO_SPEEDS.keys())},
        'label': {'type': 'string', 'required': False,
                  'description': 'произвольное имя сигнала для комментария, например LED1'},
    }

    def _execute(self, arguments: dict, context: ToolContext | None) -> ToolResult:
        port = arguments['port'].strip().upper()
        if not re.fullmatch(r'[A-Z]', port):
            return ToolResult(success=False, error='Параметр "port" должен быть одной буквой: A, B, C и т.д.')

        pin = arguments['pin']
        if not 0 <= pin <= 15:
            return ToolResult(success=False, error='Параметр "pin" должен быть числом от 0 до 15.')

        mode = _GPIO_MODES[arguments.get('mode', 'output')]
        pull = _GPIO_PULLS[arguments.get('pull', 'none')]
        speed = _GPIO_SPEEDS[arguments.get('speed', 'low')]
        label = arguments.get('label', '')
        pin_name = f'P{port}{pin}'

        comment = f' {label} ({pin_name})' if label else f' {pin_name}'
        code = (
            f'/* GPIO initialization:{comment} */\n'
            f'__HAL_RCC_GPIO{port}_CLK_ENABLE();\n'
            f'\n'
            f'GPIO_InitTypeDef GPIO_InitStruct = {{0}};\n'
            f'GPIO_InitStruct.Pin = GPIO_PIN_{pin};\n'
            f'GPIO_InitStruct.Mode = {mode};\n'
            f'GPIO_InitStruct.Pull = {pull};\n'
            f'GPIO_InitStruct.Speed = {speed};\n'
            f'HAL_GPIO_Init(GPIO{port}, &GPIO_InitStruct);\n')
        return ToolResult(success=True, output=code)


class UartCodeTool(Tool):
    """Генерация шаблона кода инициализации UART."""
    name = 'generate_uart_code'
    description = (
        'Генерирует шаблон C-кода инициализации UART/USART микроконтроллера STM32 (HAL) '
        'с настройкой выводов TX/RX. Используй при организации последовательного интерфейса.')
    parameters = {
        'uart': {'type': 'string', 'required': False,
                 'description': 'имя периферии', 'enum': ['USART1', 'USART2', 'USART3', 'UART4', 'USART6']},
        'baud_rate': {'type': 'integer', 'required': False,
                      'description': 'скорость обмена, бит/с (например 115200)'},
        'data_bits': {'type': 'string', 'required': False,
                      'description': 'длина слова', 'enum': ['8', '9']},
        'stop_bits': {'type': 'string', 'required': False,
                      'description': 'число стоповых бит', 'enum': ['1', '2']},
        'parity': {'type': 'string', 'required': False,
                   'description': 'контроль чётности', 'enum': ['none', 'even', 'odd']},
    }

    def _execute(self, arguments: dict, context: ToolContext | None) -> ToolResult:
        peripheral = arguments.get('uart', 'USART1')
        try:
            kind, number = _split_peripheral(peripheral)
        except ValueError as e:
            return ToolResult(success=False, error=str(e))

        baud_rate = arguments.get('baud_rate', 115200)
        if baud_rate <= 0:
            return ToolResult(success=False, error='Скорость обмена должна быть положительной.')

        word_length = 'UART_WORDLENGTH_' + arguments.get('data_bits', '8') + 'B'
        stop_bits = 'UART_STOPBITS_' + arguments.get('stop_bits', '1')
        parity = {'none': 'UART_PARITY_NONE', 'even': 'UART_PARITY_EVEN', 'odd': 'UART_PARITY_ODD'}[
            arguments.get('parity', 'none')]

        handle = f'huart{number.lower()}' if kind == 'UART' else f'h{kind.lower()}{number}'
        instance = f'{kind}{number}'
        tx_pin, rx_pin, gpio_af = self._default_pins(instance)

        code = (
            f'/* UART initialization: {instance}, {baud_rate} baud */\n'
            f'__HAL_RCC_{instance}_CLK_ENABLE();\n'
            f'__HAL_RCC_GPIO{tx_pin[1]}_CLK_ENABLE();\n'
            f'\n'
            f'GPIO_InitTypeDef GPIO_InitStruct = {{0}};\n'
            f'GPIO_InitStruct.Pin = GPIO_PIN_{tx_pin[2:]};\n'
            f'GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;\n'
            f'GPIO_InitStruct.Pull = GPIO_NOPULL;\n'
            f'GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_HIGH;\n'
            f'GPIO_InitStruct.Alternate = {gpio_af};\n'
            f'HAL_GPIO_Init(GPIO{tx_pin[1]}, &GPIO_InitStruct);\n'
            f'\n'
            f'GPIO_InitStruct.Pin = GPIO_PIN_{rx_pin[2:]};\n'
            f'HAL_GPIO_Init(GPIO{rx_pin[1]}, &GPIO_InitStruct);\n'
            f'\n'
            f'{handle}.Instance = {instance};\n'
            f'{handle}.Init.BaudRate = {baud_rate};\n'
            f'{handle}.Init.WordLength = {word_length};\n'
            f'{handle}.Init.StopBits = {stop_bits};\n'
            f'{handle}.Init.Parity = {parity};\n'
            f'{handle}.Init.Mode = UART_MODE_TX_RX;\n'
            f'{handle}.Init.HwFlowCtl = UART_HWCONTROL_NONE;\n'
            f'{handle}.Init.OverSampling = UART_OVERSAMPLING_16;\n'
            f'if (HAL_UART_Init(&{handle}) != HAL_OK)\n'
            f'{{\n'
            f'    Error_Handler();\n'
            f'}}\n')
        return ToolResult(success=True, output=code)

    @staticmethod
    def _default_pins(instance: str) -> tuple[str, str, str]:
        """Стандартные выводы TX/RX для типовых контроллеров серии STM32F1."""
        defaults = {
            'USART1': ('PA9', 'PA10', 'GPIO_AF7_USART1'),
            'USART2': ('PA2', 'PA3', 'GPIO_AF7_USART2'),
            'USART3': ('PB10', 'PB11', 'GPIO_AF7_USART3'),
            'UART4': ('PC10', 'PC11', 'GPIO_AF8_UART4'),
            'USART6': ('PC6', 'PC7', 'GPIO_AF8_USART6'),
        }
        return defaults.get(instance, ('PA9', 'PA10', f'GPIO_AF7_{instance}'))


class SpiCodeTool(Tool):
    """Генерация шаблона кода инициализации SPI."""
    name = 'generate_spi_code'
    description = (
        'Генерирует шаблон C-кода инициализации SPI микроконтроллера STM32 (HAL) '
        'в режиме мастера. Используй при подключении Flash-памяти, дисплеев, '
        'датчиков и других устройств по SPI.')
    parameters = {
        'spi': {'type': 'string', 'required': False,
                'description': 'имя периферии', 'enum': ['SPI1', 'SPI2', 'SPI3']},
        'mode': {'type': 'string', 'required': False,
                 'description': 'режим работы', 'enum': ['master', 'slave']},
        'baud_rate_prescaler': {'type': 'integer', 'required': False,
                                'description': 'делитель частоты шины APB',
                                'enum': [2, 4, 8, 16, 32, 64, 128, 256]},
        'clock_polarity': {'type': 'integer', 'required': False,
                           'description': 'полярность тактового сигнала CPOL', 'enum': [0, 1]},
        'clock_phase': {'type': 'integer', 'required': False,
                        'description': 'фаза тактового сигнала CPHA', 'enum': [0, 1]},
    }

    def _execute(self, arguments: dict, context: ToolContext | None) -> ToolResult:
        peripheral = arguments.get('spi', 'SPI1')
        try:
            kind, number = _split_peripheral(peripheral)
        except ValueError as e:
            return ToolResult(success=False, error=str(e))

        direction = {'master': 'SPI_MODE_MASTER', 'slave': 'SPI_MODE_SLAVE'}[arguments.get('mode', 'master')]
        prescaler = 'SPI_BAUDRATEPRESCALER_' + str(arguments.get('baud_rate_prescaler', 32))
        cpol = 'SPI_POLARITY_' + str(arguments.get('clock_polarity', 0))
        cpha = 'SPI_PHASE_1EDGE' if arguments.get('clock_phase', 0) == 0 else 'SPI_PHASE_2EDGE'

        instance = f'{kind}{number}'
        handle = f'h{kind.lower()}{number}'

        code = (
            f'/* SPI initialization: {instance}, {direction == "SPI_MODE_MASTER" and "master" or "slave"} mode */\n'
            f'__HAL_RCC_{instance}_CLK_ENABLE();\n'
            f'\n'
            f'{handle}.Instance = {instance};\n'
            f'{handle}.Init.Mode = {direction};\n'
            f'{handle}.Init.Direction = SPI_DIRECTION_2LINES;\n'
            f'{handle}.Init.DataSize = SPI_DATASIZE_8BIT;\n'
            f'{handle}.Init.CLKPolarity = {cpol};\n'
            f'{handle}.Init.CLKPhase = {cpha};\n'
            f'{handle}.Init.NSS = SPI_NSS_SOFT;\n'
            f'{handle}.Init.BaudRatePrescaler = {prescaler};\n'
            f'{handle}.Init.FirstBit = SPI_FIRSTBIT_MSB;\n'
            f'{handle}.Init.TIMode = SPI_TIMODE_DISABLE;\n'
            f'{handle}.Init.CRCCalculation = SPI_CRCCALCULATION_DISABLE;\n'
            f'if (HAL_SPI_Init(&{handle}) != HAL_OK)\n'
            f'{{\n'
            f'    Error_Handler();\n'
            f'}}\n')
        return ToolResult(success=True, output=code)


class I2cCodeTool(Tool):
    """Генерация шаблона кода инициализации I2C."""
    name = 'generate_i2c_code'
    description = (
        'Генерирует шаблон C-кода инициализации I2C микроконтроллера STM32 (HAL). '
        'Используй при подключении датчиков, EEPROM и дисплеев по шине I2C.')
    parameters = {
        'i2c': {'type': 'string', 'required': False,
                'description': 'имя периферии', 'enum': ['I2C1', 'I2C2']},
        'clock_speed': {'type': 'integer', 'required': False,
                        'description': 'частота шины в Гц: 100000 (стандартный режим) или 400000 (быстрый)'},
    }

    def _execute(self, arguments: dict, context: ToolContext | None) -> ToolResult:
        peripheral = arguments.get('i2c', 'I2C1')
        try:
            kind, number = _split_peripheral(peripheral)
        except ValueError as e:
            return ToolResult(success=False, error=str(e))

        clock_speed = arguments.get('clock_speed', 100000)
        if clock_speed not in (100000, 400000):
            return ToolResult(success=False, error='Частота шины I2C должна быть 100000 или 400000 Гц.')

        instance = f'{kind}{number}'
        handle = f'h{kind.lower()}{number}'
        duty = 'I2C_DUTYCYCLE_2' if clock_speed == 100000 else 'I2C_DUTYCYCLE_16_9'

        code = (
            f'/* I2C initialization: {instance}, {clock_speed} Hz */\n'
            f'__HAL_RCC_{instance}_CLK_ENABLE();\n'
            f'\n'
            f'{handle}.Instance = {instance};\n'
            f'{handle}.Init.ClockSpeed = {clock_speed};\n'
            f'{handle}.Init.DutyCycle = {duty};\n'
            f'{handle}.Init.OwnAddress1 = 0;\n'
            f'{handle}.Init.AddressingMode = I2C_ADDRESSINGMODE_7BIT;\n'
            f'{handle}.Init.DualAddressMode = I2C_DUALADDRESS_DISABLE;\n'
            f'{handle}.Init.OwnAddress2 = 0;\n'
            f'{handle}.Init.GeneralCallMode = I2C_GENERALCALL_DISABLE;\n'
            f'{handle}.Init.NoStretchMode = I2C_NOSTRETCH_DISABLE;\n'
            f'if (HAL_I2C_Init(&{handle}) != HAL_OK)\n'
            f'{{\n'
            f'    Error_Handler();\n'
            f'}}\n')
        return ToolResult(success=True, output=code)
