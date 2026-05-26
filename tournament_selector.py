# Helper to get pre-match odds for a match
def get_prematch_odds(token, match_key):
    url = f"https://api.sports.roanuz.com/v5/cricket/{PROJ_KEY}/match/{match_key}/pre-match-odds/"
    resp = requests.get(url, headers={"rs-token": token})
    try:
        return resp.json().get('data', {})
    except Exception:
        return {"error": "Could not fetch odds."}
from flask import Flask, render_template_string, request, jsonify
import requests

app = Flask(__name__)

# Roanuz API credentials
PROJ_KEY = 'RS_P_2040036252333510717'
API_KEY = 'RS5:962227c2090ce4e301ab67d9aaed26d2'

# HTML template with Bootstrap for responsive, modern UI
HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tournament Selector</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
    <div class="container py-5">
        <div class="row justify-content-center">
            <div class="col-md-8 col-lg-7">
                <div class="card shadow-sm">
                    <div class="card-body">
                        <h2 class="card-title mb-4 text-center">Select a Tournament</h2>
                        <form method="post">
                            <div class="mb-3">
                                <select name="tournament_key" class="form-select" required onchange="this.form.submit()">
                                    <option value="" disabled {% if not selected_key %}selected{% endif %}>Select tournament</option>
                                    {% for t in tournaments %}
                                        <option value="{{ t['key'] }}" {% if t['key'] == selected_key %}selected{% endif %}>{{ t['name'] }}</option>
                                    {% endfor %}
                                </select>
                            </div>
                            {% if matches is not none %}
                                <div class="mb-3">
                                    <select name="match_key" class="form-select" required>
                                        <option value="" disabled selected>Select upcoming match</option>
                                        {% for m in matches %}
                                            <option value="{{ m['key'] }}" {% if m['key'] == selected_match_key %}selected{% endif %}>{{ m['name'] }} | {{ m['venue'] }} | {{ m['start_time'] }}</option>
                                        {% endfor %}
                                    </select>
                                </div>
                                <div class="d-grid">
                                    <button type="submit" class="btn btn-success">Show Pre-Match Odds</button>
                                </div>
                            {% endif %}
                        </form>
                        {% if matches is not none and not matches %}
                            <div class="alert alert-warning text-center mt-4">No upcoming matches found.</div>
                        {% endif %}
                        {% if result_prediction %}
                            <div class="mt-4">
                                <h5 class="text-center">Result Prediction</h5>
                                <ul class="list-group">
                                    {% for item in result_prediction %}
                                        <li class="list-group-item d-flex justify-content-between align-items-center">
                                            <span>{{ item['team'] }}</span>
                                            <span class="badge bg-primary">{{ item['probability'] }}%</span>
                                        </li>
                                    {% endfor %}
                                </ul>
                            </div>
                        {% elif odds %}
                            <div class="mt-4">
                                <h5 class="text-center">No result prediction available.</h5>
                            </div>
                        {% endif %}
                    </div>
                </div>
            </div>
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
'''
# Helper to get fixtures for a tournament (page 2 by default)
def get_fixtures(token, tournament_key, page=2):
    url = f"https://api.sports.roanuz.com/v5/cricket/{PROJ_KEY}/tournament/{tournament_key}/fixtures/{page}/"
    resp = requests.get(url, headers={"rs-token": token})
    data = resp.json()
    matches = []
    for m in data.get('data', {}).get('matches', []):
        # Only show upcoming matches
        if m.get('status') in ('not_started', 'scheduled'):
            matches.append({
                'name': m.get('name'),
                'venue': m.get('venue', {}).get('name', 'Unknown'),
                'start_time': m.get('start_time_str', m.get('start_time', '')),
                'key': m.get('key'),
            })
    return matches

# Helper to get token
def get_token():
    url = f"https://api.sports.roanuz.com/v5/core/{PROJ_KEY}/auth/"
    resp = requests.post(url, json={"api_key": API_KEY})
    data = resp.json()
    return data.get('data', {}).get('token')

# Helper to get tournaments
def get_tournaments(token):
    url = f"https://api.sports.roanuz.com/v5/cricket/{PROJ_KEY}/featured-tournaments/"
    resp = requests.get(url, headers={"rs-token": token})
    data = resp.json()
    return data.get('data', {}).get('tournaments', [])


@app.route('/', methods=['GET', 'POST'])
def index():
    token = get_token()
    tournaments = get_tournaments(token)
    selected_key = None
    selected_match_key = None
    matches = None
    odds = None
    result_prediction = None
    team_names = {}
    if request.method == 'POST':
        selected_key = request.form.get('tournament_key')
        if selected_key:
            matches = get_fixtures(token, selected_key)
            selected_match_key = request.form.get('match_key')
            if selected_match_key:
                odds = get_prematch_odds(token, selected_match_key)
                # Extract team names for display
                if odds and 'match' in odds and 'teams' in odds['match']:
                    team_names = {k: v.get('name', k) for k, v in odds['match']['teams'].items()}
                # Extract result prediction
                try:
                    result_prediction = [
                        {
                            'team': team_names.get(item['team_key'], item['team_key']),
                            'probability': item['value']
                        }
                        for item in odds['match']['result_prediction']['automatic']['percentage']
                    ]
                    print('DEBUG: result_prediction:', result_prediction)
                    print('DEBUG: team_names:', team_names)
                except Exception as e:
                    print('DEBUG: error extracting result_prediction:', e)
                    result_prediction = None
    return render_template_string(HTML, tournaments=tournaments, selected_key=selected_key, matches=matches, selected_match_key=selected_match_key, odds=odds, result_prediction=result_prediction)

import os
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
