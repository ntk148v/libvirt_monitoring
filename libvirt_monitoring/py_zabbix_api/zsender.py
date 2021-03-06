"""A copy of Py-Zabbix Sender (link bellow).

https://github.com/blacked/py-zabbix/blob/master/pyzabbix/sender.py
"""
from decimal import Decimal
import json
import logging
import re
import socket
import struct

# For python 2 and 3 compatibility
try:
    from StringIO import StringIO
    import ConfigParser as configparser
except ImportError:
    from io import StringIO
    import configparser


try:
    from logging import NullHandler
except ImportError:
    # Added in Python 2.7
    class NullHandler(logging.Handler):
        def handle(self, record):
            pass

        def emit(self, record):
            pass

        def createLock(self):
            self.lock = None


LOG = logging.getLogger(__name__)
LOG.addHandler(NullHandler())


class ZabbixResponse(object):
    """The :class:`ZabbixResponse` contains the parsed response from Zabbix.
    """

    def __init__(self):
        self._processed = 0
        self._failed = 0
        self._total = 0
        self._time = 0
        self._chunk = 0
        pattern = (r'processed: (\d*); failed: (\d*); total: (\d*); '
                   'seconds spent: (\d*\.\d*)')
        self._regex = re.compile(pattern)

    def __repr__(self):
        """Represent detailed ZabbixResponse view."""
        result = json.dumps({'processed': self._processed,
                             'failed': self._failed,
                             'total': self._total,
                             'time': str(self._time),
                             'chunk': self._chunk})
        return result

    def parse(self, response):
        """Parse zabbix response."""
        info = response.get('info')
        res = self._regex.search(info)

        self._processed += int(res.group(1))
        self._failed += int(res.group(2))
        self._total += int(res.group(3))
        self._time += Decimal(res.group(4))
        self._chunk += 1

    @property
    def processed(self):
        return self._processed

    @property
    def failed(self):
        return self._failed

    @property
    def total(self):
        return self._total

    @property
    def time(self):
        return self._time

    @property
    def chunk(self):
        return self._chunk


class ZabbixMetric(object):
    """The :class:`ZabbixMetric` contain one metric for zabbix server.
    :type host: str
    :param host: Hostname as it displayed in Zabbix.
    :type key: str
    :param key: Key by which you will identify this metric.
    :type value: str
    :param value: Metric value.
    :type clock: int
    :param clock: Unix timestamp. Current time will used if not specified.
    >>> from pyzabbix import ZabbixMetric
    >>> ZabbixMetric('localhost', 'cpu[usage]', 20)
    """

    def __init__(self, host, key, value, clock=None):
        self.host = str(host)
        self.key = str(key)
        self.value = str(value)
        if clock:
            if isinstance(clock, (float, int)):
                self.clock = int(clock)
            else:
                raise Exception('Clock must be time in unixtime format')

    def __repr__(self):
        """Represent detailed ZabbixMetric view."""

        result = json.dumps(self.__dict__)
        LOG.debug('%s: %s', self.__class__.__name__, result)

        return result


