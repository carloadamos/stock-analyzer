# Imports
import pymongo
from datetime import datetime

# Database Connection
connection_url = 'mongodb+srv://admin:admin@cluster0.70gug.mongodb.net/exercise-tracker?retryWrites=true&w=majority'
client = pymongo.MongoClient(connection_url)
Database = client.get_database('stock-analyzer')
stocks_table = Database.stocks


def backtest():
    stocks = fetch_stocks('2GO')
    buy = True
    i = 0

    prev_macd_above_signal = False
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
                        if price_above_alma(stock) and price_above_moving_average(stock, 20):
                            trade(stock, action)
                            buy = not buy
        else:
            if not price_above_alma(stock):
                trade(stock, action)
                buy = not buy

        prev_macd_above_signal = macd_above_signal(stock)
        i += 1


def calculate_risk(close):
    return close


def convert_timestamp(timestamp):
    return datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')


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
    transaction = {"code": stock['code'], "date": convert_timestamp(stock['timestamp']),
                   "action": action, "price": stock['close']}

    print(transaction)


def value_above_target(value, min_target):
    return value > min_target


backtest()
