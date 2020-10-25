"""
cli interface to the trading ibc
"""

import logging
import signal
import os
from argparse import ArgumentParser
from datetime import (
    datetime, timedelta
)

import colorama

import ibc.argparser_helpers as argh
import ibc.service as bot
from ibc.console import Console


def run_account(args):
    """ Display account status
    """

    Console.print('Retrieving account status...')

    with bot.Service() as svc:
        Console.print('Account: ' + svc.active_account.code)

        acc = svc.refresh_account()
        Console.print_account(acc)
        Console.print_account_positions(acc)


def run_ls(args):
    """ Display accounts and orders
    """

    Console.print('Listing orders...')

    with bot.Service() as svc:
        Console.print('Account: ' + svc.active_account.code)

        svc.refresh_account()
        acc = svc.active_account
        Console.print_account(acc)
        Console.print_account_positions(acc)
        orders = svc.active_account.orders
        for order in orders:
            Console.print_order(order)
        Console.print()


def __run_monitor(svc: bot.Service) -> bool:
    """ Run monitor

        Returns True on normal exit, False on user quit request
    """

    # keyboard controls init
    global g_do_exit
    g_do_exit = False

    def on_press(key):
        global g_do_exit
        if key in ['q', 'Q']:
            g_do_exit = True
            Console.print("Terminating...")
            # Stop listener
            return False
        return True

    if os.name == 'nt':
        from ibc.key_reader import KeyAsyncReader
        key_reader = KeyAsyncReader()
        key_reader.startReading(on_press)

    def signal_handler(signalnum, stackframe):
        global g_do_exit
        Console.print("Received signal " + str(signalnum) + ", terminating...")
        g_do_exit = True

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    if os.name == 'nt':
        signal.signal(signal.SIGBREAK, signal_handler)
    else:
        signal.signal(signal.SIGQUIT, signal_handler)


    Console.print_dashboard(svc)

    while True:

        Console.print('Waiting for updates - Press Q or Ctrl-C to exit...')

        time_last_updated = datetime.now()
        while True:
            svc.broker.wait_for_update(2.)
            now = datetime.now()
            # prevent very frequent updates
            if now - time_last_updated > timedelta(seconds=1):
                break

        svc.refresh_account()

        Console.print_dashboard(svc, delete_previous_lines=True)

        if g_do_exit:
            break

    svc.refresh_account()

    Console.print_dashboard(svc, delete_previous_lines=True)
    Console.print()
    Console.print()

    return g_do_exit


def run_monitor(args):
    """ Run monitor while there are active trades or continuously
    """

    Console.print('Starting monitor...')

    with bot.Service() as svc:
        Console.print('Account: ' + svc.active_account.code)

        __run_monitor(svc)


def main():
    argparser = ArgumentParser(add_help=False)

    argparser.add_argument('--help', action=argh.EmHelpAction, help='Display help')
    argparser.add_argument("-v", "--verbose", dest="verbose", action="store_true", help="Verbose mode")

    ap_sp = argparser.add_subparsers(help='sub-command help', required=True)

    sp_train = ap_sp.add_parser('account', help='Get account status')
    sp_train.set_defaults(func=run_account)

    sp_ls = ap_sp.add_parser('ls', help='List trades/orders')
    sp_ls.set_defaults(func=run_ls)

    sp_monitor = ap_sp.add_parser('monitor', help='Monitor active trades')
    sp_monitor.set_defaults(func=run_monitor)

    args = argparser.parse_args()

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.ERROR)

    colorama.init()

    args.func(args)


if __name__ == "__main__":
    main()
