import os
from six.moves import configparser


def ini_file_loader(filename=None):
    """ Load configuration from ini file"""
    if not filename:
    	dir_path = os.path.dirname(os.path.realpath(__file__))
    	filename = dir_path + '/config.ini'
    parser = configparser.SafeConfigParser()
    parser.read([filename])
    config_dict = {}

    for section in parser.sections():
        for key, value in parser.items(section, True):
            config_dict['%s-%s' % (section, key)] = value

    return config_dict

