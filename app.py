from flask import Flask, render_template, jsonify, request
import json
import os

app = Flask(__name__)

DATA_FILE = os.path.join(os.path.dirname(__file__), 'data.json')


# ── helpers ──────────────────────────────────────────────────────────────────

def load_data():
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

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
    """Return the full dataset."""
    return jsonify(load_data())


# ── FAB CRUD ─────────────────────────────────────────────────────────────────

@app.route('/api/fabs', methods=['GET'])
def get_fabs():
    data = load_data()
    return jsonify(data['fabs'])

@app.route('/api/fabs', methods=['POST'])
def add_fab():
    """Add a new fab. Body: { id, company, loc, name, years:{} }"""
    data = load_data()
    fab = request.get_json()

    # Basic validation
    required = ['id', 'company', 'loc', 'name']
    for field in required:
        if not fab.get(field):
            return jsonify({'error': f'Missing field: {field}'}), 400

    if any(f['id'] == fab['id'] for f in data['fabs']):
        return jsonify({'error': f"Fab id '{fab['id']}' already exists"}), 409

    if fab['company'] not in data['companies']:
        return jsonify({'error': f"Unknown company '{fab['company']}'"}), 400

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
    """Update a fab's fields (name, loc, years, etc.)"""
    data = load_data()
    fab = next((f for f in data['fabs'] if f['id'] == fab_id), None)
    if not fab:
        return jsonify({'error': 'Not found'}), 404

    updates = request.get_json()
    # Don't allow changing the id
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


# ── NODE (year entry) CRUD ────────────────────────────────────────────────────

@app.route('/api/fabs/<fab_id>/years', methods=['PUT'])
def update_years(fab_id):
    """
    Set the full years dict for a fab.
    Body: { "2020": "7nm", "2021": "5nm", ... }
    """
    data = load_data()
    fab = next((f for f in data['fabs'] if f['id'] == fab_id), None)
    if not fab:
        return jsonify({'error': 'Not found'}), 404

    years = request.get_json()
    if not isinstance(years, dict):
        return jsonify({'error': 'Body must be a JSON object of year→node strings'}), 400

    fab['years'] = {str(k): v for k, v in years.items()}
    save_data(data)
    return jsonify(fab)

@app.route('/api/fabs/<fab_id>/years/<int:year>', methods=['PUT'])
def set_year_node(fab_id, year):
    """
    Set or update a single year's node for a fab.
    Body: { "node": "3nm" }
    """
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
    """Remove a fab from a specific year (fab goes dark that year)."""
    data = load_data()
    fab = next((f for f in data['fabs'] if f['id'] == fab_id), None)
    if not fab:
        return jsonify({'error': 'Not found'}), 404

    fab['years'].pop(str(year), None)
    save_data(data)
    return jsonify(fab)


# ── COMPANY CRUD ──────────────────────────────────────────────────────────────

@app.route('/api/companies', methods=['GET'])
def get_companies():
    data = load_data()
    return jsonify(data['companies'])

@app.route('/api/companies', methods=['POST'])
def add_company():
    """Body: { id(key), color, cat, full, origin }"""
    data = load_data()
    body = request.get_json()

    company_id = body.pop('id', None)
    if not company_id:
        return jsonify({'error': 'Missing "id" field'}), 400
    if company_id in data['companies']:
        return jsonify({'error': f"Company '{company_id}' already exists"}), 409

    required = ['color', 'cat', 'full', 'origin']
    for field in required:
        if field not in body:
            return jsonify({'error': f'Missing field: {field}'}), 400
    if body['cat'] not in ('foundry', 'memory', 'osat'):
        return jsonify({'error': 'cat must be foundry, memory, or osat'}), 400

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
    # Also remove all fabs that belong to this company
    data['fabs'] = [f for f in data['fabs'] if f['company'] != company_id]
    del data['companies'][company_id]
    save_data(data)
    return jsonify({'deleted': company_id})


# ── MILESTONES CRUD ───────────────────────────────────────────────────────────

@app.route('/api/milestones', methods=['GET'])
def get_milestones():
    data = load_data()
    return jsonify(data['milestones'])

@app.route('/api/milestones/<int:year>', methods=['PUT'])
def set_milestones(year):
    """Body: ["milestone 1", "milestone 2", ...]"""
    data = load_data()
    items = request.get_json()
    if not isinstance(items, list):
        return jsonify({'error': 'Body must be a JSON array of strings'}), 400
    data['milestones'][str(year)] = items
    save_data(data)
    return jsonify({str(year): items})

@app.route('/api/milestones/<int:year>', methods=['DELETE'])
def delete_milestones(year):
    data = load_data()
    data['milestones'].pop(str(year), None)
    save_data(data)
    return jsonify({'deleted': str(year)})


# ── LOCATIONS ─────────────────────────────────────────────────────────────────

@app.route('/api/coords', methods=['GET'])
def get_coords():
    data = load_data()
    return jsonify(data['coords'])

@app.route('/api/coords/<loc_id>', methods=['PUT'])
def set_coord(loc_id):
    """Body: [left_pct, top_pct]  e.g. [15.5, 20]"""
    data = load_data()
    coords = request.get_json()
    if not isinstance(coords, list) or len(coords) != 2:
        return jsonify({'error': 'Body must be [left%, top%]'}), 400
    data['coords'][loc_id] = coords
    save_data(data)
    return jsonify({loc_id: coords})


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    app.run(debug=True, port=5000)
