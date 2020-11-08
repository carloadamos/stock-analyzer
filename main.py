# Imports
import pymongo
from datetime import datetime

# Database Connection
connection_url = 'mongodb+srv://admin:admin@cluster0.70gug.mongodb.net/exercise-tracker?retryWrites=true&w=majority'
client = pymongo.MongoClient(connection_url)
Database = client.get_database('stock-analyzer')
stocks_table = Database.stocks


def fetchAllStocks():
    """
    Fetch all stocks.
    """
    return stocks_table.find()


def fetchStocks(code):
    """
    Fetch stocks based on stock code.
    """
    return list(stocks_table.find({"code": code}))


def priceAboveAlma(stock):
    """
    Identify if close price is above ALMA.
    :param stock: Stock object
    :return: boolean
    """
    if stock['alma'] is not None:
        return stock['close'] > stock['alma']


def priceAboveMovingAverage(stock, length):
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
    transaction = {"code": stock['code'], "date": datetime.utcfromtimestamp(stock['timestamp']).strftime('%Y-%m-%d %H:%M:%S'),
                   "action": action, "price": stock['close']}

    print(transaction)


# Retrieve Stocks
stocks = fetchStocks('2GO')

sell = False
action = 'BUY'
# Loop
for stock in stocks:
    action = sell and 'SELL' or 'BUY'

    if not sell:
        if priceAboveAlma(stock) and priceAboveMovingAverage(stock, 20):
            sell = not sell
            trade(stock, action)
    else:
        if not priceAboveMovingAverage(stock, 20):
            sell = not sell
            trade(stock, action)

# Check MACD Crossover Functions


# Check value


# Check volume
