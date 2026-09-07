import os, json, math, re, sqlite3
from urllib.parse import parse_qs, urlparse
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from werkzeug.security import generate_password_hash, check_password_hash
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'ulpin_demo.db')
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-change-me')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '')
OPENROUTER_MODEL = os.getenv('OPENROUTER_MODEL', 'openai/gpt-oss-20b')

COORDINATE_PATTERNS = (
    re.compile(r'@(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)'),
    re.compile(r'!3d(-?\d+(?:\.\d+)?)!4d(-?\d+(?:\.\d+)?)'),
    re.compile(r'/search/(-?\d+(?:\.\d+)?),(?:\+|\s*)(-?\d+(?:\.\d+)?)'),
)

DEMO_CENTER = {'lat': 12.9166, 'lng': 77.6229, 'name': 'Silk Board / HSR Layout, Bengaluru'}

SCHEMA = '''
CREATE TABLE IF NOT EXISTS users (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 username TEXT UNIQUE NOT NULL,
 password_hash TEXT NOT NULL,
 role TEXT NOT NULL CHECK(role IN ('admin','surveyor')),
 created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS buildings (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 building_name TEXT NOT NULL,
 ulpin TEXT UNIQUE NOT NULL,
 surveyor_id INTEGER,
 lat REAL NOT NULL,
 lng REAL NOT NULL,
 footprint_w REAL NOT NULL,
 footprint_d REAL NOT NULL,
 ground_elev REAL NOT NULL,
 height REAL NOT NULL,
 floor_height REAL NOT NULL,
 floors INTEGER NOT NULL,
 basement INTEGER NOT NULL DEFAULT 0,
 sanctioned_floors INTEGER NOT NULL,
 usage TEXT NOT NULL,
 address TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'REGISTERED',
 footprint_json TEXT,
 details_json TEXT,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(surveyor_id) REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS units (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 building_id INTEGER NOT NULL,
 floor_no INTEGER NOT NULL,
 unit_code TEXT NOT NULL,
 unit_type TEXT NOT NULL,
 width REAL NOT NULL,
 depth REAL NOT NULL,
 owner_name TEXT,
 legal_status TEXT NOT NULL DEFAULT 'REGISTERED',
 polygon_json TEXT,
 details_json TEXT,
 FOREIGN KEY(building_id) REFERENCES buildings(id)
);
'''

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def ensure_json_columns(conn):
    for table, columns in {
        'buildings': ('footprint_json', 'details_json'),
        'units': ('polygon_json', 'details_json'),
    }.items():
        existing = {row['name'] for row in conn.execute(f'PRAGMA table_info({table})')}
        for column in columns:
            if column not in existing:
                conn.execute(f'ALTER TABLE {table} ADD COLUMN {column} TEXT')

def rectangle_polygon(lat, lng, width, depth):
    """Return a small geographic rectangle in Leaflet [lat, lng] order."""
    lat_delta = float(depth) / 111320
    lng_delta = float(width) / (111320 * max(math.cos(math.radians(lat)), 0.01))
    return [[lat-lat_delta/2, lng-lng_delta/2], [lat-lat_delta/2, lng+lng_delta/2],
            [lat+lat_delta/2, lng+lng_delta/2], [lat+lat_delta/2, lng-lng_delta/2]]

def split_polygon(polygon, count):
    """Split the rectangle into vertical flat polygons for the demo map."""
    west = min(point[1] for point in polygon); east = max(point[1] for point in polygon)
    south = min(point[0] for point in polygon); north = max(point[0] for point in polygon)
    step = (east - west) / max(count, 1)
    return [[[south, west + step * index], [south, west + step * (index + 1)],
             [north, west + step * (index + 1)], [north, west + step * index]]
            for index in range(count)]

def parse_json(value, fallback=None):
    try:
        return json.loads(value) if value else fallback
    except (TypeError, ValueError):
        return fallback

