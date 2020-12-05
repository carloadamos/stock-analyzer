# Imports
import sys
from stock_list import codes
from datetime import datetime
import json
import pymongo
import pandas as pd
from logger import error_logger, info_logger, warning_logger

# database Connection
# connection_url = 'mongodb+srv://admin:admin@cluster0.70gug.mongodb.net/exercise-tracker?retryWrites=true&w=majority'
connection_url = 'mongodb://localhost:27017/'
client = pymongo.MongoClient(connection_url)
database = client.get_database('stock-analyzer')
stocks_table = database.stocks

# Constants
COMM_RATE = 1.19
START_DATE = 1451595600

# Global
all_stats = []
capital = 100000


def first_breakout(stocks, cur_pos):
    i = 0
    entry_point = stocks[cur_pos]['close']
    risk = compute_profit(entry_point, stocks[cur_pos]['alma'])

    while True:
        if i is not 0 and cur_pos is not 0:
            prev_candle = stocks[cur_pos-i]
            if close_below_alma(prev_candle):
                break
            if is_above(prev_candle['close'], prev_candle['alma']) and low_below_alma(prev_candle):
                risk = compute_profit(entry_point, prev_candle['alma'])
        i += 1

    return risk


def calculate_win_rate(code, txns):
    if len(txns) == 0:
        return {
            "code": code,
            "win_rate": 0,
            "wins": 0,
            "avg_win": 0,
            "max_win": 0,
            "loss": 0,
            "avg_loss": 0,
            "max_loss": 0,
            "total_trade": 0,
            "total": 0,
            "total_capital": 0
        }

    avg_win = 0
    avg_loss = 0
    df = pd.DataFrame(txns)
    has_open_position = False
    loss = 0
    total = 0
    valid_txns = len(txns)
    win_rate = 0
    wins = 0
    winning_trade = 0

    # For scenario where:
    # there is only one transaction and
    # it is still open
    try:
        max_loss = df['pnl'].min() < 0 and df['pnl'].min() or 0
        max_win = df['pnl'].max() > 0 and df['pnl'].max() or 0
    except:
        max_loss = 0
        max_win = 0

    for txn in txns:
        try:
            pnl = txn['pnl']
            total += pnl
            if pnl > 0:
                winning_trade += 1
                wins += pnl
            else:
                loss += pnl
        except:
            has_open_position = True
            info_logger('Open position')

    valid_txns = has_open_position and (
        valid_txns - 1) or valid_txns

    if winning_trade is not 0:
        win_rate = round(winning_trade/valid_txns * 100, 2)
        avg_win = wins != 0 and round(wins/winning_trade, 2) or 0
        avg_loss = loss != 0 and round(loss/(valid_txns-winning_trade), 2) or 0

    return {
        "code": code,
        "win_rate": win_rate,
        "wins": winning_trade,
        "avg_win": avg_win,
        "max_win": max_win,
        "loss": valid_txns - winning_trade,
        "avg_loss": avg_loss,
        "max_loss": max_loss,
        "total_trade": valid_txns,
        "total": round(total, 2),
        "total_capital": round(capital, 2)}


def candle_above(stock, indicator):
    return stock['open'] > indicator and stock['close'] > indicator


def candle_below(stock, indicator):
    return stock['open'] < indicator and stock['close'] < indicator


def close_below_alma(stock):
    """
    Identify if close price is below ALMA.
    :param stock: Stock object
    :return: boolean
    """
    if stock['alma'] is not None:
        return stock['close'] < stock['alma']


def compute_profit(buy_price, sell_price):
    return (((sell_price - buy_price) / buy_price) * 100)


def compute_pnl(txn, txns):
    return round(compute_profit(txns[-1:][0]['buy_price'], txn['sell_price']) - COMM_RATE, 2)


def convert_timestamp(timestamp):
    return datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d')


def display_stats(strategy, stats):
    print('\n{} strategy'.format(strategy))
    print('Win rate: {}% \nTotal Trade: {} \nWins: {} \nAverage Win: {}%\nMax Win: {}%\nLoss: {} \nAverage Loss: {}%\nMax Loss: {}%\nTotal: {}%\nTotal Capital: {}'
          .format(
              stats['win_rate'],
              stats['total_trade'],
              stats['wins'],
              stats['avg_win'],
              stats['max_win'],
              stats['loss'],
              stats['avg_loss'],
              stats['max_loss'],
              stats['total'],
              stats['total_capital']))


def fetch_all_stocks():
    """
    Fetch all stocks.
    """
    return stocks_table.find()


