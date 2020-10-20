import configparser


class MissingConfigurationFile(Exception):
    """Configuration file is missing"""


def get_config():
    config = configparser.ConfigParser()
    res = config.read('ibc.ini')
    if len(res) == 0:
        raise MissingConfigurationFile()
    return config
