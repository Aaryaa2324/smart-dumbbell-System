import serial
import requests
import json
import time

# Update with your Arduino serial port (e.g., 'COM3' on Windows or '/dev/ttyUSB0' on Linux/Mac)
SERIAL_PORT = 'COM3'
BAUD_RATE = 9600

# Replace this with your NEW Render Web Service URL once deployed
CLOUD_URL = 'https://your-new-render-app-name.onrender.com/api/telemetry'

def start_bridge():
    print(f"Connecting to Arduino on {SERIAL_PORT}...")
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(2) # Allow connection to settle
    except Exception as e:
        print(f"Failed to connect to serial port: {e}")
        return

    print("Edge bridge active. Forwarding telemetry to cloud...")
    
    while True:
        try:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8').strip()
                if line:
                    print(f"Received from Arduino: {line}")
                    # Expecting Arduino to output JSON like: {"rep_count": 5, "ax": 0.12, "ay": 9.81, "az": 0.05}
                    data = json.loads(line)
                    
                    response = requests.post(CLOUD_URL, json=data, timeout=5)
                    if response.status_code == 201:
                        print("Synced to Render PostgreSQL successfully.")
                    else:
                        print(f"Server error: {response.status_code}")
        except json.JSONDecodeError:
            print(f"Skipping non-JSON line: {line}")
        except requests.exceptions.RequestException as re:
            print(f"Network error posting to cloud: {re}")
        except Exception as ex:
            print(f"Unexpected error: {ex}")
        
        time.sleep(0.1)

if __name__ == '__main__':
    start_bridge()