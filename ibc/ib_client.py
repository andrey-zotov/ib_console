"""
IB-insync library helpers
"""

import logging

from ib_insync import (
    IB
)

import ibc.config as config


class IBApplicationError(Exception):
    last_ib_error_code = 0
    last_ib_error_message = ""

    def __init__(self, ib_error_message="", ib_error_code=0):
        super().__init__()
        if ib_error_code:
            self.message = ib_error_message
            self.error_code = ib_error_code
        else:
            self.message = IBApplicationError.last_ib_error_message
            self.error_code = IBApplicationError.last_ib_error_code

    def __repr__(self):
        return "IB Application Error %s: %s" % (self.error_code, self.message)


def __on_app_error(reqId, errorCode, errorString, contract):
    IBApplicationError.last_ib_error_code = errorCode
    IBApplicationError.last_ib_error_message = errorString
    logging.debug("IB Message: " + errorString)


def init_app(client_id_=int(config.get_config()['IB']['IBClientId'])):
    app = IB()
    app.errorEvent += __on_app_error
    host = config.get_config()['IB']['IBHost']
    port = int(config.get_config()['IB']['IBPort'])
    client_id = client_id_
    app.connect(host, port, clientId=client_id, readonly=True)
    return app
