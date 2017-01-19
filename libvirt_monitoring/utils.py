import logging
import logging.config
import os
from six.moves import configparser


DIR_PATH = os.path.dirname(os.path.realpath(__file__))


def ini_file_loader(filename=None):
    """ Load configuration from ini file"""
    if not filename:
        filename = DIR_PATH + '/config.ini'
    parser = configparser.SafeConfigParser()
    parser.read([filename])
    config_dict = {}

    for section in parser.sections():
        for key, value in parser.items(section, True):
            config_dict['%s-%s' % (section, key)] = value

    return config_dict


def logging_config_loader(errorfile='/var/log/libvirt_agent_error.log',
                          infofile='/var/log/libvirt_agent_info.log'):
    logini = DIR_PATH + '/logging.ini'
    logging.config.fileConfig(logini,
                              defaults={'errorfile': errorfile,
                                        'infofile': infofile},
                              disable_existing_loggers=False)
