import os
import json
import sys
import time
from flask import Flask, request, jsonify, session, Response

# --- Configuration ---
RELAY_PINS = [17, 27, 22, 23] 
DATA_FILE = 'xlr_config.json'
PIN_CODE = "1234"
SECRET_KEY = os.urandom(24)

# --- Hardware Abstraction ---
try:
    import RPi.GPIO as GPIO
    HARDWARE_PRESENT = True
    print("✅ RPi.GPIO detected. Running in HARDWARE mode.")
except (ImportError, RuntimeError):
    HARDWARE_PRESENT = False
    print("⚠️  RPi.GPIO not found. Running in SIMULATION mode.")

class RelayController:
    def __init__(self, pins):
        self.pins = pins
        self.channels = []
        self.load_state()
        if HARDWARE_PRESENT:
            try:
                GPIO.setmode(GPIO.BCM)
                GPIO.setwarnings(False)
                for ch in self.channels:
                    GPIO.setup(ch['pin'], GPIO.OUT)
                    # Logic: Active(True)=LOW, Muted(False)=HIGH
                    GPIO.output(ch['pin'], GPIO.LOW if ch['active'] else GPIO.HIGH)
            except Exception as e:
                print(f"Hardware init error: {e}")

    def load_state(self):
        defaults = [
            {'id': 0, 'name': 'Speaker', 'active': True, 'pin': self.pins[0], 'color': '#3b82f6'},
            {'id': 1, 'name': 'Reader',  'active': True, 'pin': self.pins[1], 'color': '#10b981'},
            {'id': 2, 'name': 'Left',    'active': True, 'pin': self.pins[2], 'color': '#f59e0b'},
            {'id': 3, 'name': 'Right',   'active': True, 'pin': self.pins[3], 'color': '#8b5cf6'},
        ]
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r') as f:
                    saved = json.load(f)
                    if len(saved) == len(defaults):
                        self.channels = saved
                        for i, ch in enumerate(self.channels):
                            ch['pin'] = self.pins[i]
                            ch['active'] = True # Force Unmute on boot
                            if 'color' not in ch: ch['color'] = defaults[i]['color']
                        return
            except: pass
        self.channels = defaults

    def save_state(self):
        try:
            with open(DATA_FILE, 'w') as f:
                json.dump(self.channels, f, indent=4)
        except: pass

    def set_channel(self, cid, state):
        if 0 <= cid < len(self.channels):
            self.channels[cid]['active'] = state
            if HARDWARE_PRESENT:
                GPIO.output(self.channels[cid]['pin'], GPIO.LOW if state else GPIO.HIGH)
            self.save_state()
            return True
        return False

    def update_channel(self, cid, name, color):
        if 0 <= cid < len(self.channels):
            self.channels[cid]['name'] = name
            self.channels[cid]['color'] = color
            self.save_state()
            return True
        return False

    def set_all(self, state):
        for ch in self.channels:
            ch['active'] = state
            if HARDWARE_PRESENT:
                GPIO.output(ch['pin'], GPIO.LOW if state else GPIO.HIGH)
        self.save_state()

controller = RelayController(RELAY_PINS)
app = Flask(__name__)
app.secret_key = SECRET_KEY

