import socket
import threading
from datetime import datetime

import serial
from flask import Flask

from models import SensorData, db

# Setup Flask just for DB
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sensors.db'
db.init_app(app)

# Setup Serial
ser = serial.Serial('COM3', 9600)  # Replace COM3 with your port

# Setup Socket Server for commands
HOST = '127.0.0.1'  # Standard loopback interface address (localhost)
PORT = 65432  # Port to listen on (non-privileged ports are > 1023)
socket_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
socket_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
socket_server.bind((HOST, PORT))
socket_server.listen()


def read_serial():
    buffer = ""
    while True:
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        if line.startswith("===="):
            buffer = ""
        buffer += line + "\n"

        if "lux)" in line:
            try:
                temp = float(buffer.split("Temperatura:")[1].split("°C")[0].strip())
                hum = float(buffer.split("Wilgotność:")[1].split("%")[0].strip())
                air_quality = float(buffer.split("Jakość powietrza:")[1].split("%")[0].strip())
                light_percent = float(buffer.split("Natężenie światła:")[1].split("%")[0].strip())
                lux = float(buffer.split("(")[1].split("lux")[0].strip())

                # Parse motion detection status
                motion_detected = False
                if "Wykrycie ruchu:" in buffer:
                    motion_line = buffer.split("Wykrycie ruchu:")[1].split("\n")[0].strip()
                    motion_detected = "TAK" in motion_line

                with app.app_context():
                    new_data = SensorData(
                        temperature=temp,
                        humidity=hum,
                        air_quality=air_quality,
                        light_percent=light_percent,
                        lux=lux,
                        motion_detected=motion_detected,
                        timestamp=datetime.now()
                    )
                    db.session.add(new_data)
                    db.session.commit()

                print(f"Saved: Temp={temp}C, Humidity={hum}%, Air={air_quality}%, Light={light_percent}%, Lux={lux}")
            except Exception as e:
                print(f"Error parsing buffer:\n{buffer}\nError: {e}")


def handle_socket_connections():
    """
    Handle socket connections from app.py and forward commands to the serial port
    """
    while True:
        conn, addr = socket_server.accept()
        print(f"Connected by {addr}")
        with conn:
            while True:
                try:
                    data = conn.recv(1024)
                    if not data:
                        break

                    # Decode the command
                    command = data.decode('utf-8')
                    print(f"Received command: {command}")

                    # Handle special commands
                    if command.strip() == "CHECK_CONNECTION":
                        conn.sendall(b"Connection OK")
                        continue

                    # Send the command to the Arduino
                    ser.write(data)

                    # Send a response back to app.py
                    conn.sendall(b"Command sent to Arduino")
                except Exception as e:
                    print(f"Socket error: {e}")
                    break


if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Make sure DB and tables are created

    # Start the socket server in a separate thread
    socket_thread = threading.Thread(target=handle_socket_connections, daemon=True)
    socket_thread.start()

    # Start reading from the serial port in the main thread
    read_serial()
