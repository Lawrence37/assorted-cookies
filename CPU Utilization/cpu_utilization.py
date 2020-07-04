#!/bin/env python
'''
CPU Utilization for Linux, written in Python 3

Copyright (C) 2018 Lawrence Lee

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
'''

'''
Prints the (near) instantaneous core/CPU utilization as percentages of user,
nice, system, idle, and wait loads. Utilization is the percentage of the core or
cpu's maximum processing capacity given the number of active cores and maximum
set frequency.
'''


import argparse
import glob     # glob(string)
import os       # path.isdir(string)
import pathlib  # Path
import re       # match(string, string)
import sys      # argv
import time     # sleep(float)


base_path = "/sys/devices/system/cpu/cpu"
suffix_path = "/cpufreq/"
cur_freq_path = "scaling_cur_freq"
max_freq_path = "cpuinfo_max_freq"


def calc_avg_freq(a, b, core):
    '''
    Calculates and returns the average of two frequencies, normalized to the
    core's maximum frequency.
    '''
    return (a + b) / get_max_freq(core) / 2

def calc_utilization(final, initial, freq):
    '''
    Based on the initial and final CPU times and the average normalized
    frequency, calculates and returns the core/CPU utilization, as percentages,
    categorized by user, nice, system, idle, and wait.
    '''
    deltas = [f - i for f, i in zip(final, initial)]
    total_time = sum(deltas)
    percentages = []

    if(total_time > 0):
        percentages = [100 * x / total_time * freq for x in deltas]
        percentages[3] += 100 - sum(percentages) # CPU idle.
    else:
        percentages = [0.0, 0.0, 0.0, 100.0, 0.0]

    return percentages

def get_cpu_times(core):
    '''
    Gets and returns the CPU times since boot categorized by user, nice,
    system, idle, and wait.
    '''
    times_str = ""
    pattern = "cpu" + core

    with open("/proc/stat", 'r') as file_in:
        for line in file_in:
            if(re.match(pattern, line)):
                times_str = line
                break

    return [float(x) for x in times_str.split()[1:6]]

def get_cur_freq(core):
    '''
    Gets and returns the core's (or average CPU's if no core is specified)
    current frequency.
    '''
    return get_xxx_freq(core, cur_freq_path)

def get_max_freq(core):
    '''
    Gets and returns the core's (or average CPU's if no core is specified)
    maximum frequency.
    '''
    return get_xxx_freq(core, max_freq_path)

def get_valid_cores():
    '''
    Returns a list of all valid core numbers as integers.
    '''
    pattern = base_path + '[0-9]*'
    regex_pattern = base_path + '(?P<number>[0-9]+)'
    cores = []

    paths = glob.glob(pattern)
    for path in paths:
        match = re.match(regex_pattern, path).group('number')
        if match is not None:
            cores.append(int(match))

    cores.sort()
    return cores

def get_xxx_freq(core, file_name):
    '''
    Gets and returns the core's (or average CPU's if no core is specified)
    frequency from the specifed file.
    '''
    if(core == ""): # Average all cores.
        paths = glob.glob(base_path + "[0-9]*" + suffix_path + file_name)
    else:
        paths = [base_path + core + suffix_path + file_name]

    time_sum = sum([int(pathlib.Path(path).read_text()) for path in paths])
    return float(time_sum) / len(paths)

def output(percentages):
    '''
    Prints the output of the program.
    '''
    print(
            f'{percentages[0]:.3f}\t{percentages[1]:.3f}\t{percentages[2]:.3f}'
            f'\t{percentages[3]:.3f}\t{percentages[4]:.3f}'
    )

def parse_core_num():
    '''
    Gets and returns the core number specified as the second command-line
    argument.
    '''
    if(len(sys.argv) == 3):
        if(os.path.isdir(base_path + sys.argv[2] + suffix_path)):
            return sys.argv[2]
        else:
            print("Invalid core number.")
            exit(1)
    else:
        return ""

def parse_sample_time():
    '''
    Gets and returns the sample time specified as the first command-line
    argument.
    '''
    if(float(sys.argv[1]) >= 0):
        return float(sys.argv[1])
    else:
        print("Invalid sample time.")
        exit(1)

def print_help():
    '''
    Prints usage information for this program.
    '''
    print("Prints the core/CPU's user, nice, system, idle, and wait loads as\
            percentages of the total core/CPU capacity.")
    print("Usage: " + sys.argv[0] + " <sample_time> [<core_number>]")
    print("Sample time is the period of time to sample the CPU time. Small\
            values give imprecise results. Large values may not be accurate\
            because the frequency is sampled only at the start and end.")
    print("If the core number is not specifed, an average of all cores is\
            used.")

def validate_args():
    '''
    Validates the number of command-line arguments.
    '''
    if(len(sys.argv) == 1):
        print_help()
        exit(0)
    elif(len(sys.argv) > 3):
        print_help()
        exit(1)

def get_args():
    '''
    Returns the parsed command line arguments.
    '''
    parser = argparse.ArgumentParser(
            description='Large values may not be accurate because the '
            'frequency is sampled only at the start and end.'
    )
    valid_cores = get_valid_cores()

    parser.add_argument(
            'period',
            type=float,
            help='The period of time to sample the CPU time. Small values '
            'give imprecise results.'
    )
    parser.add_argument(
            '-c',
            '--core',
            type=int,
            choices=valid_cores,
            help='Number of the core.'
    )

    return parser.parse_args()

def main():
    ## Handle command-line arguments.
    args = get_args()
    core_num = '' if args.core is None else str(args.core)
    sample_time = args.period

    # Sample initial conditions.
    data_1 = get_cpu_times(core_num)
    freq_1 = get_cur_freq(core_num)

    # Wait for sample time.
    time.sleep(sample_time)

    # Sample final conditions.
    data_2 = get_cpu_times(core_num)
    freq_2 = get_cur_freq(core_num)

    # Calculate and output core/CPU utilization.
    normalized_freq = calc_avg_freq(freq_1, freq_2, core_num)
    percentages = calc_utilization(data_2, data_1, normalized_freq)
    output(percentages)

def run():
    if __name__ == '__main__':
        main()

run()
