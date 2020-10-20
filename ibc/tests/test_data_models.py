"""
Test ibc data models
"""
import datetime
from typing import List

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

import ib_insync as ib

import ibc.data_models as dm

import pytest


###################################################################
# Fixtures

@pytest.fixture(name='engine')
def create_engine_() -> Engine:
    engine = create_engine('sqlite://', echo=False)
    dm.Base.metadata.create_all(engine)
    return engine


@pytest.fixture(name='session')
def create_session(engine) -> Session:
    return Session(engine)


@pytest.fixture(name='account')
def create_account() -> dm.Account:
    return dm.Account("prime", total_value=2235., cash_value=1000., available_funds=3500., day_trades_remaining=1)


@pytest.fixture(name='position_msft')
def create_pos_msft(account) -> dm.Position:
    return dm.Position(account, "MSFT", qty=10, price=205.35, value=2053.5)


@pytest.fixture(name='position_googl')
def create_pos_googl(account) -> dm.Position:
    return dm.Position(account, "GOOGL", qty=1, price=1440.12, value=1440.12)


@pytest.fixture(name='order_googl_acq')
def create_order_googl_acq(account) -> dm.Order:
    return dm.Order(account, 'GOOGL', dm.OrderAction.BUY,
                    req_qty=1, lmt_price=None, ib_id=1)


@pytest.fixture(name='order_googl_acq_hedge')
def create_order_googl_acq_hedge(account) -> dm.Order:
    return dm.Order(account, 'SPY_PUT_OPTION', dm.OrderAction.BUY,
                    req_qty=1, lmt_price=23., ib_id=2)


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

def test_engine_dml_create_all(engine: Engine):
    assert "Accounts" in engine.table_names()
    assert "Positions" in engine.table_names()
    assert "Orders" in engine.table_names()


def test_account_crud(session: Session, account: dm.Account):
    session.add(account)
    session.commit()

    account.update(10000., 5000., 10000., 2)
    session.commit()

    session.expire_all()

    accs: List[dm.Account] = session.query(dm.Account).all()
    assert len(accs) == 1
    assert accs[0].code == "prime"
    assert accs[0].total_value == 10000.


def test_positions_crud(session: Session, account: dm.Account, position_msft: dm.Position, position_googl: dm.Position):
    session.add(account)
    session.flush()
    session.add(position_msft)
    session.add(position_googl)
    session.commit()

    session.expire_all()

    accs: List[dm.Account] = session.query(dm.Account).all()

    assert len(accs) == 1
    assert accs[0].code == "prime"
    assert len(accs[0].positions) == 2
    assert accs[0].positions[0].symbol == "MSFT"

    position_msft.update(100, 1000., 100000.)
    session.commit()
    session.expire_all()

    accs2: List[dm.Account] = session.query(dm.Account).all()

    assert accs2[0].positions[0].symbol == "MSFT"
    assert accs2[0].positions[0].qty == 100
    assert accs[0].positions[0].qty == 100
    assert accs[0].positions[0] is accs2[0].positions[0]

    session.delete(position_msft)
    session.commit()

    assert len(accs2[0].positions) == 1


def test_orders_crud(session: Session, account: dm.Account, order_googl_acq: dm.Order, order_googl_dis: dm.Order):
    session.add(account)
    session.flush()
    session.add_all([order_googl_acq, order_googl_dis])
    session.commit()

    session.expire_all()

    orders: List[dm.Order] = session.query(dm.Order).all()

    assert len(orders) == 2
    assert orders[0].symbol == order_googl_acq.symbol

    order_googl_acq.update(dm.OrderStatus.NEW, datetime.datetime(2020, 3, 8, 9, 32, 15), datetime.datetime(2020, 3, 8, 15, 15, 15),
                           10, 1350., 1., 'LMT', 'Filled')
    session.commit()
    session.flush()

    session.expire_all()
    orders: List[dm.Order] = session.query(dm.Order).all()

    assert len(orders) == 2
    assert orders[0].avg_price == 1350.
