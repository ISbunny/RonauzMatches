from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
import os, requests

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-in-production")

MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/ronauz_matches")
mongo_client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=3000, connect=False)

def get_users_collection():
  mongo_db = mongo_client.get_default_database()
  if mongo_db is None:
    mongo_db = mongo_client["ronauz_matches"]
  users = mongo_db["users"]
  users.create_index("username", unique=True)
  return users

# ── Roanuz API ────────────────────────────────────────────────────────────────
PROJ_KEY = 'RS_P_2040036252333510717'
API_KEY  = 'RS5:962227c2090ce4e301ab67d9aaed26d2'

def roanuz_token():
  url  = f"https://api.sports.roanuz.com/v5/core/{PROJ_KEY}/auth/"
  resp = requests.post(url, json={"api_key": API_KEY})
  return resp.json().get('data', {}).get('token')

def get_tournaments(token):
  url  = f"https://api.sports.roanuz.com/v5/cricket/{PROJ_KEY}/featured-tournaments/"
  resp = requests.get(url, headers={"rs-token": token})
  return resp.json().get('data', {}).get('tournaments', [])

def get_fixtures(token, tournament_key, page=2):
  url  = f"https://api.sports.roanuz.com/v5/cricket/{PROJ_KEY}/tournament/{tournament_key}/fixtures/{page}/"
  resp = requests.get(url, headers={"rs-token": token})
  matches = []
  for m in resp.json().get('data', {}).get('matches', []):
    if m.get('status') in ('not_started', 'scheduled'):
      matches.append({
        'name':       m.get('name'),
        'venue':      m.get('venue', {}).get('name', 'Unknown'),
        'start_time': m.get('start_time_str', m.get('start_time', '')),
        'key':        m.get('key'),
      })
  return matches

def get_prematch_odds(token, match_key):
  url  = f"https://api.sports.roanuz.com/v5/cricket/{PROJ_KEY}/match/{match_key}/pre-match-odds/"
  resp = requests.get(url, headers={"rs-token": token})
  try:
    return resp.json().get('data', {})
  except Exception:
    return {"error": "Could not fetch odds."}

# ── Shared CSS / background ───────────────────────────────────────────────────
BASE_STYLE = """
*,*:before,*:after{padding:0;margin:0;box-sizing:border-box}
body{background-color:#080710}
.background{width:430px;height:520px;position:absolute;
    transform:translate(-50%,-50%);left:50%;top:50%}
.background .shape{height:200px;width:200px;position:absolute;border-radius:50%}
.shape:first-child{background:linear-gradient(#1845ad,#23a2f6);left:-80px;top:-80px}
.shape:last-child{background:linear-gradient(to right,#ff512f,#f09819);right:-30px;bottom:-80px}
form{height:auto;width:400px;background-color:rgba(255,255,255,0.13);
    position:absolute;transform:translate(-50%,-50%);top:50%;left:50%;
    border-radius:10px;backdrop-filter:blur(10px);
    border:2px solid rgba(255,255,255,0.1);
    box-shadow:0 0 40px rgba(8,7,16,0.6);padding:50px 35px}
form *{font-family:'Poppins',sans-serif;color:#ffffff;letter-spacing:0.5px;outline:none;border:none}
form h3{font-size:32px;font-weight:500;line-height:42px;text-align:center}
label{display:block;margin-top:30px;font-size:16px;font-weight:500}
input{display:block;height:50px;width:100%;background-color:rgba(255,255,255,0.07);
    border-radius:3px;padding:0 10px;margin-top:8px;font-size:14px;font-weight:300}
::placeholder{color:#e5e5e5}
button{margin-top:50px;width:100%;background-color:#ffffff;color:#080710;
    padding:15px 0;font-size:18px;font-weight:600;border-radius:5px;cursor:pointer}
button:hover{background-color:#e0e0e0}
.switch-link{text-align:center;margin-top:20px;font-size:14px}
.switch-link a{color:#23a2f6;text-decoration:none;font-weight:500}
.switch-link a:hover{text-decoration:underline}
.flash{margin-top:20px;padding:10px 15px;border-radius:5px;
    font-size:14px;text-align:center}
.flash.error{background-color:rgba(255,80,80,0.3);border:1px solid rgba(255,80,80,0.5)}
.flash.success{background-color:rgba(50,200,100,0.3);border:1px solid rgba(50,200,100,0.5)}
"""

