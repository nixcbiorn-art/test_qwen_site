
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import uvicorn
import random
import datetime

app = FastAPI(title="Weather & Analytics Hub")

@app.get("/")
async def root(request: Request):
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Analytics Dashboard</title>
    <meta charset="utf-8">
    <style>
        body{font-family:sans-serif; background:#f0f2f5; padding:20px;}
        .card{background:white; padding:20px; border-radius:8px; margin:10px 0; box-shadow:0 2px 4px rgba(0,0,0,0.1);}
        h1{color:#333;} .stat{font-size:24px; font-weight:bold; color:#007bff;}
        .plugin-info{background:#e7f3ff; border-left:4px solid #007bff;}
    </style>
    </head>
    <body>
    <h1>🌍 Global Weather Analytics</h1>
    <div class="card"><h3>Status</h3><p class="stat">System Online 🟢</p></div>
    <div class="card"><h3>Active Sources</h3><p>Moscow, London, New York, Tokyo</p></div>
    <div class="card plugin-info"><h3>🧩 Plugin API</h3><p>Endpoint: <code>/plugin/data</code></p>
    <p>Use this endpoint in your browser extension to fetch parsed data.</p></div>
    <div class="card"><h3>Live Updates</h3><p id="last-update">Waiting...</p></div>
    <script>
        setInterval(async () => {
            try {
                const res = await fetch('/api/weather');
                const data = await res.json();
                document.getElementById('last-update').innerText = "Updated: " + new Date().toLocaleTimeString() + " | Temp: " + data.temp.toFixed(1) + "°C";
            } catch(e) {
                document.getElementById('last-update').innerText = "Error updating";
            }
        }, 5000);
    </script>
    </body>
    </html>
    """
    return HTMLResponse(html)

@app.get("/api/weather")
async def get_weather():
    return {"status": "ok", "time": datetime.datetime.now().isoformat(), "temp": random.uniform(10, 25)}

@app.get("/plugin/data")
async def plugin_data():
    return {"source": "web_scraper", "data": [1, 2, 3], "timestamp": datetime.datetime.now().isoformat()}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
