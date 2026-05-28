from flask import Blueprint, redirect, render_template, request, session, url_for

from ronauz_app.services.roanuz import get_fixtures, get_prematch_odds, get_tournaments, roanuz_token


tournament_bp = Blueprint("tournament", __name__)


@tournament_bp.route("/tournament", methods=["GET", "POST"])
def tournament():
    if "username" not in session:
        return redirect(url_for("auth.login"))

    token = roanuz_token()
    tournaments = get_tournaments(token)
    selected_key = None
    selected_match_key = None
    matches = None
    odds = None
    result_prediction = None
    team_names = {}

    if request.method == "POST":
        selected_key = request.form.get("tournament_key")
        if selected_key:
            matches = get_fixtures(token, selected_key)
            selected_match_key = request.form.get("match_key")
            valid_match_keys = {m.get("key") for m in matches or []}

            # Ignore stale match values posted from a previously selected tournament.
            if selected_match_key and selected_match_key not in valid_match_keys:
                selected_match_key = None

            previous_match_key = session.get("selected_match_key")
            if selected_match_key:
                if previous_match_key and previous_match_key != selected_match_key:
                    session.pop("odds_cache", None)
                    session.pop("result_prediction_cache", None)

                odds = get_prematch_odds(token, selected_match_key)
                if odds and "match" in odds and "teams" in odds["match"]:
                    team_names = {
                        key: value.get("name", key)
                        for key, value in odds["match"]["teams"].items()
                    }

                try:
                    result_prediction = [
                        {
                            "team": team_names.get(item["team_key"], item["team_key"]),
                            "probability": item["value"],
                        }
                        for item in odds["match"]["result_prediction"]["automatic"]["percentage"]
                    ]
                except Exception:
                    result_prediction = None

                session["selected_match_key"] = selected_match_key
                session["odds_cache"] = odds
                session["result_prediction_cache"] = result_prediction

    return render_template(
        "tournament.html",
        username=session["username"],
        tournaments=tournaments,
        selected_key=selected_key,
        matches=matches,
        selected_match_key=selected_match_key,
        odds=odds,
        result_prediction=result_prediction,
    )
