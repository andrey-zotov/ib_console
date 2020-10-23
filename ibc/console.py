"""
IBC cli console operations
"""

import logging
import os
import sys
from datetime import datetime

import colorama
from typing import List, Tuple

from colorama import AnsiToWin32
import ibc.asciichart as asciichart

from ibc.data_models import Account, OrderStatus, Order
from ibc.market_data import ChartData
import ibc.service as bot


CONSOLE_DEFAULT_LOGGING_LEVEL = logging.WARNING
CONSOLE_VERBOSE_LOGGING_LEVEL = logging.INFO  # DEBUG
LOGFILE_LOGGING_LEVEL = logging.INFO


class Console:

    is_verbose_logging = True
    console_line_counter = 0

    is_spooling = False
    spool: List[Tuple[str, bool]] = []

    @staticmethod
    def fmt_float(val: float, just: int = 10) -> str:
        if val is not None:
            return str(round(val, 2)).rjust(just, ' ')
        else:
            return "-".ljust(just, ' ')

    @staticmethod
    def fmt_pct_change(val: float, just: int = 10) -> str:
        if val:
            return (("+" if val > 0. else "") + Console.fmt_float(val, 0) + "%").rjust(just, ' ')
        else:
            return "-".ljust(just, ' ')

    @staticmethod
    def logging_filter(record: logging.LogRecord) -> bool:
        console_visible_level = CONSOLE_VERBOSE_LOGGING_LEVEL if Console.is_verbose_logging else CONSOLE_DEFAULT_LOGGING_LEVEL
        if record.levelno >= console_visible_level:
            lines = int(len(record.getMessage()) / os.get_terminal_size().columns) + 1
            Console.console_line_counter += lines
        return True

    @staticmethod
    def filter_print_msg(s: str) -> str:
        """ Filter out ANSI terminal sequences (colorama's AnsiToWin32 used as example)
        """
        if not s:
            return s

        cursor = 0
        s_flt = ""
        for match in AnsiToWin32.ANSI_CSI_RE.finditer(s):
            start, end = match.span()
            if cursor < start:
                s_flt += s[cursor:start]
            cursor = end
        if cursor < len(s):
            s_flt += s[cursor:len(s)]

        return s_flt

    @staticmethod
    def print(s: str = ""):
        """ Print both to console and to log file (optionally)
        """
        s_flt = Console.filter_print_msg(s)
        terminal_width = os.get_terminal_size().columns - 30
        filler = ' ' * (terminal_width - len(s_flt))
        print_msg = s + filler
        print(print_msg)
        #lines = int(len(print_msg) / os.get_terminal_size().columns) + 1
        Console.console_line_counter += 1

    @staticmethod
    def print_account_positions(acc: Account):
        if acc.positions:
            Console.print("  Positions: \t\t                           Total cost: " + Console.fmt_float(acc.positions_value)
                          + "\t                     Total profit: " + colorama.Style.BRIGHT
                          + (colorama.Fore.GREEN if acc.positions_profit > 0. else colorama.Fore.RED) + Console.fmt_float(acc.positions_profit)
                          + " (" + Console.fmt_pct_change(100. * acc.positions_profit_margin, 0) + ")" + colorama.Style.RESET_ALL)
            for p in sorted(acc.positions, key=lambda t: (-t.value, t.symbol)):
                Console.print("  " + colorama.Style.BRIGHT + p.symbol.ljust(22) + colorama.Style.RESET_ALL +
                              "\t Qty: " + Console.fmt_float(p.qty) +
                              "\t Cost: " + Console.fmt_float(p.value) +
                              "\t Price: " + Console.fmt_float(p.price) +
                              "\t   Profit: " + (colorama.Fore.GREEN if p.profit >= 0. else colorama.Fore.RED) + Console.fmt_float(p.profit) +
                              " (" + Console.fmt_pct_change(100. * p.profit_margin, 0) + ")" + colorama.Style.RESET_ALL)
        else:
            Console.print("  No positions open")
        Console.print()

    @staticmethod
    def print_account(acc: Account):
        Console.print(colorama.Style.BRIGHT + acc.code + colorama.Style.RESET_ALL)
        Console.print("  Value:     " + colorama.Style.BRIGHT + Console.fmt_float(acc.total_value) + colorama.Style.RESET_ALL)
        Console.print("  Available: " + colorama.Style.BRIGHT + Console.fmt_float(acc.available_funds) + colorama.Style.RESET_ALL)
        Console.print("  Cash:      " + colorama.Style.BRIGHT + Console.fmt_float(acc.cash_value) + colorama.Style.RESET_ALL)
        Console.print("  Day trades:" + str(acc.day_trades_remaining))
        Console.print()

    @staticmethod
    def ljust_screen_block(block: List[str], width: int) -> List[str]:
        res = []
        for s in block:
            s_flt = Console.filter_print_msg(s)
            if len(s_flt) > width:
                res.append(s_flt)
            else:
                res.append(s + (' ' * (width - len(s_flt))))
        return res

    @staticmethod
    def merge_screen_blocks(*args) -> List[str]:
        max_lines = max([len(t) for t in args])
        line_len_by_block = [len(t[0]) for t in args]
        res = ["" for t in range(max_lines)]
        for i in range(max_lines):
            for b in range(len(args)):
                if i < len(args[b]):
                    res[i] += args[b][i]
                else:
                    res[i] += ''.ljust(line_len_by_block[b], ' ')
        return res

    @staticmethod
    def print_block(block: List[str]):
        for s in block:
            Console.print(s)

    @staticmethod
    def print_account_dashboard(svc: bot.Service, acc: Account):
        Console.print(colorama.Style.BRIGHT + acc.code + colorama.Style.RESET_ALL)

        block1 = Console.ljust_screen_block(["  Value:      " + colorama.Style.BRIGHT + Console.fmt_float(acc.total_value) + colorama.Style.RESET_ALL,
                                             "  Available:  " + colorama.Style.BRIGHT + Console.fmt_float(acc.available_funds) + colorama.Style.RESET_ALL,
                                             "  Cash:       " + colorama.Style.BRIGHT + Console.fmt_float(acc.cash_value) + colorama.Style.RESET_ALL,
                                             "  Day trades: " + colorama.Style.BRIGHT + str(acc.day_trades_remaining) + colorama.Style.RESET_ALL
                                             ], 50)

        spx_series_data = svc.broker.get_spx_chart_data()
        if spx_series_data:
            spx_open_price = spx_series_data.values[0]
            spx_price = spx_series_data.values[-1]
            spx_day_change_pct = (spx_price - spx_open_price) / spx_open_price * 100.
            spx_txt = Console.fmt_float(spx_price, 0) + " (" + Console.fmt_pct_change(spx_day_change_pct, 0) + ")"
        else:
            spx_day_change_pct = 0.
            spx_txt = "-"

        vix_series_data = svc.broker.get_vix_chart_data()
        if vix_series_data:
            vix_open = vix_series_data.values[0]
            vix = vix_series_data.values[-1]
            if vix_open:
                vix_day_change_pct = (vix - vix_open) / vix_open * 100.
            else:
                vix_day_change_pct = 0.
            vix_txt = Console.fmt_float(vix, 0) + " (" + Console.fmt_pct_change(vix_day_change_pct, 0) + ")"
        else:
            vix_day_change_pct = 0.
            vix_txt = "-"

        block2 = Console.ljust_screen_block(["  SPX:     " + (colorama.Fore.GREEN if spx_day_change_pct >= 0. else colorama.Fore.RED) + spx_txt + colorama.Style.RESET_ALL,
                                             "  VIX:     " + (colorama.Fore.GREEN if vix_day_change_pct >= 0. else colorama.Fore.RED) + vix_txt + colorama.Style.RESET_ALL
                                             ], 30)

        block = Console.merge_screen_blocks(block1, block2)
        Console.print_block(block)

        Console.print()

    @staticmethod
    def print_order(order: Order):
        order_status_cr_map = {OrderStatus.NEW: "",
                               OrderStatus.SENT: colorama.Fore.CYAN,
                               OrderStatus.ACTIVE: colorama.Fore.LIGHTGREEN_EX,
                               OrderStatus.ERROR: colorama.Fore.RED,
                               OrderStatus.OK: colorama.Fore.GREEN,
                               OrderStatus.CANCD: colorama.Style.DIM}
        Console.print("    " + order.symbol.ljust(7, ' ') +
                      order_status_cr_map[order.status] + order.status.name.ljust(7, ' ') + colorama.Style.RESET_ALL +
                      order.action.name.ljust(6, ' ') +
                      " Qty: " + (Console.fmt_float(order.qty, 0) + "/" + Console.fmt_float(order.req_qty, 0)).rjust(13, ' ') +
                      "  Price: " + (Console.fmt_float(order.avg_price, 0) + '/' + Console.fmt_float(order.lmt_price, 0)).rjust(17, ' ') +
                      "  Comm: " + Console.fmt_float(order.commission, 5)
                      )

    @staticmethod
    def create_chart_block(chart_data: ChartData, series_len: int, chart_height: int, add_time: bool = False) -> List[str]:
        block = []
        series = chart_data.resample(series_len)
        if series:
            plot_cfg = {
                "height": chart_height,
                "colors": [
                    asciichart.lightblue
                ]
            }
            if max(series) == min(series):
                plot_cfg["max"] = series[0] * 1.1
                plot_cfg["min"] = series[0] * 0.9
            plot_str = asciichart.plot(series, plot_cfg)
            block.extend(plot_str.split('\n'))
        if add_time:
            block.append(' ' + chart_data.time_from.strftime("%H:%M") + " - " + chart_data.time_to.strftime("%H:%M"))
        return block

    @staticmethod
    def print_charts(svc: bot.Service):
        terminal_width = os.get_terminal_size().columns
        block_width = int(terminal_width / (1 + len(svc.active_account.positions)) - 1)
        chart_width = block_width - 12
        if chart_width < 10:
            chart_width = 10

        spx_series_data = svc.broker.get_spx_chart_data()
        spx_block = Console.create_chart_block(spx_series_data, chart_width, 3, add_time=True)
        spx_block.insert(0, "SPX:")
        blocks = [spx_block]

        for position in sorted(svc.active_account.positions, key=lambda t: (-t.value, t.symbol)):
            chart_data = svc.broker.get_position_chart_data(position)
            if chart_data and chart_data.values:
                pos_block = Console.create_chart_block(chart_data, chart_width, 3, add_time=True)
                pos_block.insert(0, position.symbol + ":")
                blocks.append(pos_block)

        if blocks:
            block = Console.merge_screen_blocks(*[Console.ljust_screen_block(t, block_width) for t in blocks])
            Console.print_block(block)
            Console.print()

    @staticmethod
    def print_orders(orders: List[Order]):
        if orders:
            Console.print("Orders:")
            for order in orders:
                Console.print_order(order)
            Console.print()

    @staticmethod
    def print_dashboard(svc: bot.Service, delete_previous_lines: bool = False):
        account = svc.active_account
        orders = svc.active_orders

        if delete_previous_lines and Console.console_line_counter:
            sys.stdout.write('\x1b[' + str(Console.console_line_counter) + 'A')
            sys.stdout.write('\x1b[' + str(Console.console_line_counter + 1) + 'K')

        Console.console_line_counter = 0

        Console.print_account_dashboard(svc, account)
        Console.print_account_positions(account)
        Console.print_charts(svc)

        Console.print_orders(orders)

        Console.print("Updated at " + str(datetime.now().strftime("%H:%M")))
