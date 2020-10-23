import datetime
import logging
from enum import Enum

import ib_insync as ib
from typing import List

from ib_insync import BarData


class Duration(Enum):
    DAY = 1
    MONTH = 2


class ChartData:
    def __init__(self, values: List[float], time_from: datetime, time_to: datetime):
        self.values = values
        self.time_from = time_from
        self.time_to = time_to

    def resample(self, length: int) -> List[float]:
        if length >= len(self.values):
            return self.values

        values = []
        for i in range(length):
            i1 = int((1. * len(self.values) / length) * i)
            i2 = int((1. * len(self.values) / length) * (i + 1))
            if i2 > len(self.values):
                i2 = len(self.values)
            values.append(sum(self.values[i1:i2]) / (i2 - i1))

        return values


class Query:
    def __init__(self, symbol: str, duration: Duration):
        self.symbol = symbol
        self.duration = duration
        self.contract: ib.Contract = None
        self.ib_bars: ib.BarDataList = []

    def __extract_bar_average(self, ib_bar: BarData) -> float:
        if ib_bar.close:
            average = (ib_bar.open + ib_bar.close) / 2.
        else:
            average = ib_bar.open
        return average * (100. if self.contract and self.contract.secType == 'OPT' else 1.)

    def get_values(self) -> List[float]:
        return [self.__extract_bar_average(t) for t in self.ib_bars]

    def get_last_value(self) -> float:
        if self.ib_bars:
            return self.__extract_bar_average(self.ib_bars[-1])
        else:
            return None

    def get_values_start_time(self) -> datetime.datetime:
        if self.ib_bars:
            return datetime.datetime.strptime(str(self.ib_bars[0].date), "%Y-%m-%d %H:%M:%S")
        else:
            return datetime.datetime.now()

    def get_values_end_time(self) -> datetime.datetime:
        if self.ib_bars:
            return datetime.datetime.strptime(str(self.ib_bars[-1].date), "%Y-%m-%d %H:%M:%S")
        else:
            return datetime.datetime.now()

    def get_chart_data(self) -> ChartData:
        return ChartData(self.get_values(), self.get_values_start_time(), self.get_values_end_time())


class StockQuery(Query):
    def __init__(self, symbol: str, duration: Duration):
        super().__init__(symbol, duration)
        self.contract = ib.Stock(symbol, exchange='SMART', currency='USD')


class IndexQuery(Query):
    def __init__(self, symbol: str, duration: Duration):
        super().__init__(symbol, duration)
        self.contract = ib.Index(symbol, exchange='CBOE', currency='USD')


class ContractQuery(Query):
    def __init__(self, contract: ib.Contract, duration: Duration):
        super().__init__(contract.symbol, duration)
        self.contract = contract
        if self.contract.exchange == 'NASDAQ':
            self.contract.exchange = 'SMART'


class Server:
    def __init__(self, app: ib.IB):
        self.app = app
        self.queries: List[Query] = []

    def find_query(self, query: Query) -> Query:
        queries = [t for t in self.queries if t.contract.__repr__() == query.contract.__repr__() and t.duration == query.duration]
        if queries:
            return queries[0]
        else:
            return None

    def add_query(self, query: Query) -> Query:
        existing_query = self.find_query(query)
        if existing_query:
            return existing_query

        bar_size = {Duration.DAY: "1 min", Duration.MONTH: "1 day"}[query.duration]
        duration = {Duration.DAY: "1 D", Duration.MONTH: "1 M"}[query.duration]

        if not query.contract.exchange:
            query.contract.exchange = 'SMART'

        query.ib_bars = self.app.reqHistoricalData(
            query.contract,
            endDateTime="",
            durationStr=duration,
            barSizeSetting=bar_size,
            whatToShow="TRADES",
            useRTH=False,
            formatDate=1,
            keepUpToDate=True)

        self.queries.append(query)

        return query

    def query(self, query: Query):
        return self.add_query(query)

    def remove_query(self, query: Query):
        if not self.find_query(query):
            return
        for i, q in self.queries:
            if q.contract.__repr__() == query.contract.__repr__() and q.duration == query.duration:
                self.app.cancelHistoricalData(q.ib_bars)
                del self.queries[i]
                break

    def remove_all(self):
        for query in self.queries:
            self.app.cancelHistoricalData(query.ib_bars)
        self.queries = []

