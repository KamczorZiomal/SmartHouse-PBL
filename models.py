from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class SensorData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    temperature = db.Column(db.Float, nullable=False)
    humidity = db.Column(db.Float, nullable=False)
    air_quality = db.Column(db.Float, nullable=False)
    light_percent = db.Column(db.Float, nullable=False)
    lux = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
