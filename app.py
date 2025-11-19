import os
import json
import sys
import time
from flask import Flask, render_template_string, request, jsonify

# Configuration: GPIO Pins (BCM Numbering)
RELAY_PINS = [17, 27, 22, 23] 

# File to store state/names/colors persistence
DATA_FILE = 'xlr_config.json'

# --- Hardware Abstraction Layer ---
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
                for idx, channel in enumerate(self.channels):
                    GPIO.setup(channel['pin'], GPIO.OUT)
                    # Restore hardware state based on logic:
                    # Active (Unmuted) = LOW
                    # Muted = HIGH
                    GPIO.output(channel['pin'], GPIO.LOW if channel['active'] else GPIO.HIGH)
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
                    saved_data = json.load(f)
                    if len(saved_data) == len(defaults):
                        self.channels = saved_data
                        for i, ch in enumerate(self.channels):
                            ch['pin'] = self.pins[i]
                            # FORCE UNMUTED ON BOOT:
                            # Keep name/color from file, but force active to True
                            ch['active'] = True 
                            if 'color' not in ch: ch['color'] = defaults[i]['color']
                        return
            except Exception as e:
                print(f"Error loading config: {e}")
        
        self.channels = defaults

    def save_state(self):
        try:
            with open(DATA_FILE, 'w') as f:
                json.dump(self.channels, f, indent=4)
        except Exception as e:
            print(f"Failed to save state: {e}")

    def set_channel(self, channel_id, state):
        if 0 <= channel_id < len(self.channels):
            self.channels[channel_id]['active'] = state
            if HARDWARE_PRESENT:
                # Active (True) -> LOW, Muted (False) -> HIGH
                GPIO.output(self.channels[channel_id]['pin'], GPIO.LOW if state else GPIO.HIGH)
            self.save_state()
            return True
        return False

    def update_channel(self, channel_id, new_name, new_color):
        if 0 <= channel_id < len(self.channels):
            self.channels[channel_id]['name'] = new_name
            self.channels[channel_id]['color'] = new_color
            self.save_state()
            return True
        return False

    def set_all(self, state):
        for ch in self.channels:
            ch['active'] = state
            if HARDWARE_PRESENT:
                GPIO.output(ch['pin'], GPIO.LOW if state else GPIO.HIGH)
        self.save_state()

# Initialize Controller
controller = RelayController(RELAY_PINS)
app = Flask(__name__)

