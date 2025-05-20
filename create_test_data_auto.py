# Kod odpowiedzialny za stworzenie testowej bazy danych

import random
import datetime
from flask import Flask
from models import db, SensorData

# Create a Flask app instance
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sensors.db'
db.init_app(app)


def generate_random_sensor_data(num_entries=100):
    """Generate random sensor data entries."""
    data = []
    # Start time: 24 hours ago
    start_time = datetime.datetime.now() - datetime.timedelta(days=1)

    for i in range(num_entries):
        # Create timestamps at regular intervals
        timestamp = start_time + datetime.timedelta(minutes=i * 15)

        # Generate random sensor values within realistic ranges
        temperature = round(random.uniform(18.0, 28.0), 1)  # 18-28°C
        humidity = round(random.uniform(30.0, 70.0), 1)  # 30-70%
        air_quality = round(random.uniform(0.0, 100.0), 1)  # 0-100 (arbitrary scale)
        light_percent = round(random.uniform(0.0, 100.0), 1)  # 0-100%
        lux = int(random.uniform(0, 1000))  # 0-1000 lux
        motion_detected = random.choice([True, False])  # Random motion detection status

        # Create a SensorData object
        sensor_data = SensorData(
            temperature=temperature,
            humidity=humidity,
            air_quality=air_quality,
            light_percent=light_percent,
            lux=lux,
            motion_detected=motion_detected,
            timestamp=timestamp
        )
        data.append(sensor_data)

    return data


def main():
    """Main function to create and populate the database."""
    with app.app_context():
        # Create tables if they don't exist
        db.create_all()

        try:
            # Check if there's already data in the database
            existing_data_count = SensorData.query.count()
            if existing_data_count > 0:
                print(f"Database already contains {existing_data_count} entries. Clearing existing data...")
                # Delete all existing data
                SensorData.query.delete()
                db.session.commit()
                print("Existing data cleared.")
        except Exception as e:
            print(f"Error accessing database: {e}")
            print("Recreating database tables...")
            # Drop all tables and recreate them
            db.drop_all()
            db.create_all()
            print("Database tables recreated.")

        # Generate and add new test data
        print("Generating test data...")
        test_data = generate_random_sensor_data(100)  # Generate 100 entries

        # Add all entries to the database
        db.session.add_all(test_data)
        db.session.commit()

        print(f"Successfully added {len(test_data)} test data entries to the database.")
        print("Database is ready for testing!")


if __name__ == "__main__":
    main()
