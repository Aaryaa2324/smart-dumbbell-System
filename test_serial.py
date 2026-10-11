import time
import serial

# Change to COM4 or COM5 if your Arduino is on a different port
PORT = "COM3"
BAUD = 115200

print(f"Opening {PORT} at {BAUD} baud...")
try:
  ser = serial.Serial(PORT, BAUD, timeout=1)
  print("Port opened! Listening for raw data...")
  while True:
    line = ser.readline()
    if line:
      print("RAW DATA RECEIVED:", line)
    else:
      print("... waiting for Arduino data ...")
    time.sleep(0.5)
except Exception as e:
  print("Error opening port:", e)
  