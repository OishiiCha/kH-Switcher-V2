# KH XLR Switcher

A web-based and physical XLR audio switcher for Raspberry Pi. This system allows you to mute/unmute 4 channels of balanced audio via a web interface or physical push buttons, with status LED indicators.


<div align="center">
  <table>
    <tr>
      <td align="center">
        <img src="https://github.com/user-attachments/assets/9266c94e-bb6c-458c-a983-a2d55ef15a7d" width="300" alt="Device Photo">
        <br />
        <sub>Login</sub>
      </td>
      <td align="center">
        <img src="https://github.com/user-attachments/assets/288cc1b6-2331-4996-b7b5-e38b6a7f1237" width="300" alt="Wiring Schematic">
        <br />
        <sub>Simulation Mode (no GPIO present)</sub>
      </td>
      <td align="center">
        <img src="https://github.com/user-attachments/assets/1e34c17d-d0ef-45ca-b77d-01495334e729" width="300" alt="Pinout Diagram">
        <br />
        <sub>Edit</sub>
      </td>
    </tr>
  </table>
</div>





## 📂 Directory Structure

Ensure your project folder is organized exactly as follows:

```txt
app/
│
├── app.py            # Main application logic & GPIO control
├── xlr_config.json   # Stores channel names and states (auto-generated on first run)
│
├── templates/        # HTML files
│   ├── index.html
│   └── login.html
│
└── static/           # CSS and JavaScript
    ├── script.js
    └── style.css
```

-----

## 📋 GPIO Pinout Reference

Use the following pin assignments when wiring your Raspberry Pi. All pin numbers refer to **BCM** (Broadcom) numbering, not physical board pin numbers.

| Channel | Default Name | Relay GPIO | Button Input | Status LED |
| :--- | :--- | :--- | :--- | :--- |
| **1** | Speaker | `GPIO 17` | `GPIO 5` | `GPIO 6` |
| **2** | Reader | `GPIO 27` | `GPIO 13` | `GPIO 19` |
| **3** | Left | `GPIO 22` | `GPIO 26` | `GPIO 20` |
| **4** | Right | `GPIO 23` | `GPIO 24` | `GPIO 21` |

-----

## ⚡ Wiring Guide

### General Components

| Component | Pi Connection | Circuit Connection | Notes |
| :--- | :--- | :--- | :--- |
| **Relay Module** | GPIO Pin | Relay IN Pin | **Active LOW** (Logic: 0V = Relay ON/Muted) |
| **Button** | GPIO Pin | Switch Leg A | Switch Leg B → **GND** (Internal Pull-up is enabled) |
| **LED** | GPIO Pin | LED Anode (+) | LED Cathode (-) → **330Ω Resistor** → **GND** |

### XLR Audio Wiring (Short-to-Mute)

*This configuration uses the relay to short the Hot and Cold pins together to mute the signal. This is standard for balanced audio and avoids "floating" buzzing issues.*

| XLR Pin | Relay Terminal | Description |
| :--- | :--- | :--- |
| **Pin 1 (Ground)** | *Do Not Connect* | Pass directly from Input cable to Output cable. |
| **Pin 2 (Hot)** | **COM** (Common) | Connects incoming audio Hot to outgoing Hot. |
| **Pin 3 (Cold)** | **NO** (Normally Open) | Connects incoming audio Cold to outgoing Cold. |

> **Note:** When the system is **LIVE**, the relay is OFF (Open), and audio passes normally. When **MUTED**, the relay turns ON (Closed), shorting Pin 2 and 3 together to silence the audio.

-----

## 🚀 Installation & Usage

### 1\. Install Dependencies

```bash
sudo apt-get update
sudo apt-get install python3-pip python3-flask
pip3 install RPi.GPIO
```

### 2\. Run the Application

```bash
sudo python3 app.py
```

*Note: `sudo` is often required for GPIO access on Raspberry Pi.*

### 3\. Access the Interface

Open a web browser and navigate to the IP address of your Raspberry Pi:
`http://<your-pi-ip-address>`
For easiest use, change the raspberry pi hostname, eg. xlrswitch, then you can navigate to:
`xlrswitch/`

**Default Pin:** `1234`

