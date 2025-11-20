import os
import json
import sys
import time
from flask import Flask, request, jsonify, session, render_template

# --- Configuration ---
# Format: [Ch1, Ch2, Ch3, Ch4]
RELAY_PINS = [17, 27, 22, 23]
BUTTON_PINS = [5, 13, 26, 24]  # Pins for physical buttons
LED_PINS = [6, 19, 20, 21]  # Pins for status LEDs

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
    def __init__(self, relay_pins, button_pins, led_pins):
        self.relay_pins = relay_pins
        self.button_pins = button_pins
        self.led_pins = led_pins
        self.channels = []

        # Load saved state first
        self.load_state()

        if HARDWARE_PRESENT:
            self.setup_hardware()

    def setup_hardware(self):
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)

            # 1. Setup Relays and LEDs
            for i, ch in enumerate(self.channels):
                # RELAY: Output. Active(True) = LOW (usually)
                GPIO.setup(ch['pin'], GPIO.OUT)
                GPIO.output(ch['pin'], GPIO.HIGH if ch['active'] else GPIO.LOW)

                # LED: Output. Active(True) = HIGH (Light on)
                led_pin = self.led_pins[i]
                GPIO.setup(led_pin, GPIO.OUT)
                GPIO.output(led_pin, GPIO.HIGH if ch['active'] else GPIO.LOW)

            # 2. Setup Buttons (Inputs with Internal Pull-Up)
            # Connect button: Pin -> Switch -> GND
            for btn_pin in self.button_pins:
                GPIO.setup(btn_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                # Add event listener (interrupt)
                GPIO.add_event_detect(btn_pin, GPIO.FALLING, callback=self.handle_physical_button, bouncetime=300)

        except Exception as e:
            print(f"Hardware init error: {e}")

    def handle_physical_button(self, channel):
        """Callback for when a physical button is pressed"""
        # Find which index this pin belongs to
        if channel in self.button_pins:
            idx = self.button_pins.index(channel)
            print(f"🔘 Physical Button {idx + 1} Pressed")

            # Toggle state
            current_state = self.channels[idx]['active']
            self.set_channel(idx, not current_state)

    def load_state(self):
        defaults = [
            {'id': 0, 'name': 'Speaker', 'active': True, 'color': '#3b82f6'},
            {'id': 1, 'name': 'Reader', 'active': True, 'color': '#10b981'},
            {'id': 2, 'name': 'Left', 'active': True, 'color': '#f59e0b'},
            {'id': 3, 'name': 'Right', 'active': True, 'color': '#8b5cf6'},
        ]
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r') as f:
                    saved = json.load(f)
                    if len(saved) == len(defaults):
                        self.channels = saved
                        # Re-attach pin numbers to the data structure
                        for i, ch in enumerate(self.channels):
                            ch['pin'] = self.relay_pins[i]
                            # Ensure color exists
                            if 'color' not in ch: ch['color'] = defaults[i]['color']
                        return
            except:
                pass

        # If load failed, use defaults
        self.channels = defaults
        for i, ch in enumerate(self.channels):
            ch['pin'] = self.relay_pins[i]

    def save_state(self):
        try:
            with open(DATA_FILE, 'w') as f:
                # Clean data before saving (remove runtime pin info if desired, keeping it simple here)
                json.dump(self.channels, f, indent=4)
        except:
            pass

    def set_channel(self, cid, state):
        if 0 <= cid < len(self.channels):
            self.channels[cid]['active'] = state

            if HARDWARE_PRESENT:
                # RELAY Logic: Active = LOW, Muted = HIGH
                GPIO.output(self.channels[cid]['pin'], GPIO.HIGH if state else GPIO.LOW)

                # LED Logic: Active = HIGH (On), Muted = LOW (Off)
                GPIO.output(self.led_pins[cid], GPIO.HIGH if state else GPIO.LOW)

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
        for i, ch in enumerate(self.channels):
            ch['active'] = state
            if HARDWARE_PRESENT:
                # Relay
                GPIO.output(ch['pin'], GPIO.LOW if state else GPIO.HIGH)
                # LED
                GPIO.output(self.led_pins[i], GPIO.HIGH if state else GPIO.LOW)

        self.save_state()


# Initialize Controller with 3 sets of pins
controller = RelayController(RELAY_PINS, BUTTON_PINS, LED_PINS)

app = Flask(__name__)
app.secret_key = SECRET_KEY

# --- ICONS (SVG Paths) ---
ICONS = {
    "IC_SLIDERS": "M496 384H160v-16c0-8.8-7.2-16-16-16h-32c-8.8 0-16 7.2-16 16v16H16c-8.8 0-16 7.2-16 16v32c0 8.8 7.2 16 16 16h80v16c0 8.8 7.2 16 16 16h32c8.8 0 16-7.2 16-16v-16h336c8.8 0 16-7.2 16-16v-32c0-8.8-7.2-16-16-16zm0-160h-80v-16c0-8.8-7.2-16-16-16h-32c-8.8 0-16 7.2-16 16v16H16c-8.8 0-16 7.2-16 16v32c0 8.8 7.2 16 16 16h336v16c0 8.8 7.2 16 16 16h32c8.8 0 16-7.2 16-16v-16h80c8.8 0 16-7.2 16-16v-32c0-8.8-7.2-16-16-16zm0-160H288V48c0-8.8-7.2-16-16-16h-32c-8.8 0-16 7.2-16 16v16H16C7.2 64 0 71.2 0 80v32c0 8.8 7.2 16 16 16h208v16c0 8.8 7.2 16 16 16h32c8.8 0 16-7.2 16-16v-16h208c8.8 0 16-7.2 16-16V80c0-8.8-7.2-16-16-16z",
    "IC_COG": "M487.4 315.7l-42.6-24.6c4.3-23.2 4.3-47 0-70.2l42.6-24.6c4.9-2.8 7.1-8.6 5.5-14-11.1-35.6-30-67.8-54.7-94.6-3.8-4.1-10-5.1-14.8-2.3L380.8 110c-17.9-15.4-38.5-27.3-60.8-35.1V25.8c0-5.6-3.9-10.5-9.4-11.7-36.7-8.2-74.3-7.8-109.2 0-5.5 1.2-9.4 6.1-9.4 11.7V75c-22.2 7.9-42.8 19.8-60.8 35.1L88.7 85.5c-4.9-2.8-11-1.9-14.8 2.3-24.7 26.7-43.6 58.9-54.7 94.6-1.7 5.4.6 11.2 5.5 14L67.3 221c-4.3 23.2-4.3 47 0 70.2l-42.6 24.6c-4.9 2.8-7.1 8.6-5.5 14 11.1 35.6 30 67.8 54.7 94.6 3.8 4.1 10 5.1 14.8 2.3l42.6-24.6c17.9 15.4 38.5 27.3 60.8 35.1v49.2c0 5.6 3.9 10.5 9.4 11.7 36.7 8.2 74.3 7.8 109.2 0 5.5-1.2 9.4-6.1 9.4-11.7v-49.2c22.2-7.9 42.8-19.8 60.8-35.1l42.6 24.6c4.9 2.8 11 1.9 14.8-2.3 24.7-26.7 43.6-58.9 54.7-94.6 1.5-5.5-.7-11.3-5.6-14.1zM256 336c-44.1 0-80-35.9-80-80s35.9-80 80-80 80 35.9 80 80-35.9 80-80 80z",
    "IC_MUTE": "M215.03 71.05L126.06 160H24c-13.26 0-24 10.74-24 24v144c0 13.25 10.74 24 24 24h102.06l88.97 88.95c15.03 15.03 40.97 4.47 40.97-16.97V88.02c0-21.46-25.96-31.98-40.97-16.97zM461.64 272l-56.57 56.57c-6.25 6.25-6.25 16.38 0 22.63l22.63 22.63c6.25 6.25 16.38 6.25 22.63 0L506.9 317.29c6.25-6.25 6.25-16.38 0-22.63L450.34 238.1c-6.25-6.25-16.38-6.25-22.63 0l-22.63 22.63c-6.25 6.25-6.25 16.38 0 22.63L461.64 272zm0-96l45.25-45.25c6.25-6.25 6.25-16.38 0-22.63l-22.63-22.63c-6.25-6.25-16.38-6.25-22.63 0L405.07 130.71c-6.25 6.25-6.25 16.38 0 22.63l56.57 56.57c6.25 6.25 16.38 6.25 22.63 0l22.63-22.63c6.25-6.25 6.25-16.38 0-22.63L461.64 176z",
    "IC_UNMUTE": "M215.03 71.05L126.06 160H24c-13.26 0-24 10.74-24 24v144c0 13.25 10.74 24 24 24h102.06l88.97 88.95c15.03 15.03 40.97 4.47 40.97-16.97zm233.32-51.08c-11.17-7.33-26.18-4.24-33.51 6.95-7.34 11.17-4.22 26.18 6.95 33.51 66.27 43.55 105.81 116.88 106.2 195.99.48 78.72-38.62 151.51-103.77 195.46-11.07 7.47-14.01 22.47-6.55 33.53 7.47 11.07 22.45 14.03 33.53 6.55 79.41-53.59 127.05-142.28 126.46-238.23-.49-96.42-48.66-185.79-129.31-233.76zM400 128c-8.37 0-16.17 3.2-22.06 9.09L372.7 142.3c-11.86 11.86-12.06 30.91-.59 43.06 36.77 38.95 36.63 98.39 0 137.34-11.53 12.2-11.26 31.32.62 43.2l5.23 5.23c5.88 5.88 13.69 9.1 22.05 9.1 8.34 0 16.14-3.19 22.05-9.08 62.9-62.43 63.19-162.99 0-225.92-11.92-11.92-31.23-11.92-43.15 0l-5.17 5.17c-5.89-5.91-13.68-9.11-22.05-9.11z",
    "IC_TIMES": "M242.72 256l100.07-100.07c12.28-12.28 12.28-32.19 0-44.48l-22.24-22.24c-12.28-12.28-32.19-12.28-44.48 0L176 189.28 75.93 89.21c-12.28-12.28-32.19-12.28-44.48 0L9.21 111.45c-12.28 12.28-12.28 32.19 0 44.48L109.28 256 9.21 356.07c-12.28 12.28-12.28 32.19 0 44.48l22.24 22.24c12.28 12.28 32.19 12.28 44.48 0L176 322.72l100.07 100.07c12.28 12.28 32.19 12.28 44.48 0l22.24-22.24c12.28-12.28 12.28-32.19 0-44.48L242.72 256z"
}


# --- ROUTES ---

@app.route('/')
def index():
    if not session.get('auth'):
        return render_template('login.html', **ICONS)
    return render_template('index.html', **ICONS)


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