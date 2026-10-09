# Review screen for the HR officer shortlist.
import hmac
import os
import secrets
from datetime import timedelta

from flask import Flask, abort, jsonify, redirect, render_template_string, request, send_file, session, url_for

from auth import verify_password
from config import Config
from database import Database
from hr_profile import HR_JOB, REVIEW_MARKS, ROLE_CATEGORIES

app = Flask(__name__)
app.secret_key = Config.SECRET_KEY
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=12)
db = Database(Config.DATABASE_PATH)

LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Sign in · Accord Medical HR</title>
  <style>
    :root { color-scheme: light; }
    * { box-sizing: border-box; }
    body {
      margin: 0; min-height: 100vh; display: grid; place-items: center;
      background: #e7eeec; color: #1c2430;
      font-family: "Segoe UI", "Helvetica Neue", sans-serif;
    }
    form {
      width: min(420px, calc(100% - 32px)); background: #fff;
      border: 1px solid #d5e0dc; border-radius: 16px; padding: 28px;
      box-shadow: 0 16px 40px rgba(20, 40, 36, 0.08);
    }
    p.kicker { margin: 0 0 6px; color: #0e6b5c; font-size: 13px; letter-spacing: 0.04em; text-transform: uppercase; }
    h1 { margin: 0 0 8px; font-size: 28px; }
    .lead { margin: 0 0 22px; color: #52615c; line-height: 1.45; }
    label { display: block; margin: 14px 0 6px; font-size: 14px; }
    input {
      width: 100%; padding: 12px 13px; border: 1px solid #c5d2ce; border-radius: 10px;
      font: inherit; background: #fbfcfb;
    }
    input:focus { outline: 2px solid #0e6b5c; border-color: #0e6b5c; }
    button {
      margin-top: 18px; width: 100%; border: 0; border-radius: 10px;
      background: #0e6b5c; color: white; padding: 12px 14px; font: inherit; cursor: pointer;
    }
    button:hover { background: #0b574b; }
    .error { background: #fdecee; color: #8d2f39; padding: 10px 12px; border-radius: 8px; margin: 0 0 8px; }
  </style>
</head>
<body>
  <form method="post" action="/login">
    <p class="kicker">Accord Medical</p>
    <h1>HR review</h1>
    <p class="lead">Sign in to sort applicants, read how they fit the HR officer role, and save your own mark.</p>
    {% if error %}<p class="error">{{ error }}</p>{% endif %}
    <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
    <label for="email">Email</label>
    <input id="email" name="email" type="email" autocomplete="username" required value="{{ email }}">
    <label for="password">Password</label>
    <input id="password" name="password" type="password" autocomplete="current-password" required>
    <button type="submit">Sign in</button>
  </form>
</body>
</html>
"""

DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="csrf-token" content="{{ csrf_token }}">
  <title>HR review · Accord Medical</title>
  <style>
    :root { color-scheme: light; }
    * { box-sizing: border-box; }
    body { margin: 0; background: #eef2f1; color: #1c2430; font-family: "Segoe UI", "Helvetica Neue", sans-serif; }
    header {
      display: flex; justify-content: space-between; gap: 16px; align-items: center;
      padding: 18px 24px; background: #12312c; color: #f4f7f6;
    }
    header h1 { margin: 0; font-size: 22px; font-weight: 650; }
    header p { margin: 4px 0 0; color: #c9ddd7; font-size: 14px; }
    header form { margin: 0; }
    header button, .btn {
      border: 0; border-radius: 8px; padding: 8px 12px; font: inherit; cursor: pointer;
    }
    header button { background: transparent; color: #f4f7f6; border: 1px solid #3e6b63; }
    main { width: min(1180px, calc(100% - 28px)); margin: 20px auto 40px; }
    .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
    .card, .panel { background: #fff; border: 1px solid #dbe3e1; border-radius: 14px; }
    .card { padding: 14px 16px; }
    .card span { display: block; color: #5d6b66; font-size: 13px; }
    .card strong { display: block; margin-top: 4px; font-size: 26px; }
    .reminder { margin: 14px 0; color: #3d4a46; }
    details { background: #fff; border: 1px solid #dbe3e1; border-radius: 14px; padding: 12px 16px; }
    details summary { cursor: pointer; font-weight: 650; }
    details ul { margin: 8px 0 0; padding-left: 18px; color: #33403c; }
    .toolbar { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; margin: 14px 0; }
    input[type="search"], select {
      border: 1px solid #c5d2ce; border-radius: 10px; padding: 10px 12px; font: inherit; background: #fff;
    }
    input[type="search"] { flex: 1; min-width: 220px; }
    .filters { display: flex; flex-wrap: wrap; gap: 8px; }
    .chip {
      border: 1px solid #c5d2ce; background: #fff; border-radius: 999px; padding: 7px 11px; cursor: pointer; font: inherit;
    }
    .chip.active { background: #0e6b5c; color: #fff; border-color: #0e6b5c; }
    .panel { overflow: auto; }
    table { width: 100%; border-collapse: collapse; min-width: 860px; }
    th, td { text-align: left; padding: 12px 14px; border-bottom: 1px solid #e6eeeb; vertical-align: top; }
    th { font-size: 12px; letter-spacing: 0.04em; text-transform: uppercase; color: #60706b; background: #f7faf9; }
    tr { cursor: pointer; }
    tr:hover td { background: #f4faf8; }
    .role { display: inline-block; border-radius: 999px; padding: 3px 8px; font-size: 12px; background: #e7f3ef; color: #0e6b5c; }
    .role.other { background: #f3eee4; color: #6d5420; }
    .muted { color: #66716d; font-size: 13px; }
    .bar { height: 8px; background: #e6eeeb; border-radius: 99px; overflow: hidden; width: 72px; display: inline-block; vertical-align: middle; }
    .bar i { display: block; height: 100%; background: #0e6b5c; }
    .mark { font-size: 13px; font-weight: 650; }
    .mark.shortlisted, .mark.interview { color: #0e6b5c; }
    .mark.rejected { color: #8d2f39; }
    .mark.on_hold, .mark.maybe { color: #8a5a00; }
    .empty { padding: 28px; color: #52615c; }
    .drawer-back { position: fixed; inset: 0; background: rgba(18, 28, 26, 0.35); display: none; }
    .drawer-back.open { display: block; }
    .drawer {
      position: fixed; top: 0; right: 0; height: 100%; width: min(460px, 100%);
      background: #fff; transform: translateX(100%); transition: transform 0.18s ease;
      overflow: auto; padding: 22px; box-shadow: -12px 0 30px rgba(0,0,0,0.08);
    }
    .drawer-back.open .drawer { transform: none; }
    .drawer h2 { margin: 0 0 4px; }
    .close {
      float: right; border: 0; background: #eef2f1; border-radius: 8px; padding: 6px 10px; cursor: pointer; font: inherit;
    }
    .pills { display: flex; flex-wrap: wrap; gap: 6px; margin: 8px 0 14px; }
    .pill { background: #e7f3ef; color: #145246; border-radius: 999px; padding: 4px 8px; font-size: 13px; }
    .pill.gap { background: #fdecee; color: #8d2f39; }
    .criterion { margin: 8px 0; }
    .criterion b { display: block; font-size: 14px; }
    label.field, p.field { display: block; margin-top: 12px; margin-bottom: 0; font-size: 14px; }
    textarea, .drawer select {
      width: 100%; margin-top: 6px; border: 1px solid #c5d2ce; border-radius: 10px; padding: 10px; font: inherit;
    }
    .stars { display: flex; gap: 6px; margin-top: 6px; }
    .stars button { width: 42px; background: #f4f7f6; border: 1px solid #c5d2ce; }
    .stars button.on { background: #0e6b5c; color: white; border-color: #0e6b5c; }
    .actions { display: flex; gap: 8px; margin-top: 14px; }
    .btn.primary { background: #0e6b5c; color: white; }
    .btn.quiet { background: #eef2f1; }
    .history { margin-top: 18px; color: #3d4a46; font-size: 14px; }
    .history li { margin: 6px 0; }
    .warn { color: #8d2f39; min-height: 1.2em; }
    @media (max-width: 800px) {
      .stats { grid-template-columns: 1fr 1fr; }
      header { align-items: flex-start; flex-direction: column; }
    }
  </style>
</head>
<body>
  <header>
    <div>
      <h1>Applicant review</h1>
      <p>Signed in as {{ user.email }}</p>
    </div>
    <form method="post" action="/logout">
      <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
      <button type="submit">Log out</button>
    </form>
  </header>
  <main>
    <section class="stats" id="stats"></section>
    <p class="reminder">Fitness is the match to the HR officer role: a bachelor's in HR or business, and 1–2 years in HR or administration. General rating also weighs work history and how complete the CV is. People who applied for other jobs stay in the list so you can see them.</p>
    <details>
      <summary>Role being scored</summary>
      <div id="job"></div>
    </details>
    <div class="toolbar">
      <input id="search" type="search" placeholder="Search name, email, role, or experience">
      <select id="sort" aria-label="Sort by">
        <option value="general_rating">General rating</option>
        <option value="fitness">Fitness for HR</option>
        <option value="years">Years of experience</option>
        <option value="hr_years">HR or admin years</option>
        <option value="age">Age</option>
        <option value="hr_rating">Your rating</option>
        <option value="name">Name</option>
        <option value="newest">Newest</option>
      </select>
      <select id="order" aria-label="Sort direction">
        <option value="desc">High to low</option>
        <option value="asc">Low to high</option>
      </select>
    </div>
    <div class="filters" id="filters"></div>
    <section class="panel" style="margin-top:12px">
      <table>
        <thead>
          <tr>
            <th>Applicant</th>
            <th>Applied for</th>
            <th>Experience</th>
            <th>Age</th>
            <th>General</th>
            <th>Fitness</th>
            <th>Your rating</th>
            <th>Mark</th>
            <th></th>
          </tr>
        </thead>
        <tbody id="rows"></tbody>
      </table>
      <p class="empty" id="empty" hidden></p>
    </section>
  </main>
  <div class="drawer-back" id="drawer">
    <aside class="drawer" role="dialog" aria-modal="true" aria-labelledby="drawer-title">
      <button class="close" id="close" type="button">Close</button>
      <h2 id="drawer-title">Applicant</h2>
      <p class="muted" id="drawer-role"></p>
      <div id="drawer-body"></div>
    </aside>
  </div>
  <script>
    const MARKS = [
      ["unmarked", "Unmarked"],
      ["shortlisted", "Shortlisted"],
      ["interview", "Interview"],
      ["on_hold", "On hold"],
      ["maybe", "Maybe"],
      ["rejected", "Rejected"]
    ];
    const state = {
      sort: localStorage.getItem("hr_sort") || "general_rating",
      order: localStorage.getItem("hr_order") || "desc",
      role: localStorage.getItem("hr_role") || "",
      q: "",
      rating: null,
      openId: null
    };
    const csrf = document.querySelector('meta[name="csrf-token"]').content;
    const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (ch) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    }[ch]));
    const num = (value) => value === null || value === undefined || value === "" ? "—" : Number(value).toFixed(1).replace(/\\.0$/, "");

    async function api(url, options = {}) {
      const opts = Object.assign({ headers: {} }, options);
      if (opts.body) opts.headers["Content-Type"] = "application/json";
      opts.headers["X-CSRF-Token"] = csrf;
      const response = await fetch(url, opts);
      if (response.status === 401) {
        window.location = "/login";
        throw new Error("login");
      }
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.error || "Request failed");
      return data;
    }

    function stars(selected) {
      const buttons = [1, 2, 3, 4, 5].map((n) => {
        const on = Number(selected) >= n ? "on" : "";
        return '<button type="button" data-star="' + n + '" class="' + on + '">' + n + "</button>";
      }).join("");
      return '<div class="stars">' + buttons + "</div>";
    }

    async function load() {
      const [stats, job] = await Promise.all([api("/api/review"), api("/api/job")]);
      document.getElementById("stats").innerHTML = [
        ["Applicants", stats.total],
        ["Applied for HR", stats.by_role["Human Resources"] || 0],
        ["Strong HR fit", stats.strong_fit],
        ["Marked by you", stats.marked]
      ].map(([label, value]) => `<article class="card"><span>${label}</span><strong>${value}</strong></article>`).join("");
      const reqs = (job.requirements || []).map((item) => `<li>${esc(item)}</li>`).join("");
      document.getElementById("job").innerHTML = `<p><strong>${esc(job.title)}</strong>. ${esc(job.education_target)}. ${esc(job.experience_target)}.</p><ul>${reqs}</ul>`;
      const filters = document.getElementById("filters");
      const chips = [["", "All", stats.total]].concat(
        Object.entries(stats.by_role).map(([name, count]) => [name, name, count])
      );
      filters.innerHTML = chips.map(([value, label, count]) =>
        `<button type="button" class="chip ${state.role === value ? "active" : ""}" data-role="${esc(value)}">${esc(label)} ${count}</button>`
      ).join("");
      filters.querySelectorAll(".chip").forEach((button) => {
        button.onclick = () => {
          state.role = button.dataset.role;
          localStorage.setItem("hr_role", state.role);
          load();
        };
      });
      const params = new URLSearchParams({ sort: state.sort, order: state.order, q: state.q, category: state.role });
      const rows = await api("/api/applicants?" + params.toString());
      const body = document.getElementById("rows");
      const empty = document.getElementById("empty");
      if (!rows.length) {
        body.innerHTML = "";
        empty.hidden = false;
        empty.textContent = state.q || state.role
          ? "No applicants match this filter."
          : "No applicants stored yet. The review model is ready. Mail import stays off until you run it with the new mailbox credentials.";
        return;
      }
      empty.hidden = true;
      body.innerHTML = rows.map((row) => {
        const age = row.age == null ? "—" : `${row.age}${row.age_estimated ? " est." : ""}`;
        const yours = row.hr_rating == null ? "—" : `${num(row.hr_rating)}/5`;
        return `<tr data-id="${row.id}">
          <td><strong>${esc(row.full_name || "Unknown")}</strong><div class="muted">${esc(row.email || "")}</div></td>
          <td><span class="role ${row.applied_role_category === "Human Resources" ? "" : "other"}">${esc(row.applied_role_category || "Other")}</span><div class="muted">${esc(row.applied_role || "")}</div></td>
          <td>${num(row.years_experience)} yrs<div class="muted">${num(row.hr_years)} HR/admin</div></td>
          <td>${esc(age)}</td>
          <td>${num(row.general_rating)} <span class="bar"><i style="width:${Math.max(0, Math.min(100, row.general_rating || 0))}%"></i></span></td>
          <td>${num(row.fitness_score)}<div class="muted">${esc(row.fit_band || "")}</div></td>
          <td>${yours}</td>
          <td class="mark ${esc(row.hr_mark)}">${esc(markLabel(row.hr_mark))}</td>
          <td><button type="button" class="btn quiet" data-review="${row.id}">Review</button></td>
        </tr>`;
      }).join("");
      body.querySelectorAll("[data-review]").forEach((button) => {
        button.onclick = (event) => {
          event.stopPropagation();
          openReview(button.dataset.review);
        };
      });
      body.querySelectorAll("tr").forEach((tr) => {
        tr.onclick = () => openReview(tr.dataset.id);
      });
    }

    function markLabel(value) {
      const found = MARKS.find(([key]) => key === value);
      return found ? found[1] : "Unmarked";
    }

    async function openReview(id) {
      const person = await api("/api/applicants/" + id);
      state.openId = person.id;
      state.rating = person.hr_rating == null ? null : Number(person.hr_rating);
      document.getElementById("drawer-title").textContent = person.full_name || "Unknown applicant";
      document.getElementById("drawer-role").textContent = `${person.applied_role_category || "Other"} · ${person.applied_role || ""}`;
      const roles = (person.experience || person.previous_roles || []).map((role) =>
        `<li><strong>${esc(role.position || "Role")}</strong>${role.company ? " at " + esc(role.company) : ""} <span class="muted">${esc(role.start_date || "")} – ${esc(role.end_date || "")} ${esc(role.duration || "")}</span></li>`
      ).join("");
      const education = (person.education || []).map((item) =>
        `<li>${esc(item.degree || "")}${item.institution ? ", " + esc(item.institution) : ""} ${esc(item.year || "")}</li>`
      ).join("");
      const docs = (person.documents || []).map((item) =>
        `<li><a href="/api/applicants/${person.id}/documents/${item.id}" target="_blank" rel="noopener">${esc(item.kind_label || "Document")}</a> <span class="muted">${esc(item.file_name || "")}</span></li>`
      ).join("");
      const strengths = (person.strengths || []).map((item) => `<span class="pill">${esc(item)}</span>`).join("");
      const gaps = (person.gaps || []).map((item) => `<span class="pill gap">${esc(item)}</span>`).join("");
      const criteria = (person.criteria || []).map((item) =>
        `<div class="criterion"><b>${esc(item.label)} · ${num(item.points)}/${item.weight}</b><span class="muted">${esc(item.evidence || "")}</span><div class="bar"><i style="width:${Math.round((item.score || 0) * 100)}%"></i></div></div>`
      ).join("");
      const history = (person.mark_history || []).map((item) =>
        `<li>${esc(item.created_at || "")} · ${esc(markLabel(item.mark))} · ${item.rating == null ? "no rating" : num(item.rating) + "/5"}${item.notes ? " · " + esc(item.notes) : ""}</li>`
      ).join("");
      const options = MARKS.map(([value, label]) =>
        `<option value="${value}" ${person.hr_mark === value ? "selected" : ""}>${label}</option>`
      ).join("");
      document.getElementById("drawer-body").innerHTML = `
        <p>${esc(person.fitness_summary || "")}</p>
        <p class="muted">${esc(person.phone || "")} ${esc(person.location || "")}</p>
        <p><strong>General ${num(person.general_rating)}</strong> · fitness ${num(person.fitness_score)} · ${num(person.years_experience)} years · ${person.age == null ? "age unknown" : esc(String(person.age)) + (person.age_estimated ? " (estimated)" : "")}</p>
        <h3>Strengths</h3><div class="pills">${strengths || '<span class="muted">None recorded</span>'}</div>
        <h3>Gaps</h3><div class="pills">${gaps || '<span class="muted">None recorded</span>'}</div>
        <h3>Previous experience</h3><ul>${roles || "<li>No structured work history found.</li>"}</ul>
        <h3>Education</h3><ul>${education || "<li>No degree found.</li>"}</ul>
        <h3>Other documents</h3><ul>${docs || "<li>None kept with this application.</li>"}</ul>
        ${person.file_name ? `<p><a href="/api/applicants/${person.id}/cv" target="_blank" rel="noopener">Open CV file</a> <span class="muted">${esc(person.file_name)}</span></p>` : ""}
        <h3>How the score was built</h3>${criteria}
        <label class="field">Mark
          <select id="mark">${options}</select>
        </label>
        <p class="field">Your rating</p>
        ${stars(state.rating || 0)}
        <label class="field">Note
          <textarea id="notes" rows="3">${esc(person.hr_notes || "")}</textarea>
        </label>
        <p class="warn" id="save-error"></p>
        <div class="actions">
          <button class="btn primary" id="save" type="button">Save mark</button>
          <button class="btn quiet" id="clear" type="button">Clear</button>
        </div>
        <div class="history"><h3>Saved marks</h3><ul>${history || "<li>None yet.</li>"}</ul></div>
      `;
      document.querySelectorAll("[data-star]").forEach((button) => {
        button.onclick = () => {
          state.rating = Number(button.dataset.star);
          document.querySelectorAll("[data-star]").forEach((other) => {
            other.classList.toggle("on", Number(other.dataset.star) <= state.rating);
          });
        };
      });
      document.getElementById("save").onclick = () => saveMark(false);
      document.getElementById("clear").onclick = () => saveMark(true);
      document.getElementById("drawer").classList.add("open");
    }

    async function saveMark(clear) {
      const error = document.getElementById("save-error");
      error.textContent = "";
      const payload = clear ? { mark: "unmarked", rating: null, notes: "" } : {
        mark: document.getElementById("mark").value,
        rating: state.rating,
        notes: document.getElementById("notes").value
      };
      try {
        await api("/api/applicants/" + state.openId + "/mark", { method: "POST", body: JSON.stringify(payload) });
        await load();
        await openReview(state.openId);
      } catch (err) {
        error.textContent = err.message;
      }
    }

    document.getElementById("sort").value = state.sort;
    document.getElementById("order").value = state.order;
    document.getElementById("sort").onchange = (event) => {
      state.sort = event.target.value;
      localStorage.setItem("hr_sort", state.sort);
      load();
    };
    document.getElementById("order").onchange = (event) => {
      state.order = event.target.value;
      localStorage.setItem("hr_order", state.order);
      load();
    };
    let searchTimer = null;
    document.getElementById("search").oninput = (event) => {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(() => {
        state.q = event.target.value.trim();
        load();
      }, 200);
    };
    document.getElementById("close").onclick = () => document.getElementById("drawer").classList.remove("open");
    document.getElementById("drawer").onclick = (event) => {
      if (event.target.id === "drawer") event.currentTarget.classList.remove("open");
    };
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") document.getElementById("drawer").classList.remove("open");
    });
    load().catch((err) => {
      document.getElementById("empty").hidden = false;
      document.getElementById("empty").textContent = err.message;
    });
  </script>
</body>
</html>
"""


def ensure_csrf() -> str:
    token = session.get("csrf")
    if not token:
        session["csrf"] = secrets.token_hex(16)
    return session["csrf"]


def csrf_ok() -> bool:
    sent = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token") or ""
    expected = session.get("csrf") or ""
    return bool(sent) and bool(expected) and hmac.compare_digest(sent, expected)


@app.before_request
def require_login():
    if request.endpoint in {"login", "static"}:
        return None
    if session.get("user"):
        return None
    if request.path.startswith("/api/"):
        return jsonify({"error": "Sign in required"}), 401
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user") and request.method == "GET":
        return redirect(url_for("dashboard"))
    error = ""
    email = Config.DASHBOARD_EMAIL
    if request.method == "POST":
        email = (request.form.get("email") or "").strip()
        password = request.form.get("password") or ""
        if not csrf_ok():
            error = "The form expired. Try again."
        else:
            user = db.get_user(email)
            if user and verify_password(password, user["password_hash"]):
                session.clear()
                session["user"] = {"email": user["email"], "name": user["name"]}
                session["csrf"] = secrets.token_hex(16)
                session.permanent = True
                return redirect(url_for("dashboard"))
            error = "Those credentials were not recognised."
    status = 401 if error else 200
    return render_template_string(
        LOGIN_TEMPLATE,
        error=error,
        email=email,
        csrf_token=ensure_csrf(),
    ), status


@app.route("/logout", methods=["POST"])
def logout():
    if csrf_ok():
        session.clear()
    return redirect(url_for("login"))


@app.route("/")
def dashboard():
    return render_template_string(
        DASHBOARD_TEMPLATE,
        csrf_token=ensure_csrf(),
        user=session["user"],
    )


@app.route("/api/review")
def api_review():
    return jsonify(db.get_review_stats())


@app.route("/api/job")
def api_job():
    return jsonify(HR_JOB)


@app.route("/api/applicants")
def api_applicants():
    return jsonify(db.get_applicants(
        sort=request.args.get("sort", "general_rating"),
        order=request.args.get("order", "desc"),
        category=request.args.get("category", ""),
        query=request.args.get("q", ""),
    ))


@app.route("/api/applicants/<int:candidate_id>")
def api_applicant(candidate_id):
    applicant = db.get_applicant(candidate_id)
    if not applicant:
        return jsonify({"error": "Applicant not found"}), 404
    return jsonify(applicant)


@app.route("/api/applicants/<int:candidate_id>/mark", methods=["POST"])
def api_mark(candidate_id):
    if not csrf_ok():
        return jsonify({"error": "The form expired. Reload the page."}), 400
    data = request.get_json(silent=True) or {}
    mark = data.get("mark") or "unmarked"
    if mark not in REVIEW_MARKS:
        return jsonify({"error": "Unknown mark"}), 400
    try:
        saved = db.save_mark(
            candidate_id,
            mark,
            data.get("rating"),
            data.get("notes") or "",
            session["user"]["email"],
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(saved)


@app.route("/api/applicants/<int:candidate_id>/cv")
def api_cv(candidate_id):
    applicant = db.get_applicant(candidate_id)
    if not applicant:
        abort(404)
    path = _safe_stored_path(applicant.get("file_path") or "", Config.CV_STORAGE_PATH)
    if not path:
        abort(404)
    return send_file(path, as_attachment=False, download_name=os.path.basename(path))


@app.route("/api/applicants/<int:candidate_id>/documents/<int:document_id>")
def api_document(candidate_id, document_id):
    document = db.get_document(candidate_id, document_id)
    if not document:
        abort(404)
    path = _safe_stored_path(document.get("file_path") or "", Config.DOCUMENTS_PATH)
    if not path:
        abort(404)
    return send_file(path, as_attachment=False, download_name=document.get("file_name") or os.path.basename(path))


def _safe_stored_path(stored: str, root_dir: str):
    if not stored:
        return None
    root = os.path.realpath(root_dir)
    path = os.path.realpath(stored)
    try:
        if os.path.commonpath([root, path]) != root:
            return None
    except ValueError:
        return None
    if not os.path.isfile(path):
        return None
    return path


def run_dashboard(host="0.0.0.0", port=5000, debug=False):
    print(f"HR review is at http://127.0.0.1:{port}")
    print("Sign in with the HR review account. That password is not the mailbox password.")
    app.run(host=host, port=port, debug=debug, use_reloader=False)


if __name__ == "__main__":
    run_dashboard()
