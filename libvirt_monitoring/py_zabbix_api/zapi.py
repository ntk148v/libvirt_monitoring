"""A copy with some litte changes of both
Python Zabbix API libs (link bellow).

- Py-zabbix: https://github.com/blacked/py-zabbix
- Pyzabbix: https://github.com/lukecyca/pyzabbix

"""
import json
import logging
import requests


class _NullHandler(logging.Handler):

    def emit(self, record):
        pass


LOG = logging.getLogger(__name__)
LOG.addHandler(_NullHandler())


class ZabbixAPIException(Exception):
    pass


class ZabbixAPIObjectClass(object):
    """ZabbixAPI Object class"""

    def __init__(self, name, parent):
        self.name = name
        self.parent = parent

    def __getattr__(self, attr):
        """Dynamically create a method (ie: get)"""
        def fn(*args, **kwargs):
            if args and kwargs:
                raise TypeError('Found both args and kwargs')

            return self.parent.do_request(
                '{0}.{1}'.format(self.name, attr),
                args or kwargs
            )['result']
    return fn


class ZabbixAPI(object):

    def __init__(self, url='http://localhost/zabbix',
                 user='Admin', password='zabbix',
                 timeout=None, session=None):
        if session:
            self.session = session
        else:
            self.session = requests.Session()

        self.timeout = timeout

        self.id = 0
        self.url = url
        self.auth = None
        self._login(user, password)
        LOG.debug('JSON-RPC Server Endpoint: %s', self.url)

    def _login(self, user='', password=''):
        """Do login to zabbix server.

        :param user(str): Username used to login into Zabbix.
        :param password(str): Password used to login into Zabbix.
        """
        self.auth = self.user.login(user=user, password=password)
        LOG.debug("ZabbixAPI.login(%s, %s)", user, password)

    def __getattr__(self, attr):
        """Dynamically create an object class (ie: host)"""
        return ZabbixAPIObjectClass(attr, self)

    def api_version(self):
        return self.apiinfo.version()

    def confimport(self, confformat='', source='', rules=''):
        """Alias for configuration.import because it clashes with
           Python's import reserved keyword
        :param rules:
        :param source:
        :param confformat:
        """

        return self.do_request(
            method="configuration.import",
            params={"format": confformat, "source": source, "rules": rules}
        )['result']

    def do_request(self, method, params=None):
        request_json = {
            'jsonrpc': '2.0',
            'method': method,
            'params': params or {},
            'id': self.id,
        }

        # apiinfo.version and user.login doesn't require auth token
        if self.auth and (method not in ('apiinfo.version', 'user.login')):
            request_json['auth'] = self.auth

        LOG.debug("Sending: %s", json.dumps(request_json,
                                            indent=4,
                                            separators=(',', ': ')))
        response = self.session.post(
            self.url,
            data=json.dumps(request_json),
            timeout=self.timeout
        )
        LOG.debug('Response Code: %s', str(response.status_code))

        # NOTE: Getting a 412 response code means the headers are not in the
        # list of allowed headers.
        response.raise_for_status()

        if not len(response.text):
            raise ZabbixAPIException('Received empty response')

        try:
            response_json = json.loads(response.text)
        except ValueError:
            raise ZabbixAPIException(
                'Unable to parse json: %s', response.text
            )
        LOG.debug('Response Body: %s', json.dumps(response_json,
                                                  indent=4,
                                                  separators=(',', ': ')))

        self.id += 1

        if 'error' in response_json:  # some exception
            if 'data' not in response_json['error']:
                # some errors don't contain 'data': workaround for ZBX-9340
                response_json['error']['data'] = "No data"
            msg = "Error {code}: {message}, {data}".format(
                code=response_json['error']['code'],
                message=response_json['error']['message'],
                data=response_json['error']['data']
            )
            raise ZabbixAPIException(msg, response_json['error']['code'])

        return response_json
