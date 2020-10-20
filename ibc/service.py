"""
Bot actions
"""
import datetime
import logging
import math

from typing import List
import pytz
import tzlocal

from sqlalchemy.engine import Engine, create_engine
from sqlalchemy.orm import Session

import ibc.config as config
from ibc.data_models import Base, Account, Order, OrderAction, OrderStatus
from ibc.ib_service import IBBroker


class Service:
    """ Service with ibc actions

        Requires connection to database and a IBKR broker app
    """

    def __init__(self, data_engine_conn_str: str = 'sqlite://', broker: IBBroker = None):
        """ Service consutructor
            - data_engine_conn_str argument is used in tests for providing mock data connection
            - broker argument is used in tests for providing mock broker
        """
        self.data_engine_conn_str = data_engine_conn_str
        self.data_engine: Engine = None
        self.session: Session = None
        self.broker: IBBroker = broker
        self.account_code: str = ""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.broker is not None:
            self.broker.__exit__(None, None, None)
        if self.session is not None:
            self.session.close()
            self.session = None
        if self.data_engine is not None:
            self.data_engine = None

    # TODO convert to decorators
    def __init_db_engine(self):
        if self.data_engine is None:
            self.data_engine = create_engine(self.data_engine_conn_str)
        if "Accounts" not in self.data_engine.table_names():
            logging.info("Creating db schema...")
            Base.metadata.create_all(self.data_engine)

    def __init_db_session(self):
        self.__init_db_engine()
        if self.session is None:
            self.session = Session(self.data_engine)

    def __init_ib_app(self):
        if self.broker is None:
            self.broker = IBBroker().__enter__()
        self.account_code = self.broker.get_account_code()
        if not self.session.query(Account).filter(Account.code == self.account_code).all():
            acc = Account(self.account_code, 0, 0, 0, 0)
            self.session.add(acc)
            self.session.commit()

    @property
    def active_account(self) -> Account:
        self.__init_db_session()
        self.__init_ib_app()
        assert self.account_code
        return self.session.query(Account).filter(Account.code == self.account_code).one()

    def refresh_account(self) -> Account:
        """ Update account data from IB and return the objects
        """
        self.__init_db_session()
        self.__init_ib_app()

        assert self.active_account.id
        self.broker.refresh_account(self.active_account)
        self.session.commit()

        return self.active_account

    @property
    def active_orders(self) -> List[Order]:
        """ Get active trades
        """
        self.__init_db_session()

        trades = self.session.query(Order).filter(Order.status.notin_([OrderStatus.CANCD])).all()

        return trades
