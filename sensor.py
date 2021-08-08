from dataclasses import dataclass
import re
from subprocess import run

SENSOR_REGEX = re.compile(r'(?P<name>[^:]+):\s+(?P<current>[+-]\d+\.\d+)°(?P<current_unit>[CF])\s+'
                          r'\(high\s=\s(?P<high>[+-]\d+\.\d+)°(?P<high_unit>[CF]),\s+'
                          r'crit\s=\s(?P<crit>[+-]\d+\.\d+)°(?P<crit_unit>[CF])',
                          re.VERBOSE | re.I)

@dataclass
class Temperature():
    value: float
    unit: str

    def __eq__(self, other):
        return self.celcius.value == other.celcius.value

    def __lt__(self, other):
        return self.celcius.value < other.celcius.value

    def __le__(self, other):
        return self.celcius.value <= other.celcius.value

    def __gt__(self, other):
        return self.celcius.value > other.celcius.value

    def __ge__(self, other):
        return self.celcius.value >= other.celcius.value

    @staticmethod
    def f_to_c(degrees_f: float) -> float:
        return (degrees_f - 32) / 1.8

    @staticmethod
    def c_to_f(degrees_c: float) -> float:
        return 1.8 * degrees_c + 32

    @property
    def farenheit(self) -> 'Temperature':
        if self.unit == 'F':
            return self
        return Temperature(self.c_to_f(self.value), 'F')

    @property
    def celcius(self) -> 'Temperature':
        if self.unit == 'C':
            return self
        return Temperature(self.f_to_c(self.value), 'C')


@dataclass
class Sensor():
    name: str
    current: Temperature
    high: Temperature
    crit: Temperature

    def __repr__(self):
        return f"<Sensor.{self.name}.{self.current}>"

    def is_high(self):
        return current >= high

    def is_crit(self):
        return current >= crit

    @staticmethod
    def from_text(text):
        match = SENSOR_REGEX.match(text)
        if not match:
            raise ValueError('input text does not match expected pattern')
        data = match.groupdict()

        return Sensor(
            name=data['name'],
            current=Temperature(float(data['current']), data['current_unit']),
            high=Temperature(float(data['high']), data['high_unit']),
            crit=Temperature(float(data['crit']), data['crit_unit']),
        )


@dataclass
class SensorGroup():
    name: str
    adapter: str
    sensors: dict

    @staticmethod
    def from_text(text):
        lines = iter(text.split('\n'))
        name = next(lines).strip()
        _adapt, adapter = next(lines).split(':')
        if _adapt != 'Adapter':
            raise ValueError(f"bad assumption... expected 'Adapter', instead found {_adapt}")
        adapter = adapter.strip()
        sensors = dict()
        for line in lines:
            sensor = Sensor.from_text(line)
            if sensor.name in sensors:
                raise ValueError(f"another bad assumption, multiple sensors named {sensor.name}")
            sensors[sensor.name] = sensor

        return SensorGroup(name, adapter, sensors)


@dataclass
class Sensors():
    sensor_groups: list

    @staticmethod
    def get_sensors():
        proc = run('sensors', capture_output=True, check=True)
        raw_text = proc.stdout.decode().strip()
        return Sensors(sensor_groups=[SensorGroup.from_text(text) for text in raw_text.split('\n\n')])

    def to_csv(self, stream):
        columns = "chip,adapter,sensor,current,high,crit,unit\n"
        stream.write(columns)
        for chip in self.sensor_groups:
            for sensor_name, sensor in chip.sensors.items():
                stream.write(f"{chip.name},{chip.adapter},{sensor_name},{sensor.current.celcius.value},{sensor.high.celcius.value},{sensor.crit.celcius.value},C\n")


