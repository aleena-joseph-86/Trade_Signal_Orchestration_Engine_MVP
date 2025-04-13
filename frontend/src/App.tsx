import { useEffect, useState } from "react";
import { Button, Input, Modal, Table, message } from "antd";
import type { ColumnsType } from "antd/es/table";
import "./App.css";

type Signal = {
  id: string;
  symbol: string;
  units: number;
  action: string;
  order_type: "MKT" | "LMT";
  price?: number | null;
  accepted: boolean;
  rejected: boolean;
  status?: string;
};

function App() {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [editing, setEditing] = useState<Signal | null>(null);
  const [confirming, setConfirming] = useState<Signal | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchSignals = () => {
    fetch("http://localhost:8000/signals")
      .then((res) => res.json())
      .then(setSignals)
      .catch(console.error);
  };

  useEffect(() => {
    fetchSignals();
    const interval = setInterval(fetchSignals, 3000); // Refresh every 3 seconds
    return () => clearInterval(interval);
  }, []);

  const confirmAccept = (signal: Signal) => {
    setConfirming(signal);
  };

  const handleConfirmedAccept = async () => {
    if (!confirming) return;

    try {
      // First: mark as accepted
      await fetch("http://localhost:8000/trade", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(confirming),
      });

      // Second: place the order (just logs to console)
      await fetch("http://localhost:8000/place-order", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(confirming),
      });

      message.success("Trade accepted and order placed!");
    } catch (error) {
      message.error("Error placing order");
      console.error(error);
    } finally {
      setConfirming(null);
      fetchSignals();
    }
  };

  const handleReject = (signal: Signal) => {
    fetch("http://localhost:8000/reject", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(signal),
    })
      .then(() => {
        message.warning("Trade rejected!");
        fetchSignals();
      })
      .catch(console.error);
  };

  const handleEditSave = () => {
    if (!editing) return;
    setLoading(true);
    fetch(`http://localhost:8000/update/${editing.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ units: editing.units }),
    })
      .then(() => {
        message.success("Units updated");
        setEditing(null);
        fetchSignals();
      })
      .finally(() => setLoading(false));
  };

  const handlePlaceOrder = async (signal: Signal) => {
    try {
      const res = await fetch("http://localhost:8000/place-order", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(signal),
      });
  
      const data = await res.json();
  
      if (res.ok) {
        message.success("Order placed successfully!");
        setConfirming(null);  // <-- This closes the modal
        fetchSignals();       // Refresh signals
      } else {
        message.error(data.detail || "Order placement failed.");
      }
    } catch (err) {
      console.error(err);
      message.error("Error placing order.");
    }
  };
  

  const columns: ColumnsType<Signal> = [
    { title: "Symbol", dataIndex: "symbol" },
    { title: "Action", dataIndex: "action" },
    { title: "Order Type", dataIndex: "order_type" },
    {
      title: "Price",
      dataIndex: "price",
      render: (value) => (value !== null && value !== undefined ? value : "—"),
    },
    { title: "Units", dataIndex: "units" },
    {
      title: "Signal Status",
      render: (_, record) =>
        record.accepted ? (
          <span style={{ color: "green", fontWeight: 600 }}>Accepted</span>
        ) : record.rejected ? (
          <span style={{ color: "red", fontWeight: 600 }}>Rejected</span>
        ) : (
          <span style={{ color: "orange" }}>Pending</span>
        ),
    },
    {
      title: "Execution Status",
      dataIndex: "status",
      key: "executionStatus",
      render: (status) => {
        let color = "";
        switch (status) {
          case "Filled":
            color = "green";
            break;
          case "Failed":
            color = "red";
            break;
          case "Pending":
            color = "orange";
            break;
          default:
            color = "gray";
        }

        return (
          <span style={{ fontWeight: "700", color }}>
            {status || "—"}
          </span>
        );
      },
    },
    {
      title: "Actions",
      render: (_, signal) =>
        !signal.accepted && !signal.rejected ? (
          <div className="flex gap-2">
            <Button onClick={() => confirmAccept(signal)} type="primary">
              Accept
            </Button>
            <Button danger onClick={() => handleReject(signal)}>
              Reject
            </Button>
            <Button onClick={() => setEditing(signal)}>Edit</Button>
          </div>
        ) : null,
    },
  ];

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <h1 className="text-3xl font-bold mb-4">Trading Signals</h1>
      <Table dataSource={signals} columns={columns} rowKey="id" />

    {/* Modal to edit units */}
    <Modal
        open={!!editing}
        onCancel={() => setEditing(null)}
        onOk={handleEditSave}
        confirmLoading={loading}
        title="Edit Units"
      >
        <div className="space-y-4">
          <Input
            addonBefore="Units"
            type="number"
            value={editing?.units}
            onChange={(e) =>
              setEditing((prev) => prev && { ...prev, units: +e.target.value })
            }
          />
        </div>
      </Modal>

      {/* Confirmation modal for placing order */}
      <Modal
        open={!!confirming}
        onCancel={() => setConfirming(null)}
        onOk={handleConfirmedAccept}
        okText="Yes, Place Order"
        cancelText="No"
        title="Confirm Order"
      >
        <p>
          Are you sure you want to place a <strong>{confirming?.action}</strong> order for{" "}
          <strong>{confirming?.units}</strong> units of <strong>{confirming?.symbol}</strong>?
        </p>
      </Modal>
    </div>
  );
}

export default App;