def building_json(row):
    record = dict(row)
    record['footprint'] = parse_json(record.get('footprint_json')) or rectangle_polygon(
        record['lat'], record['lng'], record['footprint_w'], record['footprint_d'])
    record['details'] = parse_json(record.get('details_json'), {})
    return record

def unit_json(row, include_sensitive=False):
    record = dict(row)
    record['polygon'] = parse_json(record.get('polygon_json'))
    record['details'] = parse_json(record.get('details_json'), {})
    if not include_sensitive:
        record.pop('owner_name', None)
        record['details'].pop('owner_name', None)
    return record

def extract_coordinates(value):
    """Resolve a Google Maps URL or coordinate pair to latitude/longitude."""
    value = (value or '').strip()
    if not value:
        raise ValueError('Paste a Google Maps shared URL or enter coordinates.')
    for pattern in COORDINATE_PATTERNS:
        match = pattern.search(value)
        if match:
            lat, lng = float(match.group(1)), float(match.group(2))
            break
    else:
        parsed = urlparse(value)
        query_values = parse_qs(parsed.query)
        candidates = query_values.get('q', []) + query_values.get('query', []) + query_values.get('destination', [])
        match = re.search(r'(-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)', ' '.join(candidates))
        if not match:
            raise ValueError('No latitude and longitude were found in that Maps link.')
        lat, lng = float(match.group(1)), float(match.group(2))
    if not -90 <= lat <= 90 or not -180 <= lng <= 180:
        raise ValueError('The Maps link contains coordinates outside the valid range.')
    return lat, lng

def resolve_maps_url(value):
    """Follow short Google Maps links, then extract coordinates from the final URL."""
    value = (value or '').strip()
    try:
        return extract_coordinates(value)
    except ValueError:
        if not value.startswith(('http://', 'https://')):
            raise
        host = (urlparse(value).hostname or '').lower()
        if host not in {'maps.app.goo.gl', 'maps.google.com', 'www.google.com', 'google.com'}:
            raise ValueError('Use a Google Maps shared URL.')
        try:
            response = requests.get(value, allow_redirects=True, timeout=10,
                                    headers={'User-Agent': '3D-ULPIN-Demo/1.0'})
            response.raise_for_status()
        except requests.RequestException as error:
            raise ValueError(f'Could not open the Maps link: {error}') from error
        return extract_coordinates(response.url)

