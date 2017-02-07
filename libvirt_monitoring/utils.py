import logging
import logging.config
from six.moves import configparser

from libvirt_monitoring import settings


def ini_file_loader():
    """ Load configuration from ini file"""

    parser = configparser.SafeConfigParser()
    parser.read([settings.CONF_PATH])
    config_dict = {}

    for section in parser.sections():
        for key, value in parser.items(section, True):
            config_dict['%s-%s' % (section, key)] = value

    return config_dict


def logging_config_loader():
    # Load config.ini, get config about
    configs = ini_file_loader()
    errorfile = configs['default-error_log_file']
    infofile = configs['default-info_log_file']
    debug = configs['default-debug']

    logging.config.fileConfig(settings.LOG_CONF_PATH,
                              defaults={'errorfile': errorfile,
                                        'infofile': infofile},
                              disable_existing_loggers=False)
    # Set root logger level depend on config.ini file
    if debug == 'True':
        root_logger = logging.root
        # Set root logger's level to DEBUG
        root_logger.setLevel(logging.DEBUG)
        # Find infoHandler and set its level to DEBUG
        for handler in root_logger.handlers:
            if handler.level == logging.INFO:
                handler.setLevel(logging.DEBUG)
