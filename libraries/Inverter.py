import minimalmodbus
import random


class FakeInstrument:
    def __init__(self):
        ...

    @staticmethod
    def read_registers(a, b):
        return random.randint(0, a)

    @staticmethod
    def read_register(a):
        return random.randint(0, a)


class Register:
    # Private instrument variable that is static over all registers
    try:
        __instrument = minimalmodbus.Instrument('/dev/ttyUSB0', 1)
        __instrument.serial.baudrate = 9600  # Baud
        __instrument.serial.bytesize = 8
        __instrument.serial.parity = 'N'
        __instrument.serial.stopbits = 1
        __instrument.serial.timeout = 0.2  # seconds
    except Exception as e:
        __instrument = FakeInstrument()

    logger = None

    class NoLoggerException(Exception):
        pass

    def __init__(self, registers, name, factor=1, units=None):
        if self.logger is None:
            raise self.NoLoggerException("Predefine the static logger for all Registers before creating an instance")

        self.registers = registers
        self.name = name
        self.factor = factor
        self.units = units

        self.logger.info(f"Successfully created {self.__str__()}")

    def get_value(self):
        if isinstance(self.registers, tuple) or isinstance(self.registers, list):
            values = self.__instrument.read_registers(self.registers[0], len(self.registers))
        else:
            values = self.__instrument.read_register(self.registers)

        if isinstance(values, tuple) or isinstance(values, list):
            return_value = (values[1] << 16) + values[0]
        else:
            return_value = values

        if self.factor < 0:
            return_value = return_value if return_value <= 0x7FFF else return_value - 0xFFFF

        return return_value * abs(self.factor)

    def get_display(self):
        value = self.get_value()

        if not self.units:
            return f"{value}"
        else:
            return f"{value} {self.units}"

    def __str__(self):
        return f"<{self.name} Register ({self.registers})>"