def init_db():
    conn = db(); conn.executescript(SCHEMA)
    ensure_json_columns(conn)
    # Seed admin and surveyor
    admin = conn.execute('SELECT id FROM users WHERE username=?', ('admin',)).fetchone()
    if not admin:
        conn.execute('INSERT INTO users(username,password_hash,role) VALUES(?,?,?)',
                     ('admin', generate_password_hash('admin123'), 'admin'))
    surveyor = conn.execute('SELECT id FROM users WHERE username=?', ('surveyor1',)).fetchone()
    if not surveyor:
        sid = conn.execute('INSERT INTO users(username,password_hash,role) VALUES(?,?,?)',
                           ('surveyor1', generate_password_hash('survey123'), 'surveyor')).lastrowid
    else: sid = surveyor['id']
    # Demo buildings
    count = conn.execute('SELECT COUNT(*) AS c FROM buildings').fetchone()['c']
    legacy_seed = conn.execute("""SELECT 1 FROM buildings
                                 WHERE typeof(surveyor_id) != 'integer'
                                    OR typeof(sanctioned_floors) != 'integer'
                                 LIMIT 1""").fetchone()
    if count and legacy_seed:
        conn.execute('DELETE FROM units')
        conn.execute('DELETE FROM buildings')
        count = 0
    if count == 0:
        seeds = [
            ('Prestige Demo Tower A', '12912776480001', 12.91655, 77.62265, 22, 30, 892.0, 24.0, 3.0, 8, 1, 7, 'Mixed Use', 'Silk Board Road, Bengaluru'),
            ('Silk Board Residency B', '12912776480002', 12.91705, 77.62325, 18, 24, 891.5, 18.0, 3.0, 6, 0, 6, 'Residential', 'HSR Sector 1, Bengaluru'),
            ('HSR Commercial Block C', '12912776480003', 12.91595, 77.62405, 20, 18, 892.3, 12.0, 3.0, 4, 1, 3, 'Commercial', 'Central Silk Board, Bengaluru'),
        ]
        for s in seeds:
            conn.execute('''INSERT INTO buildings(building_name,ulpin,surveyor_id,lat,lng,footprint_w,footprint_d,ground_elev,height,floor_height,floors,basement,sanctioned_floors,usage,address)
                            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (*s[:2], sid, *s[2:]))
            bid = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
            # Create 2 units per floor + common corridor conceptually
            for f in range(1, s[9] + 1):
                for u in (1,2):
                    conn.execute('''INSERT INTO units(building_id,floor_no,unit_code,unit_type,width,depth,owner_name)
                                    VALUES(?,?,?,?,?,?,?)''',
                                 (bid, f, f'F{f:02d}-U{u:02d}', 'Residential' if s[12]=='Residential' else ('Commercial' if f==1 else 'Residential'), s[5]/2-1, s[6]-2, f'Demo Owner {f}{u}'))
            if s[10]:
                conn.execute('''INSERT INTO units(building_id,floor_no,unit_code,unit_type,width,depth,owner_name)
                                VALUES(?,?,?,?,?,?,?)''', (bid, 0, 'B01-U01', 'Parking', s[5]-2, s[6]-2, 'Common Parking'))
    for row in conn.execute('SELECT * FROM buildings WHERE footprint_json IS NULL').fetchall():
        footprint = rectangle_polygon(row['lat'], row['lng'], row['footprint_w'], row['footprint_d'])
        conn.execute('UPDATE buildings SET footprint_json=?, details_json=? WHERE id=?',
                     (json.dumps(footprint), json.dumps({'source': 'demo-seed'}), row['id']))
    for row in conn.execute('SELECT u.*, b.lat, b.lng, b.footprint_w, b.footprint_d, b.floors FROM units u JOIN buildings b ON b.id=u.building_id WHERE u.polygon_json IS NULL').fetchall():
        footprint = rectangle_polygon(row['lat'], row['lng'], row['footprint_w'], row['footprint_d'])
        polygons = split_polygon(footprint, 2)
        polygon = polygons[(row['id'] - 1) % len(polygons)]
        conn.execute('UPDATE units SET polygon_json=?, details_json=? WHERE id=?',
                     (json.dumps(polygon), json.dumps({'source': 'demo-seed', 'floor': row['floor_no'], 'owner_name': row['owner_name']}), row['id']))
    conn.commit(); conn.close()

init_db()

def login_required(role=None):
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not session.get('user_id'):
                return redirect(url_for('login', next=request.path))
            if role and session.get('role') != role:
                flash('You do not have permission to access that page.', 'error')
                return redirect(url_for('dashboard'))
            return fn(*args, **kwargs)
        return wrapper
    return deco

@app.context_processor
def inject_globals():
    return {'current_user': session.get('username'), 'current_role': session.get('role')}

@app.route('/')
def index():
    conn = db(); buildings = [building_json(row) for row in conn.execute('SELECT * FROM buildings ORDER BY id').fetchall()]; conn.close()
    return render_template('index.html', buildings=buildings, center=DEMO_CENTER)

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip(); password = request.form['password']
        conn = db(); user = conn.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone(); conn.close()
        if user and check_password_hash(user['password_hash'], password):
            session.clear(); session['user_id']=user['id']; session['username']=user['username']; session['role']=user['role']
            return redirect(request.args.get('next') or url_for('dashboard'))
        flash('Invalid credentials.', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear(); return redirect(url_for('index'))

@app.route('/dashboard')
@login_required()
def dashboard():
    conn=db(); buildings=conn.execute('SELECT b.*, u.username AS surveyor FROM buildings b LEFT JOIN users u ON b.surveyor_id=u.id ORDER BY b.id DESC').fetchall(); users=conn.execute('SELECT id,username,role,created_at FROM users ORDER BY id').fetchall(); conn.close()
    return render_template('dashboard.html', buildings=buildings, users=users)

@app.route('/admin/surveyors', methods=['POST'])
@login_required('admin')
def create_surveyor():
    username=request.form['username'].strip(); password=request.form['password']
    if len(username)<3 or len(password)<6:
        flash('Use a username of 3+ characters and a password of 6+ characters.', 'error'); return redirect(url_for('dashboard'))
    conn=db()
    try:
        conn.execute('INSERT INTO users(username,password_hash,role) VALUES(?,?,?)', (username, generate_password_hash(password), 'surveyor')); conn.commit(); flash('Surveyor created.', 'success')
    except sqlite3.IntegrityError:
        flash('Username already exists.', 'error')
    finally: conn.close()
    return redirect(url_for('dashboard'))

@app.route('/surveyor/buildings/new', methods=['GET','POST'])
@login_required('surveyor')
def new_building():
    if request.method == 'POST':
        f=request.form
        try:
            lat, lng = resolve_maps_url(f.get('maps_url')) if f.get('maps_url') else (float(f['lat']), float(f['lng']))
            floors=int(f['floors']); floor_h=float(f['floor_height']); basement=int(f.get('basement','0')); width=float(f['footprint_w']); depth=float(f['footprint_d'])
            height=floors*floor_h
            footprint = rectangle_polygon(lat, lng, width, depth)
            building_details = {'source': 'surveyor', 'maps_url': f.get('maps_url', ''), 'created_by': session['username']}
            conn=db(); conn.execute('''INSERT INTO buildings(building_name,ulpin,surveyor_id,lat,lng,footprint_w,footprint_d,ground_elev,height,floor_height,floors,basement,sanctioned_floors,usage,address,footprint_json,details_json)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (f['building_name'],f['ulpin'],session['user_id'],lat,lng,width,depth,float(f['ground_elev']),height,floor_h,floors,basement,int(f['sanctioned_floors']),f['usage'],f['address'],json.dumps(footprint),json.dumps(building_details)))
            bid=conn.execute('SELECT last_insert_rowid()').fetchone()[0]
            unit_count=max(1,int(f.get('units_per_floor','2')))
            for floor in range(1,floors+1):
                for u in range(1,unit_count+1):
                    unit_width = max(2,width/unit_count-1); unit_depth = max(2,depth-2)
                    unit_polygon = split_polygon(footprint, unit_count)[u-1]
                    owner_name = f.get('owner_name', '').strip() or 'Pending Registration'
                    legal_status = f.get('legal_status', 'REGISTERED')
                    unit_details = {'floor_number': floor, 'owner_name': owner_name, 'owner_status': 'PENDING' if owner_name == 'Pending Registration' else 'DECLARED', 'sensitive': True}
                    conn.execute('INSERT INTO units(building_id,floor_no,unit_code,unit_type,width,depth,owner_name,legal_status,polygon_json,details_json) VALUES(?,?,?,?,?,?,?,?,?,?)', (bid,floor,f'F{floor:02d}-U{u:02d}', 'Commercial' if (floor==1 and f['usage']=='Commercial') else 'Residential', unit_width,unit_depth, owner_name, legal_status,json.dumps(unit_polygon),json.dumps(unit_details)))
            if basement:
                conn.execute('INSERT INTO units(building_id,floor_no,unit_code,unit_type,width,depth,owner_name,polygon_json,details_json) VALUES(?,?,?,?,?,?,?,?,?)', (bid,0,'B01-U01','Parking',max(2,width-2),max(2,depth-2),'Common Parking',json.dumps(footprint),json.dumps({'floor_number': 0, 'owner_name': 'Common Parking', 'owner_status': 'COMMON'})))
            conn.commit(); conn.close(); flash('Building registered and volumetric units generated.', 'success'); return redirect(url_for('dashboard'))
        except sqlite3.IntegrityError:
            flash('ULPIN must be unique.', 'error')
        except Exception as e:
            flash(f'Invalid building data: {e}', 'error')
    return render_template('new_building.html', center=DEMO_CENTER)

