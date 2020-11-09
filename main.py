# Imports
import sys
import pymongo
import pandas as pd
from datetime import datetime

# database Connection
connection_url = 'mongodb+srv://admin:admin@cluster0.70gug.mongodb.net/exercise-tracker?retryWrites=true&w=majority'
client = pymongo.MongoClient(connection_url)
database = client.get_database('stock-analyzer')
stocks_table = database.stocks

comm_rate = 1.19


def backtest(code):
    stocks = fetch_stocks(code)
    buy = True
    i = 0

    prev_macd_above_signal = False
    txns = []
    # Loop
    for stock in stocks:
        action = buy and 'BUY' or 'SELL'

        if buy:
            if not prev_macd_above_signal and macd_above_signal(stock):
                if (value_above_target(stock['value'], 1000000)):
                    prev_values = get_previous_values(stocks, i, 5)
                    valid = True
                    invalid_ctr = 0

                    for value in prev_values:
                        if not value_above_target(value, 800000):
                            invalid_ctr += 1
                        if invalid_ctr > 1:
                            valid = False
                    if valid:
                        if price_above_alma(stock):
                            txn = trade(stock, action)
                            risk = calculate_risk(stocks, i)
                            if risk >= -4.0:
                                txn['risk'] = risk
                                txns.append(txn)
                                buy = not buy
        else:
            if not price_above_alma(stock):
                txn = trade(stock, action)
                txn['pnl'] = compute_pnl(txn, txns)
                txns.append(txn)
                buy = not buy

        prev_macd_above_signal = macd_above_signal(stock)
        i += 1

    df = pd.DataFrame(txns)
    print(df)

    stats = calculate_win_rate(txns)
    print('\nWin rate: {0}% Wins: {1} Loss: {2} Total: {3}%\n'.format(
        stats['win_rate'], stats['wins'], stats['loss'], stats['total']))


def calculate_win_rate(txns):
    win_rate = 0
    i = 0
    total = 0
    for txn in txns:
        if txn['action'] == 'SELL':
            if txn['pnl'] > 0:
                total += txn['pnl']
                i += 1

    if i is not 0:
        win_rate = round((i/len(txns)) * 100, 2)

    return {"win_rate": win_rate, "wins": i, "loss": len(txns) - i, "total": round(total, 2)}


def convert_timestamp(timestamp):
    return datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d')


def compute_pnl(txn, txns):
    return round(compute_profit(txns[-1:][0]['price'], txn['price']) - comm_rate, 2)


def compute_profit(buy_price, sell_price):
    return (((sell_price - buy_price) / buy_price) * 100)


def fetbuy_pricech_all_stocks():
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
    risk = 0
    i = 0
    entry_point = stocks[cur_pos]['close']

    while True:
        if i is not 0 and cur_pos is not 0:
            prev_candle = stocks[cur_pos-i]
            if price_above_alma(prev_candle) and low_below_alma(prev_candle):
                risk = compute_profit(entry_point, prev_candle['alma'])
                break
        i += 1

    return risk


def macd_above_signal(stock):
    if stock['macd'] > stock['macds']:
        return True
    return False


def previous_breakout_candle(stock, indicator):
    return stock['open'] <= indicator and stock['close'] >= indicator


def price_above_alma(stock):
    """
    Identify if close price is above ALMA.
    :param stock: Stock object
    :return: boolean
    """
    if stock['alma'] is not None:
        return stock['close'] > stock['alma']


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


backtest(sys.argv[1])
