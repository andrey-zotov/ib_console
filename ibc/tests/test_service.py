import copy
import datetime
import logging

import pytest
from typing import List

from ibc.data_models import Account, Position, OrderAction, OrderStatus
from ibc.ib_service import IBBroker
from ibc.service import Service

from ibc.tests.mocks import IBAppMock, IBPositionMock

"""
"""
###################################################################
# Fixtures


@pytest.fixture(name='app')
def create_app() -> IBAppMock:
    return IBAppMock("prime")


@pytest.fixture(name='ib_position_fb')
def create_ib_position_googl(app) -> IBPositionMock:
    res = IBPositionMock('FB', 301., 3)
    app.add_position(res)
    return res


@pytest.fixture(name='ib_position_msft')
def create_ib_position_msft(app) -> IBPositionMock:
    res = IBPositionMock('MSFT', 201., 2)
    app.add_position(res)
    return res


@pytest.fixture(name='broker')
def create_broker(app) -> IBBroker:
    return IBBroker(app)


@pytest.fixture(name='service')
def create_service(broker) -> Service:
    service = Service('sqlite://', broker)
    return service


@pytest.fixture(name='account')
def create_account(service) -> Account:
    return service.active_account


@pytest.fixture(name='position_msft')
def create_acc_position_msft(account) -> Position:
    return Position(account, 'MSFT', 1, 100., 100.)


@pytest.fixture(name='position_googl')
def create_acc_position_googl(account) -> Position:
    return Position(account, 'GOOGL', 2, 200., 400.)


###################################################################
# Tests

def test_seed_account(service):
    service.active_account
    assert "Accounts" in service.data_engine.table_names()
    assert service.session.query(Account).filter(Account.code == "prime").one().code == "prime"


def test_update_account(service, broker):
    assert service.active_account.cash_value == 0.
    service.refresh_account()

    assert service.active_account.cash_value == 1000.1


def test_update_account_add_position(service, broker, ib_position_fb):

    acc = service.refresh_account()

    assert len(acc.positions) == 1
    assert acc.positions[0].symbol == "FB"


def test_update_account_upd_position(service, broker, position_googl, position_msft, ib_position_msft):

    service.refresh_account()

    service.session.expire_all()

    acc = service.active_account

    assert len(acc.positions) == 1
    assert acc.positions[0].symbol == "MSFT"
    assert acc.positions[0].value == 402.