@app.get('/api/maps/resolve')
def maps_resolve():
    try:
        lat, lng = resolve_maps_url(request.args.get('url'))
        return jsonify({'ok': True, 'lat': lat, 'lng': lng})
    except ValueError as error:
        return jsonify({'ok': False, 'error': str(error)}), 400

@app.route('/api/buildings')
def api_buildings():
    conn=db(); rows=conn.execute('SELECT * FROM buildings ORDER BY id').fetchall(); conn.close(); return jsonify([building_json(row) for row in rows])

@app.route('/api/buildings/<int:bid>')
def api_building(bid):
    conn=db(); b=conn.execute('SELECT b.*, u.username AS surveyor FROM buildings b LEFT JOIN users u ON b.surveyor_id=u.id WHERE b.id=?',(bid,)).fetchone(); units=conn.execute('SELECT * FROM units WHERE building_id=? ORDER BY floor_no,id',(bid,)).fetchall(); conn.close()
    if not b: return jsonify({'error':'not found'}),404
    unit_records = [unit_json(unit) for unit in units]
    floors = {}
    for unit in unit_records:
        floors.setdefault(str(unit['floor_no']), []).append(unit)
    return jsonify({'building':building_json(b),'units':unit_records,'floors':floors})

@app.get('/api/buildings/<int:bid>/record')
@login_required()
def private_building_record(bid):
    conn=db(); b=conn.execute('SELECT * FROM buildings WHERE id=?',(bid,)).fetchone(); units=conn.execute('SELECT * FROM units WHERE building_id=? ORDER BY floor_no,id',(bid,)).fetchall(); conn.close()
    if not b: return jsonify({'error':'not found'}),404
    return jsonify({'building': building_json(b), 'units': [unit_json(unit, include_sensitive=True) for unit in units], 'sensitive': True})

