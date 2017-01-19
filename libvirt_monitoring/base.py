import collections


# Named tuple representing Domain State.
#
# state: virDomainState
#
StateStats = collections.namedtuple('StateStats', ['state'])

# Named tuple representing CPU statistics.
#
# number: number of CPUs
# time: cumulative CPU time
#
CPUStats = collections.namedtuple('CPUStats', ['number', 'time'])

# Named tuple representing Memory usage statistics.
#
# usage: Amount of memory used
#
MemoryUsageStats = collections.namedtuple('MemoryUsageStats', ['usage'])


# Named tuple representing Resident Memory usage statistics.
#
# resident: Amount of resident memory
#
MemoryResidentStats = collections.namedtuple('MemoryResidentStats',
                                             ['resident'])


# Named tuple representing vNICs.
#
# name: the name of the vNIC
# mac: the MAC address
# fref: the filter ref
# parameters: miscellaneous parameters
#
Interface = collections.namedtuple('Interface', ['name', 'mac',
                                                 'fref', 'parameters'])


# Named tuple representing vNIC statistics.
#
# tx_megabit_ps: number of transmitted megabits per second
# rx_megabit_ps: number of received megabits per second
# tx_packets_ps: number of transmitted packets per second
# rx_packets_ps: number of received packets per second
#
InterfaceStats = collections.namedtuple('InterfaceStats',
                                        ['tx_megabit_ps', 'rx_megabit_ps',
                                         'tx_packets_ps', 'rx_packets_ps'])

# Named tuple representing disks.
#
# device: the device name for the disk
#
Disk = collections.namedtuple('Disk', ['device'])


# Named tuple representing disk statistics.
#
# read_megabytes_ps: number of megabytes read per second
# read_requests_ps: number of read operations per second
# write_megabytes_ps: number of megabytes written per second
# write_requests_ps: number of write operations per second
# read_total_times: number of millisenconds total time read
# write_total_times: number of millisenconds total time write
# errors: number of errors
#
DiskStats = collections.namedtuple('DiskStats',
                                   ['read_megabytes_ps', 'read_requests_ps',
                                    'write_megabytes_ps', 'write_requests_ps',
                                    'write_total_times', 'read_total_times',
                                    'errors'])

# Named tuple representing disk Information.
#
# capacity: capacity of the disk
# allocation: allocation of the disk
# physical: usage of the disk
#
DiskInfo = collections.namedtuple('DiskInfo',
                                  ['capacity',
                                   'allocation',
                                   'physical'])

# Named tuple representing zabbix item.
#
# key: zabbix item key
# name: zabbix item name
# value: zabbix item value
#
Item = collections.namedtuple('Item',
                              ['key', 'name', 'value'])

# Exception types
#


class InspectorException(Exception):

    def __init__(self, message=None):
        super(InspectorException, self).__init__(message)


class NoDataException(InspectorException):
    pass


class AgentLogger(object):

    """
    Fake file-like stream object that redirects writes
    to a logger instance.
    """

    def __init__(self, logger, level):
        self.logger = logger
        self.level = level

    def write(self, message):
        # Only log if there is a message (not just a new line)
        if message.rstrip() != "":
            self.logger.log(self.level, message.rstrip())
