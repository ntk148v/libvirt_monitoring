import logging
import time
from pyzabbix import ZabbixAPI, ZabbixMetric, ZabbixSender

from libvirt_monitoring import base
from libvirt_monitoring import inspector
from libvirt_monitoring import utils


LOG = logging.getLogger(__name__)


class LibvirtAgent(object):

    def __init__(self):
        # Load config from config.ini file
        self.config = utils.ini_file_loader()
        self.inspector = inspector.LibvirtInspector()
        # Config ZabbixSender and ZabbixAPI
        if self.config['zabbix_agent-use_config'] == 'True':
            self.zsender = ZabbixSender(use_config=True)
        else:
            self.zsender = ZabbixSender(
                zabbix_server=self.config['zabbix_server-ip'],
                zabbix_port=int(self.config['zabbix_server-port']))
        LOG.debug('Init ZabbixSender object - {}' . format(self.zsender))
        self.zapi = ZabbixAPI(url=self.config['zabbix_server-url'],
                              user=self.config['zabbix_server-user'],
                              password=self.config['zabbix_server-password'])
        LOG.debug('Init ZabbixAPI object - {}' . format(self.zapi))

    def run(self):
        """Run Agent forever.
        """
        while True:
            LOG.debug('Starting agent, get and send metrics')
            self.get_and_send_metrics()
            time.sleep(60)

    def get_and_send_metrics(self):
        """Get metrics from inspector
        send it to ZabbixServer.
        """
        all_metrics = self.inspector.get_vm_metrics()
        for vm, vm_metrics in all_metrics.items():
            for metric_key, metric_value in vm_metrics.items():
                if not metric_value:
                    msg = ('Failed when get %(metric)s' %
                           {'metric': metric_key})
                    LOG.error(msg)
                    continue
                for f in metric_value._fields:
                    # Item key, example: cpustats.number[instance-000002ee]
                    item_key = "{}.{}[{}]" . format(metric_key, f, vm)
                    item_name = "{} - {} - {}" . format(vm.title(),
                                                        metric_key.title(),
                                                        f.title())
                    item_value = getattr(metric_value, f)
                    LOG.debug('Get item {} = {}' . format(
                        item_key, item_value))
                    self.send_item(base.Item(key=item_key,
                                             name=item_name,
                                             value=item_value))

    def get_agent_hostid(self):
        """Get agent hostid.
        """
        get_params = {
            'filter': {
                'host': self.config['zabbix_agent-hostname']
            }
        }

        resp = self.zapi.do_request('host.get', get_params)
        if len(resp['result']) > 1:
            LOG.info('Re-check hostname configuration,\
                you have more than one host with hostname {}'
                     . format(self.config['zabbix_agent-hostname']))
        elif len(resp['result']) == 1:
            LOG.info('Hostid {}' . format(resp['result'][0]['hostid']))
            return resp['result'][0]['hostid']
        else:
            LOG.exception('Unknow hostname {}' .
                          format(self.config['zabbix_agent-hostname']))

    def create_trigger(self, item):
        """Create trigger.
        """
        try:
            _expression = "{" + self.config['zabbix_agent-hostname'] + \
                ":" + item.key + ".count(" + \
                self.config['trigger-sec'] + \
                ")}>" + self.config['trigger-constant']
            _description = item.name + " last " + \
                self.config['trigger-sec'] + " is too high"

            # Get agent hostid
            _hostid = self.get_agent_hostid()
            if _hostid:
                # Check trigger is existed or not.
                get_params = {
                    'output': 'extend',
                    'hostids': _hostid,
                    'search': {
                        'description': item.name
                    }
                }
                # Get trigger by its id.
                resp = self.zapi.do_request('trigger.get', get_params)
                if len(resp['result']) == 0:
                    create_params = {
                        "description": _description,
                        "priority": 2,  # Warning
                        "expression": _expression,
                    }
                    # Create trigger.
                    self.zapi.do_request('trigger.create', create_params)
                    LOG.info('Create trigger!')
                else:
                    LOG.info('Trigger is existed!')
                    pass
            else:
                LOG.error('Not found hostid!')
        except Exception as e:
            LOG.error('Error when creating trigger - {}!' . format(e))
            raise e

    def create_item(self, item):
        """Create item
        """
        # Get agent hostid
        _hostid = self.get_agent_hostid()
        if _hostid:
            get_params = {
                'output': 'extend',
                'hostids': _hostid,
                'search': {
                    'key_': item.key
                }
            }

            resp = self.zapi.do_request('item.get', get_params)
            # Check item is existed or not.
            if len(resp['result']) == 0:
                create_params = {
                    'name': item.name,
                    'key_': item.key,
                    'hostid': _hostid,
                    'value_type': 3,
                    'type': 2,
                }

                self.zapi.do_request('item.create', create_params)
                LOG.info('Created new item with key {}' . format(item.key))
        else:
            LOG.error('Not found hostid!')

    def _check_threshold_item(self, item):
        """Check threshold for specific given item.
        """
        # Specific metrics.
        threshold_types = [
            'read_requests_ps',
            'write_requests_ps',
            'tx_megabits_ps',
            'rx_megabits_ps',
        ]

        for t in threshold_types:
            if t in item.key:
                return t
            else:
                return None

    def send_item(self, item):
        """Send item to Zabbix Server.

        Check if item value is over its threshold
        create item (if it is't existed) and send value
        to Zabbix Server.
        """
        try:
            _metric = self._check_threshold_item(item)
            if _metric:
                # Create item first, if it's not existed
                self.create_item(item)
                # Item value > Defined Threshold, send it to Zabbix Server
                if abs(item.value) > int(self.config['thresholds-' + _metric]):
                    metrics = \
                        [ZabbixMetric(self.config['zabbix_agent-hostname'],
                                      item.key, item.value)]
                    result = self.zsender.send(metrics)
                    LOG.info('Send metric {} : {}' . format(item.name,
                                                            result))
                    # Create trigger for this item.
                    self.create_trigger(item)
        except Exception as e:
            LOG.error(
                'Error when send metric to Zabbix Server - {}' . format(e))