@app.post('/api/buildings/<int:bid>/floor-record')
@login_required()
def update_floor_record(bid):
    payload = request.get_json(silent=True) or {}
    floor_no = payload.get('floor_no')
    unit_code = (payload.get('unit_code') or '').strip()
    try:
        floor_no = int(floor_no)
        latitude = float(payload['latitude'])
        longitude = float(payload['longitude'])
        width = float(payload['width'])
        depth = float(payload['depth'])
    except (KeyError, TypeError, ValueError):
        return jsonify({'ok': False, 'error': 'Floor, coordinates, width, and depth are required.'}), 400
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180 or width <= 0 or depth <= 0:
        return jsonify({'ok': False, 'error': 'Coordinates or dimensions are outside the valid range.'}), 400
    conn = db()
    building = conn.execute('SELECT * FROM buildings WHERE id=?', (bid,)).fetchone()
    unit = conn.execute('SELECT * FROM units WHERE building_id=? AND floor_no=? AND unit_code=?', (bid, floor_no, unit_code)).fetchone()
    if not building or not unit:
        conn.close()
        return jsonify({'ok': False, 'error': 'Building floor record not found.'}), 404
    polygon = rectangle_polygon(latitude, longitude, width, depth)
    details = parse_json(unit['details_json'], {})
    owner_name = (payload.get('owner_name') or unit['owner_name'] or '').strip()
    legal_status = payload.get('legal_status', unit['legal_status'])
    details.update({'floor_number': floor_no, 'latitude': latitude, 'longitude': longitude, 'width': width, 'depth': depth, 'owner_name': owner_name, 'legal_status': legal_status, 'updated_by': session['username']})
    conn.execute('UPDATE units SET width=?, depth=?, owner_name=?, legal_status=?, polygon_json=?, details_json=? WHERE id=?',
                 (width, depth, owner_name, legal_status, json.dumps(polygon), json.dumps(details), unit['id']))
    conn.commit()
    updated = conn.execute('SELECT * FROM units WHERE id=?', (unit['id'],)).fetchone()
    conn.close()
    return jsonify({'ok': True, 'unit': unit_json(updated, include_sensitive=True)})

