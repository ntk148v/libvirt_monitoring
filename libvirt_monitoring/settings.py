import os


# Current directory path
DIR_PATH = os.path.dirname(os.path.realpath(__file__))

# Configuration file config.ini path
CONF_PATH = DIR_PATH + '/config.ini'

# Logging configuration file path
LOG_CONF_PATH = DIR_PATH + '/logging.ini'

# VM state mapper
STATE_MAPPER = {
    0: 'VIR_DOMAIN_NONE',
    1: 'VIR_DOMAIN_RUNNING',
    2: 'VIR_DOMAIN_BLOCKED',
    3: 'VIR_DOMAIN_PAUSED',
    4: 'VIR_DOMAIN_SHUTDOWN',
    5: 'VIR_DOMAIN_SHUTOFF',
    6: 'VIR_DOMAIN_CRASHED',
    7: 'VIR_DOMAIN_PMSUSPENDED'
}

# Binary unit constants.
UNITS = {
    'Ki': 1024,  # Binary kilo unit
    'Mi': 1024 ** 2,  # Binary mega unit
    'Gi': 1024 ** 3,  # Binary giga unit
    'Ti': 1024 ** 4,  # Binary tera unit
}