# --- ICONS (SVG Paths) ---
IC_SLIDERS = "M496 384H160v-16c0-8.8-7.2-16-16-16h-32c-8.8 0-16 7.2-16 16v16H16c-8.8 0-16 7.2-16 16v32c0 8.8 7.2 16 16 16h80v16c0 8.8 7.2 16 16 16h32c8.8 0 16-7.2 16-16v-16h336c8.8 0 16-7.2 16-16v-32c0-8.8-7.2-16-16-16zm0-160h-80v-16c0-8.8-7.2-16-16-16h-32c-8.8 0-16 7.2-16 16v16H16c-8.8 0-16 7.2-16 16v32c0 8.8 7.2 16 16 16h336v16c0 8.8 7.2 16 16 16h32c8.8 0 16-7.2 16-16v-16h80c8.8 0 16-7.2 16-16v-32c0-8.8-7.2-16-16-16zm0-160H288V48c0-8.8-7.2-16-16-16h-32c-8.8 0-16 7.2-16 16v16H16C7.2 64 0 71.2 0 80v32c0 8.8 7.2 16 16 16h208v16c0 8.8 7.2 16 16 16h32c8.8 0 16-7.2 16-16v-16h208c8.8 0 16-7.2 16-16V80c0-8.8-7.2-16-16-16z"
IC_COG = "M487.4 315.7l-42.6-24.6c4.3-23.2 4.3-47 0-70.2l42.6-24.6c4.9-2.8 7.1-8.6 5.5-14-11.1-35.6-30-67.8-54.7-94.6-3.8-4.1-10-5.1-14.8-2.3L380.8 110c-17.9-15.4-38.5-27.3-60.8-35.1V25.8c0-5.6-3.9-10.5-9.4-11.7-36.7-8.2-74.3-7.8-109.2 0-5.5 1.2-9.4 6.1-9.4 11.7V75c-22.2 7.9-42.8 19.8-60.8 35.1L88.7 85.5c-4.9-2.8-11-1.9-14.8 2.3-24.7 26.7-43.6 58.9-54.7 94.6-1.7 5.4.6 11.2 5.5 14L67.3 221c-4.3 23.2-4.3 47 0 70.2l-42.6 24.6c-4.9 2.8-7.1 8.6-5.5 14 11.1 35.6 30 67.8 54.7 94.6 3.8 4.1 10 5.1 14.8 2.3l42.6-24.6c17.9 15.4 38.5 27.3 60.8 35.1v49.2c0 5.6 3.9 10.5 9.4 11.7 36.7 8.2 74.3 7.8 109.2 0 5.5-1.2 9.4-6.1 9.4-11.7v-49.2c22.2-7.9 42.8-19.8 60.8-35.1l42.6 24.6c4.9 2.8 11 1.9 14.8-2.3 24.7-26.7 43.6-58.9 54.7-94.6 1.5-5.5-.7-11.3-5.6-14.1zM256 336c-44.1 0-80-35.9-80-80s35.9-80 80-80 80 35.9 80 80-35.9 80-80 80z"
IC_MUTE = "M215.03 71.05L126.06 160H24c-13.26 0-24 10.74-24 24v144c0 13.25 10.74 24 24 24h102.06l88.97 88.95c15.03 15.03 40.97 4.47 40.97-16.97V88.02c0-21.46-25.96-31.98-40.97-16.97zM461.64 272l-56.57 56.57c-6.25 6.25-6.25 16.38 0 22.63l22.63 22.63c6.25 6.25 16.38 6.25 22.63 0L506.9 317.29c6.25-6.25 6.25-16.38 0-22.63L450.34 238.1c-6.25-6.25-16.38-6.25-22.63 0l-22.63 22.63c-6.25 6.25-6.25 16.38 0 22.63L461.64 272zm0-96l45.25-45.25c6.25-6.25 6.25-16.38 0-22.63l-22.63-22.63c-6.25-6.25-16.38-6.25-22.63 0L405.07 130.71c-6.25 6.25-6.25 16.38 0 22.63l56.57 56.57c6.25 6.25 16.38 6.25 22.63 0l22.63-22.63c6.25-6.25 6.25-16.38 0-22.63L461.64 176z"
IC_UNMUTE = "M215.03 71.05L126.06 160H24c-13.26 0-24 10.74-24 24v144c0 13.25 10.74 24 24 24h102.06l88.97 88.95c15.03 15.03 40.97 4.47 40.97-16.97zm233.32-51.08c-11.17-7.33-26.18-4.24-33.51 6.95-7.34 11.17-4.22 26.18 6.95 33.51 66.27 43.55 105.81 116.88 106.2 195.99.48 78.72-38.62 151.51-103.77 195.46-11.07 7.47-14.01 22.47-6.55 33.53 7.47 11.07 22.45 14.03 33.53 6.55 79.41-53.59 127.05-142.28 126.46-238.23-.49-96.42-48.66-185.79-129.31-233.76zM400 128c-8.37 0-16.17 3.2-22.06 9.09L372.7 142.3c-11.86 11.86-12.06 30.91-.59 43.06 36.77 38.95 36.63 98.39 0 137.34-11.53 12.2-11.26 31.32.62 43.2l5.23 5.23c5.88 5.88 13.69 9.1 22.05 9.1 8.34 0 16.14-3.19 22.05-9.08 62.9-62.43 63.19-162.99 0-225.92-11.92-11.92-31.23-11.92-43.15 0l-5.17 5.17c-5.89-5.91-13.68-9.11-22.05-9.11z"
IC_TIMES = "M242.72 256l100.07-100.07c12.28-12.28 12.28-32.19 0-44.48l-22.24-22.24c-12.28-12.28-32.19-12.28-44.48 0L176 189.28 75.93 89.21c-12.28-12.28-32.19-12.28-44.48 0L9.21 111.45c-12.28 12.28-12.28 32.19 0 44.48L109.28 256 9.21 356.07c-12.28 12.28-12.28 32.19 0 44.48l22.24 22.24c12.28 12.28 32.19 12.28 44.48 0L176 322.72l100.07 100.07c12.28 12.28 32.19 12.28 44.48 0l22.24-22.24c12.28-12.28 12.28-32.19 0-44.48L242.72 256z"

