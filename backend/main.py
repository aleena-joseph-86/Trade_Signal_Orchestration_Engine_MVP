from typing import Literal, List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, model_validator
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi.middleware.cors import CORSMiddleware
from ib_insync import IB, Stock, MarketOrder, LimitOrder, Trade
from fastapi.encoders import jsonable_encoder
from fastapi import BackgroundTasks
import uuid
import threading
import asyncio

# --- FastAPI App Initialization ---
app = FastAPI()
ib = IB()

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- MongoDB ---
MONGO_URI = "mongodb://localhost:27017"
client = AsyncIOMotorClient(MONGO_URI)
db = client.trading
signals_collection = db.signals
executions_collection = db.executions

# --- Pydantic Models ---
class Signal(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str
    units: float
    action: Literal["BUY", "SELL"]
    order_type: Literal["MKT", "LMT"]
    price: Optional[float] = None
    exchange: str = 'SMART'
    currency: str = 'USD'
    accepted: bool = False
    rejected: bool = False
    status: Optional[str] = '-'

    @model_validator(mode="after")
    def check_price_for_lmt(self):
        if self.order_type == "LMT" and self.price is None:
            raise ValueError("Price is required for LMT orders.")
        if self.order_type == "MKT":
            self.price = None
        return self

class UpdateUnits(BaseModel):
    units: float

# --- IB Connection ---
def connect_ib():
    print("🔌 Connecting to IB...")
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        ib.connect("127.0.0.1", 7497, clientId=1)
        ib.run()
    except Exception as e:
        print(f"Connection failed: {e}")
    else:
        print("✅ Connected to IB")


@app.on_event("startup")
def startup_event():
    print("🚀 Starting up...")
    thread = threading.Thread(target=connect_ib, daemon=True)
    thread.start()

@app.get("/")
def root():
    return {"message": "FastAPI + IBKR Running"}

# --- CRUD APIs ---
@app.post("/webhook")
async def receive_signal(signal: Signal):
    if await signals_collection.find_one({"id": signal.id}):
        raise HTTPException(status_code=400, detail="Signal already exists.")
    await signals_collection.insert_one(signal.model_dump())
    return {"status": "received", "id": signal.id}

@app.get("/signals", response_model=List[Signal])
async def get_signals():
    raw = await signals_collection.find().to_list(100)
    for r in raw:
        r.pop("_id", None)
    return [Signal(**r) for r in raw]


@app.post("/trade")
async def accept_signal(signal: Signal):
    result = await signals_collection.update_one(
        {"id": signal.id},
        {"$set": {"accepted": True, "rejected": False}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Signal not found.")
    return {"status": "accepted"}

@app.post("/reject")
async def reject_signal(signal: Signal):
    result = await signals_collection.update_one(
        {"id": signal.id},
        {"$set": {"rejected": True, "accepted": False}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Signal not found.")
    return {"status": "rejected"}



@app.put("/update/{signal_id}")
async def update_units(signal_id: str, update: UpdateUnits):
    result = await signals_collection.update_one(
        {"id": signal_id, "accepted": False, "rejected": False},
        {"$set": {"units": update.units}}
    )
    if result.matched_count == 0:
        raise HTTPException(
            status_code=400,
            detail="Signal not found or already acted on."
        )
    return {"status": "updated"}

@app.post("/place-order")
async def place_order(order: Signal):
    if not ib.isConnected():
        raise HTTPException(status_code=500, detail="IBKR not connected.")

    # Define contract
    contract = Stock(order.symbol, exchange=order.exchange, currency=order.currency)
    details = await ib.reqContractDetailsAsync(contract)
    if not details:
        raise HTTPException(status_code=404, detail="Symbol not found.")

    qualified_contract = details[0].contract

    # Create order
    if order.order_type == "MKT":
        ib_order = MarketOrder(order.action, order.units)
    elif order.order_type == "LMT":
        ib_order = LimitOrder(order.action, order.units, order.price)
    else:
        raise HTTPException(status_code=400, detail="Invalid order type.")

    # Place the order
    trade: Trade = ib.placeOrder(qualified_contract, ib_order)

    # --- Wait for permId and initial status ---
    retries = 0
    while (not trade.order.permId or trade.order.permId == 0 or not trade.orderStatus.status) and retries < 20:
        await asyncio.sleep(0.5)
        retries += 1

    # Wait for MKT execution if necessary
    if order.order_type == "MKT":
        while not trade.isDone():
            await asyncio.sleep(0.5)

    # Save initial execution snapshot
    execution_data = {
        "SignalId": order.id,
        "orderId": trade.order.orderId,
        "symbol": order.symbol,
        "units": order.units,
        "orderType": order.order_type,
        "action": order.action,
        "permId": trade.order.permId,
        "filled": trade.orderStatus.filled,
        "avgFillPrice": trade.orderStatus.avgFillPrice,
        "status": trade.orderStatus.status,
        "timestamp": str(trade.log[-1].time) if trade.log else None
    }
    await executions_collection.insert_one(execution_data)

    # Update signal with permId + status
    result = await signals_collection.update_one(
        {"id": order.id},
        {"$set": {
            "permId": trade.order.permId,
            "status": trade.orderStatus.status
        }}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Signal not found for update.")

    # ✅ Real-time updates: attach handler

    loop = asyncio.get_running_loop()  # Get main loop once

    def handle_order_status(trade: Trade):
        async def update_status():
            latest_status = trade.orderStatus.status
            permId = trade.order.permId
            filled = trade.orderStatus.filled
            avgFillPrice = trade.orderStatus.avgFillPrice
            signal_id = order.id

            update_fields = {
                "status": latest_status,
                "filled": filled,
                "avgFillPrice": avgFillPrice,
                "timestamp": str(trade.log[-1].time) if trade.log else None,
            }

            # Update signal
            result_signal = await signals_collection.update_one(
                {"id": signal_id},
                {"$set": update_fields}
            )
            print(f"[Update] signals_collection: {result_signal.modified_count} updated")

            # Update executions
            result_exec = await executions_collection.update_one(
                {"SignalId": signal_id},
                {"$set": update_fields}
            )
            print(f"[Update] executions_collection: {result_exec.modified_count} updated")

        # Schedule it properly
        loop.call_soon_threadsafe(lambda: asyncio.create_task(update_status()))

    trade.filledEvent += handle_order_status
    trade.statusEvent += handle_order_status

    return {
        "status": "order placed",
        "execution": jsonable_encoder(execution_data)
    }
