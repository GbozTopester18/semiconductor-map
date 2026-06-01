from flask import Flask, render_template, jsonify, request
import json
import os

app = Flask(__name__)

DATA_FILE = os.path.join(os.path.dirname(__file__), 'data.json')

# Try to import sheets loader
try:
    from sheets_loader import get_data as get_sheets_data
    USE_SHEETS = True
    print("[app] Google Sheets loader enabled")
except ImportError:
    USE_SHEETS = False
    print("[app] Using local data.json only")


def load_data():
    with open(DATA_FILE, 'r') as f:
        base = json.load(f)
    if USE_SHEETS:
        return get_sheets_data(base)
    return base


def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)


# ── pages ─────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')


# ── data API ──────────────────────────────────────────────────────────────────
@app.route('/api/data', methods=['GET'])
def get_data():
    return jsonify(load_data())

@app.route('/api/refresh', methods=['POST'])
def refresh():
    """Force a refresh from Google Sheets (clears cache)."""
    if USE_SHEETS:
        from sheets_loader import _cache
        _cache["ts"] = 0  # expire cache
    return jsonify({"status": "refreshed"})


# ── FAB CRUD ─────────────────────────────────────────────────────────────────
@app.route('/api/fabs', methods=['GET'])
def get_fabs():
    return jsonify(load_data()['fabs'])

@app.route('/api/fabs', methods=['POST'])
def add_fab():
    data = load_data()
    fab = request.get_json()
    required = ['id', 'company', 'loc', 'name']
    for field in required:
        if not fab.get(field):
            return jsonify({'error': f'Missing field: {field}'}), 400
    if any(f['id'] == fab['id'] for f in data['fabs']):
        return jsonify({'error': f"Fab id '{fab['id']}' already exists"}), 409
    fab.setdefault('years', {})
    data['fabs'].append(fab)
    save_data(data)
    return jsonify(fab), 201

@app.route('/api/fabs/<fab_id>', methods=['GET'])
def get_fab(fab_id):
    data = load_data()
    fab = next((f for f in data['fabs'] if f['id'] == fab_id), None)
    if not fab:
        return jsonify({'error': 'Not found'}), 404
    return jsonify(fab)

@app.route('/api/fabs/<fab_id>', methods=['PUT'])
def update_fab(fab_id):
    data = load_data()
    fab = next((f for f in data['fabs'] if f['id'] == fab_id), None)
    if not fab:
        return jsonify({'error': 'Not found'}), 404
    updates = request.get_json()
    updates.pop('id', None)
    fab.update(updates)
    save_data(data)
    return jsonify(fab)

@app.route('/api/fabs/<fab_id>', methods=['DELETE'])
def delete_fab(fab_id):
    data = load_data()
    original_len = len(data['fabs'])
    data['fabs'] = [f for f in data['fabs'] if f['id'] != fab_id]
    if len(data['fabs']) == original_len:
        return jsonify({'error': 'Not found'}), 404
    save_data(data)
    return jsonify({'deleted': fab_id})

@app.route('/api/fabs/<fab_id>/years/<int:year>', methods=['PUT'])
def set_year_node(fab_id, year):
    data = load_data()
    fab = next((f for f in data['fabs'] if f['id'] == fab_id), None)
    if not fab:
        return jsonify({'error': 'Not found'}), 404
    body = request.get_json()
    if 'node' not in body:
        return jsonify({'error': 'Missing "node" field'}), 400
    fab['years'][str(year)] = body['node']
    save_data(data)
    return jsonify(fab)

@app.route('/api/fabs/<fab_id>/years/<int:year>', methods=['DELETE'])
def delete_year_node(fab_id, year):
    data = load_data()
    fab = next((f for f in data['fabs'] if f['id'] == fab_id), None)
    if not fab:
        return jsonify({'error': 'Not found'}), 404
    fab['years'].pop(str(year), None)
    save_data(data)
    return jsonify(fab)


# ── COMPANIES ─────────────────────────────────────────────────────────────────
@app.route('/api/companies', methods=['GET'])
def get_companies():
    return jsonify(load_data()['companies'])

@app.route('/api/companies', methods=['POST'])
def add_company():
    data = load_data()
    body = request.get_json()
    company_id = body.pop('id', None)
    if not company_id:
        return jsonify({'error': 'Missing "id" field'}), 400
    if company_id in data['companies']:
        return jsonify({'error': f"Company '{company_id}' already exists"}), 409
    for field in ['color', 'cat', 'full', 'origin']:
        if field not in body:
            return jsonify({'error': f'Missing field: {field}'}), 400
    data['companies'][company_id] = body
    save_data(data)
    return jsonify({company_id: body}), 201

@app.route('/api/companies/<company_id>', methods=['PUT'])
def update_company(company_id):
    data = load_data()
    if company_id not in data['companies']:
        return jsonify({'error': 'Not found'}), 404
    updates = request.get_json()
    updates.pop('id', None)
    data['companies'][company_id].update(updates)
    save_data(data)
    return jsonify(data['companies'][company_id])

@app.route('/api/companies/<company_id>', methods=['DELETE'])
def delete_company(company_id):
    data = load_data()
    if company_id not in data['companies']:
        return jsonify({'error': 'Not found'}), 404
    data['fabs'] = [f for f in data['fabs'] if f['company'] != company_id]
    del data['companies'][company_id]
    save_data(data)
    return jsonify({'deleted': company_id})


# ── MILESTONES ────────────────────────────────────────────────────────────────
@app.route('/api/milestones', methods=['GET'])
def get_milestones():
    return jsonify(load_data()['milestones'])

@app.route('/api/milestones/<int:year>', methods=['PUT'])
def set_milestones(year):
    data = load_data()
    items = request.get_json()
    if not isinstance(items, list):
        return jsonify({'error': 'Body must be a JSON array of strings'}), 400
    data['milestones'][str(year)] = items
    save_data(data)
    return jsonify({str(year): items})


# ── COORDS ────────────────────────────────────────────────────────────────────
@app.route('/api/coords', methods=['GET'])
def get_coords():
    return jsonify(load_data()['coords'])


if __name__ == '__main__':
    app.run(debug=True, port=5000)