HEAD = """
<link rel="preconnect" href="https://fonts.gstatic.com">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;500;600&display=swap" rel="stylesheet">
"""

# ── Login page ────────────────────────────────────────────────────────────────
LOGIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>Login</title>
  """ + HEAD + """
  <style>""" + BASE_STYLE + """</style>
</head>
<body>
  <div class="background">
    <div class="shape"></div>
    <div class="shape"></div>
  </div>
  <form method="POST" action="/login">
    <h3>Login Here</h3>
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% for category, message in messages %}
        <div class="flash {{ category }}">{{ message }}</div>
      {% endfor %}
    {% endwith %}
    <label for="username">Username</label>
    <input type="text" name="username" placeholder="Enter username" id="username" required>
    <label for="password">Password</label>
    <input type="password" name="password" placeholder="Password" id="password" required>
    <button type="submit">Log In</button>
    <div class="switch-link">
      Don't have an account? <a href="/register">Register</a>
    </div>
  </form>
</body>
</html>
"""

# ── Register page ─────────────────────────────────────────────────────────────
REGISTER_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>Register</title>
  """ + HEAD + """
  <style>""" + BASE_STYLE + """</style>
</head>
<body>
  <div class="background">
    <div class="shape"></div>
    <div class="shape"></div>
  </div>
  <form method="POST" action="/register">
    <h3>Register</h3>
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% for category, message in messages %}
        <div class="flash {{ category }}">{{ message }}</div>
      {% endfor %}
    {% endwith %}
    <label for="username">Username</label>
    <input type="text" name="username" placeholder="Enter username" id="username" required>
    <label for="password">Password</label>
    <input type="password" name="password" placeholder="Password" id="password" required>
    <label for="confirm_password">Confirm Password</label>
    <input type="password" name="confirm_password" placeholder="Confirm password" id="confirm_password" required>
    <button type="submit">Create Account</button>
    <div class="switch-link">
      Already have an account? <a href="/login">Login</a>
    </div>
  </form>
</body>
</html>
"""

# ── Tournament Selector (protected) ───────────────────────────────────────────
TOURNAMENT_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Tournament Selector</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
  <nav class="navbar navbar-dark bg-dark px-4">
    <span class="navbar-brand fw-semibold">Roanuz Matches</span>
    <div class="d-flex align-items-center gap-3">
      <span class="text-white" style="font-size:14px">Hi, <strong>{{ username }}</strong></span>
      <a href="/logout" class="btn btn-outline-light btn-sm">Logout</a>
    </div>
  </nav>
  <div class="container py-5">
    <div class="row justify-content-center">
      <div class="col-md-8 col-lg-7">
        <div class="card shadow-sm">
          <div class="card-body">
            <h2 class="card-title mb-4 text-center">Select a Tournament</h2>
            <form method="post">
              <div class="mb-3">
                <select name="tournament_key" class="form-select" required onchange="clearOddsState(); this.form.submit()">
                  <option value="" disabled {% if not selected_key %}selected{% endif %}>Select tournament</option>
                  {% for t in tournaments %}
                    <option value="{{ t['key'] }}" {% if t['key'] == selected_key %}selected{% endif %}>{{ t['name'] }}</option>
                  {% endfor %}
                </select>
              </div>
              {% if matches is not none %}
                <div class="mb-3">
                  <select name="match_key" class="form-select" required onchange="clearOddsState()">
                    <option value="" disabled selected>Select upcoming match</option>
                    {% for m in matches %}
                      <option value="{{ m['key'] }}" {% if m['key'] == selected_match_key %}selected{% endif %}>{{ m['name'] }} | {{ m['venue'] }} | {{ m['start_time'] }}</option>
                    {% endfor %}
                  </select>
                </div>
                <div class="d-grid">
                  <button type="submit" id="oddsBtn" class="btn btn-success">Show Pre-Match Odds</button>
                </div>
                <div id="loadingIndicator" class="text-center mt-3" style="display:none;">
                  <div class="spinner-border text-success" role="status">
                    <span class="visually-hidden">Loading...</span>
                  </div>
                  <p class="mt-2 text-muted">Fetching pre-match odds, please wait...</p>
                </div>
              {% endif %}
            </form>
            {% if matches is not none and not matches %}
              <div class="alert alert-warning text-center mt-4">No upcoming matches found.</div>
            {% endif %}
            <div id="oddsState">
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
  </div>
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
  <script>
    function clearOddsState() {
      var oddsState = document.getElementById('oddsState');
      var oddsBtn = document.getElementById('oddsBtn');
      var loader = document.getElementById('loadingIndicator');
      if (oddsState) {
        oddsState.innerHTML = '';
      }
      if (oddsBtn) {
        oddsBtn.disabled = false;
        oddsBtn.innerHTML = 'Show Pre-Match Odds';
      }
      if (loader) {
        loader.style.display = 'none';
      }
    }

    document.querySelector('form').addEventListener('submit', function(e) {
      var matchKey = document.querySelector('select[name="match_key"]');
      var oddsBtn  = document.getElementById('oddsBtn');
      var loader   = document.getElementById('loadingIndicator');
      if (matchKey && matchKey.value && oddsBtn && loader) {
        oddsBtn.disabled = true;
        oddsBtn.innerHTML = 'Loading...';
        loader.style.display = 'block';
      }
    });
  </script>
