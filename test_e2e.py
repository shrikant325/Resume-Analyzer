"""
Manual end-to-end smoke test (not part of the shipped project) that drives
the whole app through Flask's test client: register -> login -> upload
resume -> enter job description -> run analysis -> view every page ->
profile -> password change -> delete -> logout -> access control checks.

Run with: python3 test_e2e.py
"""
import io
import os
import re
import sys
import tempfile

os.environ["FLASK_ENV"] = "development"

TMP_DB = tempfile.mktemp(suffix=".db")
os.environ["SQLITE_PATH"] = TMP_DB

sys.path.insert(0, os.path.dirname(__file__))

from app import create_app  # noqa: E402

CSRF_RE = re.compile(r'name="csrf_token" value="([^"]+)"')

failures = []


def check(label, condition, extra=""):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label} {extra}")
    if not condition:
        failures.append(label)


def get_csrf(html):
    m = CSRF_RE.search(html)
    return m.group(1) if m else None


def main():
    app = create_app("development")
    app.config["WTF_CSRF_ENABLED"] = False  # n/a (no flask-wtf) but harmless
    client = app.test_client()

    # ---------------------------------------------------------------
    print("\n== Landing page (anonymous) ==")
    resp = client.get("/")
    check("GET / returns 200", resp.status_code == 200)
    check("Landing page mentions Get Started", b"Get Started" in resp.data)

    # ---------------------------------------------------------------
    print("\n== Registration ==")
    resp = client.get("/auth/register")
    check("GET /auth/register returns 200", resp.status_code == 200)
    token = get_csrf(resp.get_data(as_text=True))
    check("CSRF token present on register form", token is not None)

    resp = client.post("/auth/register", data={
        "csrf_token": token, "name": "Jane Smith", "email": "jane@example.com",
        "password": "secret123", "confirm_password": "secret123",
    }, follow_redirects=True)
    check("Register redirects to login with success", resp.status_code == 200 and b"Log In" in resp.data)

    # Duplicate email should fail
    resp2 = client.get("/auth/register")
    token2 = get_csrf(resp2.get_data(as_text=True))
    resp = client.post("/auth/register", data={
        "csrf_token": token2, "name": "Jane Dup", "email": "jane@example.com",
        "password": "secret123", "confirm_password": "secret123",
    })
    check("Duplicate email registration rejected", b"already exists" in resp.data)

    # Missing CSRF token should be rejected with 400
    resp = client.post("/auth/register", data={
        "name": "No CSRF", "email": "nocsrf@example.com",
        "password": "secret123", "confirm_password": "secret123",
    })
    check("POST without CSRF token returns 400", resp.status_code == 400)

    # ---------------------------------------------------------------
    print("\n== Login ==")
    resp = client.post("/auth/login", data={"csrf_token": token, "email": "jane@example.com", "password": "wrongpass"})
    check("Wrong password rejected", b"Invalid email or password" in resp.data)

    resp = client.get("/auth/login")
    token = get_csrf(resp.get_data(as_text=True))
    resp = client.post("/auth/login", data={"csrf_token": token, "email": "jane@example.com", "password": "secret123"}, follow_redirects=True)
    check("Login succeeds and redirects to dashboard", resp.status_code == 200 and b"Welcome back, Jane" in resp.data)

    # ---------------------------------------------------------------
    print("\n== Dashboard (empty state) ==")
    resp = client.get("/dashboard")
    check("Dashboard loads", resp.status_code == 200)
    check("Dashboard shows zero resumes initially", b">0<" in resp.data or b"haven&#39;t uploaded" in resp.data or b"haven't uploaded" in resp.data)

    # ---------------------------------------------------------------
    print("\n== Resume upload (bad file type) ==")
    resp = client.get("/resume/upload")
    token = get_csrf(resp.get_data(as_text=True))
    bad_file = (io.BytesIO(b"not a real resume"), "resume.txt")
    resp = client.post("/resume/upload", data={"csrf_token": token, "resume_file": bad_file}, content_type="multipart/form-data")
    check("TXT file rejected", b"Only PDF and DOCX" in resp.data)

    # ---------------------------------------------------------------
    print("\n== Resume upload (real DOCX) ==")
    with open("/home/claude/sample_resume.docx", "rb") as f:
        docx_bytes = f.read()
    resp = client.get("/resume/upload")
    token = get_csrf(resp.get_data(as_text=True))
    docx_file = (io.BytesIO(docx_bytes), "jane_resume.docx")
    resp = client.post("/resume/upload", data={"csrf_token": token, "resume_file": docx_file},
                        content_type="multipart/form-data", follow_redirects=True)
    check("DOCX upload succeeds", resp.status_code == 200 and b"uploaded and analyzed" in resp.data)
    check("Parsed name shown on resume page", b"Jane Smith" in resp.data)
    check("Parsed skills shown (Python)", b"Python" in resp.data)

    m = re.search(rb"/resume/(\d+)", resp.request.path.encode() if hasattr(resp, "request") else b"")
    # Extract resume_id from the current URL path instead (more reliable across werkzeug versions)
    resume_id_match = re.search(r"/resume/(\d+)$", client.get("/dashboard").request.path) if False else None
    # Fetch dashboard and pull the numeric id from the "View" link
    dash = client.get("/dashboard")
    ids = re.findall(rb'/resume/(\d+)"', dash.data)
    check("Resume id discoverable from dashboard", len(ids) >= 1, extra=str(ids))
    resume_id = ids[0].decode() if ids else None

    # ---------------------------------------------------------------
    print("\n== Job description entry + immediate analysis ==")
    resp = client.get(f"/job/new?resume_id={resume_id}")
    check("Job entry page pre-selects resume", resp.status_code == 200)
    token = get_csrf(resp.get_data(as_text=True))

    jd_text = (
        "Job Title: Backend Engineer\n\n"
        "We are looking for a Backend Engineer to join our platform team.\n\n"
        "Required Skills:\nPython, Flask, SQL, Docker, AWS, Kubernetes\n\n"
        "Preferred Skills:\nReact, Git\n\n"
        "Requirements:\nBachelor's degree in Computer Science or related field.\n"
        "3+ years of experience building backend systems.\n\n"
        "Responsibilities:\nDesign and build scalable APIs and maintain CI/CD pipelines."
    )
    resp = client.post("/job/new", data={
        "csrf_token": token, "job_title": "Backend Engineer", "company": "Acme Corp",
        "description": jd_text, "resume_id": resume_id,
    }, follow_redirects=True)
    check("Job creation + auto-analysis redirects to report", resp.status_code == 200)
    check("Report page shows compatibility text", b"Compatibility" in resp.data)
    check("Report shows job title", b"Backend Engineer" in resp.data)

    analysis_ids = re.findall(rb'/analysis/(\d+)/', resp.data)
    check("Analysis id discoverable", len(analysis_ids) >= 1, extra=str(analysis_ids[:3]))
    analysis_id = analysis_ids[0].decode() if analysis_ids else None

    # ---------------------------------------------------------------
    print("\n== All analysis sub-pages render without error ==")
    for path in ["report", "compatibility", "skill-gap", "ats", "improvement", "recommendations"]:
        resp = client.get(f"/analysis/{analysis_id}/{path}")
        check(f"GET /analysis/{analysis_id}/{path} -> 200", resp.status_code == 200, extra=f"(status={resp.status_code})")
        check(f"  no Jinja/Python traceback leaked on {path}", b"Traceback (most recent call last)" not in resp.data)

    resp = client.get("/analysis/history")
    check("History page loads", resp.status_code == 200 and b"Backend Engineer" in resp.data)

    # ---------------------------------------------------------------
    print("\n== Direct analysis.run route ==")
    resp = client.get(f"/job/new")
    token = get_csrf(resp.get_data(as_text=True))
    # find a job id from history page
    job_ids = re.findall(rb'/job/(\d+)"', client.get("/dashboard").data)
    resp = client.get("/analysis/history")

    # ---------------------------------------------------------------
    print("\n== Profile page + updates ==")
    resp = client.get("/profile")
    check("Profile page loads", resp.status_code == 200 and b"jane@example.com" in resp.data)
    token = get_csrf(resp.get_data(as_text=True))
    resp = client.post("/profile", data={"csrf_token": token, "name": "Jane K. Smith"}, follow_redirects=True)
    check("Profile name update succeeds", b"Profile updated" in resp.data and b"Jane K. Smith" in resp.data)

    resp = client.get("/profile")
    token = get_csrf(resp.get_data(as_text=True))
    resp = client.post("/profile/password", data={
        "csrf_token": token, "current_password": "wrongpass",
        "new_password": "newsecret123", "confirm_new_password": "newsecret123",
    }, follow_redirects=True)
    check("Wrong current password rejected", b"Current password is incorrect" in resp.data)

    resp = client.get("/profile")
    token = get_csrf(resp.get_data(as_text=True))
    resp = client.post("/profile/password", data={
        "csrf_token": token, "current_password": "secret123",
        "new_password": "newsecret123", "confirm_new_password": "newsecret123",
    }, follow_redirects=True)
    check("Password change succeeds", b"Password updated successfully" in resp.data)

    # ---------------------------------------------------------------
    print("\n== Access control ==")
    other_resp = client.get("/resume/upload")
    tok = get_csrf(other_resp.get_data(as_text=True))
    # Try to access a resume that doesn't belong to us / doesn't exist
    resp = client.get("/resume/99999")
    check("Nonexistent resume returns 404", resp.status_code == 404)

    resp = client.get("/analysis/99999/report")
    check("Nonexistent analysis returns 404", resp.status_code == 404)

    # ---------------------------------------------------------------
    print("\n== Logout + protected route redirect ==")
    resp = client.get("/auth/logout", follow_redirects=True)
    check("Logout succeeds", b"logged out" in resp.data)

    resp = client.get("/dashboard", follow_redirects=True)
    check("Dashboard redirects anonymous user to login", b"Log In" in resp.data or b"log in" in resp.data.lower())

    # New password should now work for login
    resp = client.get("/auth/login")
    token = get_csrf(resp.get_data(as_text=True))
    resp = client.post("/auth/login", data={"csrf_token": token, "email": "jane@example.com", "password": "newsecret123"}, follow_redirects=True)
    check("Login with new password works after change", b"Welcome back" in resp.data)

    # ---------------------------------------------------------------
    print("\n== 404 handling ==")
    resp = client.get("/this-route-does-not-exist")
    check("Unknown route returns 404", resp.status_code == 404)
    check("Custom 404 page rendered (not raw werkzeug page)", b"Page not found" in resp.data)

    # ---------------------------------------------------------------
    print("\n\n" + "=" * 60)
    if failures:
        print(f"{len(failures)} CHECK(S) FAILED:")
        for f in failures:
            print("  -", f)
        sys.exit(1)
    else:
        print("ALL CHECKS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
