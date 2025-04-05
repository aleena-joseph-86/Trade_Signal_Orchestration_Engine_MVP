from typing import Literal, Optional, List
from fastapi import FastAPI
from pydantic import BaseModel, Field
import uuid

app = FastAPI()

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

signals = []

@app.get("/")
def read_root():
    return {"message": "Welcome to the Trading Signal API! Visit /docs for Swagger UI"}


class Signal(BaseModel):
    symbol: str = Field(..., example="MSFT")
    units: float = Field(..., example=10.0)
    action: Literal["BUY", "SELL"] = Field(..., example="BUY")
    id: Optional[str] = Field(None, example="123e4567-e89b-12d3-a456-426614174000")
    class Config:
        schema_extra = {
            "example": {
                "symbol": "MSFT",
                "units": 10,
                "action": "BUY"
            }
        }

@app.post("/webhook")
def receive_signal(signal: Signal):
    signal.id = str(uuid.uuid4())  
    signals.append(signal)
    return {"status": "received", "id": signal.id}

@app.get("/signals", response_model=List[Signal])
def get_signals():
    return signals

@app.post("/trade")
def place_trade(signal: Signal):
    return {
        "status": "Trade placed (mock)",
        "symbol": signal.symbol,
        "action": signal.action,
        "units": signal.units
    }
