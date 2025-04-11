from ib_async import *

# Connect to IB Gateway or TWS
ib = IB()
ib.connect('127.0.0.1', 7497, 121)
print(f"Connected: {ib.isConnected()}")

# Function to print order details
def print_order_details(trade):
    print("----- Order Details -----")
    print(f"Order ID: {trade.order.orderId}")
    print(f"Perm ID: {trade.order.permId}")
    print(f"Status: {trade.orderStatus.status}")
    print(f"Filled: {trade.orderStatus.filled}")
    print(f"Average Fill Price: {trade.orderStatus.avgFillPrice}")
    print(f"Log Entries: {trade.log}")

# Function to get order by PermId (checks open and completed orders)
def get_order_by_permid(ib, perm_id):
    ib.sleep(2)  # Wait for connection stability
    # Check open orders
    open_orders = ib.reqOpenOrders()
    for trade in open_orders:
        if trade.order.permId == perm_id:
            print(f"Found open order with PermId: {perm_id}")
            print_order_details(trade)
            return trade
    # Check completed orders
    completed_orders = ib.reqCompletedOrders(apiOnly=False)
    for trade in completed_orders:
        if trade.order.permId == perm_id:
            print(f"Found completed order with PermId: {perm_id}")
            print_order_details(trade)
            return trade
    print(f"No order found with PermId: {perm_id}")
    return None

# Specify the PermId of the old order to track
old_perm_id = 123456789  # Replace with the actual PermId of the order you want to track

# Track the order
get_order_by_permid(ib, old_perm_id)

# Disconnect
ib.disconnect()