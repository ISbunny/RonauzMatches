import requests
from flask import current_app


def roanuz_token():
    url = f"https://api.sports.roanuz.com/v5/core/{current_app.config['PROJ_KEY']}/auth/"
    resp = requests.post(url, json={"api_key": current_app.config["API_KEY"]})
    return resp.json().get("data", {}).get("token")


def get_tournaments(token):
    url = f"https://api.sports.roanuz.com/v5/cricket/{current_app.config['PROJ_KEY']}/featured-tournaments/"
    resp = requests.get(url, headers={"rs-token": token})
    return resp.json().get("data", {}).get("tournaments", [])


def get_fixtures(token, tournament_key, page=2):
    url = f"https://api.sports.roanuz.com/v5/cricket/{current_app.config['PROJ_KEY']}/tournament/{tournament_key}/fixtures/{page}/"
    resp = requests.get(url, headers={"rs-token": token})
    matches = []
    for match in resp.json().get("data", {}).get("matches", []):
        if match.get("status") in ("not_started", "scheduled"):
            matches.append(
                {
                    "name": match.get("name"),
                    "venue": match.get("venue", {}).get("name", "Unknown"),
                    "start_time": match.get("start_time_str", match.get("start_time", "")),
                    "key": match.get("key"),
                }
            )
    return matches


def get_prematch_odds(token, match_key):
    url = f"https://api.sports.roanuz.com/v5/cricket/{current_app.config['PROJ_KEY']}/match/{match_key}/pre-match-odds/"
    resp = requests.get(url, headers={"rs-token": token})
    try:
        return resp.json().get("data", {})
    except Exception:
        return {"error": "Could not fetch odds."}
