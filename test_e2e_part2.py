import io
import os
import re
import sys
import tempfile

os.environ["FLASK_ENV"] = "development"
os.environ["SQLITE_PATH"] = tempfile.mktemp(suffix=".db")
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


def register_and_login(client, email="alex@example.com", name="Alex Rivera", password="pdftest123"):
    resp = client.get("/auth/register")
    token = get_csrf(resp.get_data(as_text=True))
    client.post("/auth/register", data={
        "csrf_token": token, "name": name, "email": email,
        "password": password, "confirm_password": password,
    })
    resp = client.get("/auth/login")
    token = get_csrf(resp.get_data(as_text=True))
    client.post("/auth/login", data={"csrf_token": token, "email": email, "password": password})


def main():
    app = create_app("development")
    client = app.test_client()

    print("\n== PDF upload end-to-end ==")
    register_and_login(client)

    with open("/home/claude/sample_resume.pdf", "rb") as f:
        pdf_bytes = f.read()
    resp = client.get("/resume/upload")
    token = get_csrf(resp.get_data(as_text=True))
    pdf_file = (io.BytesIO(pdf_bytes), "alex_resume.pdf")
    resp = client.post("/resume/upload", data={"csrf_token": token, "resume_file": pdf_file},
                        content_type="multipart/form-data", follow_redirects=True)
    check("PDF upload succeeds", resp.status_code == 200 and b"uploaded and analyzed" in resp.data)
    check("Parsed name from PDF shown", b"Alex Rivera" in resp.data)
    check("Parsed skill Docker shown", b"Docker" in resp.data)
    check("Parsed skill Kubernetes shown", b"Kubernetes" in resp.data)
    check("Education level Master detected", b"Master" in resp.data)

    dash = client.get("/dashboard")
    ids = re.findall(rb'/resume/(\d+)"', dash.data)
    resume_id = ids[0].decode()

    print("\n== Run analysis against a DevOps JD (tests high skill match) ==")
    resp = client.get(f"/job/new?resume_id={resume_id}")
    token = get_csrf(resp.get_data(as_text=True))
    jd = (
        "Job Title: DevOps Engineer\n\n"
        "Required Skills:\nPython, Docker, Kubernetes, AWS, Terraform, Git, Linux\n\n"
        "Requirements:\n3+ years experience. Master's degree preferred.\n"
    )
    resp = client.post("/job/new", data={
        "csrf_token": token, "job_title": "DevOps Engineer", "company": "CloudWorks",
        "description": jd, "resume_id": resume_id,
    }, follow_redirects=True)
    check("Analysis runs successfully", resp.status_code == 200)
    # This resume should score very high skill match since nearly every skill overlaps
    html = resp.get_data(as_text=True)
    score_match = re.search(r'data-score-ring="([\d.]+)"', html)
    check("Compatibility score rendered as a number", score_match is not None, extra=str(score_match))
    if score_match:
        score = float(score_match.group(1))
        check(f"High skill overlap yields a solid score (got {score})", score >= 50)

    print("\n== Delete resume ==")
    resp = client.get(f"/resume/{resume_id}")
    token = get_csrf(resp.get_data(as_text=True))
    resp = client.post(f"/resume/{resume_id}/delete", data={"csrf_token": token}, follow_redirects=True)
    check("Resume deleted, redirected to dashboard", resp.status_code == 200 and b"Resume deleted" in resp.data)

    resp = client.get(f"/resume/{resume_id}")
    check("Deleted resume now 404s", resp.status_code == 404)

    print("\n== Second user cannot see first user's data (authorization) ==")
    client2 = app.test_client()
    register_and_login(client2, email="mallory@example.com", name="Mallory", password="whatever123")
    # mallory tries to view alex's analysis history - should just show her own (empty) history, not error
    resp = client2.get("/analysis/history")
    check("Second user's history loads fine (isolated)", resp.status_code == 200)
    check("Second user does not see first user's job title", b"CloudWorks" not in resp.data)

    print("\n\n" + "=" * 60)
    if failures:
        print(f"{len(failures)} CHECK(S) FAILED:")
        for f in failures:
            print("  -", f)
        sys.exit(1)
    else:
        print("ALL PART-2 CHECKS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
