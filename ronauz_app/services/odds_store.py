from datetime import datetime, timezone

from ronauz_app.db import get_match_odds_collection


def _team_rows_from_payload(match_payload):
    teams = match_payload.get("teams", {})
    decimal_odds = (
        match_payload.get("bet_odds", {})
        .get("automatic", {})
        .get("decimal", [])
    )
    result_prediction = (
        match_payload.get("result_prediction", {})
        .get("automatic", {})
        .get("percentage", [])
    )
    prediction_by_team = {
        item.get("team_key"): item.get("value") for item in result_prediction if item.get("team_key")
    }
    odds_by_team = {
        item.get("team_key"): item.get("value") for item in decimal_odds if item.get("team_key")
    }
    ordered_team_keys = []
    for item in result_prediction:
        team_key = item.get("team_key")
        if team_key and team_key not in ordered_team_keys:
            ordered_team_keys.append(team_key)

    for item in decimal_odds:
        team_key = item.get("team_key")
        if team_key and team_key not in ordered_team_keys:
            ordered_team_keys.append(team_key)

    rows = []
    for team_key in ordered_team_keys:
        team_meta = teams.get(team_key, {})
        rows.append(
            {
                "team_key": team_key,
                "team_name": team_meta.get("name", team_key),
                "latest_odds": odds_by_team.get(team_key),
                "latest_prediction": prediction_by_team.get(team_key),
            }
        )

    return rows


def upsert_match_odds(tournament, match_summary, odds_payload):
    match_payload = odds_payload.get("match", {})
    team_rows = _team_rows_from_payload(match_payload)
    if len(team_rows) < 2:
        return None

    fetched_at = datetime.now(timezone.utc)
    team_a = team_rows[0]
    team_b = team_rows[1]
    match_meta = match_payload.get("meta", {})

    collection = get_match_odds_collection()
    collection.update_one(
        {"match_key": match_summary.get("key")},
        {
            "$setOnInsert": {
                "open_odds_team_a": team_a["latest_odds"],
                "open_odds_team_b": team_b["latest_odds"],
                "open_winner_percentage_team_a": team_a["latest_prediction"],
                "open_winner_percentage_team_b": team_b["latest_prediction"],
                "created_at": fetched_at,
            },
            "$set": {
                "tournament_key": tournament.get("key"),
                "tournament_name": tournament.get("name"),
                "match_name": match_summary.get("name"),
                "match_start_time": match_summary.get("start_time"),
                "match_status": match_meta.get("status", match_summary.get("status")),
                "team_a_key": team_a["team_key"],
                "team_a_name": team_a["team_name"],
                "team_b_key": team_b["team_key"],
                "team_b_name": team_b["team_name"],
                "latest_odds_team_a": team_a["latest_odds"],
                "latest_odds_team_b": team_b["latest_odds"],
                "latest_winner_percentage_team_a": team_a["latest_prediction"],
                "latest_winner_percentage_team_b": team_b["latest_prediction"],
                "last_fetched_at": fetched_at,
                "raw_result_prediction": match_payload.get("result_prediction", {}),
            },
        },
        upsert=True,
    )

    collection.update_one(
        {
            "match_key": match_summary.get("key"),
            "$or": [
                {"open_winner_percentage_team_a": {"$exists": False}},
                {"open_winner_percentage_team_b": {"$exists": False}},
            ],
        },
        {
            "$set": {
                "open_winner_percentage_team_a": team_a["latest_prediction"],
                "open_winner_percentage_team_b": team_b["latest_prediction"],
            }
        },
    )

    return {
        "team_a_name": team_a["team_name"],
        "team_b_name": team_b["team_name"],
        "open_winner_percentage_team_a": team_a["latest_prediction"],
        "open_winner_percentage_team_b": team_b["latest_prediction"],
        "latest_winner_percentage_team_a": team_a["latest_prediction"],
        "latest_winner_percentage_team_b": team_b["latest_prediction"],
    }


def get_grouped_match_odds():
    collection = get_match_odds_collection()
    grouped = []
    current_group = None

    cursor = collection.find({}, {"_id": 0}).sort(
        [("tournament_name", 1), ("match_start_time", 1), ("match_name", 1)]
    )
    for row in cursor:
        tournament_key = row.get("tournament_key")
        if current_group is None or current_group["tournament_key"] != tournament_key:
            current_group = {
                "tournament_key": tournament_key,
                "tournament_name": row.get("tournament_name", tournament_key),
                "matches": [],
            }
            grouped.append(current_group)

        current_group["matches"].append(row)

    return grouped
