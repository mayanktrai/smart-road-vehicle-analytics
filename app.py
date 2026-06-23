import random
from flask import Flask, jsonify, render_template_string

app = Flask(__name__)

# Mock Data Storage
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
            body { font-family: 'Segoe UI', sans-serif; background-color: #0f172a; margin: 0; padding: 20px; color: #f8fafc; }
            .container { max-width: 1200px; margin: 0 auto; }
            header { background: linear-gradient(135deg, #1e293b, #334155); color: white; padding: 25px; border-radius: 12px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.3); margin-bottom: 25px; }
            .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 20px; margin: 20px 0; }
            .card { background: #1e293b; padding: 20px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.2); text-align: center; border: 1px solid #334155; }
            .card h3 { margin: 0; color: #94a3b8; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px; }
            .card p { margin: 10px 0 0 0; font-size: 32px; font-weight: bold; color: #38bdf8; }
            .main-content { display: grid; grid-template-columns: 2fr 1fr; gap: 20px; }
            
            /* PREMIUM HIGHWAY CANVAS */
            .video-box { background: #020617; border-radius: 12px; position: relative; height: 420px; overflow: hidden; border: 3px solid #334155; box-shadow: inset 0 0 20px rgba(0,0,0,0.8); }
            
            /* Two-Way Divided Highway */
            .road { position: absolute; width: 100%; height: 240px; background: #1e293b; top: 22%; border-top: 4px dashed #64748b; border-bottom: 4px dashed #64748b; }
            .divider-line { position: absolute; width: 100%; height: 6px; background: #f59e0b; top: 50%; transform: translateY(-50%); z-index: 5; }
            .counting-line { position: absolute; left: 50%; top: 22%; width: 4px; height: 240px; background: #06b6d4; box-shadow: 0 0 15px #06b6d4; z-index: 10; }
            
            /* DYNAMIC VEHICLE STYLES USING EMOJIS */
            .vehicle { position: absolute; display: flex; align-items: center; justify-content: center; z-index: 6; }
            
            /* YOLO Bounding Box style matching emoji size */
            .v-car { width: 55px; height: 35px; border: 2px solid #4ade80; font-size: 24px; border-radius: 4px; }
            .v-truck { width: 75px; height: 42px; border: 2px solid #f87171; font-size: 32px; border-radius: 4px; }
            .v-bike { width: 42px; height: 26px; border: 2px solid #fbbf24; font-size: 20px; border-radius: 4px; }
            .v-cycle { width: 35px; height: 22px; border: 2px solid #38bdf8; font-size: 18px; border-radius: 4px; }
            
            /* AI Labels text on top of bounding box */
            .vehicle::before { position: absolute; top: -20px; left: -2px; color: #000; font-size: 9px; font-weight: bold; padding: 1px 4px; border-radius: 3px; white-space: nowrap; }
            
            @keyframes goLeftToRight {
                0% { left: -150px; }
                100% { left: 105%; }
            }
            @keyframes goRightToLeft {
                0% { left: 105%; }
                100% { left: -150px; }
            }
            
            .table-box { background: #1e293b; padding: 20px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.2); border: 1px solid #334155; }
            h2 { margin-top: 0; color: #f1f5f9; border-bottom: 2px solid #334155; padding-bottom: 10px; font-size: 18px; }
        </style>
        <script>
            let laneOccupied = { 1: false, 2: false, 3: false, 4: false };
            let laneStopped = { 1: false, 2: false, 3: false, 4: false };

            function refreshStats() {
                fetch('/api/stats')
                .then(res => res.json())
                .then(data => {
                    let densityElement = document.getElementById('density');
                    if (laneStopped[1] || laneStopped[3]) {
                        densityElement.innerText = "Heavy (Jam)";
                        densityElement.style.color = "#f87171";
                    } else {
                        densityElement.innerText = data.density_state;
                        densityElement.style.color = "#38bdf8";
                    }
                    document.getElementById('total-vehicles').innerText = data.total_vehicles;
                    document.getElementById('total-violations').innerText = data.total_violations;
                    document.getElementById('fps').innerText = data.fps.toFixed(1);
                }).catch(err => console.log(err));
            }
            setInterval(refreshStats, 2000);
            
            window.onload = function() {
                refreshStats();
                spawnSmartTraffic();
                startOrganicTrafficStopper();
            };

            function spawnSmartTraffic() {
                const roadCanvas = document.getElementById('road-canvas');
                
                // 🟢 MAP SHAPES WITH RELEVANT REAL WORLD EMOTICONS
                const vehicleConfigs = [
                    { class: 'v-car', emoji: '🚘', label: 'Car: 94%' },
                    { class: 'v-truck', emoji: '🚛', label: 'Truck: 89%' },
                    { class: 'v-bike', emoji: '🏍️', label: 'Motorbike: 91%' },
                    { class: 'v-cycle', emoji: '🚲', label: 'Bicycle: 82%' }
                ];

                const laneTops = { 1: 26, 2: 37, 3: 53, 4: 64 };

                function trySpawn() {
                    const lane = Math.floor(Math.random() * 4) + 1;
                    
                    if (laneOccupied[lane]) {
                        setTimeout(trySpawn, 250);
                        return;
                    }

                    laneOccupied[lane] = true; 

                    const config = vehicleConfigs[Math.floor(Math.random() * vehicleConfigs.length)];
                    
                    const el = document.createElement('div');
                    el.className = `vehicle ${config.class}`;
                    el.innerHTML = config.emoji; // Set Shape
                    el.style.top = `${laneTops[lane]}%`;
                    
                    const isLeftToRight = (lane === 1 || lane === 2);
                    const speed = (Math.random() * 1.5 + 3.0).toFixed(2);
                    
                    if (isLeftToRight) {
                        el.style.animation = `goLeftToRight ${speed}s linear forwards`;
                        el.dataset.dir = "ltr";
                        // Facing right side naturally
                        el.style.transform = "scaleX(-1)"; 
                        if(laneStopped[1]) el.style.animationPlayState = 'paused';
                    } else {
                        el.style.animation = `goRightToLeft ${speed}s linear forwards`;
                        el.dataset.dir = "rtl";
                        // Facing left side naturally
                        el.style.transform = "scaleX(1)"; 
                        if(laneStopped[3]) el.style.animationPlayState = 'paused';
                    }
                    
                    el.dataset.lane = lane;

                    let tagColor = '#4ade80';
                    let labelText = config.label;
                    if(config.class === 'v-truck' && Math.random() > 0.8) {
                        labelText = 'Truck: Speeding';
                        tagColor = '#f87171';
                        el.style.border = '2px solid #f87171';
                    }
                    
                    // Create distinct bounding box label classes dynamically
                    const styleId = 'sheet-' + Math.random().toString(36).substr(2, 9);
                    const style = document.createElement('style');
                    style.id = styleId;
                    style.innerHTML = `.${styleId}::before { content: "${labelText}"; background: ${tagColor}; transform: scaleX(${isLeftToRight ? '-1' : '1'}); }`;
                    document.head.appendChild(style);
                    el.classList.add(styleId);

                    roadCanvas.appendChild(el);

                    setTimeout(() => { laneOccupied[lane] = false; }, speed * 500); 

                    setTimeout(() => {
                        el.remove();
                        style.remove();
                    }, speed * 1000);

                    let nextSpawnDelay = Math.floor(Math.random() * 800) + 400; 
                    setTimeout(trySpawn, nextSpawnDelay);
                }
                trySpawn();
            }

            function startOrganicTrafficStopper() {
                setInterval(() => {
                    const actionRoll = Math.random();
                    const vehicles = document.querySelectorAll('.vehicle');
                    const duration = Math.floor(Math.random() * 2000) + 2000;
                    
                    if (actionRoll < 0.15 && !laneStopped[3]) {
                        laneStopped[1] = true; laneStopped[2] = true;
                        vehicles.forEach(v => { if(v.dataset.dir === "ltr") v.style.animationPlayState = 'paused'; });
                        setTimeout(() => {
                            laneStopped[1] = false; laneStopped[2] = false;
                            document.querySelectorAll('.vehicle').forEach(v => { if(v.dataset.dir === "ltr") v.style.animationPlayState = 'running'; });
                        }, duration);
                    } 
                    else if (actionRoll > 0.85 && !laneStopped[1]) {
                        laneStopped[3] = true; laneStopped[4] = true;
                        vehicles.forEach(v => { if(v.dataset.dir === "rtl") v.style.animationPlayState = 'paused'; });
                        setTimeout(() => {
                            laneStopped[3] = false; laneStopped[4] = false;
                            document.querySelectorAll('.vehicle').forEach(v => { if(v.dataset.dir === "rtl") v.style.animationPlayState = 'running'; });
                        }, duration);
                    }
                }, 9000);
            }
        </script>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>Road Vehicle Analytics System</h1>
                <p style="color: #4ade80; font-weight: bold; margin: 5px 0 0 0; letter-spacing: 0.5px;">🟢 AI Core Engine: Running Asynchronous Inference</p>
            </header>
            <div class="grid">
                <div class="card"><h3>Total Vehicles</h3><p id="total-vehicles">142</p></div>
                <div class="card"><h3 style="color: #f87171;">Traffic Violations</h3><p id="total-violations" style="color: #f87171;">4</p></div>
                <div class="card"><h3>Current Density</h3><p id="density">Normal</p></div>
                <div class="card"><h3>System Performance</h3><p id="fps">29.4 FPS</p></div>
            </div>
            <div class="main-content">
                <div class="video-box" id="road-canvas">
                    <div style="position: absolute; left: 51%; top: 15%; color: #06b6d4; font-size: 11px; font-weight: bold; z-index:11; letter-spacing: 1px;">VIRTUAL COUNTING LINE</div>
                    <div class="counting-line"></div>
                    <div class="road"></div>
                    <div class="divider-line"></div>
                </div>
                <div class="table-box">
                    <h2>Live Inference Log Stream</h2>
                    <div style="background: #020617; color: #4ade80; font-family: monospace; padding: 15px; border-radius: 8px; height: 300px; overflow-y: auto; font-size: 12px; border: 1px solid #334155;" id="logger">
                        [INFO] Core AI Pipeline Engine Initialized.<br>
                        [INFO] YOLOv8 Weights Configured from local cache.<br>
                        [INFO] Hardware Acceleration: Enabled (GPU Multi-Threading)<br>
                        [INFO] Video Stream Source Connected.<br>
                    </div>
                </div>
            </div>
        </div>
        <script>
            const logs = [
                "[DETECT] Car identified - Conf: 0.94",
                "[DETECT] Truck identified - Conf: 0.89",
                "[DETECT] Motorbike identified - Conf: 0.91",
                "[DETECT] Bicycle identified - Conf: 0.82",
                "[COUNTER] Vehicle crossed virtual line",
                "[SPEED] Vehicle tracked velocity: 48 km/h",
                "[WARNING] Speed Violation Triggered! - 84 km/h"
            ];
            setInterval(() => {
                const logBox = document.getElementById('logger');
                const randomLog = logs[Math.floor(Math.random() * logs.length)];
                logBox.innerHTML += `[${new Date().toLocaleTimeString()}] ${randomLog}<br>`;
                logBox.scrollTop = logBox.scrollHeight;
            }, 1800);
        </script>
    </body>
    </html>
    """

@app.route("/api/stats")
def api_stats():
    chance = random.random()
    if chance < 0.35:
        sim_data["total_vehicles"] += 0
    elif chance < 0.85:
        sim_data["total_vehicles"] += random.randint(1, 2)
    else:
        sim_data["total_vehicles"] += random.randint(3, 4)
        
    if random.random() > 0.94:
        sim_data["total_violations"] += 1
        
    densities = ["Low", "Normal", "Heavy", "Normal"]
    sim_data["density_state"] = densities[random.randint(0, 3)]
    sim_data["fps"] = random.uniform(28.9, 29.9)
    return jsonify(sim_data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True, debug=False)
