import sqlite3
import json
import asyncio
import os
from datetime import datetime
from typing import List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import random

app = FastAPI(title="Stadium Smart Experience Platform")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database setup
DB_NAME = "events.db"

def init_db():
    """Initialize SQLite database with required tables."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Zones table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS zones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            section TEXT NOT NULL,
            current_capacity INTEGER DEFAULT 0,
            max_capacity INTEGER NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Orders table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            item_type TEXT NOT NULL,
            item_name TEXT NOT NULL,
            quantity INTEGER DEFAULT 1,
            pickup_zone TEXT NOT NULL,
            estimated_wait INTEGER DEFAULT 5,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Alerts table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message TEXT NOT NULL,
            alert_type TEXT DEFAULT 'info',
            priority TEXT DEFAULT 'normal',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Populate zones if empty
    cursor.execute("SELECT COUNT(*) FROM zones")
    if cursor.fetchone()[0] == 0:
        zones_data = [
            ("North Entrance", "Entry", 45, 100),
            ("South Entrance", "Entry", 30, 100),
            ("East Concessions", "Food", 80, 150),
            ("West Concessions", "Food", 60, 150),
            ("Main Restrooms", "Facilities", 25, 50),
            ("Upper Deck Restrooms", "Facilities", 15, 50),
            ("Merchandise Store A", "Shop", 40, 80),
            ("Merchandise Store B", "Shop", 35, 80),
            ("VIP Lounge", "Premium", 20, 60),
            ("North Seating", "Seating", 1200, 2000),
            ("South Seating", "Seating", 1500, 2000),
            ("East Seating", "Seating", 1100, 2000),
            ("West Seating", "Seating", 1300, 2000),
        ]
        cursor.executemany(
            "INSERT INTO zones (name, section, current_capacity, max_capacity) VALUES (?, ?, ?, ?)",
            zones_data
        )
    
    conn.commit()
    conn.close()

init_db()

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

# Pydantic models
class Order(BaseModel):
    customer_name: str
    item_type: str
    item_name: str
    quantity: int = 1
    pickup_zone: str

class Alert(BaseModel):
    message: str
    alert_type: str = "info"
    priority: str = "normal"

# Helper functions
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def calculate_density_level(current: int, max_capacity: int) -> str:
    ratio = current / max_capacity if max_capacity > 0 else 0
    if ratio < 0.4:
        return "low"
    elif ratio < 0.7:
        return "medium"
    else:
        return "high"

def calculate_wait_time(zone: str, item_type: str) -> int:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM orders WHERE pickup_zone = ? AND status = 'pending'",
        (zone,)
    )
    pending_count = cursor.fetchone()[0]
    conn.close()
    
    base_time = 5
    if item_type == "food":
        base_time = 8
    elif item_type == "merchandise":
        base_time = 3
    
    return base_time + (pending_count * 2)

# Routes
@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main HTML page."""
    with open("templates/index.html", "r") as f:
        return HTMLResponse(content=f.read())

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "Stadium Smart Experience"}

@app.get("/api/zones")
async def get_zones():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM zones ORDER BY section, name")
    rows = cursor.fetchall()
    conn.close()
    
    zones = []
    for row in rows:
        zones.append({
            "id": row["id"],
            "name": row["name"],
            "section": row["section"],
            "current_capacity": row["current_capacity"],
            "max_capacity": row["max_capacity"],
            "density_level": calculate_density_level(row["current_capacity"], row["max_capacity"]),
            "updated_at": row["updated_at"]
        })
    
    return {"zones": zones}

@app.post("/api/orders")
async def create_order(order: Order):
    wait_time = calculate_wait_time(order.pickup_zone, order.item_type)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO orders (customer_name, item_type, item_name, quantity, pickup_zone, estimated_wait, status)
           VALUES (?, ?, ?, ?, ?, ?, 'pending')""",
        (order.customer_name, order.item_type, order.item_name, order.quantity, order.pickup_zone, wait_time)
    )
    order_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    await manager.broadcast({
        "type": "new_order",
        "data": {"order_id": order_id, "zone": order.pickup_zone, "estimated_wait": wait_time}
    })
    
    return {
        "success": True,
        "order_id": order_id,
        "estimated_wait": wait_time,
        "message": f"Order placed! Estimated wait: {wait_time} minutes"
    }

@app.get("/api/orders")
async def get_orders():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders ORDER BY created_at DESC LIMIT 50")
    rows = cursor.fetchall()
    conn.close()
    
    orders = []
    for row in rows:
        orders.append({
            "id": row["id"],
            "customer_name": row["customer_name"],
            "item_type": row["item_type"],
            "item_name": row["item_name"],
            "quantity": row["quantity"],
            "pickup_zone": row["pickup_zone"],
            "estimated_wait": row["estimated_wait"],
            "status": row["status"],
            "created_at": row["created_at"]
        })
    
    return {"orders": orders}

@app.post("/api/alerts")
async def create_alert(alert: Alert):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO alerts (message, alert_type, priority) VALUES (?, ?, ?)",
        (alert.message, alert.alert_type, alert.priority)
    )
    alert_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    await manager.broadcast({
        "type": "alert",
        "data": {
            "id": alert_id,
            "message": alert.message,
            "alert_type": alert.alert_type,
            "priority": alert.priority,
            "timestamp": datetime.now().isoformat()
        }
    })
    
    return {"success": True, "alert_id": alert_id}

@app.get("/api/alerts")
async def get_alerts():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM alerts ORDER BY created_at DESC LIMIT 10")
    rows = cursor.fetchall()
    conn.close()
    
    alerts = []
    for row in rows:
        alerts.append({
            "id": row["id"],
            "message": row["message"],
            "alert_type": row["alert_type"],
            "priority": row["priority"],
            "created_at": row["created_at"]
        })
    
    return {"alerts": alerts}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    await websocket.send_json({"type": "connected", "message": "Connected to real-time updates"})
    
    try:
        while True:
            data = await websocket.receive_text()
            if data:
                await websocket.send_json({"type": "echo", "message": f"Received: {data}"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Background task
async def simulate_crowd_updates():
    while True:
        await asyncio.sleep(10)
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, current_capacity, max_capacity FROM zones")
        zones = cursor.fetchall()
        
        for zone in zones:
            change = random.randint(-15, 20)
            new_capacity = max(0, min(zone["current_capacity"] + change, zone["max_capacity"]))
            cursor.execute(
                "UPDATE zones SET current_capacity = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (new_capacity, zone["id"])
            )
        
        conn.commit()
        cursor.execute("SELECT id, name, current_capacity, max_capacity, section FROM zones")
        updated_zones = cursor.fetchall()
        conn.close()
        
        zones_data = []
        for z in updated_zones:
            zones_data.append({
                "id": z["id"],
                "name": z["name"],
                "section": z["section"],
                "current_capacity": z["current_capacity"],
                "max_capacity": z["max_capacity"],
                "density_level": calculate_density_level(z["current_capacity"], z["max_capacity"])
            })
        
        await manager.broadcast({"type": "crowd_update", "data": zones_data})

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(simulate_crowd_updates())

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
