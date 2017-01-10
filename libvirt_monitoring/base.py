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
# rx_bytes: number of received bytes
# rx_packets: number of received packets
# tx_bytes: number of transmitted bytes
# tx_packets: number of transmitted packets
# rx_ps: number of received megabits per second.
# tx_ps: number of transmitted megabits per second.
#
InterfaceStats = collections.namedtuple('InterfaceStats',
                                        ['rx_bytes', 'rx_packets',
                                         'tx_bytes', 'tx_packets',
                                         'transmitted_ps', 'received_ps'])

# Named tuple representing disks.
#
# device: the device name for the disk
#
Disk = collections.namedtuple('Disk', ['device'])


# Named tuple representing disk statistics.
#
# read_bytes: number of bytes read
# read_requests: number of read operations
# write_bytes: number of bytes written
# write_requests: number of write operations
# read_total_times: number of millisenconds total time read
# write_total_times: number of millisenconds total time write
# errors: number of errors
#
DiskStats = collections.namedtuple('DiskStats',
                                   ['read_bytes', 'read_requests',
                                    'write_bytes', 'write_requests',
                                    'write_total_times', 'read_total_times'
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
# #
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
