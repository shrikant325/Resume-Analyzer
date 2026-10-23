import json
import os
import uuid

from flask import Blueprint, render_template, redirect, url_for, flash, current_app, abort, request, g
from werkzeug.utils import secure_filename

from app.auth_utils import login_required
from app.repositories import (
    create_resume,
    get_resume,
    delete_resume as repo_delete_resume,
    get_resumes_for_user,
    get_jobs_for_user,
)
from app.resume.extractor import extract_text
from app.resume.parser import parse_resume

resume_bp = Blueprint("resume", __name__, template_folder="../templates/resume")


def _allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in current_app.config["ALLOWED_EXTENSIONS"]
    )


@resume_bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    if request.method == "POST":
        file = request.files.get("resume_file")

        if not file or file.filename == "":
            flash("Please choose a PDF or DOCX file to upload.", "danger")
            return render_template("resume/upload.html")
        if not _allowed_file(file.filename):
            flash("Only PDF and DOCX files are supported.", "danger")
            return render_template("resume/upload.html")

        original_name = secure_filename(file.filename)
        unique_name = f"{uuid.uuid4().hex}_{original_name}"
        save_path = os.path.join(current_app.config["UPLOAD_FOLDER"], unique_name)
        file.save(save_path)

        try:
            text = extract_text(save_path)
            if not text or len(text.strip()) < 20:
                raise ValueError("Could not extract readable text from this file.")
            parsed = parse_resume(text)
        except Exception as exc:
            if os.path.exists(save_path):
                os.remove(save_path)
            flash(f"Could not process this resume: {exc}", "danger")
            return render_template("resume/upload.html")

        resume_id = create_resume(g.user.user_id, original_name, save_path, text, parsed)
        flash("Resume uploaded and analyzed successfully.", "success")
        return redirect(url_for("resume.view_resume", resume_id=resume_id))

    return render_template("resume/upload.html")


@resume_bp.route("/<int:resume_id>")
@login_required
def view_resume(resume_id):
    resume = get_resume(resume_id)
    if not resume or resume["user_id"] != g.user.user_id:
        abort(404)
    parsed = json.loads(resume["parsed_data"]) if resume["parsed_data"] else {}
    jobs = get_jobs_for_user(g.user.user_id)
    return render_template("resume/analysis.html", resume=resume, parsed=parsed, jobs=jobs)


@resume_bp.route("/<int:resume_id>/delete", methods=["POST"])
@login_required
def delete_resume_route(resume_id):
    resume = get_resume(resume_id)
    if not resume or resume["user_id"] != g.user.user_id:
        abort(404)
    if resume["file_path"] and os.path.exists(resume["file_path"]):
        try:
            os.remove(resume["file_path"])
        except OSError:
            pass
    repo_delete_resume(resume_id)
    flash("Resume deleted.", "info")
    return redirect(url_for("main.dashboard"))
