import logging
from pyzabbix import ZabbixAPI, ZabbixMetric, ZabbixSender

from libvirt_monitoring import inspector
from libvirt_monitoring import utils


LOG = logging.getLogger(__name__)


class LibvirtAgent(object):

    def __init__(self, inspector):
        self.config = utils.ini_file_loader()
        self.inspector = inspector.LibvirtInspector()
        self.zsender = ZabbixSender(use_config=True)
        self.zapi = ZabbixAPI(url=self.config['zabbix_server-url'],
                              user=self.config['zabbix_server-user'],
                              password=self.config['zabbix_server-password'])

    def get_metrics(self):
        metrics = self.inspector.get_vm_metrics()
        # self.zsender

    def create_item(self, item):
        get_params = {
            'output': 'extend',
            'hostids': self.config['zabbix-agent_hostid'],
            'search': {
                'key_': item.key
            }
        }

        resp = self.zapi.do_request('item.get', get_params)
        # Check item is existed or not.
        if len(resp['result']) == 0:
            create_params = {
                # API docs.
                # https://www.zabbix.com/documentation/3.2/manual/api/
                # create mapper, map specific item key with
                # value_type.
            }

            self.zapi.do_request('item.create', create_params)
            LOG.info('Created new item with key {}' . format(item.key))
