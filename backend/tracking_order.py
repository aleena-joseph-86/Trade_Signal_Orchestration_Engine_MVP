from ib_async import *

# Connect to IB Gateway or TWS
ib = IB()
ib.connect('127.0.0.1', 7497, 121)
print(f"Connected: {ib.isConnected()}")

# Function to print order details
def print_order_details(trade, executions=None):
    print("----- Order Details -----")
    print(f"Order ID: {trade.order.orderId}")
    print(f"Perm ID: {trade.order.permId}")
    print(f"Status: {trade.orderStatus.status}")
    # Use execution data for filled quantities and price if available
    filled = trade.orderStatus.filled
    avg_fill_price = trade.orderStatus.avgFillPrice
    if executions:
        for exec_detail in executions:
            if exec_detail.execution.permId == trade.order.permId:
                filled = float(exec_detail.execution.shares)
                avg_fill_price = float(exec_detail.execution.price)
                break
    print(f"Filled: {filled}")
    print(f"Remaining: {trade.orderStatus.remaining}")
    print(f"Average Fill Price: {avg_fill_price}")

# Function to get execution details
def get_execution_details(ib, perm_id):
    print("----- Fetching Execution Details -----")
    executions = ib.reqExecutions()
    for exec_detail in executions:
        if exec_detail.execution.permId == perm_id:
            print(f"Found execution for PermId: {perm_id}")
            print(f"Execution ID: {exec_detail.execution.execId}")
            print(f"Shares: {exec_detail.execution.shares}")
            print(f"Price: {exec_detail.execution.price}")
            print(f"Time: {exec_detail.execution.time}")
    return executions

# Function to get order by PermId
def get_order_by_permid(ib, perm_id):
    ib.sleep(5)  # Wait for connection stability
    # Check open orders
    print("Checking open orders...")
    open_orders = ib.reqOpenOrders()
    for trade in open_orders:
        if trade.order.permId == perm_id:
            print(f"Found open order with PermId: {perm_id}")
            print_order_details(trade)
            return trade
    # Check completed orders
    print("Checking completed orders...")
    completed_orders = ib.reqCompletedOrders(apiOnly=True)
    for trade in completed_orders:
        if trade.order.permId == perm_id:
            print(f"Found completed order with PermId: {perm_id}")
            executions = get_execution_details(ib, perm_id)
            print_order_details(trade, executions)
            return trade
    print(f"No order found with PermId: {perm_id}")
    return None

# Specify the PermId of the order to track
old_perm_id = 1759905465  # Use the completed order PermId

# Track the order
get_order_by_permid(ib, old_perm_id)

# Disconnect
ib.disconnect()