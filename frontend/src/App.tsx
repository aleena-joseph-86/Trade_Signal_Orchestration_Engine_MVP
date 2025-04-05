import { useEffect, useState, useRef } from "react";
import "./App.css";

type Signal = {
  id: string;
  symbol: string;
  percent: number;
  action: string;
  accepted?: boolean;
};

function App() {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [editingSignalId, setEditingSignalId] = useState<string | null>(null);
  const [editedSignal, setEditedSignal] = useState<Signal | null>(null);
  const acceptedSignalsRef = useRef<Set<string>>(new Set());

  const fetchSignals = () => {
    fetch("http://localhost:8000/signals")
      .then((res) => res.json())
      .then((data) => {
        // Preserve local accepted state
        const updated = data.map((signal: Signal) => ({
          ...signal,
          accepted: acceptedSignalsRef.current.has(signal.id),
        }));
        setSignals(updated);
      })
      .catch(console.error);
  };

  useEffect(() => {
    const interval = setInterval(fetchSignals, 3000);
    fetchSignals();
    return () => clearInterval(interval);
  }, []);

  const handleAccept = (signal: Signal) => {
    fetch("http://localhost:8000/trade", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(signal),
    })
      .then((res) => res.json())
      .then((data) => {
        console.log("Trade accepted:", data);
        acceptedSignalsRef.current.add(signal.id);
        setSignals((prev) =>
          prev.map((s) => (s.id === signal.id ? { ...s, accepted: true } : s))
        );
      });
  };

  const handleEdit = (signal: Signal) => {
    setEditingSignalId(signal.id);
    setEditedSignal({ ...signal });
  };

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>
  ) => {
    const { name, value } = e.target;
    if (editedSignal) {
      setEditedSignal({
        ...editedSignal,
        [name]: name === "percent" ? Number(value) : value,
      });
    }
  };

  const handleSave = () => {
    if (!editedSignal) return;
    setSignals((prev) =>
      prev.map((s) => (s.id === editedSignal.id ? editedSignal : s))
    );
    setEditingSignalId(null);
    setEditedSignal(null);
  };

  const handleCancel = () => {
    setEditingSignalId(null);
    setEditedSignal(null);
  };

  return (
    <div className="container">
      <h1>Trading Signals</h1>

      {signals.length === 0 && <p>No trading signals yet.</p>}

      {signals.map((signal) =>
        editingSignalId === signal.id && editedSignal ? (
          <div key={signal.id} className="signal-card">
            <input
              name="symbol"
              value={editedSignal.symbol}
              onChange={handleChange}
            />
            <input
              name="percent"
              type="number"
              value={editedSignal.percent}
              onChange={handleChange}
            />
            <select
              name="action"
              value={editedSignal.action}
              onChange={handleChange}
            >
              <option value="BUY">BUY</option>
              <option value="SELL">SELL</option>
            </select>
            <div>
              <button onClick={handleSave} className="accept">
                Save
              </button>
              <button onClick={handleCancel}>Cancel</button>
            </div>
          </div>
        ) : (
          <div key={signal.id} className="signal-card">
            <p>
              <strong>{signal.action}</strong> {signal.percent}% of AUM in{" "}
              <strong>{signal.symbol}</strong>
            </p>
            <div>
              {signal.accepted ? (
                <button disabled className="accepted">
                  Accepted
                </button>
              ) : (
                <button onClick={() => handleAccept(signal)} className="accept">
                  Accept
                </button>
              )}
              <button onClick={() => handleEdit(signal)} className="edit">
                Edit
              </button>
            </div>
          </div>
        )
      )}
    </div>
  );
}

export default App;
