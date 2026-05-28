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


def get_fixtures(token, tournament_key, page=None, max_pages=6):
    pages = [page] if page is not None else list(range(1, max_pages + 1))
    matches = []
    seen_match_keys = set()

    for page_no in pages:
        url = f"https://api.sports.roanuz.com/v5/cricket/{current_app.config['PROJ_KEY']}/tournament/{tournament_key}/fixtures/{page_no}/"
        resp = requests.get(url, headers={"rs-token": token})
        page_matches = resp.json().get("data", {}).get("matches", [])

        if not page_matches and page is None:
            break

        for match in page_matches:
            status = match.get("status")
            if status not in ("not_started", "scheduled"):
                continue

            match_key = match.get("key")
            if not match_key or match_key in seen_match_keys:
                continue

            seen_match_keys.add(match_key)
            matches.append(
                {
                    "name": match.get("name"),
                    "venue": match.get("venue", {}).get("name", "Unknown"),
                    "start_time": match.get("start_time_str", match.get("start_time", "")),
                    "key": match_key,
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
