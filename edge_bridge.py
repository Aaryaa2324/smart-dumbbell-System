import serial
import requests
import json
import time

SERIAL_PORT = 'COM3'  # Update if needed
BAUD_RATE = 115200
CLOUD_URL = 'https://smart-dumbbell-service.onrender.com/api/telemetry' # Replace with your live Render URL

def start_bridge():
    print(f"Connecting to Arduino on {SERIAL_PORT} at {BAUD_RATE} baud...")
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.5)
        time.sleep(2)
    except Exception as e:
        print(f"Serial connection error: {e}")
        return

    print("High-speed edge bridge active. Streaming telemetry...")
    
    while True:
        try:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8').strip()
                if line and line.startswith("{"):
                    data = json.loads(line)
                    response = requests.post(CLOUD_URL, json=data, timeout=2)
                    if response.status_code == 201:
                        print(f"Synced Reps: {data.get('rep_count')} | Accel: X={data.get('ax')}")
        except json.JSONDecodeError:
            pass
        except requests.exceptions.RequestException:
            pass
        except Exception:
            pass
        
        time.sleep(0.2)

if __name__ == '__main__':
    start_bridge()