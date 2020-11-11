# Imports
import sys
import pymongo
import pandas as pd
import logging
from datetime import datetime
from stock_list import codes

# database Connection
connection_url = 'mongodb+srv://admin:admin@cluster0.70gug.mongodb.net/exercise-tracker?retryWrites=true&w=majority'
client = pymongo.MongoClient(connection_url)
database = client.get_database('stock-analyzer')
stocks_table = database.stocks

# Logger
logging.basicConfig(filename='executions.log', level=logging.DEBUG,
                    format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

# Constants
COMM_RATE = 1.19
RISK = 4
TARGET_VALUE = 1000000
TARGET_PREVIOUS_VALUE = 800000
START_DATE = 1451595600

# Global
all_stats = []


def calculate_risk(stocks, cur_pos):
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
            logging.info('Open position')
            print('Open position')

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


def check_risk():
    check_risk = input(
        'Include risk checking? Current value is: {0} [Y/N] '.format(RISK))
    check_risk = check_risk.upper()
    check_risk = check_risk == 'Y' and True or False

    return check_risk


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


def double_cross():
    all_txns = []

    code = input('Enter stock to test: ')
    include_risk = check_risk()
    save = save_file()
    name = ''

    if save:
        name = file_name()

    if code != '':
        code = code.upper()
        stocks = code == 'ALL' and codes or [code]
        all_txns = double_cross_process_backtest(stocks, include_risk)

    if len(all_txns) != 0:
        stats = calculate_win_rate(code != 'ALL' and code or 'ALL', all_txns)

        txnsdf = pd.DataFrame(all_txns)
        statsdf = pd.DataFrame(all_stats)

        txnsdf['risk'] = txnsdf['risk'].astype(str) + '%'
        txnsdf['pnl'] = txnsdf['pnl'].astype(str) + '%'
        txnsdf.style.format({'pnl': "{0:+g}"})

        statsdf['win_rate'] = statsdf['win_rate'].astype(str) + '%'
        statsdf['max_win'] = statsdf['max_win'].astype(str) + '%'
        statsdf['max_loss'] = statsdf['max_loss'].astype(str) + '%'
        statsdf['total'] = statsdf['total'].astype(str) + '%'

        if save:
            with pd.ExcelWriter('{0}.xlsx'.format(name)) as writer:  # pylint: disable=abstract-class-instantiated
                statsdf.to_excel(writer, sheet_name='Summary')
                txnsdf.to_excel(writer, sheet_name='Details')

        pd.set_option('display.max_rows', 1000)

        print(txnsdf)
        display_stats('DOUBLE CROSS', stats)
        print(statsdf)
        show_parameters('MAMA', code, include_risk, save, name)


def double_cross_backtest(code, check_risk):
    stocks = fetch_stocks(code)
    buy = True
    i = 0

    prev_alma_above_ma = False
    txns = []
    # Loop
    for stock in stocks:
        action = buy and 'BUY' or 'SELL'

        if (stock['alma'] is not None
            and stock['macd'] is not None
                and stock['ma20'] is not None):
            if stock['timestamp'] >= START_DATE:
                if buy:
                    if not prev_alma_above_ma and is_above(stock['macd'], stock['macds']):
                        if (candle_above_indicator(stock, stock['alma'])
                                and candle_above_indicator(stock, stock['ma20'])
                                and is_above(stock['alma'], stock['ma20'])):
                            risk = round(calculate_risk(stocks, i), 2)
                            if check_risk:
                                if risk >= -RISK:
                                    txn = trade(stock, action)
                                    txn['risk'] = risk
                                    txns.append(txn)
                                    buy = not buy
                            else:
                                txn = trade(stock, action)
                                txns.append(txn)
                                txn['risk'] = risk
                                buy = not buy
                else:
                    if close_below_alma(stock) and close_below_alma(stocks[i-1]):
                        txn = trade(stock, action)
                        txns[len(txns)-1]['sell_date'] = txn['sell_date']
                        txns[len(txns)-1]['sell_price'] = txn['sell_price']
                        txns[len(txns)-1]['pnl'] = compute_pnl(txn, txns)
                        buy = not buy

        if stock['alma'] is not None and stock['ma20'] is not None:
            prev_alma_above_ma = is_above(stock['alma'], stock['ma20'])

        i += 1

    return txns


def double_cross_process_backtest(codes_to_test, include_risk):
    logging.info('Starting DOUBLE CROSS test')
    print('Starting DOUBLE CROSS test\n')

    txns = []
    for code in codes_to_test:
        logging.info('Starting test of {}'.format(code))
        print('Starting test of {}'.format(code))

        txn = double_cross_backtest(code, check_risk)
        get_stats(code, txn)
        txns = txns + txn

        logging.info('End of test of {}'.format(code))
        print('End of test of {}'.format(code))

    logging.info('End of DOUBLE CROSS test')
    print('\nEnd of DOUBLE CROSS test')

    return txns


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


def file_name():
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


def is_green_candle(stock):
    return stock['close'] > stock['open']


def low_below_alma(stock):
    if stock['alma'] is not None:
        return stock['low'] < stock['alma']


def main():
    strat = input(
        'Which strategy would you like to test?\n[1 - MAMA]\n[2 - DOUBLE CROSS]: ')

    if strat == '1':
        mama()
    elif strat == '2':
        double_cross()
    else:
        print('No other strategy yet')


def mama():
    all_txns = []

    code = input('Enter stock to test: ')
    include_risk = check_risk()
    save = save_file()
    name = ''

    if save:
        name = file_name()

    if code != '':
        code = code.upper()
        stocks = code == 'ALL' and codes or [code]

        all_txns = mama_process_backtest(stocks, include_risk)

    if len(all_txns) != 0:
        stats = calculate_win_rate(code != 'ALL' and code or 'ALL', all_txns)

        txnsdf = pd.DataFrame(all_txns)
        statsdf = pd.DataFrame(all_stats)

        txnsdf['risk'] = txnsdf['risk'].astype(str) + '%'
        txnsdf['pnl'] = txnsdf['pnl'].astype(str) + '%'
        txnsdf.style.format({'pnl': "{0:+g}"})

        statsdf['win_rate'] = statsdf['win_rate'].astype(str) + '%'
        statsdf['max_win'] = statsdf['max_win'].astype(str) + '%'
        statsdf['max_loss'] = statsdf['max_loss'].astype(str) + '%'
        statsdf['total'] = statsdf['total'].astype(str) + '%'

        if save:
            with pd.ExcelWriter('{0}.xlsx'.format(name)) as writer:  # pylint: disable=abstract-class-instantiated
                statsdf.to_excel(writer, sheet_name='Summary')
                txnsdf.to_excel(writer, sheet_name='Details')

        pd.set_option('display.max_rows', 1000)

        print(txnsdf)
        display_stats('MAMA', stats)
        print(statsdf)
        show_parameters('MAMA', code, include_risk, save, name)


def mama_backtest(code, check_risk=True):
    stocks = fetch_stocks(code)
    buy = True
    i = 0

    prev_macd_above_signal = False
    txns = []
    # Loop
    for stock in stocks:
        action = buy and 'BUY' or 'SELL'

        if stock['timestamp'] >= START_DATE:
            if buy:
                if not prev_macd_above_signal and is_above(stock['macd'], stock['macds']):
                    if (is_above(stock['value'], TARGET_VALUE)):
                        prev_values = get_previous_values(stocks, i, 5)
                        valid = True
                        invalid_ctr = 0

                        for value in prev_values:
                            if not is_above(value, TARGET_PREVIOUS_VALUE):
                                invalid_ctr += 1
                            if invalid_ctr > 1:
                                valid = False
                        if valid:
                            if is_above(stock['close'], stock['alma']):
                                risk = round(calculate_risk(stocks, i), 2)
                                if check_risk:
                                    if risk >= -RISK:
                                        txn = trade(stock, action)
                                        txn['risk'] = risk
                                        txns.append(txn)
                                        buy = not buy
                                else:
                                    txn = trade(stock, action)
                                    txns.append(txn)
                                    txn['risk'] = risk
                                    buy = not buy
            else:
                if close_below_alma(stock) and close_below_alma(stocks[i-1]):
                    txn = trade(stock, action)
                    txns[len(txns)-1]['sell_date'] = txn['sell_date']
                    txns[len(txns)-1]['sell_price'] = txn['sell_price']
                    txns[len(txns)-1]['pnl'] = compute_pnl(txn, txns)
                    buy = not buy

        prev_macd_above_signal = is_above(stock['macd'], stock['macds'])
        i += 1

    return txns


def mama_process_backtest(codes_to_test, check_risk=True):
    logging.info('Starting MAMA test')
    print('Starting MAMA test\n')

    txns = []
    for code in codes_to_test:
        logging.info('Starting test of {}'.format(code))
        print('Starting test of {}'.format(code))

        txn = mama_backtest(code, check_risk)
        get_stats(code, txn)
        txns = txns + txn

        logging.info('End of test of {}'.format(code))
        print('End of test of {}'.format(code))

    logging.info('End of MAMA test')
    print('\nEnd of MAMA test')

    return txns


def previous_breakout_candle(stock, indicator):
    return stock['open'] <= indicator and stock['close'] >= indicator


def save_file():
    save = input('Save result to excel file? [Y/N]: ')
    save = save.upper()
    return save == 'Y' and True or False


def show_parameters(strategy, stock, risk, save_file, filename=''):
    print('\nPARAMETERS USED IN THIS TEST \nStrategy: {0} \nStock: {1} \nRisk: {2} \nSave File: {3} \nFilename: {4}'
          .format(
              strategy, stock, risk, save_file, filename
          ))


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
