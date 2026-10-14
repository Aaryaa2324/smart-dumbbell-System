import serial
import requests
import json
import time

SERIAL_PORT = 'COM3'
BAUD_RATE = 115200
# Make sure this matches your exact Render live URL ending in /api/telemetry
CLOUD_URL = 'https://smart-dumbbell-setup.onrender.com/api/telemetry'

def start_bridge():
    print(f"Connecting to Arduino on {SERIAL_PORT} at {BAUD_RATE} baud...")
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(2)
    except Exception as e:
        print(f"Failed to connect to serial port: {e}")
        return

    print("Edge bridge active and filtering valid JSON telemetry...")
    
    while True:
        try:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                # Ensure we only process complete JSON payloads starting with { and ending with }
                if line.startswith("{") and line.endswith("}"):
                    data = json.loads(line)
                    response = requests.post(CLOUD_URL, json=data, timeout=5)
                    if response.status_code == 201:
                        print(f"-> Synced! Reps: {data.get('rep_count')} | Accel X: {data.get('ax')}")
                    else:
                        print(f"-> Server responded with status: {response.status_code}")
        except json.JSONDecodeError:
            pass
        except requests.exceptions.RequestException as re:
            print(f"-> Network error posting to Render: {re}")
        except Exception:
            pass
        
        time.sleep(0.05)

if __name__ == '__main__':
    start_bridge()