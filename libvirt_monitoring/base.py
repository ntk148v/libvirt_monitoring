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

# Named tuple representing CPU Utilization statistics.
#
# util: CPU utilization in percentage
#
CPUUtilStats = collections.namedtuple('CPUUtilStats', ['util'])

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
#
InterfaceStats = collections.namedtuple('InterfaceStats',
                                        ['rx_bytes', 'rx_packets',
                                         'tx_bytes', 'tx_packets'])


# Named tuple representing vNIC rate statistics.
#
# rx_bytes_rate: rate of received bytes
# tx_bytes_rate: rate of transmitted bytes
#
InterfaceRateStats = collections.namedtuple('InterfaceRateStats',
                                            ['rx_bytes_rate', 'tx_bytes_rate'])


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
# errors: number of errors
#
DiskStats = collections.namedtuple('DiskStats',
                                   ['read_bytes', 'read_requests',
                                    'write_bytes', 'write_requests',
                                    'errors'])

# Named tuple representing disk rate statistics.
#
# read_bytes_rate: number of bytes read per second
# read_requests_rate: number of read operations per second
# write_bytes_rate: number of bytes written per second
# write_requests_rate: number of write operations per second
#
DiskRateStats = collections.namedtuple('DiskRateStats',
                                       ['read_bytes_rate',
                                        'read_requests_rate',
                                        'write_bytes_rate',
                                        'write_requests_rate'])

# Named tuple representing disk latency statistics.
#
# disk_latency: average disk latency
#
DiskLatencyStats = collections.namedtuple('DiskLatencyStats',
                                          ['disk_latency'])

# Named tuple representing disk iops statistics.
#
# iops: number of iops per second
#
DiskIOPSStats = collections.namedtuple('DiskIOPSStats',
                                       ['iops_count'])


# Named tuple representing disk Information.
#
# capacity: capacity of the disk
# allocation: allocation of the disk
# physical: usage of the disk

DiskInfo = collections.namedtuple('DiskInfo',
                                  ['capacity',
                                   'allocation',
                                   'physical'])

# Named tuple representing zabbix item.
# 
# key: zabbix item key.
# name: zabbix item name.
# value: zabbix item value.
Item = collections.namedtuple('Item',
                              ['key, name, value'])

# Exception types
#
class InspectorException(Exception):

    def __init__(self, message=None):
        super(InspectorException, self).__init__(message)


class NoDataException(InspectorException):
    pass
