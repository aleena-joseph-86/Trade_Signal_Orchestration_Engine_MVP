from typing import Literal, List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, model_validator
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi.middleware.cors import CORSMiddleware
import uuid

# --- FastAPI App Initialization ---
app = FastAPI()

# --- CORS Configuration ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for dev; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- MongoDB Connection ---
MONGO_URI = "mongodb://localhost:27017"
client = AsyncIOMotorClient(MONGO_URI)
db = client.trading
signals_collection = db.signals

# --- Pydantic Models ---
class Signal(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str
    units: float
    action: Literal["BUY", "SELL"]
    order_type: Literal["MKT", "LMT"]
    price: Optional[float] = None
    accepted: bool = False
    rejected: bool = False

    @model_validator(mode="after")
    def check_price_for_lmt(self):
        if self.order_type == "LMT" and self.price is None:
            raise ValueError("Price is required for LMT orders.")
        if self.order_type == "MKT":
            self.price = None  # Ensure price is null for MKT
        return self

class UpdateUnits(BaseModel):
    units: float

# --- Routes ---

@app.get("/")
def root():
    return {"message": "Trading Signal API is live. Visit /docs for Swagger."}


@app.post("/webhook")
async def receive_signal(signal: Signal):
    existing = await signals_collection.find_one({"id": signal.id})
    if existing:
        raise HTTPException(status_code=400, detail="Signal already exists.")
    await signals_collection.insert_one(signal.dict())
    return {"status": "received", "id": signal.id}


@app.get("/signals", response_model=List[Signal])
async def get_signals():
    raw_signals = await signals_collection.find().to_list(length=100)
    cleaned_signals = []

    for doc in raw_signals:
        doc.pop("_id", None)

        # Fill missing fields
        doc.setdefault("order_type", "MKT")
        doc.setdefault("price", None)
        doc.setdefault("accepted", False)
        doc.setdefault("rejected", False)

        try:
            cleaned_signals.append(Signal(**doc))
        except Exception as e:
            print(f"Skipping invalid signal due to: {e}")

    return cleaned_signals


@app.post("/trade")
async def accept_signal(signal: Signal):
    result = await signals_collection.update_one(
        {"id": signal.id},
        {"$set": {"accepted": True, "rejected": False}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Signal not found.")
    return {"status": "accepted", "id": signal.id}


@app.post("/reject")
async def reject_signal(signal: Signal):
    result = await signals_collection.update_one(
        {"id": signal.id},
        {"$set": {"rejected": True, "accepted": False}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Signal not found.")
    return {"status": "rejected", "id": signal.id}


@app.put("/update/{signal_id}")
async def update_units(signal_id: str, update: UpdateUnits):
    result = await signals_collection.update_one(
        {"id": signal_id, "accepted": False, "rejected": False},
        {"$set": {"units": update.units}}
    )
    if result.matched_count == 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot update. Signal either not found or already accepted/rejected.",
        )
    return {"status": "updated", "units": update.units}


@app.post("/place-order")
async def place_order(signal: Signal):
    print(f"Placing final order for: {signal.symbol}, units: {signal.units}, action: {signal.action}")
    return {
        "status": "Order placed",
        "symbol": signal.symbol,
        "units": signal.units
    }