# --- SHARED CSS ---
# Standard python string, double braces {{ }} not needed because we won't use render_template
CSS = """
<style>
    :root { --bg: #0f172a; --card: #1e293b; --txt: #f1f5f9; --mut: #94a3b8; --acc: #3b82f6; --err: #ef4444; }
    * { box-sizing: border-box; }
    body { background: var(--bg); color: var(--txt); font-family: system-ui, sans-serif; margin: 0; padding: 20px; min-height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; }
    
    /* Login */
    .pin-dots { display: flex; gap: 15px; margin-bottom: 30px; justify-content: center; }
    .dot { width: 16px; height: 16px; border-radius: 50%; background: #334155; border: 1px solid #475569; transition: 0.2s; }
    .dot.active { background: var(--acc); box-shadow: 0 0 10px var(--acc); border-color: transparent; }
    .dot.err { background: var(--err); animation: shake 0.3s; }
    @keyframes shake { 0%, 100% {transform: translate(0);} 25% {transform: translate(-5px);} 75% {transform: translate(5px);} }
    
    .keypad { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; max-width: 300px; margin: 0 auto; }
    .key { width: 70px; height: 70px; border-radius: 50%; background: var(--card); border: 1px solid #334155; display: flex; align-items: center; justify-content: center; font-size: 1.5rem; cursor: pointer; user-select: none; transition: 0.1s; }
    .key:active { background: var(--acc); border-color: var(--acc); transform: scale(0.95); }

    /* App */
    .container { width: 100%; max-width: 800px; background: var(--card); border-radius: 16px; border: 1px solid #334155; overflow: hidden; margin-top: 20px; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.5); }
    .header { padding: 20px; border-bottom: 1px solid #334155; display: flex; justify-content: space-between; align-items: center; }
    .header h1 { margin: 0; font-size: 1.2rem; display: flex; align-items: center; gap: 10px; }
    
    .btn-icon { background: transparent; border: none; color: var(--mut); cursor: pointer; padding: 8px; border-radius: 8px; transition: 0.2s; }
    .btn-icon:hover, body.edit .btn-icon { color: white; background: #334155; }
    body.edit .btn-icon { color: var(--acc); }

    .master-controls { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; padding: 16px; background: #162032; border-bottom: 1px solid #334155; }
    .btn-master { padding: 15px; border-radius: 12px; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; font-size: 0.85rem; cursor: pointer; border: 1px solid transparent; transition: 0.2s; display: flex; align-items: center; justify-content: center; gap: 10px; }
    
    .btn-mute { background: rgba(239, 68, 68, 0.15); color: #f87171; border-color: rgba(239, 68, 68, 0.3); }
    .btn-mute:hover { background: #ef4444; color: white; }
    
    .btn-unmute { background: rgba(16, 185, 129, 0.15); color: #34d399; border-color: rgba(16, 185, 129, 0.3); }
    .btn-unmute:hover { background: #10b981; color: white; }

    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 15px; padding: 20px; }
    
    .card { background: #0f172a80; border: 2px solid #334155; border-radius: 12px; padding: 15px; height: 100px; display: flex; align-items: center; justify-content: space-between; cursor: pointer; position: relative; overflow: hidden; transition: 0.2s; }
    .card-left { display: flex; align-items: center; gap: 15px; }
    .icon-box { width: 45px; height: 45px; border-radius: 50%; display: flex; align-items: center; justify-content: center; border: 1px solid #475569; }
    .status { font-size: 0.7rem; font-weight: bold; margin-top: 4px; display: flex; align-items: center; gap: 5px; }
    .status-dot { width: 6px; height: 6px; border-radius: 50%; }
    
    .toggle { width: 46px; height: 26px; border-radius: 20px; background: #334155; padding: 2px; transition: 0.3s; }
    .thumb { width: 22px; height: 22px; background: white; border-radius: 50%; transition: 0.3s; }
    .color-bar { position: absolute; bottom: 0; left: 0; right: 0; height: 5px; opacity: 0.5; }

    /* Edit Mode */
    body.edit .card { border-style: dashed; animation: pulse 2s infinite; }
    body.edit .toggle { opacity: 0.2; }
    @keyframes pulse { 0% { border-color: #334155; } 50% { border-color: #64748b; } 100% { border-color: #334155; } }
    .edit-overlay-icon { position: absolute; top: 8px; right: 8px; opacity: 0; transition: 0.2s; background: var(--card); border: 1px solid #475569; border-radius: 50%; padding: 4px; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; }
    body.edit .edit-overlay-icon { opacity: 1; }

    /* Modal */
    .modal { position: fixed; inset: 0; background: #000c; backdrop-filter: blur(5px); display: flex; align-items: center; justify-content: center; opacity: 0; pointer-events: none; transition: 0.2s; z-index: 100; }
    .modal.open { opacity: 1; pointer-events: auto; }
    .modal-box { background: var(--card); width: 90%; max-width: 350px; padding: 20px; border-radius: 12px; border: 1px solid #334155; transform: scale(0.95); transition: 0.2s; }
    .modal.open .modal-box { transform: scale(1); }
    input { width: 100%; background: var(--bg); border: 1px solid #334155; color: white; padding: 10px; border-radius: 8px; margin-bottom: 15px; }
    .colors { display: grid; grid-template-columns: repeat(6, 1fr); gap: 8px; margin-bottom: 20px; }
    .swatch { aspect-ratio: 1; border-radius: 50%; cursor: pointer; border: 2px solid transparent; }
    .swatch.sel { border-color: white; box-shadow: 0 0 8px white; }
    .btns { display: flex; justify-content: flex-end; gap: 10px; }
    button { padding: 8px 16px; border-radius: 6px; border: none; cursor: pointer; font-weight: bold; }
    .btn-save { background: var(--acc); color: white; }
    .btn-cancel { background: transparent; color: var(--mut); }

    #demo { position: fixed; top: 0; left: 0; width: 100%; background: #d97706; color: white; text-align: center; padding: 5px; font-size: 0.8rem; display: none; z-index: 50; }
    .icon { width: 20px; height: 20px; fill: currentColor; }
    .icon-lg { width: 24px; height: 24px; fill: currentColor; }
    .icon-xl { width: 28px; height: 28px; fill: currentColor; }
    .conn-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--mut); margin-left: 10px; }
    .conn-dot.online { background: #10b981; box-shadow: 0 0 8px #10b981; }
    .conn-dot.offline { background: #ef4444; }
</style>
"""

