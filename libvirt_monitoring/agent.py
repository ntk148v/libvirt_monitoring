import logging
import time
from pyzabbix import ZabbixAPI, ZabbixMetric, ZabbixSender

from libvirt_monitoring import base
from libvirt_monitoring import inspector
from libvirt_monitoring import utils


LOG = logging.getLogger(__name__)
TRIGGERID = None


class LibvirtAgent(object):

    def __init__(self):
        self.config = utils.ini_file_loader()
        self.inspector = inspector.LibvirtInspector()
        self.zsender = ZabbixSender(use_config=True)
        self.zapi = ZabbixAPI(url=self.config['zabbix_server-url'],
                              user=self.config['zabbix_server-user'],
                              password=self.config['zabbix_server-password'])

    def run(self):
        while True:
            self.get_and_send_metrics()
            time.sleep(60)

    def get_and_send_metrics(self):
        all_metrics = self.inspector.get_vm_metrics()
        for vm, vm_metrics in all_metrics.items():
            for metric_key, metric_value in vm_metrics.items():
                for f in metric_value._fields:
                    # Item key, example: cpustats.number[instance-000002ee]
                    item_key = "{}.{}[{}]" . format(metric_key, f, vm)
                    item_name = "{} - {} - {}" . format(vm.title(),
                                                        metric_key.title(),
                                                        f.title())
                    item_value = getattr(metric_value,  f)
                    self.send_item(base.Item(key=item_key,
                                             name=item_name,
                                             value=item_value))

    def get_agent_hostid(self):
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
        try:
            _expression = "{" + self.config['zabbix_agent-hostname'] + \
                ":" + item.key + ".count(" + \
                self.config['trigger-sec'] + \
                ")}>" + self.config['trigger-constant']

            create_params = {
                "description": item.name + " last 5 mins is too high",
                "priority": 2,  # Warning
                "expression": _expression,
            }

            resp = self.zapi.do_request('trigger.create', create_params)
            global TRIGGERID
            TRIGGERID = resp['result']['triggerids']
            LOG.info('Create trigger!')
        except Exception as e:
            LOG.error('Error when creating trigger - {}!' . format(e))
            raise e

    def create_item(self, item):
        _hostid = self.get_agent_hostid()
        if _hostid:
            get_params = {
                'output': 'extend',
                'hostid': _hostid,
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

    def _check_trigger(self, triggerids):
        if triggerids:
            get_params = {
                'triggerids': triggerids,
            }

            resp = self.zapi.do_request('trigger.get', get_params)
            return len(resp['result']) > 0
        else:
            return False

    def _check_threshold_item(self, item):
        threshold_types = [
            'read_requests',
            'write_requests',
            'transmitted_ps',
            'received_ps',
        ]

        for t in threshold_types:
            if t in item.key:
                return t
            else:
                return None

    def send_item(self, item):
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
                    # Check trigger is existed or not.
                    if not self._check_trigger(TRIGGERID):
                        # Create trigger for this item.
                        self.create_trigger(item)
        except Exception as e:
            LOG.error(
                'Error when send metric to Zabbix Server - {}' . format(e))
