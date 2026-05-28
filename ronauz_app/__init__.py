import os

from flask import Flask

from .db import init_mongo
from .routes.auth import auth_bp
from .routes.tournament import tournament_bp


def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "change-this-in-production")

    app.config["SECRET_KEY"] = app.secret_key
    app.config["MONGODB_URI"] = os.environ.get(
        "MONGODB_URI", "mongodb://localhost:27017/ronauz_matches"
    )
    app.config["PROJ_KEY"] = os.environ.get("PROJ_KEY", "RS_P_2040036252333510717")
    app.config["API_KEY"] = os.environ.get(
        "API_KEY", "RS5:962227c2090ce4e301ab67d9aaed26d2"
    )

    app.config.from_prefixed_env()

    init_mongo(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(tournament_bp)

    return app
