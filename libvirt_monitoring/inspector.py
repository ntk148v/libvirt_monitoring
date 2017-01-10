import logging
import time

from lxml import etree
from oslo_config import cfg
from oslo_utils import units
import six

from libvirt_monitoring import base
from libvirt_monitoring import utils

libvirt = None

log = logging.getLogger(__name__)

OPTS = [
    cfg.StrOpt('libvirt_type',
               default='kvm',
               choices=['kvm', 'lxc', 'qemu', 'uml', 'xen'],
               help='Libvirt domain type.'),
    cfg.StrOpt('libvirt_uri',
               default='',
               help='Override the default libvirt URI '
                    '(which is dependent on libvirt_type).'),
]

CONF = cfg.CONF
CONF.register_opts(OPTS)


def retry_on_disconnect(function):
    def decorator(self, *args, **kwargs):
        try:
            return function(self, *args, **kwargs)
        except libvirt.libvirtError as e:
            if (e.get_error_code() == libvirt.VIR_ERR_SYSTEM_ERROR and
                e.get_error_domain() in (libvirt.VIR_FROM_REMOTE,
                                         libvirt.VIR_FROM_RPC)):
                self.connection = None
                return function(self, *args, **kwargs)
            else:
                raise

    return decorator


class LibvirtInspector(object):
    per_type_uris = dict(uml='uml:///system', xen='xen:///', lxc='lxc:///')

    def __init__(self):
        self.uri = self._get_uri()
        self.connection = None

    def _get_uri(self):
        return CONF.libvirt_uri or self.per_type_uris.get(CONF.libvirt_type,
                                                          'qemu:///system')

    def _get_connection(self):
        if not self.connection:
            global libvirt
            if libvirt is None:
                libvirt = __import__('libvirt')
            self.connection = libvirt.openReadOnly(self.uri)

        return self.connection

    @retry_on_disconnect
    def get_vm_metrics(self):
        self._get_connection()
        all_domains = self.connection.listAllDomains()
        # Format e.x:
        # resutls = {
        #   'instance-00000315' : {
        #          'statestats' : StateStats(state=1),
        #          'cpustats' : CPUStats(number=1, time=100)
        #           ...
        #   }
        # }
        results = {}
        for domain in all_domains:
            state = domain.info()[0]
            result = {}
            # Get domain state.
            result['statestats'] = self._inspect_state(domain)

            # Only get metrics info of running domain.
            if state == libvirt.VIR_DOMAIN_RUNNING:
                # Get cpu metrics.
                if self._check_collected_metric('cpustats'):
                    result['cpustats'] = self._inspect_cpus(domain)
                # Get network metrics/interface.
                if self._check_collected_metric('interfacestats'):
                    for vnic in self._inspect_vnics(domain):
                        result['interfacestats_' + vnic[0].name] = vnic[1]
                # Get disk metrics/disk.
                if self._check_collected_metric('diskstats'):
                    for disk in self._inspect_disks(domain):
                        result['diskstats_' + disk[0].device] = disk[1]
                # Get disk info metrics/disk.
                if self._check_collected_metric('diskinfo'):
                    for disk in self._inspect_disk_info(domain):
                        result['diskinfo_' + disk[0].device] = disk[1]
                # Get memory usage metrics.
                if self._check_collected_metric('memoryusagestats'):
                    result['memoryusagestats'] = self._inspect_memory_usage(
                        domain)
                # Get memory resident metrics.
                if self._check_collected_metric('memoryresidentstats'):
                    result['memoryresidentstats'] = \
                        self._inspect_memory_resident(domain)

            results[domain.name()] = result
        return results

    def _check_collected_metric(self, metric):
        LOG.info('Collecting %s!' % metric)
        return utils.ini_file_loader()['metrics-'+metric] == 'True'

    def _inspect_state(self, domain):
        dom_info = domain.info()
        return base.StateStats(state=dom_info[0])

    def _inspect_cpus(self, domain):
        dom_info = domain.info()
        return base.CPUStats(number=dom_info[3], time=dom_info[4])

    def _inspect_vnics(self, domain):
        tree = etree.fromstring(domain.XMLDesc(0))
        for iface in tree.findall('devices/interface'):
            target = iface.find('target')
            if target is not None:
                name = target.get('dev')
            else:
                continue
            mac = iface.find('mac')
            if mac is not None:
                mac_address = mac.get('address')
            else:
                continue
            fref = iface.find('filterref')
            if fref is not None:
                fref = fref.get('filter')

            params = dict((p.get('name').lower(), p.get('value'))
                          for p in iface.findall('filterref/parameter'))
            interface = base.Interface(name=name, mac=mac_address,
                                       fref=fref, parameters=params)
            dom_stats_1 = domain.interfaceStats(name)
            time.sleep(1)
            dom_stats_2 = domain.interfaceStats(name)
            # Calculate transmitted/received megabits per second.
            transmitted_ps = abs(
                (dom_stats_1[4] - dom_stats_2[4]) * 8 * pow(10, -6))
            received_ps = abs(
                (dom_stats_1[0] - dom_stats_2[0]) * 8 * pow(10, -6))
            stats = base.InterfaceStats(rx_bytes=dom_stats_1[0],
                                        rx_packets=dom_stats_1[1],
                                        tx_bytes=dom_stats_1[4],
                                        tx_packets=dom_stats_1[5],
                                        transmitted_ps=transmitted_ps,
                                        received_ps=received_ps)
            yield (interface, stats)

    def _inspect_disks(self, domain):
        tree = etree.fromstring(domain.XMLDesc(0))
        for device in filter(
            bool,
            [target.get("dev")
             for target in tree.findall('devices/disk/target')]):
            disk = base.Disk(device=device)
            block_stats = domain.blockStats(device)
            block_latency_stats = domain.blockStatsFlags(device)
            stats = base.DiskStats(read_requests=block_stats[0],
                                   read_bytes=block_stats[1],
                                   write_requests=block_stats[2],
                                   write_bytes=block_stats[3],
                                   write_total_times=block_latency_stats[
                                       'wr_total_times'] / 1E6,
                                   read_total_times=block_latency_stats[
                                       'rd_total_times'] / 1E6,
                                   errors=block_stats[4])
            yield (disk, stats)

    def _inspect_memory_usage(self, domain, duration=None):
        try:
            memory_stats = domain.memoryStats()
            if (memory_stats and
                    memory_stats.get('available') and
                    memory_stats.get('unused')):
                memory_used = (memory_stats.get('available') -
                               memory_stats.get('unused'))
                # Stat provided from libvirt is in KB, converting it to MB.
                memory_used = memory_used / units.Ki
                return base.MemoryUsageStats(usage=memory_used)
            else:
                msg = ('Failed to inspect memory usage of instance '
                       '<name=%(name)s, id=%(id)s>, '
                       'can not get info from libvirt.') % {
                    'name': domain.name(), 'id': domain.ID()}
                raise base.NoDataException(msg)
        # memoryStats might launch an exception if the method is not supported
        # by the underlying hypervisor being used by libvirt.
        except libvirt.libvirtError as e:
            msg = ('Failed to inspect memory usage of %(instance_uuid)s, '
                   'can not get info from libvirt: %(error)s') % {
                'instance_uuid': domain.ID(), 'error': e}
            raise base.NoDataException(msg)

    def _inspect_disk_info(self, domain):
        tree = etree.fromstring(domain.XMLDesc(0))
        for disk in tree.findall('devices/disk'):
            disk_type = disk.get('type')
            if disk_type:
                if disk_type == 'network':
                    log.debug('Inspection disk usage of network disk '
                              '%(domain_id)s unsupported by libvirt' % {
                                  'domain_id': domain.ID()})
                    continue
                target = disk.find('target')
                device = target.get('dev')
                if device:
                    dsk = base.Disk(device=device)
                    block_info = domain.blockInfo(device)
                    info = base.DiskInfo(capacity=block_info[0],
                                         allocation=block_info[1],
                                         physical=block_info[2])
                    yield (dsk, info)

    def _inspect_memory_resident(self, domain, duration=None):
        memory = domain.memoryStats()['rss'] / units.Ki
        return base.MemoryResidentStats(resident=memory)
