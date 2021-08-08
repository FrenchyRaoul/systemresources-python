from dataclasses import dataclass
import pandas as pd
import re
from subprocess import run

KERNEL_REGEX = re.compile(r'(?P<kernel>[^\t]+)\s+(?P<date>[^\t]+)\s(?P<architecture>[^\t]+)\s+\((?P<num_cpus>\d+)\sCPU\)')
CPU_REGEX = re.compile(r'avg-cpu:\s+%user\s+%nice\s+%system\s+%iowait\s+%steal\s+%idle')

@dataclass
class IOStats():
    kernel_data: dict
    cpu_data: dict
    device_table: pd.DataFrame
    
    @staticmethod
    def get_iostats():
        proc = run('iostat', capture_output=True, check=True)
        raw_text = proc.stdout.decode().strip()
        return IOStats.from_text(raw_text)
    
    @staticmethod
    def from_text(text):
        kernel_dataa = None
        cpu_data = None
        device_table = None

        lines = iter(text.split('\n'))

        match = KERNEL_REGEX.match(next(lines))
        if match:
            kernel_data = match.groupdict()

        for line in lines:

            if line.startswith('avg-cpu'):
                cpu_cols = re.sub(r"\s+", " ", line).replace('%', '').split()[1:]
                cpu_vals = re.sub(r"\s+", " ", next(lines)).split()
                cpu_data = dict(zip(cpu_cols, cpu_vals))

            data = list()
            if line.startswith('Device'):
                columns = re.sub(r"\s+", " ", line).split()
                for line in lines:
                    if line.strip():
                        data.append(re.sub(r"\s+", " ", line).split())

                device_table = pd.DataFrame(data, columns=columns)
                device_table.loc[:, [col for col in device_table.columns if col != 'Device']] = device_table.loc[:, [col for col in device_table.columns if col != 'Device']].astype('float') 
            
        return IOStats(kernel_data, cpu_data, device_table)
