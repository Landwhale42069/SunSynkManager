import minimalmodbus
from threading import Timer


class SunSynkInstrument(minimalmodbus.Instrument):
    def __init__(self):
        try:
            super(SunSynkInstrument, self).__init__('/dev/ttyUSB0', 1)
            self.serial.baudrate = 9600  # Baud
            self.serial.bytesize = 8
            self.serial.parity = 'N'
            self.serial.stopbits = 1
            self.serial.timeout = 0.2  # seconds
        except Exception as e:
            print('Dev mode')

        self.update_to_get = []
        self.__registers = {}

    def _self_update(self):
        t = Timer(1, self._self_update, []).start()

        for register in self.update_to_get:
            if isinstance(register, tuple) or isinstance(register, list):
                self.__registers[str(register)] = self.read_registers(register)
            else:
                self.__registers[str(register)] = self.read_register(register)

    def _read_register(self, register):
        return self.__registers[str(register)]


class Register:
    # Private instrument variable that is static over all registers
    __instrument = SunSynkInstrument()

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

        self.__instrument.update_to_get.append(registers)

        self.logger.info(f"Successfully created {self.__str__()}")

    def get_value(self):
        if isinstance(self.registers, tuple) or isinstance(self.registers, list):
            values = self.__instrument.read_registers(self.registers[0], len(self.registers))
        else:
            values = self.__instrument._read_register(self.registers)

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


