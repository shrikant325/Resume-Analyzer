import re

from flask import Blueprint, render_template, redirect, url_for, flash, request, session, g
from werkzeug.security import generate_password_hash, check_password_hash

from app.repositories import create_user, get_user_by_email

auth_bp = Blueprint("auth", __name__, template_folder="../templates/auth")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if g.user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        confirm_password = request.form.get("confirm_password") or ""

        errors = []
        if not name:
            errors.append("Full name is required.")
        if not EMAIL_RE.match(email):
            errors.append("Please enter a valid email address.")
        if len(password) < 6:
            errors.append("Password must be at least 6 characters long.")
        if password != confirm_password:
            errors.append("Passwords do not match.")
        if not errors and get_user_by_email(email):
            errors.append("An account with that email already exists.")

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template("auth/register.html", form_data={"name": name, "email": email})

        create_user(name, email, generate_password_hash(password))
        flash("Account created successfully. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form_data=None)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if g.user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        user = get_user_by_email(email)
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["user_id"]
            session.permanent = True
            flash(f"Welcome back, {user['name']}!", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("main.dashboard"))
        flash("Invalid email or password.", "danger")

    return render_template("auth/login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.index"))
