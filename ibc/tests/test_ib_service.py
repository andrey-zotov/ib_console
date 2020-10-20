import datetime

import pytest
from typing import List

from ib_insync import OrderStatus

import ibc.data_models as dm
from ibc.ib_service import IBBroker
from ibc.tests.mocks import IBAppMock, IBPositionMock, IBTradeFillMock

"""
"""
###################################################################
# Fixtures


@pytest.fixture(name='app')
def create_app_mock():
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


@pytest.fixture(name='service')
def create_service(app):
    return IBBroker(app)


@pytest.fixture(name='account')
def create_account() -> dm.Account:
    return dm.Account('prime', 3000., 2000., 1000., 3)


@pytest.fixture(name='position_msft')
def create_acc_position_msft(account) -> dm.Position:
    return dm.Position(account, 'MSFT', 1, 100., 100.)


@pytest.fixture(name='position_googl')
def create_acc_position_googl(account) -> dm.Position:
    return dm.Position(account, 'GOOGL', 2, 200., 400.)


@pytest.fixture(name='order_googl_acq')
def create_order_googl_acq(account) -> dm.Order:
    return dm.Order(account, 'GOOGL', dm.OrderAction.BUY,
                    req_qty=1, lmt_price=1420.53, ib_id=1)


@pytest.fixture(name='order_googl_acq_hedge')
def create_order_googl_acq_hedge(account) -> dm.Order:
    return dm.Order(account, 'SPY_PUT_OPTION', dm.OrderAction.BUY,
                    lmt_price=23., ib_id=2)


@pytest.fixture(name='order_googl_dis')
def create_order_googl_dis(account) -> dm.Order:
    return dm.Order(account, 'GOOGL', dm.OrderAction.SELL,
                    req_qty=1, lmt_price=None, ib_id=3)


@pytest.fixture(name='order_googl_dis_hedge')
def create_order_googl_dis_hedge(account) -> dm.Order:
    return dm.Order(account, 'SPY_PUT_OPTION', dm.OrderAction.SELL,
                    req_qty=1, lmt_price=None, ib_id=4)


###################################################################
# Tests

def test_update_account_clear_pos(service: IBBroker, account: dm.Account, position_msft: dm.Position, position_googl: dm.Position):

    assert len(account.positions) == 2
    service.refresh_account(account)

    assert account.total_value == 3000.1
    assert account.cash_value == 1000.1
    assert account.available_funds == 2000.1
    assert account.day_trades_remaining == 2
    assert len(account.positions) == 0


def test_update_account_add_pos(app, ib_position_fb, service: IBBroker, account: dm.Account, position_msft: dm.Position, position_googl: dm.Position):

    assert len(account.positions) == 2
    assert len(app.positions('a')) == 1
    service.refresh_account(account)
    assert len(account.positions) == 1

    assert len(account.positions) == 1
    assert account.positions[0].symbol == 'FB'
    assert account.positions[0].value == ib_position_fb.avgCost * ib_position_fb.position


def test_update_account_upd_pos(app, ib_position_msft, service: IBBroker, account: dm.Account, position_msft: dm.Position, position_googl: dm.Position):

    service.refresh_account(account)

    assert len(account.positions) == 1
    assert account.positions[0].symbol == 'MSFT'
    assert account.positions[0].value == ib_position_msft.avgCost * ib_position_msft.position


def test_create_contract_valid(app, service: IBBroker):
    contract = service.create_contract('GOOGL')
    assert contract is not None


def test_create_contract_nyse(app, service: IBBroker):
    contract = service.create_contract('MSFT')
    assert contract is not None
    assert contract.exchange == 'NYSE'


def test_create_contract_dummy(app, service: IBBroker):
    contract = service.create_contract('DUMMY')
    assert contract is None