def fetch_stocks(code):
    """
    Fetch stocks based on stock code.
    """
    return list(stocks_table.find({"code": code}))


def get_filename():
    return input('Enter filename: ')


def get_previous_values(stocks, cur_pos, length):
    prev_values = []

    for i in range(length+1):
        if i is not 0:
            if cur_pos > length+1:
                prev_values.append(stocks[cur_pos-i]['value'])
            else:
                prev_values.append(0)

    return prev_values


def get_stats(code, txns):
    all_stats.append(calculate_win_rate(code, txns))


def is_above(above, below):
    return above > below


def is_below(below, above):
    return below < above


def is_green_candle(stock):
    return stock['close'] > stock['open']


def low_below_alma(stock):
    if stock['alma'] is not None:
        return stock['low'] < stock['alma']


def main():
    configs = ''
    txns = []
    filename = ''
    setup = []
    strat_name = ''
    stocks = []

    strat = input(
        'Which strategy would you like to test?\n[1 - MAMA]\n[2 - DOUBLE CROSS]: ')

    code = input('Enter stock to test: ')

    if code != '':
        code = code.upper()
        stocks = code == 'ALL' and codes or [code]

        save = save_file()

        if save:
            filename = get_filename()

        if strat == '1':
            strat_name = 'MAMA'
            configs = ['mama.config.json']
        elif strat == '2':
            strat_name = 'DOUBLE CROSS'
            configs = ['double_cross.config.json']
        elif strat.upper() == 'ALL':
            strat_name = 'ALL'
            configs = ['mama.config.json', 'double_cross.config.json']
        else:
            print('No strategy like that yet')

        for config in configs:
            with open('{}'.format(config)) as file:
                setup.append(json.loads(file.read()))

        info_logger('Starting {} test'.format(strat_name))
        txns = backtest(setup, stocks)
        info_logger('End {} test'.format(strat_name))

        if code == 'ALL':
            get_stats(code, txns)

        display_report(strat_name, code, txns, save, filename)
        show_parameters('{}'.format(strat_name), code, save, filename)
    else:
        info_logger('Enter stock to test')


def display_report(name, code, txns, save, filename):
    if len(txns) != 0:
        stats = calculate_win_rate(code != 'ALL' and code or 'ALL', txns)
        txnsdf = pd.DataFrame(txns)
        txnsdf.sort_values(['code', 'buy_date'], ascending=True,
                           inplace=True, na_position='last')
        txnsdf['pnl'] = txnsdf['pnl'].astype(str) + '%'
        statsdf = pd.DataFrame(all_stats)
        statsdf['win_rate'] = statsdf['win_rate'].astype(str) + '%'
        statsdf['max_win'] = statsdf['max_win'].astype(str) + '%'
        statsdf['avg_win'] = statsdf['avg_win'].astype(str) + '%'
        statsdf['max_loss'] = statsdf['max_loss'].astype(str) + '%'
        statsdf['avg_loss'] = statsdf['avg_loss'].astype(str) + '%'
        statsdf.sort_values(['total'], ascending=True,
                            inplace=True, na_position='last')
        statsdf['total'] = statsdf['total'].astype(str) + '%'
        pd.set_option('display.max_rows', 10000)

        if save:
            save_report(filename, txnsdf, statsdf)

        info_logger(txnsdf)
        info_logger(statsdf)
        display_stats('{}'.format(name), stats)


def save_report(filename, txns, stats):
    with pd.ExcelWriter('results/{0}.xlsx'.format(filename)) as writer:  # pylint: disable=abstract-class-instantiated
        stats.to_excel(writer, sheet_name='Summary')
        txns.to_excel(writer, sheet_name='Details')


def backtest(setup, stocks):
    buy = []
    risk = []
    sell = []
    stop = 0
    trail_stop = []
    txn = []
    txns = []

    for stock_code in stocks:
        info_logger('Starting test of {}'.format(stock_code))

        for strat in setup:
            try:
                buy = strat['buy']
                sell = strat['sell']
                risk = strat['risk']
                stop = strat['stop']
                trail_stop = strat['trail_stop']
            except:
                error_logger('Error in configuration file')

            txn = process_backtest(stock_code, buy, sell,
                                   risk, stop, trail_stop)
            get_stats(stock_code, txn)
            txns = txns + txn

        info_logger('End of test of {}'.format(stock_code))

    return txns


def valid_previous_values(prev_values, target_prev_value):
    invalid_ctr = 0
    valid = True

    for value in prev_values:
        if not is_above(value, target_prev_value):
            invalid_ctr += 1
        if invalid_ctr > 1:
            valid = False

    return valid


