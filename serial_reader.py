import serial
from time import sleep
from datetime import datetime
from models import SensorData, db
from flask import Flask

# Setup Flask just for DB
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sensors.db'
db.init_app(app)

# Setup Serial
ser = serial.Serial('COM3', 9600)  # Replace COM3 with your port


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
                lux = int(buffer.split("(")[1].split("lux")[0].strip())

                with app.app_context():
                    new_data = SensorData(
                        temperature=temp,
                        humidity=hum,
                        air_quality=air_quality,
                        light_percent=light_percent,
                        lux=lux,
                        timestamp=datetime.now()
                    )
                    db.session.add(new_data)
                    db.session.commit()

                print(f"Saved: Temp={temp}C, Humidity={hum}%, Air={air_quality}%, Light={light_percent}%, Lux={lux}")
            except Exception as e:
                print(f"Error parsing buffer:\n{buffer}\nError: {e}")


if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Make sure DB and tables are created
    read_serial()
