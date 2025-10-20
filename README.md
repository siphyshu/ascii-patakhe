# 🎆 ASCII Patakhe - Live Multiplayer Fireworks

A beautiful, real-time multiplayer ASCII fireworks display where everyone sees the same celebration! Perfect for Diwali or any festive occasion.

## ✨ Features

- **Real-time Multiplayer**: All users see the same fireworks synchronized across the globe
- **Live Statistics**: 
  - Total fireworks launched (persistent across restarts)
  - Launch rate (fireworks per minute)
  - Online users count
- **Smart Performance**: Automatic sampling during high traffic to maintain smooth performance
- **Rate Limiting**: IP-based cooldown (0.3s) to prevent spam
- **Auto-reconnection**: WebSocket reconnects automatically if connection drops
- **Beautiful Effects**: Multiple firework types (peony, palm, willow, ring) with realistic physics

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Redis (for state management)

### Local Development

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd ascii-fireworks
   ```

2. **Start Redis** (using Docker - recommended)
   ```bash
   docker-compose up -d
   ```
   
   Or install Redis locally:
   - **Windows**: Download from [Redis for Windows](https://github.com/microsoftarchive/redis/releases)
   - **Mac**: `brew install redis && brew services start redis`
   - **Linux**: `sudo apt install redis-server && sudo systemctl start redis`

3. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the server**
   ```bash
   python server.py
   ```

5. **Open in browser**
   ```
   http://localhost:8000
   ```

6. **Test multiplayer**: Open multiple browser windows/tabs to see real-time synchronization!

## 🔧 Configuration

Create a `.env` file in the root directory (use `.env.example` as template):

```env
REDIS_URL=redis://localhost:6379
RATE_LIMIT_SECONDS=0.3
```

### Environment Variables

- `REDIS_URL`: Redis connection string (default: `redis://localhost:6379`)
- `RATE_LIMIT_SECONDS`: Cooldown between launches per IP (default: `0.3`)

## 📊 How It Works

### Architecture

```
┌─────────────┐      WebSocket       ┌──────────────┐      Redis      ┌───────────┐
│   Browser   │ ◄─────────────────► │ FastAPI      │ ◄──────────────► │   Redis   │
│   Client    │                      │ Server       │                  │           │
└─────────────┘                      └──────────────┘                  └───────────┘
     ▲                                      │                                │
     │                                      │                                │
     └──────────── All clients see ────────┴────────────────────────────────┘
                  the same fireworks!
```

### Performance Optimization

The system automatically adjusts display rate based on traffic:
- **< 5 launches/sec**: Show all fireworks
- **5-10 launches/sec**: Show every 2nd firework
- **10-20 launches/sec**: Show every 5th firework
- **> 20 launches/sec**: Show every 10th firework

The counter always shows the accurate total - only the visual display is sampled!

## 🌐 Deployment

### Deploy to Railway

1. Install Railway CLI: `npm i -g @railway/cli`
2. Login: `railway login`
3. Create new project: `railway init`
4. Add Redis: `railway add redis`
5. Deploy: `railway up`

### Deploy to Render

1. Create account on [Render](https://render.com)
2. Create new "Web Service" linked to your repo
3. Add Redis instance from Render dashboard
4. Set environment variable `REDIS_URL` to your Redis connection string
5. Deploy!

### Deploy to fly.io

1. Install flyctl: https://fly.io/docs/hands-on/install-flyctl/
2. Login: `fly auth login`
3. Launch: `fly launch`
4. Add Redis: `fly redis create`
5. Deploy: `fly deploy`

## 🎮 Usage

1. **Click** the "Launch Patakha!" button or press **Space** to launch a firework
2. Everyone connected sees your firework in real-time!
3. Watch the statistics update:
   - **Patakhe Launched**: Total count (all time)
   - **Patakhe Rate**: Launches per minute
   - **Online**: Current active users

## 🛠️ Technical Stack

- **Frontend**: Vanilla JavaScript, Tailwind CSS
- **Backend**: Python FastAPI
- **WebSockets**: Real-time bidirectional communication
- **Redis**: State persistence and rate limiting
- **Docker**: Easy local Redis setup

## 📝 API Reference

### WebSocket Messages

**Client → Server:**
```json
{
  "type": "launch",
  "timestamp": 1234567890
}
```

**Server → Client:**
```json
// Firework launch
{
  "type": "firework",
  "x": 0.75,
  "count": 1234,
  "sample_rate": 1
}

// Statistics update
{
  "type": "stats",
  "total": 5000,
  "rate": 45.5,
  "online": 23
}

// Rate limit notification
{
  "type": "cooldown",
  "message": "Please wait..."
}
```

### REST Endpoints

- `GET /` - Serve the main HTML page
- `GET /stats` - Get current statistics (JSON)

## 🤝 Contributing

Contributions are welcome! Feel free to:
- Report bugs
- Suggest new features
- Submit pull requests

## 📄 License

MIT License - feel free to use this for your own celebrations!

## 🎉 Credits

Created with 💖 for celebrating festivals together, no matter where you are in the world!

---

**Happy Diwali! 🪔✨**