# --- HTML Template (Offline Ready + FA Icons) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KH XLR Switcher</title>
    <style>
        :root {
            --bg-body: #0f172a;
            --bg-card: #1e293b;
            --bg-hover: #334155;
            --border: #334155;
            --text-main: #f1f5f9;
            --text-muted: #94a3b8;
            --success: #10b981;
            --danger: #ef4444;
            --blue: #3b82f6;
            --font-stack: system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }

        * { box-sizing: border-box; }

        body {
            background-color: var(--bg-body);
            color: var(--text-main);
            font-family: var(--font-stack);
            margin: 0;
            padding: 20px;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }

        /* Layout */
        .container {
            width: 100%;
            max-width: 900px;
            background-color: #1e293b;
            border-radius: 16px;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);
            border: 1px solid var(--border);
            overflow: hidden;
            position: relative;
            z-index: 10;
            margin-top: 20px;
        }

        .header {
            background-color: #1e293b;
            padding: 20px;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .header h1 { margin: 0; font-size: 1.25rem; letter-spacing: 0.05em; display: flex; align-items: center; gap: 10px; }
        .header-controls { display: flex; align-items: center; gap: 15px; }

        /* Grid */
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 16px;
            padding: 20px;
        }

        /* Master Controls */
        .master-controls {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
            padding: 16px;
            background-color: #162032;
            border-bottom: 1px solid var(--border);
        }

        .btn-master {
            padding: 15px;
            border-radius: 12px;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-size: 0.85rem;
            cursor: pointer;
            border: 1px solid transparent;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
        }

        .btn-mute-all { background: rgba(239, 68, 68, 0.15); color: #f87171; border-color: rgba(239, 68, 68, 0.3); }
        .btn-mute-all:hover { background: #ef4444; color: white; }
        
        .btn-unmute-all { background: rgba(16, 185, 129, 0.15); color: #34d399; border-color: rgba(16, 185, 129, 0.3); }
        .btn-unmute-all:hover { background: #10b981; color: white; }

        /* Channel Card */
        .channel-card {
            position: relative;
            background-color: rgba(30, 41, 59, 0.5);
            border: 2px solid var(--border);
            border-radius: 12px;
            padding: 16px;
            height: 110px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            cursor: pointer;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            user-select: none;
            overflow: hidden;
        }

        .card-content { display: flex; align-items: center; justify-content: space-between; height: 100%; padding-bottom: 10px; }
        .card-left { display: flex; align-items: center; gap: 16px; flex: 1; min-width: 0; }
        
        .icon-circle {
            width: 48px; height: 48px;
            border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            border: 1px solid;
            transition: all 0.3s;
        }
        
        .channel-info h3 { margin: 0; font-size: 1.1rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .status-text { font-size: 0.75rem; font-weight: bold; letter-spacing: 1px; margin-top: 4px; display: flex; align-items: center; gap: 6px; font-family: monospace; }
        .status-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; transition: background 0.3s; }

        /* Toggle Visual */
        .toggle-track {
            width: 50px; height: 28px;
            border-radius: 99px;
            padding: 2px;
            display: flex;
            transition: background-color 0.3s;
        }
        .toggle-thumb {
            width: 24px; height: 24px;
            background: white;
            border-radius: 50%;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            transition: transform 0.3s;
        }

        /* Color Bar */
        .color-bar {
            position: absolute; bottom: 0; left: 0; right: 0;
            height: 6px;
            transition: all 0.3s;
        }

        /* Edit Mode Overrides */
        body.edit-mode .channel-card {
            border-style: dashed;
            border-color: var(--text-muted);
            animation: pulse-border 2s infinite;
            transform: scale(0.98);
        }
        body.edit-mode .toggle-track { opacity: 0.2; filter: grayscale(100%); }
        
        @keyframes pulse-border {
            0% { border-color: #475569; }
            50% { border-color: #94a3b8; }
            100% { border-color: #475569; }
        }

        /* Modal */
        .modal-overlay {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0, 0, 0, 0.85);
            backdrop-filter: blur(4px);
            z-index: 100;
            display: flex; align-items: center; justify-content: center;
            opacity: 0; pointer-events: none;
            transition: opacity 0.2s;
        }
        .modal-overlay.active { opacity: 1; pointer-events: auto; }
        
        .modal-box {
            background: var(--bg-card);
            width: 90%; max-width: 400px;
            padding: 24px;
            border-radius: 16px;
            border: 1px solid var(--border);
            box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5);
            transform: scale(0.95); transition: transform 0.2s;
        }
        .modal-overlay.active .modal-box { transform: scale(1); }

        .form-group { margin-bottom: 20px; }
        .form-label { display: block; color: var(--text-muted); font-size: 0.75rem; font-weight: bold; text-transform: uppercase; margin-bottom: 8px; letter-spacing: 0.05em; }
        .form-input {
            width: 100%; background: #0f172a; border: 1px solid var(--border);
            color: white; padding: 12px 16px; border-radius: 8px;
            font-size: 1rem; outline: none; transition: border 0.2s;
        }
        .form-input:focus { border-color: var(--blue); }

        /* Palette */
        .palette-grid { display: grid; grid-template-columns: repeat(6, 1fr); gap: 10px; }
        .swatch {
            width: 100%; aspect-ratio: 1;
            border-radius: 50%;
            cursor: pointer;
            border: 2px solid transparent;
            position: relative;
            transition: transform 0.2s;
        }
        .swatch:hover { transform: scale(1.1); }
        .swatch.selected { border-color: white; transform: scale(1.15); box-shadow: 0 0 10px rgba(255,255,255,0.3); }
        .swatch.selected::after {
            content: ''; position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
            width: 6px; height: 10px; border: solid white; border-width: 0 2px 2px 0; transform: translate(-50%, -60%) rotate(45deg);
            filter: drop-shadow(0 0 2px black);
        }

        .modal-actions { display: flex; justify-content: flex-end; gap: 12px; margin-top: 24px; }
        .btn-secondary { background: transparent; color: var(--text-muted); }
        .btn-secondary:hover { color: white; background: var(--bg-hover); }
        .btn-primary { background: var(--blue); color: white; box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.5); }
        .btn-primary:hover { background: #2563eb; }

        /* Utility & Icons */
        .icon { width: 18px; height: 18px; fill: currentColor; }
        .icon-lg { width: 24px; height: 24px; fill: currentColor; }
        .icon-xl { width: 28px; height: 28px; fill: currentColor; }
        
        #demo-banner {
            position: absolute; top: 0; left: 0; width: 100%;
            background: #d97706; color: white; text-align: center;
            padding: 8px; font-weight: bold; font-size: 0.85rem; letter-spacing: 1px;
            z-index: 50; display: none;
        }

        .edit-badge {
            position: absolute; top: 8px; right: 8px;
            background: var(--bg-card); border: 1px solid var(--border);
            border-radius: 50%; width: 24px; height: 24px;
            display: flex; align-items: center; justify-content: center;
            opacity: 0; transition: opacity 0.2s; pointer-events: none;
        }
        body.edit-mode .edit-badge { opacity: 1; }

        /* Status Connection Dot */
        .conn-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--text-muted); }
        .conn-dot.online { background: var(--success); box-shadow: 0 0 8px var(--success); }
        .conn-dot.offline { background: var(--danger); }

        .btn-edit-toggle { color: var(--text-muted); padding: 8px; border-radius: 8px; background: transparent; border: none; cursor: pointer; transition: all 0.2s; }
        .btn-edit-toggle:hover { color: white; background: var(--bg-hover); }
        .btn-edit-toggle.active { background: var(--blue); color: white; }

    </style>
</head>
<body>

    <div id="demo-banner">
        ⚠️ SIMULATION MODE
    </div>

    <div class="container">
        <!-- Header -->
        <div class="header">
            <h1>
                <!-- FA Sliders Icon -->
                <svg class="icon-xl" style="color: var(--blue);" viewBox="0 0 512 512"><path d="M496 384H160v-16c0-8.8-7.2-16-16-16h-32c-8.8 0-16 7.2-16 16v16H16c-8.8 0-16 7.2-16 16v32c0 8.8 7.2 16 16 16h80v16c0 8.8 7.2 16 16 16h32c8.8 0 16-7.2 16-16v-16h336c8.8 0 16-7.2 16-16v-32c0-8.8-7.2-16-16-16zm0-160h-80v-16c0-8.8-7.2-16-16-16h-32c-8.8 0-16 7.2-16 16v16H16c-8.8 0-16 7.2-16 16v32c0 8.8 7.2 16 16 16h336v16c0 8.8 7.2 16 16 16h32c8.8 0 16-7.2 16-16v-16h80c8.8 0 16-7.2 16-16v-32c0-8.8-7.2-16-16-16zm0-160H288V48c0-8.8-7.2-16-16-16h-32c-8.8 0-16 7.2-16 16v16H16C7.2 64 0 71.2 0 80v32c0 8.8 7.2 16 16 16h208v16c0 8.8 7.2 16 16 16h32c8.8 0 16-7.2 16-16v-16h208c8.8 0 16-7.2 16-16V80c0-8.8-7.2-16-16-16z"/></svg>
                KH XLR Switcher
            </h1>
            <div class="header-controls">
                <button id="master-edit-btn" class="btn-edit-toggle" onclick="toggleEditMode()" title="Settings">
                    <!-- FA Cog Icon -->
                    <svg class="icon-lg" viewBox="0 0 512 512"><path d="M487.4 315.7l-42.6-24.6c4.3-23.2 4.3-47 0-70.2l42.6-24.6c4.9-2.8 7.1-8.6 5.5-14-11.1-35.6-30-67.8-54.7-94.6-3.8-4.1-10-5.1-14.8-2.3L380.8 110c-17.9-15.4-38.5-27.3-60.8-35.1V25.8c0-5.6-3.9-10.5-9.4-11.7-36.7-8.2-74.3-7.8-109.2 0-5.5 1.2-9.4 6.1-9.4 11.7V75c-22.2 7.9-42.8 19.8-60.8 35.1L88.7 85.5c-4.9-2.8-11-1.9-14.8 2.3-24.7 26.7-43.6 58.9-54.7 94.6-1.7 5.4.6 11.2 5.5 14L67.3 221c-4.3 23.2-4.3 47 0 70.2l-42.6 24.6c-4.9 2.8-7.1 8.6-5.5 14 11.1 35.6 30 67.8 54.7 94.6 3.8 4.1 10 5.1 14.8 2.3l42.6-24.6c17.9 15.4 38.5 27.3 60.8 35.1v49.2c0 5.6 3.9 10.5 9.4 11.7 36.7 8.2 74.3 7.8 109.2 0 5.5-1.2 9.4-6.1 9.4-11.7v-49.2c22.2-7.9 42.8-19.8 60.8-35.1l42.6 24.6c4.9 2.8 11 1.9 14.8-2.3 24.7-26.7 43.6-58.9 54.7-94.6 1.5-5.5-.7-11.3-5.6-14.1zM256 336c-44.1 0-80-35.9-80-80s35.9-80 80-80 80 35.9 80 80-35.9 80-80 80z"/></svg>
                </button>
                <div id="status-dot" class="conn-dot"></div>
            </div>
        </div>

        <!-- Master Controls -->
        <div class="master-controls">
            <button class="btn btn-master btn-mute-all" onclick="controlAll(false)">
                <!-- FA Volume Mute -->
                <svg class="icon" viewBox="0 0 512 512"><path d="M215.03 71.05L126.06 160H24c-13.26 0-24 10.74-24 24v144c0 13.25 10.74 24 24 24h102.06l88.97 88.95c15.03 15.03 40.97 4.47 40.97-16.97V88.02c0-21.46-25.96-31.98-40.97-16.97zM461.64 272l-56.57 56.57c-6.25 6.25-6.25 16.38 0 22.63l22.63 22.63c6.25 6.25 16.38 6.25 22.63 0L506.9 317.29c6.25-6.25 6.25-16.38 0-22.63L450.34 238.1c-6.25-6.25-16.38-6.25-22.63 0l-22.63 22.63c-6.25 6.25-6.25 16.38 0 22.63L461.64 272zm0-96l45.25-45.25c6.25-6.25 6.25-16.38 0-22.63l-22.63-22.63c-6.25-6.25-16.38-6.25-22.63 0L405.07 130.71c-6.25 6.25-6.25 16.38 0 22.63l56.57 56.57c6.25 6.25 16.38 6.25 22.63 0l22.63-22.63c6.25-6.25 6.25-16.38 0-22.63L461.64 176z"/></svg>
                Mute All
            </button>
            <button class="btn btn-master btn-unmute-all" onclick="controlAll(true)">
                <!-- FA Volume Up -->
                <svg class="icon" viewBox="0 0 576 512"><path d="M215.03 71.05L126.06 160H24c-13.26 0-24 10.74-24 24v144c0 13.25 10.74 24 24 24h102.06l88.97 88.95c15.03 15.03 40.97 4.47 40.97-16.97V88.02c0-21.46-25.96-31.98-40.97-16.97zm233.32-51.08c-11.17-7.33-26.18-4.24-33.51 6.95-7.34 11.17-4.22 26.18 6.95 33.51 66.27 43.55 105.81 116.88 106.2 195.99.48 78.72-38.62 151.51-103.77 195.46-11.07 7.47-14.01 22.47-6.55 33.53 7.47 11.07 22.45 14.03 33.53 6.55 79.41-53.59 127.05-142.28 126.46-238.23-.49-96.42-48.66-185.79-129.31-233.76zM400 128c-8.37 0-16.17 3.2-22.06 9.09L372.7 142.3c-11.86 11.86-12.06 30.91-.59 43.06 36.77 38.95 36.63 98.39 0 137.34-11.53 12.2-11.26 31.32.62 43.2l5.23 5.23c5.88 5.88 13.69 9.1 22.05 9.1 8.34 0 16.14-3.19 22.05-9.08 62.9-62.43 63.19-162.99 0-225.92-11.92-11.92-31.23-11.92-43.15 0l-5.17 5.17c-5.89-5.91-13.68-9.11-22.05-9.11z"/></svg>
                Unmute All
            </button>
        </div>

        <!-- Channels Grid -->
        <div id="channel-list" class="grid">
            <div style="text-align:center; color: #64748b; grid-column: 1/-1; padding: 40px;">Loading System...</div>
        </div>

        <!-- Footer -->
        <div style="padding: 15px; text-align: center; color: #64748b; font-size: 0.75rem; background: #0f172a; border-top: 1px solid #1e293b;">
            XLR Switcher - OishiiCha
        </div>
    </div>

    <!-- Edit Modal -->
    <div id="edit-modal" class="modal-overlay">
        <div class="modal-box">
            <div style="display:flex; justify-content:space-between; margin-bottom: 20px;">
                <h3 style="margin:0; font-size:1.25rem;">Edit Channel</h3>
                <button onclick="closeModal()" style="background:none; border:none; color:#94a3b8; cursor:pointer;">
                    <!-- FA Times Icon -->
                    <svg class="icon" viewBox="0 0 352 512"><path d="M242.72 256l100.07-100.07c12.28-12.28 12.28-32.19 0-44.48l-22.24-22.24c-12.28-12.28-32.19-12.28-44.48 0L176 189.28 75.93 89.21c-12.28-12.28-32.19-12.28-44.48 0L9.21 111.45c-12.28 12.28-12.28 32.19 0 44.48L109.28 256 9.21 356.07c-12.28 12.28-12.28 32.19 0 44.48l22.24 22.24c12.28 12.28 32.19 12.28 44.48 0L176 322.72l100.07 100.07c12.28 12.28 32.19 12.28 44.48 0l22.24-22.24c12.28-12.28 12.28-32.19 0-44.48L242.72 256z"/></svg>
                </button>
            </div>

            <input type="hidden" id="edit-channel-id">
            <input type="hidden" id="edit-channel-color-value">

            <div class="form-group">
                <label class="form-label">Channel Name</label>
                <input type="text" id="edit-channel-name" class="form-input" placeholder="e.g. Vocals" autocomplete="off">
            </div>

            <div class="form-group">
                <label class="form-label">Channel Color</label>
                <div class="palette-grid" id="color-palette-grid"></div>
            </div>

            <div class="modal-actions">
                <button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="saveChannelSettings()">Save Changes</button>
            </div>
        </div>
    </div>

    <script>
        // --- Exact FA SVGs embedded for offline use ---
        const ICONS = {
            // FA Microphone
            mic: '<svg class="icon-xl" viewBox="0 0 352 512"><path d="M176 352c53.02 0 96-42.98 96-96V96c0-53.02-42.98-96-96-96S80 42.98 80 96v160c0 53.02 42.98 96 96 96zm160-160h-16c-8.84 0-16 7.16-16 16v48c0 74.8-64.49 134.82-140.79 127.38C96.71 376.89 48 317.11 48 250.3V208c0-8.84-7.16-16-16-16H16c-8.84 0-16 7.16-16 16v40.16c0 89.65 63.97 169.6 152 181.69V464H96c-8.84 0-16 7.16-16 16v16c0 8.84 7.16 16 16 16h160c8.84 0 16-7.16 16-16v-16c0-8.84-7.16-16-16-16h-56v-33.77C285.71 418.47 352 344.9 352 256v-48c0-8.84-7.16-16-16-16z"/></svg>',
            // FA Pen
            pen: '<svg class="icon" style="width:14px; height:14px;" viewBox="0 0 512 512"><path d="M290.74 93.24l128.02 128.02-277.99 277.99-114.14 12.6C11.35 513.54-1.56 500.62.14 485.34l12.7-114.22 277.9-277.88zm207.2-19.06l-60.11-60.11c-18.75-18.75-49.16-18.75-67.91 0l-56.55 56.55 128.02 128.02 56.55-56.55c18.75-18.76 18.75-49.16 0-67.91z"/></svg>'
        };

        // --- State ---
        let lastState = [];
        let isEditMode = false;
        const PRESET_COLORS = ['#ef4444', '#f97316', '#f59e0b', '#eab308', '#84cc16', '#10b981', '#06b6d4', '#3b82f6', '#6366f1', '#d946ef', '#ffffff', '#000000'];

        document.addEventListener('DOMContentLoaded', () => {
            fetchStatus();
            renderPalette();
            document.getElementById('edit-channel-name').addEventListener('keypress', e => {
                if (e.key === 'Enter') saveChannelSettings();
            });
        });

        function toggleEditMode() {
            isEditMode = !isEditMode;
            document.body.classList.toggle('edit-mode', isEditMode);
            document.getElementById('master-edit-btn').classList.toggle('active', isEditMode);
            renderChannels(lastState, true);
        }

        async function fetchStatus() {
            try {
                const res = await fetch(`/api/status?t=${new Date().getTime()}`);
                const data = await res.json();
                document.getElementById('demo-banner').style.display = data.hardware === false ? 'block' : 'none';
                renderChannels(data.channels);
                updateConn(true);
            } catch (e) {
                console.error(e);
                updateConn(false);
            }
        }

        function updateConn(online) {
            const dot = document.getElementById('status-dot');
            dot.className = 'conn-dot ' + (online ? 'online' : 'offline');
        }

        function renderChannels(channels, force = false) {
            if (!force && JSON.stringify(channels) === JSON.stringify(lastState) && !isEditMode) return;
            lastState = channels;
            
            const container = document.getElementById('channel-list');
            container.innerHTML = '';

            channels.forEach(ch => {
                const isActive = ch.active;
                const color = ch.color || '#3b82f6';
                const isMuted = !isActive;

                // Styles
                const borderColor = isActive ? color : '#334155';
                const glow = isActive ? `box-shadow: 0 0 15px ${color}40, inset 0 0 20px ${color}10;` : '';
                const statusText = isActive ? 'LIVE' : 'MUTED';
                const statusColor = isActive ? '#10b981' : '#ef4444';
                
                // Icon Circle
                const iconBg = isActive ? `color: ${color}; border-color: ${color}; background: ${color}15;` : `color: #64748b; border-color: #475569; background: transparent;`;

                // Toggle Switch
                const trackBg = isActive ? '#10b981' : '#334155';
                const thumbTransform = isActive ? 'translateX(22px)' : 'translateX(0)';

                // Bottom Bar
                const barOpacity = isActive ? 1 : 0.2;
                const barShadow = isActive ? `box-shadow: 0 0 10px ${color}, 0 0 5px white;` : '';

                const action = isEditMode ? `openEditModal(${ch.id}, '${ch.name.replace(/'/g, "\\'")}', '${color}')` : `toggleChannel(${ch.id})`;

                const html = `
                <div class="channel-card" style="border-color: ${isEditMode ? '#475569' : borderColor}; ${isEditMode ? '' : glow}" onclick="${action}">
                    <div class="edit-badge">${ICONS.pen}</div>
                    
                    <div class="card-content">
                        <div class="card-left">
                            <div class="icon-circle" style="${iconBg}">${ICONS.mic}</div>
                            <div class="channel-info">
                                <h3>${ch.name}</h3>
                                <div class="status-text" style="color: ${statusColor}">
                                    <span class="status-dot" style="background: ${statusColor}"></span>
                                    ${statusText}
                                </div>
                            </div>
                        </div>
                        
                        <div class="toggle-track" style="background-color: ${trackBg}">
                            <div class="toggle-thumb" style="transform: ${thumbTransform}"></div>
                        </div>
                    </div>

                    <div class="color-bar" style="background-color: ${color}; opacity: ${barOpacity}; ${barShadow}"></div>
                </div>`;
                
                container.innerHTML += html;
            });
        }

        async function toggleChannel(id) {
            if(isEditMode) return;
            
            // Optimistic UI
            const newState = JSON.parse(JSON.stringify(lastState));
            const idx = newState.findIndex(c => c.id === id);
            if (idx !== -1) {
                newState[idx].active = !newState[idx].active;
                renderChannels(newState);
            }

            await fetch(`/api/toggle/${id}`, { method: 'POST' });
            fetchStatus();
        }

        async function controlAll(state) {
            if(isEditMode) return;
            const newState = JSON.parse(JSON.stringify(lastState));
            newState.forEach(ch => ch.active = state);
            renderChannels(newState);

            const action = state ? 'unmute' : 'mute';
            await fetch(`/api/all/${action}`, { method: 'POST' });
            fetchStatus();
        }

        // --- Modal ---
        function renderPalette() {
            const grid = document.getElementById('color-palette-grid');
            grid.innerHTML = '';
            PRESET_COLORS.forEach(c => {
                const el = document.createElement('div');
                el.className = 'swatch';
                el.style.backgroundColor = c;
                if (c === '#000000') el.style.border = '1px solid #475569';
                el.onclick = () => selectColor(c, el);
                el.dataset.color = c;
                grid.appendChild(el);
            });
        }

        function selectColor(color, el) {
            document.getElementById('edit-channel-color-value').value = color;
            document.querySelectorAll('.swatch').forEach(s => s.classList.remove('selected'));
            el.classList.add('selected');
        }

        function openEditModal(id, name, color) {
            document.getElementById('edit-channel-id').value = id;
            document.getElementById('edit-channel-name').value = name;
            document.getElementById('edit-channel-color-value').value = color;
            
            document.querySelectorAll('.swatch').forEach(s => {
                if (s.dataset.color.toLowerCase() === color.toLowerCase()) s.classList.add('selected');
                else s.classList.remove('selected');
            });
            
            document.getElementById('edit-modal').classList.add('active');
            setTimeout(() => document.getElementById('edit-channel-name').focus(), 50);
        }

        function closeModal() {
            document.getElementById('edit-modal').classList.remove('active');
        }

        async function saveChannelSettings() {
            const id = document.getElementById('edit-channel-id').value;
            const name = document.getElementById('edit-channel-name').value;
            const color = document.getElementById('edit-channel-color-value').value;

            if (name) {
                await fetch(`/api/update/${id}`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({name, color})
                });
                fetchStatus();
                closeModal();
            }
        }
        
        setInterval(fetchStatus, 2000);
    </script>
</body>
</html>
"""

# --- Routes & Server ---

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify({
        "channels": controller.channels,
        "hardware": HARDWARE_PRESENT
    })

@app.route('/api/toggle/<int:channel_id>', methods=['POST'])
def toggle_channel(channel_id):
    if 0 <= channel_id < len(controller.channels):
        current_state = controller.channels[channel_id]['active']
        controller.set_channel(channel_id, not current_state)
        return jsonify({"success": True})
    return jsonify({"success": False}), 400

@app.route('/api/all/<action>', methods=['POST'])
def control_all_channels(action):
    if action == 'mute':
        controller.set_all(False)
    elif action == 'unmute':
        controller.set_all(True)
    return jsonify({"success": True})

@app.route('/api/update/<int:channel_id>', methods=['POST'])
def update_channel_route(channel_id):
    data = request.json
    if data and 'name' in data and 'color' in data:
        controller.update_channel(channel_id, data['name'], data['color'])
        return jsonify({"success": True})
    return jsonify({"success": False}), 400

if __name__ == '__main__':
    print(f"Starting Web Server...")
    print(f"Access at http://<your-pi-ip>:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)
