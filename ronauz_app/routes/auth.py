from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from pymongo.errors import DuplicateKeyError
from werkzeug.security import check_password_hash, generate_password_hash

from ronauz_app.db import SINGLE_ACCOUNT_GUARD_FIELD, get_users_collection


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/")
def home():
    if "username" in session:
        return redirect(url_for("tournament.tournament"))
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if "username" in session:
        return redirect(url_for("tournament.tournament"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if not username or not password:
            flash("Please fill in all fields.", "error")
            return render_template("login.html"), 400

        try:
            user = get_users_collection().find_one({"username": username})
            if user and check_password_hash(user["password"], password):
                session["username"] = username
                return redirect(url_for("tournament.tournament"))
            flash("Invalid username or password.", "error")
            return render_template("login.html"), 400
        except Exception:
            flash("Database is unavailable right now. Check MONGODB_URI.", "error")
            return render_template("login.html"), 500

    return render_template("login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if "username" in session:
        return redirect(url_for("tournament.tournament"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not username or not password or not confirm:
            flash("Please fill in all fields.", "error")
            return render_template("register.html"), 400
        if len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
            return render_template("register.html"), 400
        if password != confirm:
            flash("Passwords do not match.", "error")
            return render_template("register.html"), 400

        hashed = generate_password_hash(password)
        try:
            get_users_collection().insert_one(
                {
                    "username": username,
                    "password": hashed,
                    SINGLE_ACCOUNT_GUARD_FIELD: True,
                }
            )
            flash("Account created! Please log in.", "success")
            return redirect(url_for("auth.login"))
        except DuplicateKeyError as err:
            if SINGLE_ACCOUNT_GUARD_FIELD in str(err):
                flash("User registration is closed. Please contact the administrator.", "warning")
                return render_template("register.html"), 403
            flash("Username already taken.", "error")
            return render_template("register.html"), 400
        except Exception:
            flash("Database is unavailable right now. Check MONGODB_URI.", "error")
            return render_template("register.html"), 500

    return render_template("register.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
