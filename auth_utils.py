"""
Small, dependency-free auth helpers:

  * login_required  - route decorator that redirects anonymous users to login
  * generate_csrf_token / validate_csrf - a minimal CSRF double-submit token,
    stored in the signed session cookie and echoed back by every POST form.
"""

import secrets
from functools import wraps

from flask import g, session, redirect, url_for, request, flash, abort


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not g.user.is_authenticated:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)
    return wrapped_view


def generate_csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)
    return session["csrf_token"]


def validate_csrf():
    token = request.form.get("csrf_token", "")
    expected = session.get("csrf_token", "")
    if not expected or not token or not secrets.compare_digest(token, expected):
        abort(400)
