import os
import logging
import signal
import subprocess
import psutil
import asyncio
import threading
from flask import Flask, request, jsonify, render_template_string
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
from werkzeug.utils import secure_filename

# --------------------------------------------------------------------------------
# CONFIGURATION
# --------------------------------------------------------------------------------
# টোকেন এখন অটোমেটিক Render এর Environment Variable থেকে নিবে
TOKEN = os.getenv("TOKEN") 
PORT = 8080
BASE_DIR = "user_bots"
if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)

# --------------------------------------------------------------------------------
# FLASK WEB SERVER (THE ULTRA UI)
# --------------------------------------------------------------------------------
app = Flask(__name__)

# HTML TEMPLATE (Sci-Fi Cyberpunk Design)
HTML_UI = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>NEXUS ULTRA</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;700&family=Fira+Code:wght@400&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #00f3ff;
            --secondary: #bc13fe;
            --bg-dark: #050505;
            --glass: rgba(255, 255, 255, 0.05);
            --border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        * { box-sizing: border-box; }

        body {
            background-color: var(--bg-dark);
            background-image: 
                radial-gradient(circle at 10% 20%, rgba(0, 243, 255, 0.1) 0%, transparent 20%),
                radial-gradient(circle at 90% 80%, rgba(188, 19, 254, 0.1) 0%, transparent 20%);
            color: #fff;
            font-family: 'Rajdhani', sans-serif;
            margin: 0;
            padding: 20px;
            height: 100vh;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }

        /* Animated Background Grid */
        body::before {
            content: "";
            position: absolute;
            top: 0; left: 0; width: 200%; height: 200%;
            background: linear-gradient(transparent 0%, rgba(0, 243, 255, 0.05) 2%, transparent 3%),
                        linear-gradient(90deg, transparent 0%, rgba(188, 19, 254, 0.05) 2%, transparent 3%);
            background-size: 50px 50px;
            animation: gridMove 20s linear infinite;
            z-index: -1;
            opacity: 0.3;
        }

        @keyframes gridMove {
            0% { transform: translate(0, 0); }
            100% { transform: translate(-50px, -50px); }
        }

        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 25px;
            padding-bottom: 15px;
            border-bottom: 1px solid rgba(0, 243, 255, 0.3);
            box-shadow: 0 10px 20px -10px rgba(0, 243, 255, 0.1);
        }

        .brand {
            font-size: 1.8rem;
            font-weight: 700;
            letter-spacing: 2px;
            background: linear-gradient(90deg, var(--primary), #fff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-shadow: 0 0 15px rgba(0, 243, 255, 0.5);
        }

        .user-badge {
            font-size: 0.9rem;
            background: rgba(0, 243, 255, 0.1);
            padding: 5px 10px;
            border-radius: 20px;
            border: 1px solid var(--primary);
            color: var(--primary);
        }

        /* Stats Cards */
        .stats-container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-bottom: 20px;
        }

        .card {
            background: var(--glass);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border: var(--border);
            border-radius: 15px;
            padding: 15px;
            position: relative;
            overflow: hidden;
            transition: transform 0.3s;
        }
        
        .card:hover { transform: translateY(-3px); }

        .card::after {
            content: "";
            position: absolute;
            top: 0; left: 0; width: 3px; height: 100%;
            background: var(--primary);
            box-shadow: 0 0 10px var(--primary);
        }

        .stat-label {
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: rgba(255,255,255,0.6);
            margin-bottom: 5px;
        }

        .stat-value {
            font-size: 1.5rem;
            font-weight: bold;
            font-family: 'Fira Code', monospace;
        }

        /* Status Indicator */
        .status-box {
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: rgba(0, 0, 0, 0.4);
            padding: 10px 15px;
            border-radius: 10px;
            border: 1px solid #333;
            margin-bottom: 20px;
        }

        .status-indicator {
            width: 12px; height: 12px;
            border-radius: 50%;
            background: #333;
            box-shadow: 0 0 0 #000;
            transition: 0.3s;
        }
        .status-indicator.active {
            background: var(--primary);
            box-shadow: 0 0 15px var(--primary);
        }

        /* Upload Area */
        .upload-zone {
            border: 2px dashed rgba(255,255,255,0.2);
            border-radius: 15px;
            padding: 30px;
            text-align: center;
            transition: 0.3s;
            position: relative;
            background: rgba(0,0,0,0.2);
            margin-bottom: 20px;
        }

        .upload-zone:hover {
            border-color: var(--secondary);
            background: rgba(188, 19, 254, 0.05);
        }

        .upload-zone input {
            position: absolute;
            width: 100%; height: 100%;
            top: 0; left: 0;
            opacity: 0;
            cursor: pointer;
        }

        .upload-icon { font-size: 2rem; margin-bottom: 10px; display: block; }

        /* Buttons */
        .btn-group { display: flex; gap: 10px; margin-bottom: 20px; }
        
        .btn {
            flex: 1;
            padding: 15px;
            border: none;
            border-radius: 10px;
            font-family: 'Rajdhani', sans-serif;
            font-weight: 700;
            font-size: 1rem;
            text-transform: uppercase;
            cursor: pointer;
            transition: 0.3s;
            color: #000;
        }

        .btn-start {
            background: var(--primary);
            box-shadow: 0 0 20px rgba(0, 243, 255, 0.3);
        }
        .btn-start:hover { box-shadow: 0 0 30px rgba(0, 243, 255, 0.6); }

        .btn-stop {
            background: var(--secondary);
            color: #fff;
            box-shadow: 0 0 20px rgba(188, 19, 254, 0.3);
        }

        /* Terminal */
        .terminal-window {
            background: #0a0a0a;
            border: 1px solid #333;
            border-radius: 10px;
            flex-grow: 1;
            padding: 15px;
            font-family: 'Fira Code', monospace;
            font-size: 0.8rem;
            color: #0f0;
            overflow-y: auto;
            box-shadow: inset 0 0 20px #000;
            position: relative;
        }
        
        .terminal-window::before {
            content: "SYSTEM_LOGS_V2.0";
            position: absolute;
            top: 5px; right: 10px;
            font-size: 0.6rem;
            color: #555;
        }

        .log-line { margin-bottom: 5px; opacity: 0; animation: fadeIn 0.3s forwards; }
        @keyframes fadeIn { to { opacity: 1; } }

    </style>
