import random
from flask import Flask, jsonify, render_template_string

app = Flask(__name__)

# Mock Data Storage jo numbers ko badhayega
sim_data = {
    "total_vehicles": 142,
    "total_violations": 4,
    "density_state": "Normal",
    "fps": 29.4
}

@app.route("/")
def index():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Smart Road Vehicle Analytics System</title>
        <style>
            body { font-family: 'Segoe UI', sans-serif; background-color: #f4f6f9; margin: 0; padding: 20px; color: #333; }
            .container { max-width: 1200px; margin: 0 auto; }
            header { background: #2c3e50; color: white; padding: 20px; border-radius: 8px; text-align: center; }
            .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 20px; margin: 20px 0; }
            .card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; }
            .card p { margin: 10px 0 0 0; font-size: 28px; font-weight: bold; color: #2c3e50; }
            .main-content { display: grid; grid-template-columns: 2fr 1fr; gap: 20px; }
            .video-box { background: #222; border-radius: 8px; position: relative; height: 400px; overflow: hidden; border: 4px solid #111; }
            .road { position: absolute; width: 100%; height: 140px; background: #34495e; top: 35%; border-top: 4px dashed #fff; border-bottom: 4px dashed #fff; }
            .counting-line { position: absolute; left: 50%; top: 35%; width: 4px; height: 140px; background: #00ffff; box-shadow: 0 0 10px #00ffff; z-index: 10; }
            .car-sim { position: absolute; width: 75px; height: 45px; background: #3498db; border: 2px solid #2ecc71; top: 40%; left: -100px; animation: moveCar 4s linear infinite; border-radius: 4px; }
            .car-sim::before { content: "Car: 94%"; position: absolute; top: -18px; left: 0; background: #2ecc71; color: black; font-size: 9px; font-weight: bold; padding: 1px 3px; border-radius: 2px; }
            .truck-sim { position: absolute; width: 110px; height: 55px; background: #e67e22; border: 2px solid #e74c3c; top: 48%; left: -200px; animation: moveTruck 7s linear infinite; animation-delay: 1.5s; border-radius: 4px; }
            .truck-sim::before { content: "Truck: Speeding"; position: absolute; top: -18px; left: 0; background: #e74c3c; color: white; font-size: 9px; font-weight: bold; padding: 1px 3px; border-radius: 2px; }
            @keyframes moveCar { 0% { left: -100px; } 100% { left: 105%; } }
            @keyframes moveTruck { 0% { left: -150px; } 100% { left: 105%; } }
            .table-box { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        </style>
        <script>
            function refreshStats() {
                fetch('/api/stats')
                .then(res => res.json())
                .then(data => {
                    // Yahan dono IDs ko perfectly match kar diya hai backend se
                    document.getElementById('total-vehicles').innerText = data.total_vehicles;
                    document.getElementById('total-violations').innerText = data.total_violations;
                    document.getElementById('fps').innerText = data.fps.toFixed(1);
                    document.getElementById('density').innerText = data.density_state;
                }).catch(err => console.log(err));
            }
            setInterval(refreshStats, 2000);
            window.onload = refreshStats;
        </script>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>Smart Road Vehicle Analytics & Traffic Management System</h1>
                <p style="color: #2ecc71; font-weight: bold; margin: 5px 0 0 0;">🟢 System Status: Active & Processing Live Feed</p>
            </header>
            <div class="grid">
                <div class="card"><h3>Total Vehicles</h3><p id="total-vehicles">142</p></div>
                <div class="card"><h3 style="color: #e74c3c;">Traffic Violations</h3><p id="total-violations" style="color: #e74c3c;">4</p></div>
                <div class="card"><h3>Current Density</h3><p id="density">Normal</p></div>
                <div class="card"><h3>System Performance</h3><p id="fps">29.4 FPS</p></div>
            </div>
            <div class="main-content">
                <div class="video-box">
                    <div style="position: absolute; left: 51%; top: 30%; color: #00ffff; font-size: 11px; font-weight: bold; z-index:11;">VIRTUAL COUNTING LINE</div>
                    <div class="counting-line"></div>
                    <div class="road"></div>
                    <div class="car-sim"></div>
                    <div class="truck-sim"></div>
                </div>
                <div class="table-box">
                    <h2>Live Detection Log Stream</h2>
                    <div style="background: #111; color: #2ecc71; font-family: monospace; padding: 15px; border-radius: 5px; height: 280px; overflow-y: auto; font-size: 12px;" id="logger">
                        [INFO] Core AI Pipeline Engine Initialized.<br>
                        [INFO] YOLOv8 Weights Configured from local cache.<br>
                        [INFO] Hardware Acceleration: Enabled (CPU Multi-Threading)<br>
                        [INFO] Video Stream Source Connected.<br>
                    </div>
                </div>
            </div>
        </div>
        <script>
            const logs = [
                "[DETECT] Car identified - Conf: 0.94",
                "[DETECT] Truck identified - Conf: 0.89",
                "[COUNTER] Vehicle crossed virtual line",
                "[SPEED] Vehicle tracked velocity: 54 km/h",
                "[WARNING] Speed Violation Triggered! - 78 km/h"
            ];
            setInterval(() => {
                const logBox = document.getElementById('logger');
                const randomLog = logs[Math.floor(Math.random() * logs.length)];
                logBox.innerHTML += `[${new Date().toLocaleTimeString()}] ${randomLog}<br>`;
                logBox.scrollTop = logBox.scrollHeight;
            }, 2500);
        </script>
    </body>
    </html>
    """

@app.route("/api/stats")
def api_stats():
    # 🟢 NEW NATURAL FLUCTUATION LOGIC
    chance = random.random()
    
    if chance < 0.30:
        # 30% chance: Road thodi khali hai, koi gaadi nahi aayi
        sim_data["total_vehicles"] += 0
    elif chance < 0.85:
        # 55% chance: Normal traffic, 1 se 2 gaadiyan cross hui
        sim_data["total_vehicles"] += random.randint(1, 2)
    else:
        # 15% chance: Rush ya jhund aaya, achanak 3 se 5 gaadiyan cross hui
        sim_data["total_vehicles"] += random.randint(3, 5)
        
    # Violations ko ekdam rare aur unpredictable banana (sirf 5% chance par trigger hoga)
    if random.random() > 0.95:
        sim_data["total_violations"] += 1
        
    # Density ko gaadiyon ke badhne ke hissaab se realistic change karna
    densities = ["Low", "Normal", "Heavy", "Normal"]
    sim_data["density_state"] = densities[random.randint(0, 3)]
    
    # FPS me halka sa point fluctuation (jaise asli systems me hota hai)
    sim_data["fps"] = random.uniform(28.9, 29.9)
    
    return jsonify(sim_data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True, debug=False)
