A *very* basic cli for Interactive Brokers

Uses IBKR API to display in command line:
* Account and indicators
* Orders

Usage:
* `pip install -r requirements.txt`
* copy `ibc.ini.dist` to `ibc.ini` and configure IBKR API port and client Id
* Note that client ID has to match Master Client ID in order for cli to see orders from other API clients and GUI 
* `python ibc.py account` to display account 
* `python ibc.py ls` to display orders
* `python ibc.py monitor` to display dashboard with account details and orders and continuously update it

Screenshots:
![Monitor](https://raw.githubusercontent.com/andrey-zotov/ib_console/main/ib_console.png "Monitor")

Thanks:
* erdewit for [ib_insync](https://github.com/erdewit/ib_insync)
* kroitor for [asciichart](https://github.com/kroitor/asciichart)