</head>
<body>
    <div class="header">
        <div class="brand">NEXUS ULTRA</div>
        <div class="user-badge" id="username">Guest</div>
    </div>

    <div class="stats-container">
        <div class="card">
            <div class="stat-label">CPU Load</div>
            <div class="stat-value" id="cpu" style="color: var(--primary)">0%</div>
        </div>
        <div class="card" style="--primary: var(--secondary)">
            <div class="stat-label">RAM Usage</div>
            <div class="stat-value" id="ram" style="color: var(--secondary)">0%</div>
        </div>
    </div>

    <div class="status-box">
        <span style="font-weight: bold; color: #aaa;">SYSTEM STATUS</span>
        <div style="display: flex; align-items: center; gap: 10px;">
            <span id="status-text" style="font-size: 0.9rem;">OFFLINE</span>
            <div class="status-indicator" id="status-dot"></div>
        </div>
    </div>

    <div class="upload-zone" id="drop-zone">
        <span class="upload-icon">☁️</span>
        <strong>UPLOAD PYTHON BOT</strong>
        <div style="font-size: 0.8rem; color: #888; margin-top: 5px;">Tap to select .py file</div>
        <input type="file" id="fileInput" accept=".py">
    </div>

    <div class="btn-group">
        <button class="btn btn-start" onclick="control('start')">INITIALIZE</button>
        <button class="btn btn-stop" onclick="control('stop')">TERMINATE</button>
    </div>

    <div class="terminal-window" id="terminal">
        <div class="log-line">> Connecting to Neural Cloud...</div>
        <div class="log-line">> Waiting for user input...</div>
    </div>

    <script>
        const tg = window.Telegram.WebApp;
        tg.expand();
        tg.enableClosingConfirmation();

        // User Setup
        document.getElementById('username').innerText = tg.initDataUnsafe.user?.first_name || 'Commander';
        const userId = tg.initDataUnsafe.user?.id || 'demo_user';

        // UI Feedback
        function log(msg, type='info') {
            const term = document.getElementById('terminal');
            const line = document.createElement('div');
            line.className = 'log-line';
            line.style.color = type === 'err' ? '#ff0055' : '#00f3ff';
            line.innerText = `> ${msg}`;
            term.appendChild(line);
            term.scrollTop = term.scrollHeight;
        }

        // File Upload
        document.getElementById('fileInput').addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if(!file) return;

            log(`Uploading module: ${file.name}...`);
            const formData = new FormData();
            formData.append('file', file);
            formData.append('user_id', userId);

            try {
                const res = await fetch('/upload', { method: 'POST', body: formData });
                const data = await res.json();
                log(data.message);
                if(res.ok) document.getElementById('drop-zone').style.borderColor = '#00f3ff';
            } catch (e) {
                log("Upload protocol failed.", 'err');
            }
        });

        // Controls
        async function control(action) {
            log(`Executing command: ${action.toUpperCase()}...`);
            try {
                const res = await fetch(`/${action}`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ user_id: userId })
                });
                const data = await res.json();
                
                if(data.status === 'success') {
                    log(`Command executed successfully.`);
                    updateStatus(action === 'start');
                } else {
                    log(`Error: ${data.message}`, 'err');
                }
            } catch (e) {
                log("Connection lost.", 'err');
            }
        }

        function updateStatus(active) {
            const dot = document.getElementById('status-dot');
            const text = document.getElementById('status-text');
            if(active) {
                dot.classList.add('active');
                text.innerText = "SYSTEM ONLINE";
                text.style.color = "#00f3ff";
                text.style.textShadow = "0 0 10px #00f3ff";
            } else {
                dot.classList.remove('active');
                text.innerText = "OFFLINE";
                text.style.color = "#aaa";
                text.style.textShadow = "none";
            }
        }

        // Live Polling
        setInterval(async () => {
            // Stats
            try {
                const sRes = await fetch('/stats');
                const stats = await sRes.json();
                document.getElementById('cpu').innerText = stats.cpu + '%';
                document.getElementById('ram').innerText = stats.ram + '%';
            } catch(e) {}

            // Logs
            try {
                const lRes = await fetch(`/logs?user_id=${userId}`);
                const lData = await lRes.json();
                if(lData.logs && lData.logs.length > 10) {
                    const term = document.getElementById('terminal');
                    // Clear and update logic could be smarter, but simple append for now
                    // For this demo, we just show the latest chunk if it's new
                    // In real app, we'd append only new lines.
                }
            } catch(e) {}
        }, 2000);
    </script>
