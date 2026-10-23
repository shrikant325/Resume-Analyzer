from flask import Blueprint, render_template, redirect, url_for, flash, request, g
from werkzeug.security import generate_password_hash, check_password_hash

from app.auth_utils import login_required
from app.repositories import (
    get_resumes_for_user,
    get_analyses_for_user,
    update_user_name,
    update_user_password,
)

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    if g.user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return render_template("index.html")


@main_bp.route("/dashboard")
@login_required
def dashboard():
    resumes = get_resumes_for_user(g.user.user_id)
    analyses = get_analyses_for_user(g.user.user_id)
    latest = analyses[0] if analyses else None
    avg_compat = round(sum(a["compatibility_score"] for a in analyses) / len(analyses), 2) if analyses else 0
    return render_template(
        "dashboard.html",
        resumes=resumes,
        analyses=analyses[:5],
        latest=latest,
        total_resumes=len(resumes),
        total_analyses=len(analyses),
        avg_compat=avg_compat,
    )


@main_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        if not name:
            flash("Name cannot be empty.", "danger")
        else:
            update_user_name(g.user.user_id, name)
            flash("Profile updated.", "success")
        return redirect(url_for("main.profile"))
    return render_template("profile.html")


@main_bp.route("/profile/password", methods=["POST"])
@login_required
def change_password():
    current_password = request.form.get("current_password") or ""
    new_password = request.form.get("new_password") or ""
    confirm_new_password = request.form.get("confirm_new_password") or ""

    if not check_password_hash(g.user.password_hash, current_password):
        flash("Current password is incorrect.", "danger")
    elif len(new_password) < 6:
        flash("New password must be at least 6 characters.", "danger")
    elif new_password != confirm_new_password:
        flash("New passwords do not match.", "danger")
    else:
        update_user_password(g.user.user_id, generate_password_hash(new_password))
        flash("Password updated successfully.", "success")
    return redirect(url_for("main.profile"))