def process_backtest(code, buy_criteria, sell_criteria, risk_criteria, stoploss, trail_stop):
    stock_data = fetch_stocks(code)
    buy = True
    i = 0

    txns = []
    trade_capital = 0
    global capital

    for stock in stock_data:
        action = buy and 'BUY' or 'SELL'
        prev_stock = stock_data[i-1]

        if (prev_stock['alma'] is not None
            and prev_stock['macd'] is not None
            and prev_stock['ma20'] is not None
                and prev_stock['volume20'] is not None):

            if stock['timestamp'] >= START_DATE:

                # Variables for eval
                # pylint: disable=unused-variable
                alma = stock['alma']
                close = stock['close']
                ma20 = stock['ma20']
                macd = stock['macd']
                macds = stock['macds']
                prev_alma = prev_stock['alma']
                prev_close = prev_stock['close']
                prev_macd = prev_stock['macd']
                prev_macds = prev_stock['macds']
                prev_ma20 = prev_stock['ma20']
                prev_values = get_previous_values(stock_data, i, 5)
                value = stock['value']
                volume = stock['volume']
                volume20 = stock['volume20']

                # BUYING STOCK
                if buy:
                    valid = False
                    for condition in buy_criteria:
                        valid = True
                        valid = eval(condition)
                        if not valid:
                            break

                    if valid:
                        for condition in risk_criteria:
                            valid = eval(condition)
                            if not valid:
                                break

                        if valid:
                            trade_capital = capital * 0.08
                            txn = trade(stock, action, trade_capital)
                            txn['candle'] = is_green_candle(
                                stock) and 'Green' or 'Red'
                            txn['above_ma20'] = is_above(
                                close, ma20) and 'Yes' or 'No'
                            txns.append(txn)
                            capital += -(trade_capital)
                            buy = not buy
                else:
                    exit_criteria = ''
                    paperloss = compute_profit(
                        txns[len(txns)-1]['buy_price'], close)
                    stop = compute_profit(prev_close, close)
                    valid = False

                    if int(stoploss) != 0 and int(stoploss) >= paperloss:
                        buy_price = txns[len(txns)-1]['buy_price']
                        cut_price = round(buy_price -
                                          (buy_price * abs(int(stoploss))/100), 2)

                        if cut_price >= stock['low'] and cut_price <= stock['high']:
                            exit_criteria = 'STOPLOSS'
                            stock['close'] = cut_price
                            valid = True

                    elif len(trail_stop) != 0:
                        for condition in trail_stop:
                            exit_criteria = 'TRAIL STOP'
                            valid = True
                            valid = eval(condition)
                            if not valid:
                                break

                    if not valid:
                        for condition in sell_criteria:
                            exit_criteria = 'NORMAL EXIT'
                            valid = True
                            valid = eval(condition)
                            if not valid:
                                break

                    if valid:
                        txn = trade(stock, action)
                        pnl = compute_pnl(txn, txns)
                        amount = round(trade_capital * (pnl/100), 2)
                        txns[len(txns)-1]['sell_date'] = txn['sell_date']
                        txns[len(txns)-1]['sell_price'] = txn['sell_price']
                        txns[len(txns)-1]['pnl'] = pnl
                        txns[len(txns)-1]['exit'] = exit_criteria
                        txns[len(txns)-1]['amount'] = amount
                        capital += trade_capital + amount
                        buy = not buy

        i += 1

    return txns


def previous_breakout_candle(stock, indicator):
    return stock['open'] <= indicator and stock['close'] >= indicator


def save_file():
    save = input('Save result to excel file? [Y/N]: ')
    save = save.upper()
    return save == 'Y' and True or False


def show_parameters(strategy, stock, save_file, filename=''):
    print('\nPARAMETERS USED IN THIS TEST \nStrategy: {0} \nStock: {1} \nSave File: {2} \nFilename: {3}'
          .format(
              strategy, stock, save_file, filename
          ))


def stock_to_test():
    code = input('Enter stock to test: ')
    return code != '' and code.upper() or ''


def trade(stock, action, trade_capital=0):
    txn = {}

    if action == 'BUY':
        txn = {"code": stock['code'], "buy_date": convert_timestamp(stock['timestamp']),
               "buy_price": stock['close'], "bought_shares": int(trade_capital/stock['close'])}
    else:
        txn = {"code": stock['code'], "sell_date": convert_timestamp(stock['timestamp']),
               "sell_price": stock['close']}

    return txn


main()
