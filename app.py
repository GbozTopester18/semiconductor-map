from flask import Flask, render_template, jsonify, request
import json, os

app = Flask(__name__)
DATA_FILE = os.path.join(os.path.dirname(__file__), 'data.json')

def load_data():
    try:
        from sheets_loader import get_data
        with open(DATA_FILE) as f:
            base = json.load(f)
        return get_data(base)
    except Exception as e:
        print(f"[app] Sheets loader error: {e} — using local data.json")
        with open(DATA_FILE) as f:
            return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/api/data')
def get_data():
    return jsonify(load_data())

@app.route('/api/refresh', methods=['POST'])
def refresh():
    try:
        from sheets_loader import _cache
        _cache["ts"] = 0
    except:
        pass
    return jsonify({"status": "refreshed"})

@app.route('/api/fabs', methods=['GET'])
def get_fabs():
    return jsonify(load_data()['fabs'])

@app.route('/api/fabs', methods=['POST'])
def add_fab():
    data = load_data()
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
    data = load_data()
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
    data = load_data()
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
    data = load_data()
    if request.method=='GET': return jsonify(data['companies'])
    b = request.get_json()
    cid = b.pop('id', None)
    if not cid: return jsonify({'error':'Missing id'}), 400
    if cid in data['companies']: return jsonify({'error':'Exists'}), 409
    data['companies'][cid] = b
    save_data(data); return jsonify({cid:b}), 201

@app.route('/api/companies/<cid>', methods=['PUT','DELETE'])
def company(cid):
    data = load_data()
    if cid not in data['companies']: return jsonify({'error':'Not found'}), 404
    if request.method=='PUT':
        u=request.get_json(); u.pop('id',None); data['companies'][cid].update(u)
        save_data(data); return jsonify(data['companies'][cid])
    data['fabs']=[f for f in data['fabs'] if f['company']!=cid]
    del data['companies'][cid]; save_data(data); return jsonify({'deleted':cid})

@app.route('/api/milestones', methods=['GET'])
def get_milestones():
    return jsonify(load_data()['milestones'])

@app.route('/api/milestones/<int:year>', methods=['PUT','DELETE'])
def milestone(year):
    data = load_data()
    if request.method=='PUT':
        items=request.get_json()
        data['milestones'][str(year)]=items; save_data(data)
        return jsonify({str(year):items})
    data['milestones'].pop(str(year),None); save_data(data)
    return jsonify({'deleted':str(year)})

@app.route('/api/coords', methods=['GET'])
def coords():
    return jsonify(load_data()['coords'])

if __name__ == '__main__':
    app.run(debug=True, port=5000)