</body>
</html>
"""

# ── Routes ────────────────────────────────────────────────────────────────────
@app.route('/')
def home():
    if 'username' in session:
        return redirect(url_for('tournament'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        return redirect(url_for('tournament'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        if not username or not password:
            flash('Please fill in all fields.', 'error')
            return render_template_string(LOGIN_HTML)
        try:
            user = get_users_collection().find_one({"username": username})
            if user and check_password_hash(user['password'], password):
                session['username'] = username
                return redirect(url_for('tournament'))
            flash('Invalid username or password.', 'error')
        except Exception:
            flash('Database is unavailable right now. Check MONGODB_URI.', 'error')
    return render_template_string(LOGIN_HTML)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'username' in session:
        return redirect(url_for('tournament'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm  = request.form.get('confirm_password', '')
        if not username or not password or not confirm:
            flash('Please fill in all fields.', 'error')
            return render_template_string(REGISTER_HTML)
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
            return render_template_string(REGISTER_HTML)
        if password != confirm:
            flash('Passwords do not match.', 'error')
            return render_template_string(REGISTER_HTML)
        hashed = generate_password_hash(password)
        try:
            get_users_collection().insert_one({"username": username, "password": hashed})
            flash('Account created! Please log in.', 'success')
            return redirect(url_for('login'))
        except DuplicateKeyError:
            flash('Username already taken.', 'error')
        except Exception:
            flash('Database is unavailable right now. Check MONGODB_URI.', 'error')
    return render_template_string(REGISTER_HTML)

@app.route('/tournament', methods=['GET', 'POST'])
def tournament():
    if 'username' not in session:
        return redirect(url_for('login'))
    token = roanuz_token()
    tournaments = get_tournaments(token)
    selected_key       = None
    selected_match_key = None
    matches            = None
    odds               = None
    result_prediction  = None
    team_names         = {}
    if request.method == 'POST':
        selected_key = request.form.get('tournament_key')
        if selected_key:
            matches = get_fixtures(token, selected_key)
            selected_match_key = request.form.get('match_key')
            previous_match_key = session.get('selected_match_key')
            if selected_match_key:
                if previous_match_key and previous_match_key != selected_match_key:
                    session.pop('odds_cache', None)
                    session.pop('result_prediction_cache', None)
                odds = get_prematch_odds(token, selected_match_key)
                if odds and 'match' in odds and 'teams' in odds['match']:
                    team_names = {k: v.get('name', k) for k, v in odds['match']['teams'].items()}
                try:
                    result_prediction = [
                        {
                            'team':        team_names.get(item['team_key'], item['team_key']),
                            'probability': item['value']
                        }
                        for item in odds['match']['result_prediction']['automatic']['percentage']
                    ]
                except Exception:
                    result_prediction = None
                session['selected_match_key'] = selected_match_key
                session['odds_cache'] = odds
                session['result_prediction_cache'] = result_prediction
    return render_template_string(
        TOURNAMENT_HTML,
        username=session['username'],
        tournaments=tournaments,
        selected_key=selected_key,
        matches=matches,
        selected_match_key=selected_match_key,
        odds=odds,
        result_prediction=result_prediction
    )

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)
