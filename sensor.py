from dataclasses import dataclass
import re
from subprocess import run

DEFAULT_TEMPERATURE_UNIT = 'C'


# Package id 0:  +40.0°C  (high = +80.0°C, crit = +100.0°C)
# Core 0:        +22.0°C  (high = +80.0°C, crit = +100.0°C)
# Core 4:        +32.0°C  (high = +80.0°C, crit = +100.0°C)
# temp1:        +27.8°C  (crit = +105.0°C)
# Sensor 1:      +7.8°C  (low  = -273.1°C, high = +65261.8°C)
SENSOR_REGEX = re.compile(r'(?P<name>[^:]+):\s+(?P<current>[+-]\d+\.\d+)°(?P<current_unit>[CF])\s+'
                          r'\('
                          r'(low\s*=\s*(?P<low>[+-]\d+\.\d+)°(?P<low_unit>[CF]),?\s*)?'
                          r'(high\s*=\s*(?P<high>[+-]\d+\.\d+)°(?P<high_unit>[CF]),?\s*)?'
                          r'(crit\s*=\s*(?P<crit>[+-]\d+\.\d+)°(?P<crit_unit>[CF]))?'
                          r'\)',
                          re.VERBOSE | re.I)

# Composite:     +7.8°C  (low  = -273.1°C, high = +84.8°C)
#                        (crit = +84.8°C)
COMPOSITE_REGEX = re.compile(r'\(crit\s*=\s*(?P<crit>[+-]\d+\.\d+)°(?P<crit_unit>[CF])\)')

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
    low: Temperature
    high: Temperature
    crit: Temperature

    def __repr__(self):
        return f"<Sensor.{self.name}.{self.current}>"
    
    def is_low(self): 
        return current >= low

    def is_high(self):
        return current >= high

    def is_crit(self):
        return current >= crit
    
    def update_crit(self, text):
        """
        some composite temperatures have the critical temp on a separate line. if we encounter this, parse and update the object.
        """
        match = COMPOSITE_REGEX.match(text)
        float(match['crit'] or 'inf')
        match['crit_unit']
        self.crit = Temperature(float(match['crit'] or 'inf'), match['crit_unit'])

    @staticmethod
    def from_text(text):
        match = SENSOR_REGEX.match(text)
        if not match:
            raise ValueError('input text does not match expected pattern')
        data = match.groupdict()

        return Sensor(
            name=data['name'],
            current=Temperature(float(data['current']), data['current_unit']),
            low=Temperature(float(data['low'] or '-inf'), data['low_unit'] or DEFAULT_TEMPERATURE_UNIT),
            high=Temperature(float(data['high'] or 'inf'), data['high_unit'] or DEFAULT_TEMPERATURE_UNIT),
            crit=Temperature(float(data['crit'] or 'inf'), data['crit_unit'] or DEFAULT_TEMPERATURE_UNIT),
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
            line = line.strip()
            if line:
                try:
                    sensor = Sensor.from_text(line)
                    if sensor.name in sensors:
                        raise ValueError(f"another bad assumption, multiple sensors named {sensor.name}")
                    sensors[sensor.name] = sensor
                except ValueError:
                    sensor.update_crit(line)

        return SensorGroup(name, adapter, sensors)


@dataclass
class Sensors():
    sensor_groups: dict

    @staticmethod
    def get_sensors():
        proc = run('sensors', capture_output=True, check=True)
        raw_text = proc.stdout.decode().strip()
        sensor_groups = [SensorGroup.from_text(text) for text in raw_text.split('\n\n')]
        return Sensors({group.name: group for group in sensor_groups})

    def to_csv(self, stream):
        columns = "chip,adapter,sensor,current,high,crit,unit\n"
        stream.write(columns)
        for name, group in self.sensor_groups.items():
            for sensor_name, sensor in group.sensors.items():
                stream.write(f"{name},{group.adapter},{sensor_name},{sensor.current.celcius.value},{sensor.high.celcius.value},{sensor.crit.celcius.value},C\n")