# --- HTML TEMPLATES ---
LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KH XLR Switcher - Login</title>
    __CSS__
</head>
<body>
    <h2 style="margin-bottom: 20px;">SECURITY ACCESS</h2>
    <div class="pin-dots">
        <div class="dot" id="d1"></div><div class="dot" id="d2"></div><div class="dot" id="d3"></div><div class="dot" id="d4"></div>
    </div>
    <div class="keypad">
        <div class="key" onclick="k(1)">1</div><div class="key" onclick="k(2)">2</div><div class="key" onclick="k(3)">3</div>
        <div class="key" onclick="k(4)">4</div><div class="key" onclick="k(5)">5</div><div class="key" onclick="k(6)">6</div>
        <div class="key" onclick="k(7)">7</div><div class="key" onclick="k(8)">8</div><div class="key" onclick="k(9)">9</div>
        <div class="key" onclick="clr()" style="color:var(--err); font-size:1rem;">CLR</div>
        <div class="key" onclick="k(0)">0</div>
    </div>
    <div style="position:absolute; bottom:20px; color:var(--mut); font-size:0.75rem;">XLR Switcher - OishiiCha</div>
    <script>
        let p = "";
        function k(n) { if(p.length<4) { p+=n; u(); if(p.length===4) c(); } }
        function clr() { p=""; u(); }
        function u() { for(let i=1;i<=4;i++) { document.getElementById('d'+i).className = i<=p.length ? 'dot active' : 'dot'; } }
        async function c() {
            try {
                let r = await fetch('/api/login', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({pin:p}) });
                let d = await r.json();
                if(d.success) location.reload();
                else { document.querySelectorAll('.dot').forEach(e=>e.classList.add('err')); setTimeout(()=>{ document.querySelectorAll('.dot').forEach(e=>e.classList.remove('err')); clr(); }, 400); }
            } catch(e) { clr(); }
        }
        document.addEventListener('keydown', e => { if(e.key>='0' && e.key<='9') k(e.key); else if(e.key==='Backspace') clr(); });
    </script>
