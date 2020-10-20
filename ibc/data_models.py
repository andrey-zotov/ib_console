"""
    Object model for ibc operations:
    - Account
    - Positions
    - Trades
    - Orders
"""

import enum
import datetime
import logging
import math
from typing import List

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Date,
    DateTime,
    Enum,
    ForeignKey
)


Base = declarative_base()


class Account(Base):
    """ Account
    """
    __tablename__ = "Accounts"

    id = Column(Integer, primary_key=True)
    code = Column(String, nullable=False, unique=True)
    total_value = Column(Float, nullable=False)
    cash_value = Column(Float, nullable=False)
    available_funds = Column(Float, nullable=False)
    day_trades_remaining = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    positions = relationship("Position", cascade="all, delete-orphan", lazy='subquery')
    orders = relationship("Order", back_populates="account")

    def __init__(self, code: str, total_value: float, cash_value: float, available_funds: float, day_trades_remaining: int):
        self.code = code
        self.total_value = total_value
        self.cash_value = cash_value
        self.available_funds = available_funds
        self.day_trades_remaining = day_trades_remaining
        self.positions: List[Position] = []
        self.created_at = datetime.datetime.utcnow()
        self.updated_at = datetime.datetime.utcnow()

    def update(self, total_value: float, cash_value: float, available_funds: float, day_trades_remaining: int):
        self.total_value = total_value
        self.cash_value = cash_value
        self.available_funds = available_funds
        self.day_trades_remaining = day_trades_remaining
        self.updated_at = datetime.datetime.utcnow()

    @property
    def positions_value(self) -> float:
        return sum([t.value for t in self.positions])

    @property
    def positions_current_value(self) -> float:
        return sum([t.current_value for t in self.positions])

    @property
    def positions_profit(self) -> float:
        return sum([t.profit for t in self.positions])

    @property
    def positions_profit_margin(self) -> float:
        return (sum([t.profit for t in self.positions]) / self.positions_value) if self.positions_value else 0.


class Position(Base):
    """ Positions currently held in the account
    """
    __tablename__ = "Positions"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey('Accounts.id'), nullable=False)
    symbol = Column(String, nullable=False)
    qty = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    value = Column(Float, nullable=False)
    current_price = Column(Float, nullable=True)
    current_value = Column(Float, nullable=True)
    profit = Column(Float, nullable=True)
    profit_margin = Column(Float, nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    account = relationship(Account, back_populates="positions", lazy="subquery")

    def __init__(self, account: Account, symbol: str, qty: int, price: float, value: float):
        self.account = account
        self.account_id = account.id
        self.symbol = symbol
        self.qty = qty
        self.price = price
        self.value = value

        self.current_price = price
        self.current_value = value
        self.profit = 0.
        self.profit_margin = 0.

        self.created_at = datetime.datetime.utcnow()
        self.updated_at = datetime.datetime.utcnow()

    def update(self, qty: int, price: float, value: float):
        self.qty = qty
        self.price = price
        self.value = value
        self.updated_at = datetime.datetime.utcnow()

    def update_pnl(self, last_price: float):
        if last_price is not None and not math.isnan(last_price):
            self.current_price = last_price
            self.current_value = abs(self.qty * last_price)
            if self.qty >= 0:
                self.profit = self.current_value - self.value
            else:
                self.profit = self.value - self.current_value
            self.profit_margin = (self.profit / self.value) if self.value else 0.
            self.updated_at = datetime.datetime.utcnow()


class OrderStatus(enum.Enum):
    """ Order status
        - NEW - New order created
        - SENT - Order sent
        - ACTIVE - Order active
        - CANCD - Order cancelled
        - OK - Order completed
        - ERROR - Order error
    """

    NEW = 10
    SENT = 20
    ACTIVE = 30
    OK = 40
    CANCD = 50
    ERROR = 60


class OrderAction(enum.Enum):
    """ Order action
        - BUY - Purchase
        - SELL - Sale
    """
    BUY = 10
    SELL = 20


class Order(Base):
    """ Order

        Order and its execution details
    """
    __tablename__ = "Orders"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey('Accounts.id'), nullable=False)

    code = Column(String, nullable=False)
    symbol = Column(String, nullable=False)
    status = Column(Enum(OrderStatus), nullable=False)
    action = Column(Enum(OrderAction), nullable=False)
    req_qty = Column(Integer, nullable=False)
    lmt_price = Column(Float, nullable=True)

    sent_at = Column(DateTime)
    completed_at = Column(DateTime)

    qty = Column(Integer, nullable=False, default=0, doc="Actual filled quantity")
    avg_price = Column(Float, doc="Actual average price")
    commission = Column(Float, doc="Broker commission")

    ib_id = Column(Integer, doc="IB order id")
    ib_order_type = Column(String, doc="IB order type")
    ib_order_status = Column(String, doc="IB order status")

    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    account = relationship(Account, back_populates="orders")

    def __init__(self, account: Account, symbol: str, action: OrderAction, req_qty: int, lmt_price: float, ib_id: int):
        self.account = account
        self.account_id = account.id
        self.code = symbol + ' ' + action.name + ' ' + str(datetime.datetime.now())
        self.symbol = symbol
        self.status = OrderStatus.NEW
        self.action = action
        self.req_qty = req_qty
        self.lmt_price = lmt_price

        self.sent_at: datetime = None
        self.completed_at: datetime = None
        self.qty = 0
        self.avg_price = 0.
        self.commission = 0.

        self.ib_id = ib_id

        self.created_at = datetime.datetime.utcnow()
        self.updated_at = datetime.datetime.utcnow()

    def update(self, status: OrderStatus, sent_at: datetime.datetime, completed_at: datetime.datetime, qty: int, avg_price: float, commission: float,
               ib_order_type: str = None, ib_order_status: str = None):

        self.status = status

        self.sent_at = sent_at
        self.completed_at = completed_at
        self.qty = qty
        self.avg_price = avg_price
        self.commission = commission

        self.ib_order_type = ib_order_type
        self.ib_order_status = ib_order_status

        self.updated_at = datetime.datetime.utcnow()
