from libvirt_monitoring import inspector
from pyzabbix import ZabbixMetric, ZabbixSender


THRESHOLD = {
	# 'cpu_threshold': 90,	
}


class LibvirtAgent(object):

	def __init__(self, inspector):
		self.inspector = inspector.LibvirtInspector()
        self.sender = ZabbixSender(use_config=True)

    def send(self):
        metrics = self.inspector.get_vm_metrics()
        # self.sender
