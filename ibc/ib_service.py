""" IB access layer
"""
import datetime
import logging

import ib_insync as ib
from typing import List, Dict, Tuple

import ibc.config as config
from ibc.data_models import Account, Order, Position, OrderAction, OrderStatus
import ibc.market_data as md


class IBBroker:
    """ Service with IB broker actions.

        The service is responsible for mapping IB specific calls, event handlers and objects to internal entities.
    """

    def __init__(self, app: ib.IB = None):
        """ Service constructor
            - app argument is used in tests for providing mock app/db
        """
        self.app: ib.IB = app
        self.md: md.Server = None
        self.contracts: Dict[str, ib.Contract] = {}
        self.__position_chart_data: List[Tuple[Position, md.ChartData]] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.app is not None:
            self.md.remove_all()
            self.app.disconnect()

    def __init_ib_app(self):
        if self.app is None:
            import ibc.ib_auto_app as ib  # pylint: disable=import-outside-toplevel
            self.app = ib.APP
        if self.md is None:
            self.md = md.Server(self.app)

    def find_position_chart_data_index(self, position: Position):
        for i, val in enumerate(self.__position_chart_data):
            if val[0] is position:
                return i
        return -1

    def get_position_chart_data(self, position: Position):
        i = self.find_position_chart_data_index(position)
        if i >= 0:
            return self.__position_chart_data[i][1]
        else:
            return None

    def store_position_chart_data(self, position: Position, chart_data: md.ChartData):
        i = self.find_position_chart_data_index(position)
        t = (position, chart_data)
        if i >= 0:
            self.__position_chart_data[i] = t
        else:
            self.__position_chart_data.append(t)

    def clear_position_chart_data(self, position: Position):
        i = self.find_position_chart_data_index(position)
        if i >= 0:
            del self.__position_chart_data[i]

    def get_account_code(self):
        """ Get primary account code
        """
        self.__init_ib_app()
        for acs in self.app.accountSummary():
            if acs.account != 'all':
                return acs.account
        logging.error("IB account selection error")
        raise Exception("IB account selection error")

    def refresh_account(self, account: Account):
        """ Update account data from IB
        """
        self.__init_ib_app()

        account_code = self.get_account_code()
        if account.code != account_code:
            logging.error("Attempt to update wrong account (IB account: " + account_code + ", BT account: " + account.code + ")")
            raise ValueError()

        total_cash_value = 0.
        available_funds = 0.
        net_liquidation = 0.
        day_trades_remaining = 0
        for acs in self.app.accountSummary():
            if acs.account == account.code:
                if acs.tag == 'TotalCashValue':
                    total_cash_value = float(acs.value)
                elif acs.tag == 'AvailableFunds':
                    available_funds = float(acs.value)
                elif acs.tag == 'NetLiquidation':
                    net_liquidation = float(acs.value)
                elif acs.tag == 'DayTradesRemaining':
                    day_trades_remaining = int(acs.value)
        account.update(total_value=net_liquidation, cash_value=total_cash_value, available_funds=available_funds, day_trades_remaining=day_trades_remaining)

        symbols = []
        for ib_position in self.app.positions(account.code):
            symbol = ib_position.contract.symbol
            if ib_position.contract.secType == 'OPT':
                symbol = symbol + ' ' + ib_position.contract.lastTradeDateOrContractMonth + ' ' \
                         + str(ib_position.contract.strike) + ' ' + ib_position.contract.right
            symbols.append(symbol)
            found = False
            for position in account.positions:
                if position.symbol == symbol:  # TODO need more granular matching, e.g. for options
                    position.update(qty=int(ib_position.position), price=ib_position.avgCost, value=ib_position.avgCost * abs(ib_position.position))
                    price_query = self.md.query(md.ContractQuery(ib_position.contract, md.Duration.DAY))
                    self.store_position_chart_data(position, price_query.get_chart_data())
                    current_price = price_query.get_last_value()
                    if current_price:
                        position.update_pnl(current_price)
                    found = True
                    break
            if not found:
                add_pos = Position(account=account, symbol=symbol,
                                   qty=int(ib_position.position), price=ib_position.avgCost, value=ib_position.avgCost * abs(ib_position.position))
                price_query = self.md.query(md.ContractQuery(ib_position.contract, md.Duration.DAY))
                self.store_position_chart_data(add_pos, price_query.get_chart_data())
                current_price = price_query.get_last_value()
                add_pos.update_pnl(current_price)

        for i in range(len(account.positions) - 1, -1, -1):
            position = account.positions[i]
            if position.symbol not in symbols:
                self.clear_position_chart_data(position)
                self.md.remove_query(md.StockQuery(position.symbol, md.Duration.DAY))
                del account.positions[i]

        self.app.reqAllOpenOrders()
        for ib_trade in self.app.trades() + self.app.reqCompletedOrders(False):
            symbol = ib_trade.contract.symbol
            if ib_trade.contract.secType == 'OPT':
                symbol = symbol + ' ' + ib_trade.contract.lastTradeDateOrContractMonth + ' ' \
                         + str(ib_trade.contract.strike) + ' ' + ib_trade.contract.right
            found = False
            for order in account.orders:
                if order.ib_id == ib_trade.order.permId:
                    self.refresh_order(order, ib_trade)
                    found = True
                    break
            if not found:
                add_ord = Order(account=account, symbol=symbol, action=OrderAction[ib_trade.order.action],
                                req_qty=int(ib_trade.order.totalQuantity), lmt_price=ib_trade.order.lmtPrice,
                                ib_id=ib_trade.order.permId)
                self.refresh_order(add_ord, ib_trade)

    def get_spx_value(self) -> float:
        self.__init_ib_app()

        return self.md.query(md.IndexQuery('SPX', md.Duration.DAY)).get_values()[-1]

    def get_spx_chart_data(self) -> md.ChartData:
        self.__init_ib_app()

        #return self.md.query(md.IndexQuery('SPX', md.Duration.DAY)).get_values()

        # use SPY as it has data outside RTH
        spx_data = self.md.query(md.ContractQuery(self.create_contract('SPY'), md.Duration.DAY)).get_chart_data()
        spx_data.values = [t * 10. for t in spx_data.values]
        return spx_data

    def get_vix_value(self) -> float:
        self.__init_ib_app()

        return self.md.query(md.IndexQuery('VIX', md.Duration.DAY)).get_values()[-1]

    def get_vix_chart_data(self) -> md.ChartData:
        self.__init_ib_app()

        return self.md.query(md.IndexQuery('VIX', md.Duration.DAY)).get_chart_data()

    def find_ib_trade(self, order: Order) -> ib.Trade:
        self.__init_ib_app()

        # otherwise the trade will not exist in app.trades() after IB restart
        self.app.reqAllOpenOrders()

        for ib_trade in self.app.trades() + self.app.reqCompletedOrders(False):
            if ib_trade.order.permId == order.ib_id:
                return ib_trade
        logging.warning("Order " + order.code + " (ID " + str(order.ib_id) + ") not found in the IB session")
        return None

    def create_contract(self, symbol: str, exchange: str = 'SMART'):
        self.__init_ib_app()

        if symbol in self.contracts:
            return self.contracts[symbol]

        ib_contract = ib.Stock(symbol, exchange, 'USD')  # ISLAND NYSE
        ib_contract_details = self.app.reqContractDetails(ib_contract)
        if len(ib_contract_details) == 1:
            self.contracts[symbol] = ib_contract
            return ib_contract
        if len(ib_contract_details) > 1:
            # ambiguous symbol, try to refine via ISLAND and NYSE
            if exchange == 'SMART':
                return self.create_contract(symbol, 'ISLAND')
            else:
                logging.error("Couldn't unequivocally resole symbol " + symbol + " via SMART, ISLAND or NYSE")
                return None
        else:  # if not ib_contract_details:
            if exchange == 'ISLAND':
                return self.create_contract(symbol, 'NYSE')
            else:  # exchange == 'SMART' or exchange == 'NYSE' or any other exchange
                logging.error("Contract for symbol " + symbol + " not found")
                return None

    def get_order_fills_from_executions(self, ib_trade: ib.Trade) -> List[ib.Fill]:
        self.__init_ib_app()

        return [t for t in self.app.fills() if t.execution.permId == ib_trade.order.permId]

    def refresh_order(self, order: Order, ib_trade: ib.Trade):
        """ Update order data from IB
        """
        self.__init_ib_app()

        if ib_trade is not None:
            if ib_trade.isDone():
                if ib_trade.orderStatus.status == ib.OrderStatus.Filled:
                    status = OrderStatus.OK
                else:  # if ib_trade.orderStatus.status in [ib.OrderStatus.ApiCancelled, ib.OrderStatus.Cancelled]:
                    status = OrderStatus.CANCD
            elif ib_trade.isActive():
                if ib_trade.orderStatus.status == ib.OrderStatus.Submitted:
                    status = OrderStatus.ACTIVE
                else:
                    logging.info('EE:' + ib_trade.orderStatus.status)
                    status = OrderStatus.SENT
            elif ib_trade.orderStatus.status == ib.OrderStatus.PendingCancel:
                status = OrderStatus.ACTIVE
            else:  # Inactive
                logging.error("Order " + order.code + " IB status (" + ib_trade.orderStatus.status + ") is in inactive state")
                status = OrderStatus.ERROR

            latest_fill_time = None
            qty = 0
            total = 0.
            commission = 0.
            fills = ib_trade.fills
            if not fills:
                fills = self.get_order_fills_from_executions(ib_trade)
            for fill in fills:
                if latest_fill_time is None or latest_fill_time < fill.time:
                    latest_fill_time = fill.time
                price = fill.execution.price or fill.execution.avgPrice
                qty += fill.execution.shares
                total += price * fill.execution.shares
                commission += fill.commissionReport.commission
            avg_price = (total / qty) if qty else 0.
            completed_at = latest_fill_time if status == OrderStatus.OK else None

            order.update(status=status, sent_at=order.sent_at, completed_at=completed_at, qty=qty, avg_price=avg_price, commission=commission,
                         ib_order_type=ib_trade.order.orderType, ib_order_status=ib_trade.orderStatus.status)

            return True

        else:
            return False

    def wait_for_update(self, timeout_sec: float):
        self.__init_ib_app()

        self.app.waitOnUpdate(timeout_sec)

    def sleep(self, secs: float):
        self.__init_ib_app()

        self.app.sleep(secs)
