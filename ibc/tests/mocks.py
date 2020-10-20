import datetime
from typing import List

from ib_insync import Contract, ContractDetails, Order, OrderStatus


class IBContractMock:
    def __init__(self, symbol):
        self.symbol = symbol
        self.secType = 'STK'
        self.exchange = 'ISLAND'


class IBPositionMock:
    def __init__(self, symbol, avgCost, position):
        self.contract = IBContractMock(symbol)
        self.avgCost = avgCost
        self.position = position


class IBTradeFillMock:
    def __init__(self, shares, price, avgPrice, commission):
        class ExecutionMock:
            def __init__(self, shares, price, avgPrice, commission):
                self.shares = shares
                self.price = price
                self.avgPrice = avgPrice
                self.commission = commission

        class CommissionReportMock:
            def __init__(self, commission):
                self.commission = commission

        self.time = datetime.datetime.now()
        self.execution = ExecutionMock(shares, price, avgPrice, commission)
        self.commissionReport = CommissionReportMock(commission)


class IBTradeMock:
    def __init__(self, contract, order):
        class OrderStatusMock:
            def __init__(self, orderStatus):
                self.status = orderStatus

        self.contract = contract
        self.order = order
        self.orderStatus = OrderStatusMock(OrderStatus.PendingSubmit)
        self.fills = []

    def isDone(self):
        return self.orderStatus.status in OrderStatus.DoneStates

    def isActive(self):
        return self.orderStatus.status in OrderStatus.ActiveStates


class IBAppMock:

    order_id = 1

    def __init__(self, account_code):
        self.is_mock = True
        self.__positions: List[IBPositionMock] = []
        self.account_code = account_code
        self.mock_price = 20.
        self.acc_NetLiquidation = "3000.1"
        self.acc_TotalCashValue = "1000.1"
        self.acc_AvailableFunds = "2000.1"
        self.acc_DayTradesRemaining = "2"
        self.mock_trades: List[IBTradeMock] = []

    def disconnect(self):
        pass

    def accountSummary(self):

        class accSummaryRec:
            def __init__(self, account, tag, value):
                self.account = account
                self.tag = tag
                self.value = value

        return [
            accSummaryRec(self.account_code, "NetLiquidation", self.acc_NetLiquidation),
            accSummaryRec(self.account_code, "TotalCashValue", self.acc_TotalCashValue),
            accSummaryRec(self.account_code, "AvailableFunds", self.acc_AvailableFunds),
            accSummaryRec(self.account_code, "DayTradesRemaining", self.acc_DayTradesRemaining),
            accSummaryRec("all", "Dummy1", "1"),
            accSummaryRec("all", "Dummy2", "1")
        ]

    def add_position(self, position):
        self.__positions.append(position)

    def positions(self, account):
        return self.__positions

    def reqHistoricalData(self, contract, endDateTime, durationStr, barSizeSetting, whatToShow, useRTH, formatDate, keepUpToDate):
        class Price:
            def __init__(self, _open):
                self.open = _open
                self.average = _open
                self.date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return [Price(self.mock_price)]

    def reqContractDetails(self, contract: Contract) -> List[ContractDetails]:
        if contract.symbol == 'MSFT' and contract.exchange == 'SMART':
            return [ContractDetails(contract=contract, validExchanges='NYSE'), ContractDetails(contract=contract, validExchanges='DUMMY')]
        if contract.symbol == 'MSFT' and contract.exchange == 'ISLAND':
            return []
        if contract.symbol == 'DUMMY':
            return []
        return [ContractDetails(contract=contract, validExchanges='NYSE')]

    def placeOrder(self, contract: Contract, order: Order):
        trade = IBTradeMock(contract, order)
        order.orderId = self.order_id
        self.order_id += 1
        self.mock_trades.append(trade)
        return trade

    def trades(self):
        return self.mock_trades

    def orders(self):
        return [t.order for t in self.trades()]

    def reqCompletedOrders(self, dummy):
        return []

    def cancelOrder(self, order: Order):
        trade = [t for t in self.trades() if t.order.orderId == order.orderId][0]
        trade.orderStatus.status = OrderStatus.Cancelled
        return trade

    def waitOnUpdate(self, timeout: float = 0):
        pass

    def reqAllOpenOrders(self):
        return self.mock_trades