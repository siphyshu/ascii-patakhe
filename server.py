import asyncio
import json
import logging
import os
import random
import time
from typing import Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as redis

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
RATE_LIMIT_SECONDS = float(os.getenv("RATE_LIMIT_SECONDS", "0.3"))

# Redis keys
COUNTER_KEY = "patakha:counter"
RATE_KEY = "patakha:rate"
RATE_LIMIT_KEY = "patakha:ratelimit:{ip}"

# Connect to Redis
redis_client: redis.Redis = None


class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.client_ips: dict = {}

    async def connect(self, websocket: WebSocket, client_ip: str):
        # Note: websocket.accept() should be called BEFORE this method
        self.active_connections.add(websocket)
        self.client_ips[websocket] = client_ip
        logger.info(f"Client connected from {client_ip}. Total: {len(self.active_connections)}")
        
        # Send current stats to new client
        await self.send_stats_to_client(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        client_ip = self.client_ips.pop(websocket, "unknown")
        logger.info(f"Client disconnected from {client_ip}. Total: {len(self.active_connections)}")

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")

    async def broadcast(self, message: dict):
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected.add(connection)
        
        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

    async def send_stats_to_client(self, websocket: WebSocket):
        """Send current stats to a specific client"""
        try:
            total = await redis_client.get(COUNTER_KEY)
            total = int(total) if total else 0
            
            rate = await get_launch_rate()
            online = len(self.active_connections)
            
            await self.send_personal_message({
                "type": "stats",
                "total": total,
                "rate": rate,
                "online": online
            }, websocket)
        except Exception as e:
            logger.error(f"Error sending stats to client: {e}")

    def get_online_count(self) -> int:
        return len(self.active_connections)


manager = ConnectionManager()


@app.on_event("startup")
async def startup_event():
    global redis_client
    try:
        logger.info(f"Connecting to Redis at {REDIS_URL}...")
        redis_client = await redis.from_url(REDIS_URL, decode_responses=True)
        await redis_client.ping()
        logger.info("✅ Connected to Redis")
        
        # Initialize counter if not exists
        if not await redis_client.exists(COUNTER_KEY):
            await redis_client.set(COUNTER_KEY, 0)
            logger.info("✅ Initialized counter")
        else:
            current = await redis_client.get(COUNTER_KEY)
            logger.info(f"✅ Counter exists with value: {current}")
        
        # Start background task to broadcast stats
        asyncio.create_task(broadcast_stats_periodically())
        logger.info("✅ Started background stats broadcaster")
    except Exception as e:
        logger.error(f"❌ Startup error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise


@app.on_event("shutdown")
async def shutdown_event():
    if redis_client:
        await redis_client.close()
    logger.info("Disconnected from Redis")


async def get_launch_rate() -> float:
    """Calculate launches per second based on recent activity"""
    try:
        # Get launches from the last 30 seconds for better average
        now = time.time()
        thirty_seconds_ago = now - 30
        
        # Count launches in the last 30 seconds
        count = await redis_client.zcount(RATE_KEY, thirty_seconds_ago, now)
        
        # Clean up old entries (older than 1 minute)
        one_minute_ago = now - 60
        await redis_client.zremrangebyscore(RATE_KEY, 0, one_minute_ago)
        
        # Calculate per-second rate (count over 30 seconds, divided by 30)
        rate = count / 30.0
        return round(rate, 1)
    except Exception as e:
        logger.error(f"Error calculating launch rate: {e}")
        return 0.0


async def check_rate_limit(client_ip: str) -> bool:
    """Check if client is rate limited. Returns True if allowed, False if limited."""
    try:
        key = RATE_LIMIT_KEY.format(ip=client_ip)
        
        # Check if key exists (client is rate limited)
        if await redis_client.exists(key):
            return False  # Rate limited
        
        # Set the key with expiry in milliseconds (for sub-second precision)
        await redis_client.set(key, "1", px=int(RATE_LIMIT_SECONDS * 1000))
        
        return True  # Allowed
    except Exception as e:
        logger.error(f"Error checking rate limit: {e}")
        return True  # Allow on error


def calculate_sample_rate(rate_per_second: float) -> int:
    """Calculate sampling rate based on current launch rate (per second)"""
    if rate_per_second <= 15:
        return 1  # Show all fireworks under 15/sec
    elif rate_per_second > 30:
        return 10
    elif rate_per_second > 20:
        return 5
    else:
        return 2


async def broadcast_stats_periodically():
    """Background task to broadcast stats every 2 seconds"""
    while True:
        try:
            await asyncio.sleep(2)
            
            if manager.get_online_count() > 0:
                total = await redis_client.get(COUNTER_KEY)
                total = int(total) if total else 0
                
                rate = await get_launch_rate()
                online = manager.get_online_count()
                
                await manager.broadcast({
                    "type": "stats",
                    "total": total,
                    "rate": rate,
                    "online": online
                })
        except Exception as e:
            logger.error(f"Error broadcasting stats: {e}")


@app.get("/")
async def get_index():
    """Serve the main HTML file"""
    return FileResponse("index.html")


@app.get("/background.png")
async def get_background():
    """Serve the background image"""
    try:
        return FileResponse("background.png")
    except Exception as e:
        logger.warning(f"Background image not found: {e}")
        return {"error": "Background not found"}


@app.get("/favicon.ico")
async def get_favicon():
    """Serve the favicon"""
    try:
        return FileResponse("favicon.ico")
    except Exception as e:
        logger.warning(f"Favicon not found: {e}")
        return {"error": "Favicon not found"}



@app.get("/og.png")
async def get_og():
    """Serve the og image"""
    try:
        return FileResponse("og.png")
    except Exception as e:
        logger.warning(f"OG image not found: {e}")
        return {"error": "OG image not found"}


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Check Redis connection
        await redis_client.ping()
        return {
            "status": "healthy",
            "redis": "connected",
            "online_users": manager.get_online_count()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "redis": "disconnected",
            "error": str(e)
        }


@app.get("/stats")
async def get_stats():
    """REST endpoint for current stats"""
    try:
        total = await redis_client.get(COUNTER_KEY)
        total = int(total) if total else 0
        
        rate = await get_launch_rate()
        online = manager.get_online_count()
        
        return {
            "total": total,
            "rate": rate,
            "online": online
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return {"error": str(e)}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    logger.info("=== WebSocket connection attempt ===")
    logger.info(f"WebSocket details: {websocket.client}, {websocket.headers}")
    
    try:
        # Accept the connection first
        logger.info("Attempting to accept WebSocket connection...")
        await websocket.accept()
        logger.info("✅ WebSocket connection accepted!")
        
        # Get client IP (handle both direct connections and proxied connections)
        client_ip = "unknown"
        try:
            if websocket.client:
                client_ip = websocket.client.host
                logger.info(f"Client IP: {client_ip}")
            # Check for forwarded IP (if behind proxy)
            if "x-forwarded-for" in websocket.headers:
                client_ip = websocket.headers["x-forwarded-for"].split(",")[0].strip()
                logger.info(f"Forwarded IP: {client_ip}")
        except Exception as e:
            logger.warning(f"Could not get client IP: {e}")
            client_ip = "unknown"
        
        # Register with manager (but don't call accept again)
        manager.active_connections.add(websocket)
        manager.client_ips[websocket] = client_ip
        logger.info(f"✅ Client registered from {client_ip}. Total: {len(manager.active_connections)}")
        
        # Send current stats to new client
        try:
            logger.info("Sending initial stats to client...")
            total = await redis_client.get(COUNTER_KEY)
            total = int(total) if total else 0
            
            rate = await get_launch_rate()
            online = len(manager.active_connections)
            
            await websocket.send_json({
                "type": "stats",
                "total": total,
                "rate": rate,
                "online": online
            })
            logger.info(f"✅ Sent initial stats: total={total}, rate={rate}, online={online}")
        except Exception as e:
            logger.error(f"❌ Error sending initial stats: {e}")
            raise
        
        logger.info("Entering message receive loop...")
        while True:
            # Receive message from client
            try:
                message = await websocket.receive_text()
                logger.info(f"📨 Received raw message: {message}")
                data = json.loads(message)
                logger.info(f"📨 Parsed message: {data}")
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON: {e}")
                continue
            
            if data.get("type") == "launch":
                # Check rate limit
                if not await check_rate_limit(client_ip):
                    await manager.send_personal_message({
                        "type": "cooldown",
                        "message": "Please wait before launching another firework"
                    }, websocket)
                    continue
                
                # Increment counter
                new_count = await redis_client.incr(COUNTER_KEY)
                
                # Add to rate tracking (sorted set with timestamp as score)
                now = time.time()
                await redis_client.zadd(RATE_KEY, {str(now): now})
                
                # Calculate current rate for sampling
                rate_per_second = await get_launch_rate()
                sample_rate = calculate_sample_rate(rate_per_second)
                
                # Determine if this firework should be shown (sampling)
                should_display = (new_count % sample_rate == 0)
                
                if should_display:
                    # Generate random x position (client will scale to their viewport)
                    x_percent = random.uniform(0.1, 0.9)  # 10% to 90% of width
                    
                    # Broadcast to all clients
                    await manager.broadcast({
                        "type": "firework",
                        "x": x_percent,
                        "count": new_count,
                        "sample_rate": sample_rate
                    })
                else:
                    # Still update the counter for all clients
                    await manager.broadcast({
                        "type": "count_update",
                        "count": new_count
                    })
                
    except WebSocketDisconnect as e:
        logger.info(f"🔌 WebSocket disconnected normally: {e}")
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"❌ WebSocket error: {type(e).__name__}: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        manager.disconnect(websocket)
    finally:
        # Ensure cleanup
        if websocket in manager.active_connections:
            logger.info("🧹 Final cleanup of connection")
            manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8500,
        log_level="info",
        access_log=True
    )

