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
TARGET_VALUE = 1000000
TARGET_PREVIOUS_VALUE = 800000
START_DATE = 1451595600

# Global
all_stats = []


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
            "max_win": 0,
            "loss": 0,
            "max_loss": 0,
            "total": 0
        }

    win_rate = 0
    winning_trade = 0
    total = 0
    df = pd.DataFrame(txns)
    max_loss = df['pnl'].min() < 0 and df['pnl'].min() or 0
    max_win = df['pnl'].max() > 0 and df['pnl'].max() or 0
    has_open_position = False
    valid_txns = len(txns)

    for txn in txns:
        try:
            total += txn['pnl']
            if txn['pnl'] > 0:
                winning_trade += 1
        except:
            has_open_position = True
            info_logger('Open position')

    valid_txns = has_open_position and (
        valid_txns - 1) or valid_txns

    if winning_trade is not 0:
        win_rate = round(winning_trade/valid_txns * 100, 2)

    return {
        "code": code,
        "win_rate": win_rate,
        "wins": winning_trade,
        "max_win": max_win,
        "loss": valid_txns - winning_trade,
        "max_loss": max_loss,
        "total": round(total, 2)}


def candle_above_indicator(stock, indicator):
    return is_green_candle(stock) and stock['open'] > indicator


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
    print('Win rate: {0}% \nWins: {1}\nMax Win: {2}%\nLoss: {3}\nMax Loss: {4}%\nTotal: {5}%\n'
          .format(
              stats['win_rate'],
              stats['wins'],
              stats['max_win'],
              stats['loss'],
              stats['max_loss'],
              stats['total']))


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


def get_stats(code, txn):
    all_stats.append(calculate_win_rate(code, txn))


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
    config_filename = ''
    txns = []
    filename = ''
    setup = ''
    stocks = []

    strat = input(
        'Which strategy would you like to test?\n[1 - MAMA]\n[2 - DOUBLE CROSS]: ')

    code = input('Enter stock to test: ')

    if code != '':
        code = code.upper()
        stocks = code == 'ALL' and codes or [code]
        info_logger('Starting DOUBLE CROSS test')

    save = save_file()

    if save:
        filename = get_filename()

    if strat == '1':
        config_filename = 'mama.config.json'
    elif strat == '2':
        config_filename = 'double_cross.config.json'
    else:
        print('No strategy like that yet')

    with open('{}'.format(config_filename)) as file:
        setup = json.loads(file.read())

    txns = backtest(setup, stocks)

    if len(txns) != 0:
        stats = calculate_win_rate(code != 'ALL' and code or 'ALL', txns)

        txnsdf = pd.DataFrame(txns)
        statsdf = pd.DataFrame(all_stats)

        txnsdf['pnl'] = txnsdf['pnl'].astype(str) + '%'
        txnsdf.style.format({'pnl': "{0:+g}"})

        statsdf['win_rate'] = statsdf['win_rate'].astype(str) + '%'
        statsdf['max_win'] = statsdf['max_win'].astype(str) + '%'
        statsdf['max_loss'] = statsdf['max_loss'].astype(str) + '%'
        statsdf['total'] = statsdf['total'].astype(str) + '%'

        if save:
            with pd.ExcelWriter('{0}.xlsx'.format(filename)) as writer:  # pylint: disable=abstract-class-instantiated
                statsdf.to_excel(writer, sheet_name='Summary')
                txnsdf.to_excel(writer, sheet_name='Details')

        pd.set_option('display.max_rows', 1000)

        print(txnsdf)
        display_stats('DOUBLE CROSS', stats)
        print(statsdf)

        show_parameters('MAMA', code, save, filename)


def backtest(setup, stocks):
    buy = []
    risk = []
    sell = []
    txns = []

    try:
        buy = setup['buy']
        sell = setup['sell']
        risk = setup['risk'] is not None and setup['risk'] or []
    except:
        error_logger('Error in configuration file')

    for stock_code in stocks:
        info_logger('Starting test of {}'.format(stock_code))

        txn = perform_backtest(stock_code, buy, sell, risk)
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


def perform_backtest(code, buy_conditions, sell_conditions, risk_conditions):
    stocks = fetch_stocks(code)
    buy = True
    i = 0

    prev_macd_above_signal = False
    txns = []
    # Loop
    for stock in stocks:
        action = buy and 'BUY' or 'SELL'

        if (stock['alma'] is not None
            and stock['macd'] is not None
            and stock['ma20'] is not None
                and stock['volume20'] is not None):

            if stock['timestamp'] >= START_DATE:

                # Variables for eval
                # pylint: disable=unused-variable
                alma = stock['alma']
                close = stock['close']
                ma20 = stock['ma20']
                macd = stock['macd']
                macds = stock['macds']
                prev_alma = stocks[i-1]['alma']
                prev_close = stocks[i-1]['close']
                prev_ma20 = stocks[i-1]['ma20']
                prev_values = get_previous_values(stocks, i, 5)
                target_prev_values = TARGET_PREVIOUS_VALUE
                target_value = TARGET_VALUE
                value = stock['value']
                volume = stock['volume']
                volume20 = stock['volume20']

                # BUYING STOCK
                if buy:
                    valid = False
                    for condition in buy_conditions:
                        if not prev_macd_above_signal:
                            valid = True
                            valid = eval(condition)
                            if not valid:
                                break

                    if valid:
                        for condition in risk_conditions:
                            valid = eval(condition)
                            if not valid:
                                break

                        if valid:
                            txn = trade(stock, action)
                            txns.append(txn)
                            buy = not buy
                else:
                    valid = False
                    for condition in sell_conditions:
                        valid = True
                        valid = eval(condition)
                        if not valid:
                            break

                    if valid:
                        txn = trade(stock, action)
                        txns[len(txns)-1]['sell_date'] = txn['sell_date']
                        txns[len(txns)-1]['sell_price'] = txn['sell_price']
                        txns[len(txns)-1]['pnl'] = compute_pnl(txn, txns)
                        buy = not buy

        prev_macd_above_signal = is_above(stock['macd'], stock['macds'])
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


def trade(stock, action):
    txn = {}

    if action == 'BUY':
        txn = {"code": stock['code'], "buy_date": convert_timestamp(stock['timestamp']),
               "buy_price": stock['close']}
    else:
        txn = {"code": stock['code'], "sell_date": convert_timestamp(stock['timestamp']),
               "sell_price": stock['close']}

    return txn


main()
