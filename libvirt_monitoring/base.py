import collections
import re
import subprocess
import sys


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
# tx_megabit_ps: number of transmitted megabit per second
# rx_megabit_ps: number of received megabit per second
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
# r_await: The average time (in milliseconds) for read requests
# w_await: The average time (in milliseconds) for write requests
# errors: number of errors
#
DiskStats = collections.namedtuple('DiskStats',
                                   ['read_megabytes_ps', 'read_requests_ps',
                                    'write_megabytes_ps', 'write_requests_ps',
                                    'r_await', 'w_await',
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


class IOStatError(Exception):
    pass


class CmdError(IOStatError):
    pass


class ParseError(IOStatError):
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


# Class IOStat is inherited from collecd-iostat-python
# with a little customization.
# https://github.com/deniszh/collectd-iostat-python/

class IOStat(object):
    def __init__(self, interval=2, count=2, disks=[]):
        self.path = self._get_iostat_path()
        self.interval = interval
        self.count = count
        self.disks = disks

    def _get_iostat_path(self):
        proc = subprocess.Popen('which iostat',
                                shell=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        path, error = proc.communicate()
        if error:
            raise Exception()
        else:
            return path.rstrip()

    def parse_diskstats(self, input):
        """
        Parse iostat -d and -dx output.If there are more
        than one series of statistics, get the last one.
        By default parse statistics for all avaliable block devices.

        @type input: C{string}
        @param input: iostat output

        @type disks: list of C{string}s
        @param input: lists of block devices that
        statistics are taken for.

        @return: C{dictionary} contains per block device statistics.
        Statistics are in form of C{dictonary}.
        Main statistics:
          tps  Blk_read/s  Blk_wrtn/s  Blk_read  Blk_wrtn
        Extended staistics (available with post 2.5 kernels):
          rrqm/s  wrqm/s  r/s  w/s  rsec/s  wsec/s  rkB/s  wkB/s  avgrq-sz \
          avgqu-sz  await  svctm  %util
        See {man iostat} for more details.
        """
        dstats = {}
        dsi = input.rfind('Device:')
        if dsi == -1:
            raise ParseError('Unknown input format: %r' % input)

        ds = input[dsi:].splitlines()
        hdr = ds.pop(0).split()[1:]

        for d in ds:
            if d:
                d = d.split()
                d = [re.sub(r',', '.', element) for element in d]
                dev = d.pop(0)
                if (dev in self.disks) or not self.disks:
                    dstats[dev] = dict([(k, float(v)) for k, v in zip(hdr, d)])

        return dstats

    def sum_dstats(self, stats, smetrics):
        """
        Compute the summary statistics for chosen metrics.
        """
        avg = {}

        for disk, metrics in stats.iteritems():
            for mname, metric in metrics.iteritems():
                if mname not in smetrics:
                    continue
                if mname in avg:
                    avg[mname] += metric
                else:
                    avg[mname] = metric

        return avg

    def _run(self, options=None):
        """
        Run iostat command.
        """
        close_fds = 'posix' in sys.builtin_module_names
        args = '%s %s %s %s %s' % (
            self.path,
            ''.join(options),
            self.interval,
            self.count,
            ' '.join(self.disks))

        return subprocess.Popen(
            args,
            bufsize=1,
            shell=True,
            stdout=subprocess.PIPE,
            close_fds=close_fds)

    @staticmethod
    def _get_childs_data(child):
        """
        Return child's data when avaliable.
        """
        (stdout, stderr) = child.communicate()
        ecode = child.poll()

        if ecode != 0:
            raise CmdError('Command %r returned %d' % (child.cmd, ecode))

        return stdout

    def get_diskstats(self):
        """
        Get all avaliable disks statistics that we can get.
        """
        dstats = self._run(options=['-kNd'])
        extdstats = self._run(options=['-kNdx'])
        dsd = self._get_childs_data(dstats)
        edd = self._get_childs_data(extdstats)
        ds = self.parse_diskstats(dsd)
        eds = self.parse_diskstats(edd)

        for dk, dv in ds.iteritems():
            if dk in eds:
                ds[dk].update(eds[dk])

        return ds

    def get_specific_diskstat(self, device):
        """
        Get specific disk statistics.
        """
        return self.get_diskstats()[device]
