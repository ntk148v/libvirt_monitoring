import logging
import time

from lxml import etree
from oslo_config import cfg

from libvirt_monitoring import base
from libvirt_monitoring import settings
from libvirt_monitoring import utils

libvirt = None

LOG = logging.getLogger(__name__)

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
            result = {}
            msg = '### Inspect metrics of %(instance_uuid)s' % {
                'instance_uuid': domain.UUIDString()}
            LOG.info(msg)
            # Get domain state.
            statestats = self._inspect_state(domain)
            self._log_inspection(statestats)
            result['statestats'] = statestats

            # Only get metrics info of running domain.
            if statestats.state == 'VIR_DOMAIN_RUNNING':
                # Get cpu metrics.
                if self._check_collected_metric('cpustats'):
                    _cpustats = self._inspect_cpus(domain)
                    self._log_inspection(_cpustats)
                    result['cpustats'] = _cpustats
                # Get network metrics/interface.
                if self._check_collected_metric('interfacestats'):
                    _interfacestats = list(self._inspect_vnics(domain))
                    self._log_inspection(_interfacestats)
                    for vnic in _interfacestats:
                        result['interfacestats_' + vnic[0].name] = vnic[1]
                # Get disk metrics/disk.
                if self._check_collected_metric('diskstats'):
                    _diskstats = list(self._inspect_disks(domain))
                    self._log_inspection(_diskstats)
                    for disk in _diskstats:
                        result['diskstats_' + disk[0].device] = disk[1]
                # Get disk info metrics/disk.
                if self._check_collected_metric('diskinfo'):
                    _diskinfo = list(self._inspect_disk_info(domain))
                    self._log_inspection(_diskinfo)
                    for disk in _diskinfo:
                        result['diskinfo_' + disk[0].device] = disk[1]
                # Get memory usage metrics.
                if self._check_collected_metric('memoryusagestats'):
                    _memoryusagestats = self._inspect_memory_usage(domain)
                    self._log_inspection(_memoryusagestats)
                    result['memoryusagestats'] = _memoryusagestats
                # Get memory resident metrics.
                if self._check_collected_metric('memoryresidentstats'):
                    _memoryresidentstats = \
                        self._inspect_memory_resident(domain)
                    self._log_inspection(_memoryresidentstats)
                    result['memoryresidentstats'] = _memoryresidentstats

            results[domain.UUIDString()] = result
        return results

    def _cal_metric_ps(self, current_metric, prev_metric, unit='MB/s'):
        """Calculate metric value per second"""
        result = current_metric - prev_metric
        if unit == 'MB/s':
            return result * pow(10, -6)
        elif unit == 'Mb/s':
            return result * 8 * pow(10, -6)
        elif unit == 'packets/s' or unit == 'operations/s':
            return result
        else:
            LOG.exception('Unknow unit type!')

    def _log_inspection(self, metric):
        """Log inspect operation"""
        msg = 'Collecting %(metric)s' % {'metric': metric}
        LOG.info(msg)

    def _check_collected_metric(self, metric):
        return utils.ini_file_loader()['metrics-' + metric] == 'True'

    def _inspect_state(self, domain):
        dom_info = domain.info()
        # Get state from intefer to string.
        state = settings.STATE_MAPPER[dom_info[0]]
        return base.StateStats(state=state)

    def _inspect_cpus(self, domain):
        try:
            dom_info = domain.info()
            return base.CPUStats(number=dom_info[3], time=dom_info[4])
        except libvirt.libvirtError as e:
            msg = ('Failed to inspect cpu stats of %(instance_uuid)s, '
                   'can not get info from libvirt: %(error)s') % {
                'instance_uuid': domain.UUIDString(), 'error': e}
            LOG.error(msg)

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
            stats = None
            try:
                # Get stats.
                dom_stats_1 = domain.interfaceStats(name)
                time.sleep(1)
                dom_stats_2 = domain.interfaceStats(name)
                # Calculate transmitted/received megabit/second.
                tx_megabit_ps = self._cal_metric_ps(dom_stats_2[4],
                                                    dom_stats_1[4],
                                                    unit='Mb/s')
                rx_megabit_ps = self._cal_metric_ps(dom_stats_2[0],
                                                    dom_stats_1[0],
                                                    unit='Mb/s')
                # Calculate transmitted/received packets/second.
                tx_packets_ps = self._cal_metric_ps(dom_stats_2[5],
                                                    dom_stats_1[5],
                                                    unit='packets/s')
                rx_packets_ps = self._cal_metric_ps(dom_stats_2[1],
                                                    dom_stats_1[1],
                                                    unit='packets/s')
                stats = base.InterfaceStats(tx_megabit_ps=tx_megabit_ps,
                                            rx_megabit_ps=rx_megabit_ps,
                                            tx_packets_ps=tx_packets_ps,
                                            rx_packets_ps=rx_packets_ps)
            except libvirt.libvirtError as e:
                msg = ('Failed to inspect %(interface)s stats of '
                       '%(instance_uuid)s, can not get info from'
                       'libvirt: %(error)s') % {
                    'interface': interface,
                    'instance_uuid': domain.UUIDString(),
                    'error': e}
                LOG.error(msg)

            yield (interface, stats)

    def _inspect_disks(self, domain):
        tree = etree.fromstring(domain.XMLDesc(0))
        for device in filter(
            bool,
            [target.get("dev")
             for target in tree.findall('devices/disk/target')]):
            disk = base.Disk(device=device)
            stats = None
            try:
                block_stats_1 = domain.blockStats(device)
                # block_latency_stats_1 = domain.blockStatsFlags(device)
                time.sleep(1)
                block_stats_2 = domain.blockStats(device)
                # Calculate read/write operations/s.
                read_requests_ps = self._cal_metric_ps(block_stats_2[0],
                                                       block_stats_1[0],
                                                       unit='operations/s')
                write_requests_ps = self._cal_metric_ps(block_stats_2[2],
                                                        block_stats_1[2],
                                                        unit='operations/s')
                # Calculate read/write megabytes/s.
                read_megabytes_ps = self._cal_metric_ps(block_stats_2[1],
                                                        block_stats_1[1],
                                                        unit='MB/s')
                write_megabytes_ps = self._cal_metric_ps(block_stats_2[3],
                                                         block_stats_1[3],
                                                         unit='MB/s')
                stats = base.DiskStats(read_requests_ps=read_requests_ps,
                                       write_requests_ps=write_requests_ps,
                                       read_megabytes_ps=read_megabytes_ps,
                                       write_megabytes_ps=write_megabytes_ps,
                                       errors=block_stats_2[4])
            except libvirt.libvirtError as e:
                msg = ('Failed to inspect %(device)s stats of '
                       '%(instance_uuid)s, can not get info from'
                       'libvirt: %(error)s') % {
                    'device': device, 'instance_uuid': domain.UUIDString(),
                    'error': e}
                LOG.error(msg)

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
                memory_used = memory_used / settings.UNITS['Ki']
                return base.MemoryUsageStats(usage=memory_used)
            else:
                msg = ('Failed to inspect memory usage of instance '
                       '<name=%(name)s, id=%(id)s>, '
                       'can not get info from libvirt.') % {
                    'name': domain.name(), 'id': domain.ID()}
                LOG.error(msg)
                return None
                # raise base.NoDataException(msg)
        # memoryStats might launch an exception if the method is not supported
        # by the underlying hypervisor being used by libvirt.
        except libvirt.libvirtError as e:
            msg = ('Failed to inspect memory usage of %(instance_uuid)s, '
                   'can not get info from libvirt: %(error)s') % {
                'instance_uuid': domain.UUIDString(), 'error': e}
            LOG.error(msg)
            # raise base.NoDataException(msg)

    def _inspect_disk_info(self, domain):
        tree = etree.fromstring(domain.XMLDesc(0))
        for disk in tree.findall('devices/disk'):
            disk_type = disk.get('type')
            if disk_type:
                if disk_type == 'network':
                    LOG.info('Inspection disk usage of network disk '
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
        try:
            memory = domain.memoryStats()['rss'] / settings.UNITS['Ki']
            return base.MemoryResidentStats(resident=memory)
        except libvirt.libvirtError as e:
            msg = ('Failed to inspect memory resident of %(instance_uuid)s, '
                   'can not get info from libvirt: %(error)s') % {
                'instance_uuid': domain.UUIDString(), 'error': e}
            LOG.error(msg)
