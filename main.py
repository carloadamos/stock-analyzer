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


def backtest(code, check_risk=True):
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
                if not prev_macd_above_signal and macd_above_signal(stock):
                    if (value_above_target(stock['value'], TARGET_VALUE)):
                        prev_values = get_previous_values(stocks, i, 5)
                        valid = True
                        invalid_ctr = 0

                        for value in prev_values:
                            if not value_above_target(value, TARGET_PREVIOUS_VALUE):
                                invalid_ctr += 1
                            if invalid_ctr > 1:
                                valid = False
                        if valid:
                            if close_above_alma(stock):
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
                                    risk = calculate_risk(stocks, i)
                                    txn['risk'] = risk
                                    buy = not buy
            else:
                if close_below_alma(stock) and close_below_alma(stocks[i-1]):
                    txn = trade(stock, action)
                    txn['pnl'] = compute_pnl(txn, txns)
                    txns.append(txn)
                    buy = not buy

        prev_macd_above_signal = macd_above_signal(stock)
        i += 1

    return txns


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
    i = 0
    total = 0
    df = pd.DataFrame(txns)
    max_loss = df['pnl'].min()
    max_win = df['pnl'].max()
    for txn in txns:
        if txn['action'] == 'SELL':
            if txn['pnl'] > 0:
                total += txn['pnl']
                i += 1

    if i is not 0:
        win_rate = round((i/len(txns)) * 100, 2)

    return {
        "code": code,
        "win_rate": win_rate,
        "wins": i,
        "max_win": max_win,
        "loss": len(txns) - i,
        "max_loss": max_loss,
        "total": round(total, 2)}


def convert_timestamp(timestamp):
    return datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d')


def compute_pnl(txn, txns):
    return round(compute_profit(txns[-1:][0]['price'], txn['price']) - COMM_RATE, 2)


def compute_profit(buy_price, sell_price):
    return (((sell_price - buy_price) / buy_price) * 100)


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


def get_previous_values(stocks, cur_pos, length):
    prev_values = []

    for i in range(length+1):
        if i is not 0:
            if cur_pos > length+1:
                prev_values.append(stocks[cur_pos-i]['value'])
            else:
                prev_values.append(0)

    return prev_values


def calculate_risk(stocks, cur_pos):
    i = 0
    entry_point = stocks[cur_pos]['close']
    risk = compute_profit(entry_point, stocks[cur_pos]['alma'])

    while True:
        if i is not 0 and cur_pos is not 0:
            prev_candle = stocks[cur_pos-i]
            if close_below_alma(prev_candle):
                break
            if close_above_alma(prev_candle) and low_below_alma(prev_candle):
                risk = compute_profit(entry_point, prev_candle['alma'])
        i += 1

    return risk


def macd_above_signal(stock):
    if stock['macd'] > stock['macds']:
        return True
    return False


def previous_breakout_candle(stock, indicator):
    return stock['open'] <= indicator and stock['close'] >= indicator


def close_above_alma(stock):
    """
    Identify if close price is above ALMA.
    :param stock: Stock object
    :return: boolean
    """
    if stock['alma'] is not None:
        return stock['close'] > stock['alma']


def close_below_alma(stock):
    """
    Identify if close price is below ALMA.
    :param stock: Stock object
    :return: boolean
    """
    if stock['alma'] is not None:
        return stock['close'] < stock['alma']


def low_below_alma(stock):
    if stock['alma'] is not None:
        return stock['low'] < stock['alma']


def price_above_moving_average(stock, length):
    """
    Identify if close price is above MA.
    :param stock: Stock object
    :param length: Size of MA
    """
    if length == 20:
        if stock['ma20'] is not None:
            return stock['close'] > stock['ma20']
    elif length == 50:
        if stock['ma50'] is not None:
            return stock['close'] > stock['ma50']
    elif length == 100:
        if stock['ma100'] is not None:
            return stock['close'] > stock['ma100']
    else:
        return False


def trade(stock, action):
    return {"code": stock['code'], "date": convert_timestamp(stock['timestamp']),
            "action": action, "price": stock['close']}


def value_above_target(value, min_target):
    return value > min_target


def process_backtest(codes_to_test, check_risk=True):
    logging.info('Starting test for ALL stocks')
    print('Starting test for ALL stocks\n')

    txns = []
    for code in codes_to_test:
        logging.info('Starting test of {}'.format(code))
        print('Starting test of {}'.format(code))

        txn = backtest(code, check_risk)
        get_stats(code, txn)
        txns = txns + txn

        logging.info('End of test of {}'.format(code))
        print('End of test of {}'.format(code))

    logging.info('End of test for ALL stocks')
    print('End of test for ALL stocks\n')

    return txns


def get_stats(code, txn):
    all_stats.append(calculate_win_rate(code, txn))


def check_risk():
    check_risk = input(
        'Include risk checking? Current value is: {0} [Y/N] '.format(RISK))
    check_risk = check_risk.upper()
    check_risk = check_risk == 'Y' and True or False

    return check_risk


def display_stats(stats):
    print('\nWin rate: {0}% \nWins: {1}\nMax Win: {2}%\nLoss: {3}\nMax Loss: {4}%\nTotal: {5}%\n'
          .format(
              stats['win_rate'],
              stats['wins'],
              stats['max_win'],
              stats['loss'],
              stats['max_loss'],
              stats['total']))


all_txns = []
check_risk = check_risk()
stocks = []

if len(sys.argv) > 1:
    code = sys.argv[1].upper()
    stocks = code == 'ALL' and codes or [code]

    all_txns = process_backtest(stocks, check_risk)

else:
    code = input('Enter stock to test: ')

    if code != '':
        code = code.upper()
        stocks = code == 'ALL' and codes or [code]

        all_txns = process_backtest(stocks, check_risk)
    else:
        all_txns = process_backtest(stocks, check_risk)

if len(all_txns) != 0:
    stats = calculate_win_rate('ALL', all_txns)

    txns_df = pd.DataFrame(all_txns)
    # txns_df.to_excel("result.xlsx", engine='xlsxwriter')
    pd.set_option('display.max_rows', txns_df.shape[0]+1)

    stats_df = pd.DataFrame(all_stats)
    # txns_df.to_excel("result.xlsx", engine='xlsxwriter')
    pd.set_option('display.max_rows', stats_df.shape[0]+1)

    with pd.ExcelWriter('result.xlsx') as writer:  # pylint: disable=abstract-class-instantiated
        stats_df.to_excel(writer, sheet_name='Summary')
        txns_df.to_excel(writer, sheet_name='Details')

    print(txns_df)
    display_stats(stats)
    print(stats_df)