</body>
</html>
"""

# Global Process Storage
user_processes = {}

# FLASK ROUTES
@app.route('/')
def index():
    return render_template_string(HTML_UI)

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files: return jsonify({'message': 'No file'}), 400
    file = request.files['file']
    user_id = request.form.get('user_id')
    
    if file and user_id:
        path = os.path.join(BASE_DIR, str(user_id))
        if not os.path.exists(path): os.makedirs(path)
        file.save(os.path.join(path, "bot.py"))
        return jsonify({'message': '✅ Module installed successfully.'})
    return jsonify({'message': 'Upload failed'}), 500

@app.route('/start', methods=['POST'])
def start_bot():
    user_id = str(request.json.get('user_id'))
    path = os.path.join(BASE_DIR, user_id)
    script = os.path.join(path, "bot.py")
    
    if not os.path.exists(script): return jsonify({'status': 'error', 'message': 'No bot found'})
    if user_id in user_processes: return jsonify({'status': 'error', 'message': 'Already active'})

    log_file = open(os.path.join(path, "log.txt"), "w")
    proc = subprocess.Popen(["python3", script], cwd=path, stdout=log_file, stderr=log_file, preexec_fn=os.setsid)
    user_processes[user_id] = {'proc': proc, 'log': log_file}
    return jsonify({'status': 'success'})

@app.route('/stop', methods=['POST'])
def stop_bot():
    user_id = str(request.json.get('user_id'))
    if user_id in user_processes:
        try: os.killpg(os.getpgid(user_processes[user_id]['proc'].pid), signal.SIGTERM)
        except: pass
        user_processes[user_id]['log'].close()
        del user_processes[user_id]
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error', 'message': 'Not active'})

@app.route('/stats')
def stats():
    return jsonify({'cpu': psutil.cpu_percent(), 'ram': psutil.virtual_memory().percent})

@app.route('/logs')
def logs():
    user_id = request.args.get('user_id')
    try:
        with open(os.path.join(BASE_DIR, str(user_id), "log.txt"), 'r') as f:
            return jsonify({'logs': f.read()[-1000:]})
    except: return jsonify({'logs': ''})

def run_flask():
    app.run(host='0.0.0.0', port=PORT)

# --------------------------------------------------------------------------------
# TELEGRAM BOT SETUP
# --------------------------------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Render URL টি নিজে থেকে ডিটেক্ট করা কঠিন, তাই ইউজারকে এটি ম্যানুয়ালি সেট করতে হবে
    # কিন্তু এই মেসেজটি সুন্দর হবে
    
    render_url = "YOUR_RENDER_URL_HERE" # আপনার রেন্ডার লিঙ্কটি এখানে দিন
    
    text = (
        "🌌 **NEXUS ULTRA HOSTING** 🌌\n"
        "──────────────────────\n"
        "Access the Neural Cloud Dashboard to manage your bots.\n"
        "Advanced Graphic Interface Loaded."
    )
    
    kb = [[InlineKeyboardButton("🚀 INITIALIZE SYSTEM", web_app=WebAppInfo(url=render_url))]]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))

def main():
    if not TOKEN:
        print("Error: TOKEN not found in Environment Variables!")
        return

    threading.Thread(target=run_flask, daemon=True).start()
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    
    print("🚀 Nexus Ultra System Online...")
    app.run_polling()

if __name__ == '__main__':
    main()
