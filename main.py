import os
import logging
import signal
import subprocess
import psutil
import asyncio
import threading
from flask import Flask, request, jsonify, render_template_string
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup, MenuButtonWebApp
from telegram.ext import Application, CommandHandler, ContextTypes
from werkzeug.utils import secure_filename

# --------------------------------------------------------------------------------
# CONFIGURATION
# --------------------------------------------------------------------------------
TOKEN = "YOUR_BOT_TOKEN_HERE"  # আপনার বটের টোকেন দিন
PORT = 8080
BASE_DIR = "user_bots"
if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)

# --------------------------------------------------------------------------------
# FLASK WEB SERVER (THE UI)
# --------------------------------------------------------------------------------
app = Flask(__name__)

# HTML TEMPLATE (The Beautiful Interface)
HTML_UI = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>Nexus Prime Console</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #0a0a0a;
            --card: #161616;
            --primary: #00ff88;
            --danger: #ff0055;
            --text: #e0e0e0;
            --dim: #666;
        }
        body {
            background-color: var(--bg);
            color: var(--text);
            font-family: 'JetBrains Mono', monospace;
            margin: 0;
            padding: 20px;
            -webkit-tap-highlight-color: transparent;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            border-bottom: 1px solid #333;
            padding-bottom: 10px;
        }
        .brand { font-size: 1.2rem; font-weight: bold; color: var(--primary); text-shadow: 0 0 10px rgba(0,255,136,0.3); }
        
        .stats-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-bottom: 20px;
        }
        .card {
            background: var(--card);
            padding: 15px;
            border-radius: 12px;
            border: 1px solid #333;
        }
        .stat-label { font-size: 0.8rem; color: var(--dim); }
        .stat-value { font-size: 1.2rem; font-weight: bold; margin-top: 5px; }
        
        .btn {
            width: 100%;
            padding: 12px;
            border: none;
            border-radius: 8px;
            font-family: inherit;
            font-weight: bold;
            cursor: pointer;
            margin-top: 10px;
            transition: 0.2s;
        }
        .btn-primary { background: var(--primary); color: #000; }
        .btn-danger { background: var(--danger); color: #fff; }
        .btn:active { transform: scale(0.98); }

        .terminal {
            background: #000;
            border: 1px solid #333;
            border-radius: 8px;
            padding: 10px;
            height: 200px;
            overflow-y: auto;
            font-size: 0.8rem;
            color: #ccc;
            margin-top: 20px;
            white-space: pre-wrap;
        }
        .log-entry { margin-bottom: 4px; }
        .log-info { color: #4caf50; }
        .log-err { color: #ff5252; }

        /* Upload Zone */
        .upload-box {
            border: 2px dashed #333;
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            margin-bottom: 20px;
            position: relative;
        }
        .upload-box input {
            position: absolute;
            top: 0; left: 0; width: 100%; height: 100%;
            opacity: 0;
            cursor: pointer;
        }
        .status-dot {
            height: 10px; width: 10px;
            background-color: var(--dim);
            border-radius: 50%;
            display: inline-block;
            margin-right: 5px;
        }
        .running { background-color: var(--primary); box-shadow: 0 0 8px var(--primary); }
    </style>
</head>
<body>
    <div class="header">
        <div class="brand">⚡ NEXUS PRIME</div>
        <div id="user-name">Guest</div>
    </div>

    <div class="stats-grid">
        <div class="card">
            <div class="stat-label">CPU USAGE</div>
            <div class="stat-value" id="cpu">0%</div>
        </div>
        <div class="card">
            <div class="stat-label">RAM USAGE</div>
            <div class="stat-value" id="ram">0%</div>
        </div>
    </div>

    <div class="card">
        <div class="stat-label">STATUS</div>
        <div style="display: flex; align-items: center; margin-top: 10px;">
            <span id="status-dot" class="status-dot"></span>
            <span id="status-text" class="stat-value">Stopped</span>
        </div>
    </div>

    <div class="upload-box">
        <div style="font-size: 2rem;">☁️</div>
        <p>Tap to Upload .py File</p>
        <input type="file" id="fileInput" accept=".py">
    </div>
    <div id="upload-msg" style="text-align: center; color: var(--primary); margin-bottom: 10px;"></div>

    <button class="btn btn-primary" onclick="controlBot('start')">▶ START SERVER</button>
    <button class="btn btn-danger" onclick="controlBot('stop')">⏹ STOP SERVER</button>
    
    <div class="terminal" id="logs">
        <div class="log-entry">> System Ready...</div>
    </div>

    <script>
        let tg = window.Telegram.WebApp;
        tg.expand();
        document.getElementById('user-name').innerText = tg.initDataUnsafe.user ? tg.initDataUnsafe.user.first_name : 'User';
        let userId = tg.initDataUnsafe.user ? tg.initDataUnsafe.user.id : 'demo';

        // File Upload
        document.getElementById('fileInput').addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (!file) return;
            
            const formData = new FormData();
            formData.append('file', file);
            formData.append('user_id', userId);

            document.getElementById('upload-msg').innerText = "Uploading...";
            
            try {
                const res = await fetch('/upload', { method: 'POST', body: formData });
                const data = await res.json();
                document.getElementById('upload-msg').innerText = data.message;
            } catch (err) {
                document.getElementById('upload-msg').innerText = "Upload Failed";
            }
        });

        // Bot Controls
        async function controlBot(action) {
            try {
                const res = await fetch(`/${action}`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ user_id: userId })
                });
                const data = await res.json();
                updateStatus(action === 'start');
            } catch (e) {
                console.log(e);
            }
        }

        function updateStatus(isRunning) {
            const dot = document.getElementById('status-dot');
            const text = document.getElementById('status-text');
            if (isRunning) {
                dot.classList.add('running');
                text.innerText = "Running";
                text.style.color = "var(--primary)";
            } else {
                dot.classList.remove('running');
                text.innerText = "Stopped";
                text.style.color = "var(--text)";
            }
        }

        // Live Updates
        setInterval(async () => {
            // Stats
            const res = await fetch('/stats');
            const stats = await res.json();
            document.getElementById('cpu').innerText = stats.cpu + '%';
            document.getElementById('ram').innerText = stats.ram + '%';

            // Logs
            const logRes = await fetch(`/logs?user_id=${userId}`);
            const logData = await logRes.json();
            const term = document.getElementById('logs');
            if(logData.logs) {
                term.innerText = logData.logs;
                term.scrollTop = term.scrollHeight;
            }
        }, 2000);

    </script>