class ZabbixSender(object):
    """The :class:`ZabbixSender` send metrics to Zabbix server.
    Implementation of
    `zabbix protocol <https://www.zabbix.com/documentation/1.8/protocols>`_.
    :type zabbix_server: str
    :param zabbix_server: Zabbix server ip address. Default: `127.0.0.1`
    :type zabbix_port: int
    :param zabbix_port: Zabbix server port. Default: `10051`
    :type use_config: str
    :param use_config: Path to zabbix_agentd.conf file to load settings from.
         If value is `True` then default config path will used:
         /etc/zabbix/zabbix_agentd.conf
    :type chunk_size: int
    :param chunk_size: Number of metrics send to the server at one time
    >>> from pyzabbix import ZabbixMetric, ZabbixSender
    >>> metrics = []
    >>> m = ZabbixMetric('localhost', 'cpu[usage]', 20)
    >>> metrics.append(m)
    >>> zbx = ZabbixSender('127.0.0.1')
    >>> zbx.send(metric)
    """

    def __init__(self,
                 zabbix_server='127.0.0.1',
                 zabbix_port=10051,
                 use_config=None,
                 chunk_size=250):

        self.chunk_size = chunk_size

        if use_config:
            self.zabbix_uri = self._load_from_config(use_config)
        else:
            self.zabbix_uri = [(zabbix_server, zabbix_port)]

    def __repr__(self):
        """Represent detailed ZabbixSender view."""

        result = json.dumps(self.__dict__, ensure_ascii=False)
        LOG.debug('%s: %s', self.__class__.__name__, result)

        return result

    def _load_from_config(self, config_file):
        """Load zabbix server ip address and port from zabbix agent file.
        If Server or Port variable won't be found in the file, they will be
        set up from defaults: 127.0.0.1:10051
        :type config_file: str
        :param use_config: Path to zabbix_agentd.conf file to load settings
            from. If value is `True` then default config path will used:
            /etc/zabbix/zabbix_agentd.conf
        """

        if config_file and isinstance(config_file, bool):
            config_file = '/etc/zabbix/zabbix_agentd.conf'

        LOG.debug('Used config: %s', config_file)

        #  This is workaround for config wile without sections
        with open(config_file, 'r') as f:
            config_file_data = "[root]\n" + f.read()

        default_params = {
            'Server': '127.0.0.1',
            'Port': 10051,
        }

        config_file_fp = StringIO(config_file_data)
        config = configparser.RawConfigParser(default_params)
        config.readfp(config_file_fp)
        zabbix_server = config.get('root', 'Server')
        zabbix_port = config.get('root', 'Port')
        hosts = [server.strip() for server in zabbix_server.split(',')]
        result = [(server, zabbix_port) for server in hosts]
        LOG.debug('Loaded params: %s', result)

        return result

    def _receive(self, sock, count):
        """Reads socket to receive data from zabbix server.
        :type socket: :class:`socket._socketobject`
        :param socket: Socket to read.
        :type count: int
        :param count: Number of bytes to read from socket.
        """

        buf = b''

        while len(buf) < count:
            chunk = sock.recv(count - len(buf))
            if not chunk:
                break
            buf += chunk

        return buf

    def _create_messages(self, metrics):
        """Create a list of zabbix messages from a list of ZabbixMetrics.
        :type metrics_array: list
        :param metrics_array: List of :class:`zabbix.sender.ZabbixMetric`.
        :rtype: list
        :return: List of zabbix messages.
        """

        messages = []

        # Fill the list of messages
        for m in metrics:
            messages.append(str(m))

        LOG.debug('Messages: %s', messages)

        return messages

    def _create_request(self, messages):
        """Create a formatted request to zabbix from a list of messages.
        :type messages: list
        :param messages: List of zabbix messages
        :rtype: list
        :return: Formatted zabbix request
        """

        msg = ','.join(messages)
        request = '{{"request":"sender data","data":[{msg}]}}'.format(msg=msg)
        request = request.encode('utf-8')
        LOG.debug('Request: %s', request)

        return request

    def _create_packet(self, request):
        """Create a formatted packet from a request.
        :type request: str
        :param request: Formatted zabbix request
        :rtype: str
        :return: Data packet for zabbix
        """

        data_len = struct.pack('<Q', len(request))
        packet = b'ZBXD\x01' + data_len + request

        def ord23(x):
            if not isinstance(x, int):
                return ord(x)
            else:
                return x

        LOG.debug('Packet [str]: %s', packet)
        LOG.debug('Packet [hex]: %s',
                  ':'.join(hex(ord23(x))[2:] for x in packet))
        return packet

    def _get_response(self, connection):
        """Get response from zabbix server, reads from self.socket.
        :type connection: :class:`socket._socketobject`
        :param connection: Socket to read.
        :rtype: dict
        :return: Response from zabbix server or False in case of error.
        """

        response_header = self._receive(connection, 13)
        LOG.debug('Response header: %s', response_header)

        if (not response_header.startswith(b'ZBXD\x01') or
                len(response_header) != 13):
            LOG.debug('Zabbix return not valid response.')
            result = False
        else:
            response_len = struct.unpack('<Q', response_header[5:])[0]
            response_body = connection.recv(response_len)
            result = json.loads(response_body.decode('utf-8'))
            LOG.debug('Data received: %s', result)

            # Get info from result.
            #
            # result = {u'info': u'processed: 1; failed: 0; total: 1;
            # seconds spent: 0.000034', u'response': u'success'}
            #
            # info = {u'failed': u'0', u'total': u'1', u'processed': u'1',
            # u'seconds spent': u'0.000034'}
            #
            info = []
            for e in result['info'].split(';'):
                info.append([_e.strip() for _e in e.split(':')])
            info = dict(info)

            if int(info['failed']) > 0:
                LOG.error(
                    '### Failed when sending metric to server: %s ###', info)
            if int(info['processed']) > 0:
                LOG.info(
                    '### Success when sending metric to server: %s ###', info)

        try:
            connection.close()
        except Exception as err:
            pass

        return result

    def _chunk_send(self, metrics):
        """Send the one chunk metrics to zabbix server.
        :type metrics: list
        :param metrics: List of :class:`zabbix.sender.ZabbixMetric` to send
            to Zabbix
        :rtype: str
        :return: Response from Zabbix Server
        """
        messages = self._create_messages(metrics)
        request = self._create_request(messages)
        packet = self._create_packet(request)

        for host_addr in self.zabbix_uri:
            LOG.debug('Sending data to %s', host_addr)

            # create socket object
            connection = socket.socket()

            # server and port must be tuple
            connection.connect(host_addr)

            try:
                connection.sendall(packet)
            except Exception as err:
                # In case of error we should close connection, otherwise
                # we will close it afret data will be received.
                connection.close()
                raise Exception(err)

            response = self._get_response(connection)
            LOG.debug('%s response: %s', host_addr, response)

            if response and response.get('response') != 'success':
                LOG.debug('Response error: %s}', response)
                raise Exception(response)

        return response

    def send(self, metrics):
        """Send the metrics to zabbix server.
        :type metrics: list
        :param metrics: List of :class:`zabbix.sender.ZabbixMetric` to send
            to Zabbix
        :rtype: :class:`pyzabbix.sender.ZabbixResponse`
        :return: Parsed response from Zabbix Server
        """
        result = ZabbixResponse()
        for m in range(0, len(metrics), self.chunk_size):
            result.parse(self._chunk_send(metrics[m:m + self.chunk_size]))
        return result
