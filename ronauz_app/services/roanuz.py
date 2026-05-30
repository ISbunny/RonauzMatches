import requests
from flask import current_app


def _safe_json(resp):
    try:
        payload = resp.json()
    except ValueError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _extract_data(payload):
    data = payload.get("data")
    return data if isinstance(data, dict) else {}


def _log_roanuz_error(endpoint, resp, payload):
    error = payload.get("error")
    if error:
        current_app.logger.warning(
            "Roanuz API error on %s: status=%s code=%s message=%s",
            endpoint,
            resp.status_code,
            error.get("code"),
            error.get("msg"),
        )


def roanuz_token():
    url = f"https://api.sports.roanuz.com/v5/core/{current_app.config['PROJ_KEY']}/auth/"
    resp = requests.post(url, json={"api_key": current_app.config["API_KEY"]}, timeout=15)
    payload = _safe_json(resp)
    _log_roanuz_error("auth", resp, payload)
    return _extract_data(payload).get("token")


def get_tournaments(token):
    url = f"https://api.sports.roanuz.com/v5/cricket/{current_app.config['PROJ_KEY']}/featured-tournaments/"
    resp = requests.get(url, headers={"rs-token": token}, timeout=20)
    payload = _safe_json(resp)
    _log_roanuz_error("featured-tournaments", resp, payload)
    tournaments = _extract_data(payload).get("tournaments", [])
    return tournaments if isinstance(tournaments, list) else []


def get_fixtures(token, tournament_key, page=None, max_pages=6):
    pages = [page] if page is not None else list(range(1, max_pages + 1))
    matches = []
    seen_match_keys = set()

    for page_no in pages:
        url = f"https://api.sports.roanuz.com/v5/cricket/{current_app.config['PROJ_KEY']}/tournament/{tournament_key}/fixtures/{page_no}/"
        resp = requests.get(url, headers={"rs-token": token}, timeout=20)
        payload = _safe_json(resp)
        _log_roanuz_error("fixtures", resp, payload)
        page_matches = _extract_data(payload).get("matches", [])
        if not isinstance(page_matches, list):
            page_matches = []

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
    try:
        resp = requests.get(url, headers={"rs-token": token}, timeout=20)
    except requests.RequestException:
        return {"error": "Could not fetch odds."}

    payload = _safe_json(resp)
    _log_roanuz_error("pre-match-odds", resp, payload)
    return _extract_data(payload)