</body>
</html>
"""

APP_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KH XLR Switcher</title>
    __CSS__
</head>
<body>
    <div id="demo">⚠️ SIMULATION MODE</div>
    <div class="container">
        <div class="header">
            <h1>
                <svg class="icon-xl" viewBox="0 0 512 512"><path d="__IC_SLIDERS__" fill="currentColor"/></svg>
                KH XLR Switcher
            </h1>
            <div style="display:flex; align-items:center;">
                <button class="btn-icon" onclick="toggleEdit()" title="Settings">
                    <svg class="icon-lg" viewBox="0 0 512 512"><path d="__IC_COG__" fill="currentColor"/></svg>
                </button>
                <div id="status-dot" class="conn-dot"></div>
            </div>
        </div>
        
        <div class="master-controls">
            <button class="btn-master btn-mute" onclick="allCh('mute')">
                <svg class="icon" viewBox="0 0 512 512"><path d="__IC_MUTE__" fill="currentColor"/></svg>
                MUTE ALL
            </button>
            <button class="btn-master btn-unmute" onclick="allCh('unmute')">
                <svg class="icon" viewBox="0 0 576 512"><path d="__IC_UNMUTE__" fill="currentColor"/></svg>
                UNMUTE ALL
            </button>
        </div>

        <div id="list" class="grid"></div>
        <div style="text-align:center; padding:15px; font-size:0.8rem; color:var(--mut);">XLR Switcher - OishiiCha</div>
    </div>

    <div id="modal" class="modal">
        <div class="modal-box">
            <div style="display:flex; justify-content:space-between; margin-bottom:20px;">
                <h3 style="margin:0">Edit Channel</h3>
                <button class="btn-icon" onclick="closeModal()" style="padding:0;"><svg class="icon" viewBox="0 0 352 512"><path d="__IC_TIMES__" fill="currentColor"/></svg></button>
            </div>
            <input id="e-name" type="text">
            <div id="pal" class="colors"></div>
            <div class="btns">
                <button class="btn-cancel" onclick="closeModal()">Cancel</button>
                <button class="btn-save" onclick="save()">Save</button>
            </div>
        </div>
    </div>

    <script>
        let st = [], edit = false, eId = -1, eCol = '';
        const COLS = ['#ef4444', '#f97316', '#f59e0b', '#eab308', '#84cc16', '#10b981', '#06b6d4', '#3b82f6', '#6366f1', '#d946ef', '#ffffff', '#000000'];
        // Embedded icons for JS rendering
        const IC_MIC = '<svg class="icon-xl" viewBox="0 0 352 512"><path d="M176 352c53.02 0 96-42.98 96-96V96c0-53.02-42.98-96-96-96S80 42.98 80 96v160c0 53.02 42.98 96 96 96zm160-160h-16c-8.84 0-16 7.16-16 16v48c0 74.8-64.49 134.82-140.79 127.38C96.71 376.89 48 317.11 48 250.3V208c0-8.84-7.16-16-16-16H16c-8.84 0-16 7.16-16 16v40.16c0 89.65 63.97 169.6 152 181.69V464H96c-8.84 0-16 7.16-16 16v16c0 8.84 7.16 16 16 16h160c8.84 0 16-7.16 16-16v-16c0-8.84-7.16-16-16-16h-56v-33.77C285.71 418.47 352 344.9 352 256v-48c0-8.84-7.16-16-16-16z" fill="currentColor"/></svg>';
        const IC_PEN = '<svg class="icon" style="width:14px; height:14px;" viewBox="0 0 512 512"><path d="M290.74 93.24l128.02 128.02-277.99 277.99-114.14 12.6C11.35 513.54-1.56 500.62.14 485.34l12.7-114.22 277.9-277.88zm207.2-19.06l-60.11-60.11c-18.75-18.75-49.16-18.75-67.91 0l-56.55 56.55 128.02 128.02 56.55-56.55c18.75-18.76 18.75-49.16 0-67.91z" fill="currentColor"/></svg>';

        // Init
        (async()=>{
            let r = await fetch('/api/status?t='+Date.now());
            if(r.status===401) location.reload();
            let d = await r.json();
            if(!d.hardware) document.getElementById('demo').style.display='block';
            draw(d.channels);
            updateConn(true);
            
            let pal = document.getElementById('pal');
            COLS.forEach(c => {
                let d = document.createElement('div');
                d.className='swatch'; d.style.background=c;
                if(c==='#000000') d.style.border='1px solid #334155';
                d.onclick=()=>{ eCol=c; document.querySelectorAll('.swatch').forEach(x=>x.classList.remove('sel')); d.classList.add('sel'); };
                pal.appendChild(d);
            });
            setInterval(poll, 2000);
        })();

        async function poll() {
            try {
                let r = await fetch('/api/status?t='+Date.now());
                if(r.status===401) location.reload();
                let d = await r.json();
                if(!edit) draw(d.channels);
                updateConn(true);
            } catch(e){ updateConn(false); }
        }

        function updateConn(ok) {
            document.getElementById('status-dot').className = 'conn-dot ' + (ok ? 'online' : 'offline');
        }

        function draw(chs) {
            if(JSON.stringify(chs)===JSON.stringify(st) && !edit) return;
            st = chs;
            let h = '';
            chs.forEach(c => {
                let col = c.color || '#3b82f6';
                let on = c.active;
                let bc = on ? col : '#334155';
                let glow = on ? `box-shadow:0 0 15px ${col}40` : '';
                let actC = on ? '#10b981' : '#ef4444';
                let actT = on ? 'LIVE' : 'MUTED';
                let tr = on ? 'transform:translateX(20px)' : '';
                let tb = on ? '#10b981' : '#334155';
                let iconBg = on ? `color:${col}; border-color:${col}; background:${col}15` : `color:#64748b; border-color:#475569`;
                // Safe JS string escaping manually
                let safeName = c.name.replace(/'/g, "\\\\'"); 
                
                h += `<div class="card" style="border-color:${edit?'#475569':bc}; ${edit?'':glow}" onclick="${edit?`openModal(${c.id}, '${safeName}', '${col}')`:`toggle(${c.id})`}">
                    <div class="edit-overlay-icon">${IC_PEN}</div>
                    <div class="card-left">
                        <div class="icon-box" style="${iconBg}">${IC_MIC}</div>
                        <div>
                            <div style="font-weight:bold; font-size:1.1rem;">${c.name}</div>
                            <div class="status" style="color:${actC}"><div class="status-dot" style="background:${actC}"></div>${actT}</div>
                        </div>
                    </div>
                    <div class="toggle" style="background:${tb}"><div class="thumb" style="${tr}"></div></div>
                    <div class="color-bar" style="background:${col}; ${on?'opacity:1; box-shadow:0 0 10px '+col:''}"></div>
                </div>`;
            });
            document.getElementById('list').innerHTML = h;
        }

        async function toggle(id) {
            if(edit) return;
            let t = JSON.parse(JSON.stringify(st));
            let i = t.findIndex(x=>x.id===id);
            if(i>=0) { t[i].active = !t[i].active; draw(t); }
            await fetch('/api/toggle/'+id, {method:'POST'});
            poll();
        }

        async function allCh(a) {
            if(edit) return;
            let s = a==='unmute';
            let t = JSON.parse(JSON.stringify(st));
            t.forEach(x=>x.active=s);
            draw(t);
            await fetch('/api/all/'+a, {method:'POST'});
            poll();
        }

        function toggleEdit() {
            edit = !edit;
            document.body.className = edit ? 'edit' : '';
            draw(st);
        }

        function openModal(id, n, c) {
            eId = id; eCol = c;
            document.getElementById('e-name').value = n;
            document.querySelectorAll('.swatch').forEach(x => {
                if(x.style.background.includes(c)) x.classList.add('sel'); else x.classList.remove('sel');
            });
            document.getElementById('modal').className = 'modal open';
        }

        function closeModal() { document.getElementById('modal').className = 'modal'; }

        async function save() {
            let n = document.getElementById('e-name').value;
            if(n) {
                await fetch('/api/update/'+eId, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({name:n, color:eCol}) });
                poll();
                closeModal();
            }
        }
    </script>
</body>
</html>
"""

