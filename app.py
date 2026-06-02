from flask import Flask, render_template, jsonify, request, make_response
import json, os, threading

app = Flask(__name__)

@app.after_request
def add_headers(response):
    response.headers['X-Frame-Options'] = 'ALLOWALL'
    response.headers['Content-Security-Policy'] = "frame-ancestors *"
    return response
DATA_FILE = os.path.join(os.path.dirname(__file__), 'data.json')

# Load data.json once at startup into memory
_data_cache = None
_cache_lock = threading.Lock()

def get_cached_data():
    global _data_cache
    if _data_cache is None:
        with _cache_lock:
            if _data_cache is None:
                with open(DATA_FILE) as f:
                    _data_cache = json.load(f)
                # Try sheets refresh in background — never blocks requests
                threading.Thread(target=_refresh_from_sheets, daemon=True).start()
    return _data_cache

def _refresh_from_sheets():
    global _data_cache
    try:
        from sheets_loader import load_from_sheets
        import copy
        merged, err = load_from_sheets(copy.deepcopy(_data_cache))
        if not err:
            with _cache_lock:
                _data_cache = merged
            print("[app] Sheets data loaded in background")
        else:
            print(f"[app] Sheets skipped: {err}")
    except Exception as e:
        print(f"[app] Sheets error: {e}")

def save_data(data):
    global _data_cache
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    with _cache_lock:
        _data_cache = data

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/api/data')
def api_data():
    return jsonify(get_cached_data())

@app.route('/api/refresh', methods=['POST'])
def refresh():
    threading.Thread(target=_refresh_from_sheets, daemon=True).start()
    return jsonify({"status": "refreshing"})

@app.route('/api/fabs', methods=['GET'])
def get_fabs():
    return jsonify(get_cached_data()['fabs'])

@app.route('/api/fabs', methods=['POST'])
def add_fab():
    data = get_cached_data()
    fab = request.get_json()
    for field in ['id','company','loc','name']:
        if not fab.get(field):
            return jsonify({'error': f'Missing: {field}'}), 400
    if any(f['id']==fab['id'] for f in data['fabs']):
        return jsonify({'error': 'ID exists'}), 409
    fab.setdefault('years', {})
    data['fabs'].append(fab)
    save_data(data)
    return jsonify(fab), 201

@app.route('/api/fabs/<fab_id>', methods=['GET','PUT','DELETE'])
def fab(fab_id):
    data = get_cached_data()
    f = next((x for x in data['fabs'] if x['id']==fab_id), None)
    if not f: return jsonify({'error':'Not found'}), 404
    if request.method=='GET': return jsonify(f)
    if request.method=='PUT':
        u = request.get_json(); u.pop('id',None); f.update(u)
        save_data(data); return jsonify(f)
    data['fabs'] = [x for x in data['fabs'] if x['id']!=fab_id]
    save_data(data); return jsonify({'deleted':fab_id})

@app.route('/api/fabs/<fab_id>/years/<int:year>', methods=['PUT','DELETE'])
def fab_year(fab_id, year):
    data = get_cached_data()
    f = next((x for x in data['fabs'] if x['id']==fab_id), None)
    if not f: return jsonify({'error':'Not found'}), 404
    if request.method=='PUT':
        b = request.get_json()
        if 'node' not in b: return jsonify({'error':'Missing node'}), 400
        f['years'][str(year)] = b['node']
    else:
        f['years'].pop(str(year), None)
    save_data(data); return jsonify(f)

@app.route('/api/companies', methods=['GET','POST'])
def companies():
    data = get_cached_data()
    if request.method=='GET': return jsonify(data['companies'])
    b = request.get_json()
    cid = b.pop('id', None)
    if not cid: return jsonify({'error':'Missing id'}), 400
    if cid in data['companies']: return jsonify({'error':'Exists'}), 409
    data['companies'][cid] = b
    save_data(data); return jsonify({cid:b}), 201

@app.route('/api/companies/<cid>', methods=['PUT','DELETE'])
def company(cid):
    data = get_cached_data()
    if cid not in data['companies']: return jsonify({'error':'Not found'}), 404
    if request.method=='PUT':
        u=request.get_json(); u.pop('id',None)
        data['companies'][cid].update(u)
        save_data(data); return jsonify(data['companies'][cid])
    data['fabs']=[f for f in data['fabs'] if f['company']!=cid]
    del data['companies'][cid]; save_data(data)
    return jsonify({'deleted':cid})

@app.route('/api/milestones', methods=['GET'])
def get_milestones():
    return jsonify(get_cached_data()['milestones'])

@app.route('/api/milestones/<int:year>', methods=['PUT','DELETE'])
def milestone(year):
    data = get_cached_data()
    if request.method=='PUT':
        items=request.get_json()
        data['milestones'][str(year)]=items
        save_data(data); return jsonify({str(year):items})
    data['milestones'].pop(str(year),None)
    save_data(data); return jsonify({'deleted':str(year)})

@app.route('/api/coords', methods=['GET'])
def coords():
    return jsonify(get_cached_data()['coords'])

if __name__ == '__main__':
    app.run(debug=True, port=5000)
