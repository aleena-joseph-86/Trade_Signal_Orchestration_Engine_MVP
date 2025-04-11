from ib_async import *

# Connect to IB Gateway or TWS
ib = IB()
ib.connect('127.0.0.1', 7497, 121)

def get_order_details(order_id):
    print("----- Order Details -----")
    print(f"Order ID: {trade.order.orderId}")
    print(f"Status: {trade.orderStatus.status}")
    print(f"Filled: {trade.orderStatus.filled}")
    print(f"Average Fill Price: {trade.orderStatus.avgFillPrice}")
    print(f"Log Entries: {trade.log}")

# Optional: Set market data type to delayed (4 = delayed-frozen)
ib.reqMarketDataType(4)

# Define the stock contract
contract = Stock('AAPL', 'SMART', 'USD')

# Create a limit order to BUY 100 shares at $180
order = MarketOrder('BUY', 100)

# Place the order
trade = ib.placeOrder(contract, order)
print(f"Order placed: {trade}")

ib.sleep(3)

# Optional: check order status
print(f"Order status: {trade.orderStatus.status}")
print(f"Filled: {trade.orderStatus.filled}")
print(f"Order ID: {trade.order.orderId}")

get_order_details(trade.order.orderId)