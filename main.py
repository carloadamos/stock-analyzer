# Imports
import pymongo

# Database Connection
connection_url = 'mongodb+srv://admin:admin@cluster0.70gug.mongodb.net/exercise-tracker?retryWrites=true&w=majority'
client = pymongo.MongoClient(connection_url)
Database = client.get_database('stock-analyzer')
stocks_table = Database.stocks

# Retrieve Stocks


def fetchAllStocks():
    return stocks_table.find()


def fetchStocks(code):
    return list(stocks_table.find({"code": code}))


# Loop
fetchStocks('2GO')

# Check MACD Crossover

# Check close price against ALMA

# Check value

# Check volume
