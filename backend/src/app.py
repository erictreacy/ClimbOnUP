from flask import Flask, jsonify
from flask_cors import CORS
import duckdb

app = Flask(__name__)
CORS(app)

# Connect to the DuckDB database
conn = duckdb.connect('climbing.db')

@app.route('/api/areas', methods=['GET'])
def get_areas():
    try:
        # Execute query to get all areas with their routes
        conn.execute('''
            SELECT 
                a.*,
                COUNT(r.id) as route_count
            FROM climbing_areas a
            LEFT JOIN routes r ON r.area_id = a.id
            GROUP BY a.id
        ''')
        areas = [dict(row) for row in conn.fetchall()]
        
        return jsonify({'areas': areas})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/routes', methods=['GET'])
def get_routes():
    try:
        # Get all routes with their photos
        conn.execute('''
            SELECT 
                r.*,
                array_agg(json_object(
                    'url', p.url,
                    'caption', p.caption
                )) as photos
            FROM routes r
            LEFT JOIN route_photos p ON p.route_id = r.id
            GROUP BY r.id
        ''')
        routes = [dict(row) for row in conn.fetchall()]
        
        return jsonify({'routes': routes})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