</body>
</html>
"""

# Global storage for processes
user_processes = {}

@app.route('/')
def index():
    return render_template_string(HTML_UI)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'message': 'No file part'}), 400
    file = request.files['file']
    user_id = request.form.get('user_id')
    
    if file.filename == '':
        return jsonify({'message': 'No selected file'}), 400
    
    if file and user_id:
        user_path = os.path.join(BASE_DIR, str(user_id))
        if not os.path.exists(user_path):
            os.makedirs(user_path)
        
        filename = "bot.py" # Force rename to bot.py for simplicity
        file.save(os.path.join(user_path, filename))
        return jsonify({'message': '✅ Upload Successful!'})
    return jsonify({'message': 'Error'}), 500

@app.route('/start', methods=['POST'])
def start_bot():
    data = request.json
    user_id = str(data.get('user_id'))
    user_path = os.path.join(BASE_DIR, user_id)
    script_path = os.path.join(user_path, "bot.py")

    if not os.path.exists(script_path):
        return jsonify({'status': 'error', 'message': 'No bot file found'}), 404

    if user_id in user_processes:
        return jsonify({'status': 'error', 'message': 'Already running'})

    # Log file
    log_file = open(os.path.join(user_path, "log.txt"), "w")
    
    # Start Process
    proc = subprocess.Popen(
        ["python3", script_path],
        cwd=user_path,
        stdout=log_file,
        stderr=log_file,
        preexec_fn=os.setsid
    )
    
    user_processes[user_id] = {'proc': proc, 'log': log_file}
    return jsonify({'status': 'success'})

@app.route('/stop', methods=['POST'])
def stop_bot():
    data = request.json
    user_id = str(data.get('user_id'))
    
    if user_id in user_processes:
        proc = user_processes[user_id]['proc']
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except:
            pass
        user_processes[user_id]['log'].close()
        del user_processes[user_id]
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error', 'message': 'Not running'})

@app.route('/stats')
def stats():
    return jsonify({
        'cpu': psutil.cpu_percent(),
        'ram': psutil.virtual_memory().percent
    })

@app.route('/logs')
def get_logs():
    user_id = request.args.get('user_id')
    log_path = os.path.join(BASE_DIR, str(user_id), "log.txt")
    if os.path.exists(log_path):
        with open(log_path, 'r') as f:
            return jsonify({'logs': f.read()[-2000:]})
    return jsonify({'logs': '> Waiting for logs...'})

def run_flask():
    app.run(host='0.0.0.0', port=PORT)

# --------------------------------------------------------------------------------
# TELEGRAM BOT
# --------------------------------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # এই URL টি আপনার হোস্টিং URL হবে
    # Render এ হোস্ট করার পর URL টি পাবেন
    # আপাতত এটি ডাইনামিক রাখতে হবে না, ইউজার সেটআপের পর কোডে URL বসাবে
    
    text = (
        "🔥 **NEXUS PRIME HOSTING** 🔥\n\n"
        "Manage your bots with our advanced cloud dashboard.\n"
        "Click the button below to open the console."
    )
    
    # বাটনটি WebApp ওপেন করবে
    kb = [[InlineKeyboardButton("🚀 OPEN CONSOLE", web_app=WebAppInfo(url=f"YOUR_RENDER_URL"))]]
    
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))

def main():
    # Start Flask in thread
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Start Bot
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    
    print("🚀 Nexus Prime System Online...")
    app.run_polling()

if __name__ == '__main__':
    main()
