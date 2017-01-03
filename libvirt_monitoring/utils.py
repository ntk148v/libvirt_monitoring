from six.moves import configparser


def ini_file_loader(filename='libvirt_monitoring/config.ini'):
    """ Load configuration from ini file"""
    parser = configparser.SafeConfigParser()
    parser.read([filename])
    config_dict = {}

    for section in parser.sections():
        for key, value in parser.items(section, True):
            config_dict['%s-%s' % (section, key)] = value

    return config_dict

