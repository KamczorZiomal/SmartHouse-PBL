from flask import Flask, render_template, jsonify
from models import db, SensorData

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sensors.db'
db.init_app(app)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/data')
def get_data():
    data = SensorData.query.order_by(SensorData.timestamp.desc()).limit(20).all()
    result = []
    latest = None
    oldest = None
    if data:
        latest = {
            'temperature': data[0].temperature,
            'humidity': data[0].humidity,
            'air_quality': data[0].air_quality,
            'light_percent': data[0].light_percent
        }
        oldest = {
            'temperature': data[-1].temperature,
            'humidity': data[-1].humidity,
            'air_quality': data[-1].air_quality,
            'light_percent': data[-1].light_percent
        }
        history = [{
            'timestamp': entry.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            'temperature': entry.temperature,
            'humidity': entry.humidity,
            'air_quality': entry.air_quality,
            'light_percent': entry.light_percent
        } for entry in reversed(data)]
        result = {'latest': latest, 'oldest': oldest, 'history': history}
    return jsonify(result)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
