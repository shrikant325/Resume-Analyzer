import json

from flask import Blueprint, render_template, redirect, url_for, flash, abort, request, current_app, g

from app.auth_utils import login_required
from app.repositories import (
    get_resume,
    get_job,
    get_analysis,
    get_analyses_for_user,
    get_analysis_skills,
    get_recommendations,
)
from app.analysis.engine import run_full_analysis, get_weights_from_config
from app.analysis.scoring import score_interpretation

analysis_bp = Blueprint("analysis", __name__, template_folder="../templates/analysis")


@analysis_bp.route("/run", methods=["POST"])
@login_required
def run():
    resume_id = request.form.get("resume_id", type=int)
    job_id = request.form.get("job_id", type=int)
    resume = get_resume(resume_id) if resume_id else None
    job = get_job(job_id) if job_id else None

    if not resume or not job or resume["user_id"] != g.user.user_id or job["user_id"] != g.user.user_id:
        flash("Please choose a valid resume and job description.", "danger")
        return redirect(url_for("main.dashboard"))

    analysis_id = run_full_analysis(
        resume, job, get_weights_from_config(current_app.config), current_app.config["USE_SENTENCE_TRANSFORMERS"]
    )
    flash("Analysis complete.", "success")
    return redirect(url_for("analysis.report", analysis_id=analysis_id))


def _owned_analysis_or_404(analysis_id):
    analysis = get_analysis(analysis_id)
    if not analysis:
        abort(404)
    if analysis["resume_user_id"] != g.user.user_id:
        abort(403)
    return analysis


def _build_context(analysis_id, active):
    analysis = _owned_analysis_or_404(analysis_id)
    skills = get_analysis_skills(analysis_id)
    matching = [s["skill_name"] for s in skills if s["skill_status"] == "matching"]
    missing = [(s["skill_name"], s["priority"]) for s in skills if s["skill_status"] == "missing"]
    additional = [s["skill_name"] for s in skills if s["skill_status"] == "additional"]

    recs = get_recommendations(analysis_id)
    improvements = [r for r in recs if r["recommendation_type"] == "improvement"]
    skill_recs = [r for r in recs if r["recommendation_type"] == "skill"]

    ats_checks = json.loads(analysis["ats_details"]) if analysis["ats_details"] else []
    explain = json.loads(analysis["explainability"]) if analysis["explainability"] else []

    return dict(
        analysis=analysis,
        matching=matching,
        missing=missing,
        additional=additional,
        improvements=improvements,
        skill_recs=skill_recs,
        ats_checks=ats_checks,
        explain=explain,
        interpretation=score_interpretation(analysis["compatibility_score"]),
        active=active,
    )


@analysis_bp.route("/<int:analysis_id>/report")
@login_required
def report(analysis_id):
    return render_template("analysis/report.html", **_build_context(analysis_id, "report"))


@analysis_bp.route("/<int:analysis_id>/compatibility")
@login_required
def compatibility(analysis_id):
    return render_template("analysis/compatibility.html", **_build_context(analysis_id, "compatibility"))


@analysis_bp.route("/<int:analysis_id>/skill-gap")
@login_required
def skill_gap(analysis_id):
    return render_template("analysis/skill_gap.html", **_build_context(analysis_id, "skill_gap"))


@analysis_bp.route("/<int:analysis_id>/ats")
@login_required
def ats(analysis_id):
    return render_template("analysis/ats.html", **_build_context(analysis_id, "ats"))


@analysis_bp.route("/<int:analysis_id>/improvement")
@login_required
def improvement(analysis_id):
    return render_template("analysis/improvement.html", **_build_context(analysis_id, "improvement"))


@analysis_bp.route("/<int:analysis_id>/recommendations")
@login_required
def recommendations(analysis_id):
    return render_template("analysis/recommendations.html", **_build_context(analysis_id, "recommendations"))


@analysis_bp.route("/history")
@login_required
def history():
    analyses = get_analyses_for_user(g.user.user_id)
    return render_template("analysis/history.html", analyses=analyses)
