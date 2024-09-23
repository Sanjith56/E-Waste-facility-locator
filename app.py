from flask import Flask, request, jsonify, render_template
import mysql.connector
from mysql.connector import errorcode
import os

app = Flask(__name__)

# Database configuration from environment variables
DB_CONFIG = {
    'user': os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', 'root'),
    'host': os.getenv('MYSQL_HOST', 'localhost'),
    'database': os.getenv('MYSQL_DATABASE', 'ewaste_locator'),
}

def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Something is wrong with your user name or password")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Database does not exist")
        else:
            print(err)
        return None

@app.route('/maps')
def maps():
    return render_template('maps.html')

@app.route('/get_locations', methods=['GET'])
def get_locations():
    conn = get_db_connection()
    if conn is None:
        return jsonify({'error': 'Database connection failed'}), 500

    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM ewaste_locations')
    locations = cursor.fetchall()
    cursor.close()
    conn.close()

    return jsonify(locations), 200

@app.route('/add_location', methods=['POST'])
def add_location():
    data = request.json
    if not data:
        return jsonify({'error': 'Request must be JSON'}), 400

    name = data.get('name')
    address = data.get('address')
    latitude = data.get('latitude')
    longitude = data.get('longitude')

    if not all([name, address, latitude, longitude]):
        return jsonify({'error': 'Missing data'}), 400

    conn = get_db_connection()
    if conn is None:
        return jsonify({'error': 'Database connection failed'}), 500

    cursor = conn.cursor()
    cursor.execute('INSERT INTO ewaste_locations (name, address, latitude, longitude) VALUES (%s, %s, %s, %s)',
                   (name, address, latitude, longitude))
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({'message': 'Location added successfully'}), 201

@app.route('/find_nearest', methods=['GET'])
def find_nearest():
    user_lat = float(request.args.get('latitude'))
    user_lon = float(request.args.get('longitude'))

    conn = get_db_connection()
    if conn is None:
        return jsonify({'error': 'Database connection failed'}), 500

    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM ewaste_locations')
    locations = cursor.fetchall()
    cursor.close()
    conn.close()

    def calculate_distance(lat1, lon1, lat2, lon2):
        from math import radians, cos, sin, sqrt, atan2

        R = 6371  # Earth radius in kilometers
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        return R * c

    nearest_location = None
    min_distance = float('inf')

    for loc in locations:
        distance = calculate_distance(user_lat, user_lon, loc['latitude'], loc['longitude'])
        if distance < min_distance:
            min_distance = distance
            nearest_location = loc

    if nearest_location:
        return jsonify(nearest_location), 200
    else:
        return jsonify({'message': 'No locations found'}), 404

if __name__ == '__main__':
    app.run(debug=True)