@app.route('/view/<int:bid>')
def view3d(bid):
    conn=db(); row=conn.execute('SELECT * FROM buildings WHERE id=?',(bid,)).fetchone(); conn.close()
    b = dict(row) if row else None
    if not b: return 'Not found',404
    return render_template('viewer3d.html', building=b)

@app.get('/3d')
def city3d():
    conn = db(); rows = conn.execute('SELECT * FROM buildings ORDER BY id').fetchall(); conn.close()
    return render_template('city3d.html', buildings=[building_json(row) for row in rows], center=DEMO_CENTER)

@app.post('/api/ai/analyze')
def ai_analyze():
    if not OPENROUTER_API_KEY:
        return jsonify({'ok':False,'error':'OPENROUTER_API_KEY is not configured on the server.'}), 400
    payload=request.get_json(silent=True) or {}; bid=payload.get('building_id')
    conn=db(); b=conn.execute('SELECT b.*, u.username AS surveyor FROM buildings b LEFT JOIN users u ON b.surveyor_id=u.id WHERE b.id=?',(bid,)).fetchone(); units=conn.execute('SELECT floor_no,unit_code,unit_type,legal_status FROM units WHERE building_id=? ORDER BY floor_no,id',(bid,)).fetchall(); conn.close()
    if not b: return jsonify({'ok':False,'error':'Building not found'}),404
    building={'name':b['building_name'],'ulpin':b['ulpin'],'floors':b['floors'],'sanctioned_floors':b['sanctioned_floors'],'height_m':b['height'],'floor_height_m':b['floor_height'],'usage':b['usage'],'units':[dict(x) for x in units]}
    prompt='''You are an AI assistant inside a 3D cadastral PoC. Analyze the supplied demo building record. Do NOT claim this is an official government record. Return concise JSON with keys: summary, risks, validation, next_steps. Mention if observed floors exceed sanctioned floors. Treat missing ownership/legal details as demo placeholders.'''
    body={'model':OPENROUTER_MODEL,'messages':[{'role':'system','content':prompt},{'role':'user','content':json.dumps(building)}], 'temperature':0.2}
    try:
        r=requests.post('https://openrouter.ai/api/v1/chat/completions',headers={'Authorization':f'Bearer {OPENROUTER_API_KEY}','Content-Type':'application/json','HTTP-Referer':os.getenv('APP_BASE_URL',''),'X-Title':'3D ULPIN Demo'},json=body,timeout=40)
        if r.status_code >= 400:
            return jsonify({'ok':False,'error':f'OpenRouter returned {r.status_code}: {r.text[:600]}'}),502
        content=r.json()['choices'][0]['message']['content']
    except requests.RequestException as error:
        return jsonify({'ok':False,'error':f'Could not reach OpenRouter: {error}'}),502
    except (KeyError, IndexError, TypeError, ValueError):
        return jsonify({'ok':False,'error':'OpenRouter returned an unexpected response.'}),502
    return jsonify({'ok':True,'content':content,'model':OPENROUTER_MODEL})

if __name__ == '__main__':
    app.run(host='0.0.0.0',port=int(os.getenv('PORT','5000')),debug=True)