# Inject CSS and Icons safely
LOGIN_HTML = LOGIN_HTML.replace('__CSS__', CSS)
APP_HTML = APP_HTML.replace('__CSS__', CSS)
APP_HTML = APP_HTML.replace('__IC_SLIDERS__', IC_SLIDERS)
APP_HTML = APP_HTML.replace('__IC_COG__', IC_COG)
APP_HTML = APP_HTML.replace('__IC_MUTE__', IC_MUTE)
APP_HTML = APP_HTML.replace('__IC_UNMUTE__', IC_UNMUTE)
APP_HTML = APP_HTML.replace('__IC_TIMES__', IC_TIMES)

# --- ROUTES ---

@app.route('/')
def index():
    # Manually return HTML so Flask doesn't try to template parse it
    if not session.get('auth'): 
        return Response(LOGIN_HTML, mimetype='text/html')
    return Response(APP_HTML, mimetype='text/html')

@app.route('/api/login', methods=['POST'])
def login():
    if request.json.get('pin') == PIN_CODE:
        session['auth'] = True
        return jsonify(success=True)
    return jsonify(success=False), 401

@app.route('/api/status')
def status():
    if not session.get('auth'): return jsonify(error="Auth"), 401
    return jsonify(channels=controller.channels, hardware=HARDWARE_PRESENT)

@app.route('/api/toggle/<int:cid>', methods=['POST'])
def toggle(cid):
    if not session.get('auth'): return jsonify(error="Auth"), 401
    s = controller.channels[cid]['active']
    controller.set_channel(cid, not s)
    return jsonify(success=True)

@app.route('/api/all/<action>', methods=['POST'])
def all_c(action):
    if not session.get('auth'): return jsonify(error="Auth"), 401
    controller.set_all(action == 'unmute')
    return jsonify(success=True)

@app.route('/api/update/<int:cid>', methods=['POST'])
def update(cid):
    if not session.get('auth'): return jsonify(error="Auth"), 401
    d = request.json
    controller.update_channel(cid, d['name'], d['color'])
    return jsonify(success=True)

if __name__ == '__main__':
    print("Starting XLR Switcher...")
    app.run(host='0.0.0.0', port=80, debug=False)
