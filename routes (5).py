import json

from flask import Blueprint, render_template, redirect, url_for, flash, abort, request, g, current_app

from app.auth_utils import login_required
from app.repositories import create_job, get_job, get_jobs_for_user, get_resumes_for_user, get_resume
from app.job.parser import parse_job_description
from app.analysis.engine import run_full_analysis, get_weights_from_config

job_bp = Blueprint("job", __name__, template_folder="../templates/job")


@job_bp.route("/new", methods=["GET", "POST"])
@login_required
def new_job():
    resume_id = request.values.get("resume_id", type=int)

    if request.method == "POST":
        job_title = (request.form.get("job_title") or "").strip()
        company = (request.form.get("company") or "").strip()
        description = (request.form.get("description") or "").strip()

        errors = []
        if not job_title:
            errors.append("Job title is required.")
        if len(description) < 30:
            errors.append("Please paste a fuller job description (at least 30 characters).")

        if errors:
            for err in errors:
                flash(err, "danger")
            resumes = get_resumes_for_user(g.user.user_id)
            return render_template(
                "job/enter.html",
                resumes=resumes,
                selected_resume_id=resume_id,
                form_data={"job_title": job_title, "company": company, "description": description},
            )

        parsed = parse_job_description(description)
        job_id = create_job(g.user.user_id, job_title, company, description, parsed)
        flash("Job description analyzed.", "success")

        if resume_id:
            resume = get_resume(resume_id)
            if resume and resume["user_id"] == g.user.user_id:
                job = get_job(job_id)
                analysis_id = run_full_analysis(
                    resume, job, get_weights_from_config(current_app.config),
                    current_app.config["USE_SENTENCE_TRANSFORMERS"],
                )
                return redirect(url_for("analysis.report", analysis_id=analysis_id))

        return redirect(url_for("job.view_job", job_id=job_id))

    resumes = get_resumes_for_user(g.user.user_id)
    return render_template("job/enter.html", resumes=resumes, selected_resume_id=resume_id, form_data=None)


@job_bp.route("/<int:job_id>")
@login_required
def view_job(job_id):
    job = get_job(job_id)
    if not job or job["user_id"] != g.user.user_id:
        abort(404)
    parsed = json.loads(job["parsed_data"]) if job["parsed_data"] else {}
    resumes = get_resumes_for_user(g.user.user_id)
    return render_template("job/analysis.html", job=job, parsed=parsed, resumes=resumes)
