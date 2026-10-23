import os
from datetime import datetime
from types import SimpleNamespace

from flask import Flask, render_template, g, session, request

from app.config import config_map
from app import db as db_module
from app.auth_utils import generate_csrf_token, validate_csrf


def create_app(config_name=None):
    config_name = config_name or os.environ.get("FLASK_ENV", "default")
    app = Flask(__name__)
    app.config.from_object(config_map.get(config_name, config_map["default"]))

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    if app.config["DB_BACKEND"] == "sqlite" and app.config["SQLITE_PATH"] != ":memory:":
        os.makedirs(os.path.dirname(app.config["SQLITE_PATH"]), exist_ok=True)

    db_module.init_app(app)

    from app.auth.routes import auth_bp
    from app.main.routes import main_bp
    from app.resume.routes import resume_bp
    from app.job.routes import job_bp
    from app.analysis.routes import analysis_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(resume_bp, url_prefix="/resume")
    app.register_blueprint(job_bp, url_prefix="/job")
    app.register_blueprint(analysis_bp, url_prefix="/analysis")

    with app.app_context():
        db_module.init_db(app)

    @app.before_request
    def load_logged_in_user():
        from app.repositories import get_user_by_id
        user_id = session.get("user_id")
        row = get_user_by_id(user_id) if user_id else None
        if row:
            g.user = SimpleNamespace(is_authenticated=True, **row)
        else:
            g.user = SimpleNamespace(is_authenticated=False)

    @app.before_request
    def csrf_protect():
        if request.method == "POST":
            validate_csrf()

    @app.context_processor
    def inject_globals():
        return {"current_user": g.user, "csrf_token": generate_csrf_token}

    @app.template_filter("dt")
    def format_datetime(value, fmt="%b %d, %Y %I:%M %p"):
        if not value:
            return ""
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value)
            except ValueError:
                try:
                    value = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    return value
        return value.strftime(fmt)

    @app.template_filter("pct")
    def format_percent(value):
        try:
            return int(round(float(value)))
        except (TypeError, ValueError):
            return 0

    @app.errorhandler(400)
    def bad_request(_e):
        return render_template("errors/error.html", code=400, message="Bad request. Please try again."), 400

    @app.errorhandler(403)
    def forbidden(_e):
        return render_template("errors/error.html", code=403, message="You don't have permission to view this."), 403

    @app.errorhandler(404)
    def not_found(_e):
        return render_template("errors/error.html", code=404, message="Page not found."), 404

    @app.errorhandler(413)
    def too_large(_e):
        return render_template("errors/error.html", code=413, message="File is too large. The limit is 8 MB."), 413

    @app.errorhandler(500)
    def server_error(_e):
        return render_template("errors/error.html", code=500, message="Something went wrong on our end."), 500

    return app
