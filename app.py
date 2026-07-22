from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("DATABASE_PATH", BASE_DIR / "qlhn.db"))

app = FastAPI(title="Quản lý hành nghề CDC Hải Phòng", version="0.2.0")
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "change-this-secret-before-production"),
)

CSS = """
:root{font-family:Inter,Arial,sans-serif;color:#1e293b;background:#f1f5f9}
*{box-sizing:border-box}body{margin:0}.wrap{max-width:1280px;margin:auto;padding:24px}
nav{background:#0f4c81;color:white;padding:14px 24px;display:flex;gap:18px;align-items:center;flex-wrap:wrap}
nav a{color:white;text-decoration:none;font-weight:600}.brand{font-size:19px;margin-right:auto}
.card{background:white;border-radius:14px;padding:20px;margin:16px 0;box-shadow:0 2px 10px #00000012}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:14px}
.stat{font-size:30px;font-weight:800;color:#0f4c81}.muted{color:#64748b}.danger{color:#b91c1c}.warn{color:#b45309}.ok{color:#047857}
table{width:100%;border-collapse:collapse;background:white}th,td{padding:11px;border-bottom:1px solid #e2e8f0;text-align:left;vertical-align:top}th{background:#eaf2f8}
input,select,textarea{width:100%;padding:10px;border:1px solid #cbd5e1;border-radius:8px;background:white}textarea{min-height:90px}
label{font-weight:650;display:block;margin:10px 0 5px}.row{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.row3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}
button,.btn{display:inline-block;border:0;border-radius:8px;background:#0f4c81;color:white;padding:10px 14px;text-decoration:none;cursor:pointer;font-weight:650}.btn.secondary{background:#475569}.btn.danger{background:#b91c1c}
.badge{display:inline-block;padding:4px 8px;border-radius:999px;background:#e2e8f0;font-size:12px}.badge.ok{background:#d1fae5}.badge.warn{background:#fef3c7}.badge.danger{background:#fee2e2}
.alert{padding:12px;border-radius:8px;background:#fff7ed;border:1px solid #fdba74;margin:10px 0}
@media(max-width:720px){.row,.row3{grid-template-columns:1fr}.wrap{padding:12px}table{font-size:13px}}
"""


def h(text: object) -> str:
    import html
    return html.escape("" if text is None else str(text))


def page(request: Request, title: str, body: str) -> HTMLResponse:
    user = request.session.get("user")
    auth = ""
    if user:
        auth = f"""
        <nav><div class='brand'>QLHN • CDC Hải Phòng</div>
        <a href='/'>Tổng quan</a><a href='/practitioners'>Người hành nghề</a>
        <a href='/positions'>Vị trí hành nghề</a><a href='/submissions'>Hồ sơ gửi Sở</a>
        <a href='/logout'>Đăng xuất ({h(user)})</a></nav>"""
    return HTMLResponse(f"""<!doctype html><html lang='vi'><head><meta charset='utf-8'>
    <meta name='viewport' content='width=device-width,initial-scale=1'><title>{h(title)}</title>
    <style>{CSS}</style></head><body>{auth}<main class='wrap'>{body}</main></body></html>""")


@contextmanager
def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db() -> None:
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS practitioners(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          code TEXT UNIQUE NOT NULL, full_name TEXT NOT NULL,
          identity_number TEXT, professional_title TEXT NOT NULL,
          qualification TEXT, specialty TEXT, department TEXT,
          employment_status TEXT NOT NULL DEFAULT 'Đang công tác', notes TEXT,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS licenses(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          practitioner_id INTEGER NOT NULL REFERENCES practitioners(id) ON DELETE CASCADE,
          document_type TEXT NOT NULL, license_number TEXT NOT NULL,
          issue_date TEXT, expiry_date TEXT, issuing_authority TEXT,
          practice_scope TEXT, status TEXT NOT NULL DEFAULT 'Còn hiệu lực',
          verified_original INTEGER NOT NULL DEFAULT 0, notes TEXT
        );
        CREATE TABLE IF NOT EXISTS positions(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          practitioner_id INTEGER NOT NULL REFERENCES practitioners(id) ON DELETE CASCADE,
          facility_name TEXT NOT NULL, facility_type TEXT NOT NULL DEFAULT 'Thuộc CDC',
          department TEXT, position_name TEXT NOT NULL,
          is_primary INTEGER NOT NULL DEFAULT 1,
          start_date TEXT NOT NULL, end_date TEXT,
          weekdays TEXT NOT NULL, start_time TEXT NOT NULL, end_time TEXT NOT NULL,
          workflow_status TEXT NOT NULL DEFAULT 'Khoa/phòng đề nghị', notes TEXT
        );
        CREATE TABLE IF NOT EXISTS submissions(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          reference_number TEXT, subject TEXT NOT NULL,
          sent_date TEXT, received_date TEXT, response_number TEXT,
          response_date TEXT, status TEXT NOT NULL DEFAULT 'Dự thảo nội bộ', notes TEXT,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS submission_items(
          submission_id INTEGER NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
          position_id INTEGER NOT NULL REFERENCES positions(id) ON DELETE CASCADE,
          PRIMARY KEY(submission_id, position_id)
        );
        """)
        if not con.execute("SELECT 1 FROM practitioners LIMIT 1").fetchone():
            con.execute("""INSERT INTO practitioners(code,full_name,identity_number,professional_title,qualification,specialty,department)
            VALUES('CDC001','Nguyễn Văn A','031000000001','Bác sĩ y học dự phòng','Bác sĩ','Y học dự phòng','Phòng khám')""")


init_db()


def require_login(request: Request) -> None:
    if not request.session.get("user"):
        raise HTTPException(303, headers={"Location": "/login"})


def current_license(con: sqlite3.Connection, practitioner_id: int):
    today = date.today().isoformat()
    return con.execute("""SELECT * FROM licenses WHERE practitioner_id=?
      AND status NOT IN ('Đình chỉ','Thu hồi')
      AND (expiry_date IS NULL OR expiry_date='' OR expiry_date>=?)
      ORDER BY COALESCE(expiry_date,'9999-12-31') DESC,id DESC LIMIT 1""", (practitioner_id, today)).fetchone()


def conflict_count(con: sqlite3.Connection, pos: sqlite3.Row) -> int:
    rows = con.execute("""SELECT * FROM positions WHERE practitioner_id=? AND id<>?
      AND workflow_status NOT IN ('Đã chấm dứt','Không gửi Sở')
      AND start_date<=COALESCE(?, '9999-12-31')
      AND COALESCE(end_date,'9999-12-31')>=?""",
      (pos["practitioner_id"], pos["id"], pos["end_date"], pos["start_date"])).fetchall()
    days = set((pos["weekdays"] or "").split(","))
    count = 0
    for other in rows:
        if not days.intersection(set((other["weekdays"] or "").split(","))):
            continue
        if pos["start_time"] < other["end_time"] and other["start_time"] < pos["end_time"]:
            count += 1
    return count


@app.get("/login")
def login_page(request: Request):
    if request.session.get("user"):
        return RedirectResponse("/", 303)
    return page(request, "Đăng nhập", """
    <div class='card' style='max-width:420px;margin:70px auto'><h1>Quản lý hành nghề CDC</h1>
    <p class='muted'>Hệ thống nội bộ quản lý giấy phép và đăng ký hành nghề với Sở Y tế.</p>
    <form method='post'><label>Tài khoản</label><input name='username' required>
    <label>Mật khẩu</label><input name='password' type='password' required><br><br><button>Đăng nhập</button></form>
    <p class='muted'>Dữ liệu mẫu: admin / Admin@123</p></div>""")


@app.post("/login")
def login(request: Request, username: Annotated[str, Form()], password: Annotated[str, Form()]):
    if username == os.getenv("APP_USERNAME", "admin") and password == os.getenv("APP_PASSWORD", "Admin@123"):
        request.session["user"] = username
        return RedirectResponse("/", 303)
    return page(request, "Đăng nhập", "<div class='card danger'>Sai tài khoản hoặc mật khẩu.</div><a class='btn' href='/login'>Thử lại</a>")


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", 303)


@app.get("/")
def dashboard(request: Request):
    require_login(request)
    with db() as con:
        p_count = con.execute("SELECT COUNT(*) FROM practitioners WHERE employment_status='Đang công tác'").fetchone()[0]
        position_count = con.execute("SELECT COUNT(*) FROM positions WHERE workflow_status!='Đã chấm dứt'").fetchone()[0]
        pending = con.execute("SELECT COUNT(*) FROM positions WHERE workflow_status NOT IN ('Sở Y tế đã ghi nhận','Đã chấm dứt')").fetchone()[0]
        no_license = con.execute("""SELECT p.id,p.full_name FROM practitioners p WHERE p.employment_status='Đang công tác'
        AND NOT EXISTS(SELECT 1 FROM licenses l WHERE l.practitioner_id=p.id AND l.status NOT IN ('Đình chỉ','Thu hồi')
        AND (l.expiry_date IS NULL OR l.expiry_date='' OR l.expiry_date>=date('now')))""").fetchall()
        positions = con.execute("SELECT x.*,p.full_name FROM positions x JOIN practitioners p ON p.id=x.practitioner_id ORDER BY x.id DESC LIMIT 12").fetchall()
        conflicts = [(x, conflict_count(con, x)) for x in positions]
    body = f"""<h1>Tổng quan quản lý hành nghề</h1>
    <div class='grid'><div class='card'><div class='stat'>{p_count}</div><div>Người đang công tác</div></div>
    <div class='card'><div class='stat'>{position_count}</div><div>Vị trí hành nghề đang quản lý</div></div>
    <div class='card'><div class='stat'>{pending}</div><div>Vị trí chưa được Sở ghi nhận</div></div>
    <div class='card'><div class='stat danger'>{len(no_license)}</div><div>Người chưa có GPHN hợp lệ</div></div></div>"""
    if no_license:
        body += "<div class='card'><h2>Cảnh báo giấy phép</h2>" + "".join(f"<div class='alert'>{h(r['full_name'])}: chưa có giấy phép hợp lệ.</div>" for r in no_license) + "</div>"
    body += "<div class='card'><h2>Vị trí mới cập nhật</h2><table><tr><th>Người hành nghề</th><th>Vị trí</th><th>Lịch</th><th>Trạng thái</th><th>Cảnh báo</th></tr>"
    for pos, count in conflicts:
        warn = f"<span class='badge danger'>{count} lịch trùng</span>" if count else "<span class='badge ok'>Không trùng</span>"
        body += f"<tr><td>{h(pos['full_name'])}</td><td>{h(pos['position_name'])}<br><span class='muted'>{h(pos['facility_name'])}</span></td><td>{h(pos['weekdays'])}<br>{h(pos['start_time'])}–{h(pos['end_time'])}</td><td>{h(pos['workflow_status'])}</td><td>{warn}</td></tr>"
    body += "</table></div>"
    return page(request, "Tổng quan", body)


@app.get("/practitioners")
def practitioners(request: Request):
    require_login(request)
    with db() as con:
        rows = con.execute("SELECT * FROM practitioners ORDER BY full_name").fetchall()
        data = []
        for row in rows:
            data.append((row, current_license(con, row["id"])))
    body = "<h1>Người hành nghề thuộc CDC</h1><a class='btn' href='/practitioners/new'>Thêm người hành nghề</a><div class='card'><table><tr><th>Mã</th><th>Họ tên</th><th>Chức danh</th><th>Khoa/phòng</th><th>Giấy phép hiện tại</th></tr>"
    for row, lic in data:
        lic_text = f"{h(lic['license_number'])}<br><span class='muted'>{h(lic['practice_scope'])}</span>" if lic else "<span class='badge danger'>Chưa có</span>"
        body += f"<tr><td>{h(row['code'])}</td><td><a href='/practitioners/{row['id']}'>{h(row['full_name'])}</a></td><td>{h(row['professional_title'])}</td><td>{h(row['department'])}</td><td>{lic_text}</td></tr>"
    body += "</table></div>"
    return page(request, "Người hành nghề", body)


@app.get("/practitioners/new")
def practitioner_form(request: Request):
    require_login(request)
    return page(request, "Thêm người hành nghề", """
    <h1>Thêm người hành nghề thuộc CDC</h1><div class='card'><form method='post'>
    <div class='row'><div><label>Mã nhân sự</label><input name='code' required></div><div><label>Họ tên</label><input name='full_name' required></div></div>
    <div class='row'><div><label>Số định danh</label><input name='identity_number'></div><div><label>Chức danh chuyên môn</label><input name='professional_title' required></div></div>
    <div class='row3'><div><label>Văn bằng</label><input name='qualification'></div><div><label>Chuyên khoa</label><input name='specialty'></div><div><label>Khoa/phòng</label><input name='department'></div></div>
    <label>Ghi chú</label><textarea name='notes'></textarea><br><button>Lưu hồ sơ</button></form></div>""")


@app.post("/practitioners/new")
def practitioner_create(request: Request, code: Annotated[str, Form()], full_name: Annotated[str, Form()], professional_title: Annotated[str, Form()], identity_number: Annotated[str, Form()]="", qualification: Annotated[str, Form()]="", specialty: Annotated[str, Form()]="", department: Annotated[str, Form()]="", notes: Annotated[str, Form()]=""):
    require_login(request)
    with db() as con:
        try:
            con.execute("INSERT INTO practitioners(code,full_name,identity_number,professional_title,qualification,specialty,department,notes) VALUES(?,?,?,?,?,?,?,?)", (code.strip(),full_name.strip(),identity_number.strip(),professional_title.strip(),qualification.strip(),specialty.strip(),department.strip(),notes.strip()))
        except sqlite3.IntegrityError:
            return page(request,"Lỗi","<div class='card danger'>Mã nhân sự đã tồn tại.</div>")
    return RedirectResponse("/practitioners",303)


@app.get("/practitioners/{pid}")
def practitioner_detail(pid: int, request: Request):
    require_login(request)
    with db() as con:
        p = con.execute("SELECT * FROM practitioners WHERE id=?",(pid,)).fetchone()
        if not p: raise HTTPException(404)
        licenses = con.execute("SELECT * FROM licenses WHERE practitioner_id=? ORDER BY id DESC",(pid,)).fetchall()
        positions = con.execute("SELECT * FROM positions WHERE practitioner_id=? ORDER BY id DESC",(pid,)).fetchall()
    body = f"<h1>{h(p['full_name'])}</h1><div class='card'><b>{h(p['professional_title'])}</b> • {h(p['department'])}<br><span class='muted'>Mã: {h(p['code'])} • Số định danh: {h(p['identity_number'])}</span></div>"
    body += f"<div class='card'><h2>Giấy phép/chứng chỉ</h2><a class='btn' href='/practitioners/{pid}/licenses/new'>Thêm giấy phép</a><table><tr><th>Số</th><th>Loại</th><th>Hiệu lực</th><th>Phạm vi</th><th>Đối chiếu</th></tr>"
    for x in licenses:
        body += f"<tr><td>{h(x['license_number'])}</td><td>{h(x['document_type'])}</td><td>{h(x['issue_date'])} → {h(x['expiry_date'])}</td><td>{h(x['practice_scope'])}</td><td>{'Đã đối chiếu' if x['verified_original'] else 'Chưa đối chiếu'}</td></tr>"
    body += "</table></div><div class='card'><h2>Vị trí hành nghề</h2><table><tr><th>Cơ sở</th><th>Vị trí</th><th>Lịch</th><th>Trạng thái</th></tr>"
    for x in positions:
        body += f"<tr><td>{h(x['facility_name'])}</td><td>{h(x['position_name'])}</td><td>{h(x['weekdays'])} {h(x['start_time'])}–{h(x['end_time'])}</td><td>{h(x['workflow_status'])}</td></tr>"
    body += "</table></div>"
    return page(request,p['full_name'],body)


@app.get("/practitioners/{pid}/licenses/new")
def license_form(pid: int, request: Request):
    require_login(request)
    return page(request,"Thêm giấy phép",f"""<h1>Thêm giấy phép</h1><div class='card'><form method='post'>
    <div class='row'><div><label>Loại giấy tờ</label><select name='document_type'><option>Giấy phép hành nghề</option><option>Chứng chỉ hành nghề chuyển tiếp</option></select></div><div><label>Số giấy phép</label><input name='license_number' required></div></div>
    <div class='row3'><div><label>Ngày cấp</label><input type='date' name='issue_date'></div><div><label>Ngày hết hạn</label><input type='date' name='expiry_date'></div><div><label>Cơ quan cấp</label><input name='issuing_authority'></div></div>
    <label>Phạm vi hành nghề</label><textarea name='practice_scope'></textarea><label><input style='width:auto' type='checkbox' name='verified_original' value='1'> Đã đối chiếu bản gốc</label><br><button>Lưu giấy phép</button></form></div>""")


@app.post("/practitioners/{pid}/licenses/new")
def license_create(pid: int, request: Request, document_type: Annotated[str, Form()], license_number: Annotated[str, Form()], issue_date: Annotated[str, Form()]="", expiry_date: Annotated[str, Form()]="", issuing_authority: Annotated[str, Form()]="", practice_scope: Annotated[str, Form()]="", verified_original: Annotated[str|None, Form()]=None):
    require_login(request)
    with db() as con:
        con.execute("INSERT INTO licenses(practitioner_id,document_type,license_number,issue_date,expiry_date,issuing_authority,practice_scope,verified_original) VALUES(?,?,?,?,?,?,?,?)",(pid,document_type,license_number,issue_date,expiry_date,issuing_authority,practice_scope,1 if verified_original else 0))
    return RedirectResponse(f"/practitioners/{pid}",303)


@app.get("/positions")
def positions(request: Request):
    require_login(request)
    with db() as con:
        rows=con.execute("SELECT x.*,p.full_name FROM positions x JOIN practitioners p ON p.id=x.practitioner_id ORDER BY x.id DESC").fetchall()
        data=[(x,conflict_count(con,x)) for x in rows]
    body="<h1>Vị trí làm việc hành nghề</h1><a class='btn' href='/positions/new'>Đăng ký vị trí mới</a><div class='card'><table><tr><th>Người hành nghề</th><th>Cơ sở/vị trí</th><th>Thời gian</th><th>Luồng nội bộ</th><th>Kiểm tra</th></tr>"
    for x,c in data:
        check=f"<span class='badge danger'>{c} lịch trùng</span>" if c else "<span class='badge ok'>Hợp lệ sơ bộ</span>"
        body+=f"<tr><td>{h(x['full_name'])}</td><td>{h(x['facility_name'])}<br><b>{h(x['position_name'])}</b></td><td>{h(x['start_date'])} → {h(x['end_date'])}<br>{h(x['weekdays'])} {h(x['start_time'])}–{h(x['end_time'])}</td><td>{h(x['workflow_status'])}</td><td>{check}</td></tr>"
    body+="</table></div>"
    return page(request,"Vị trí hành nghề",body)


@app.get("/positions/new")
def position_form(request: Request):
    require_login(request)
    with db() as con: people=con.execute("SELECT id,full_name,professional_title FROM practitioners WHERE employment_status='Đang công tác' ORDER BY full_name").fetchall()
    options="".join(f"<option value='{x['id']}'>{h(x['full_name'])} — {h(x['professional_title'])}</option>" for x in people)
    return page(request,"Đăng ký vị trí",f"""<h1>Đăng ký vị trí hành nghề</h1><div class='card'><form method='post'>
    <label>Người hành nghề</label><select name='practitioner_id'>{options}</select>
    <div class='row'><div><label>Tên cơ sở/địa điểm</label><input name='facility_name' value='Trung tâm Kiểm soát bệnh tật thành phố Hải Phòng' required></div><div><label>Loại cơ sở</label><select name='facility_type'><option>Thuộc CDC</option><option>Ngoài CDC - chỉ khai báo</option></select></div></div>
    <div class='row'><div><label>Khoa/phòng</label><input name='department'></div><div><label>Vị trí công tác hành nghề</label><input name='position_name' required></div></div>
    <label><input style='width:auto' type='checkbox' name='is_primary' value='1' checked> Cơ sở hành nghề chính</label>
    <div class='row'><div><label>Ngày bắt đầu</label><input type='date' name='start_date' required></div><div><label>Ngày kết thúc</label><input type='date' name='end_date'></div></div>
    <div class='row3'><div><label>Ngày trong tuần</label><input name='weekdays' placeholder='T2,T3,T4,T5,T6' required></div><div><label>Giờ bắt đầu</label><input type='time' name='start_time' required></div><div><label>Giờ kết thúc</label><input type='time' name='end_time' required></div></div>
    <label>Ghi chú</label><textarea name='notes'></textarea><br><button>Lưu đề nghị</button></form></div>""")


@app.post("/positions/new")
def position_create(request: Request, practitioner_id: Annotated[int, Form()], facility_name: Annotated[str, Form()], facility_type: Annotated[str, Form()], position_name: Annotated[str, Form()], start_date: Annotated[str, Form()], weekdays: Annotated[str, Form()], start_time: Annotated[str, Form()], end_time: Annotated[str, Form()], department: Annotated[str, Form()]="", end_date: Annotated[str, Form()]="", is_primary: Annotated[str|None, Form()]=None, notes: Annotated[str, Form()]=""):
    require_login(request)
    if start_time>=end_time: return page(request,"Lỗi","<div class='card danger'>Giờ kết thúc phải sau giờ bắt đầu.</div>")
    with db() as con:
        if not current_license(con,practitioner_id):
            return page(request,"Lỗi","<div class='card danger'>Người hành nghề chưa có giấy phép hợp lệ; chưa thể tạo vị trí đăng ký.</div>")
        con.execute("INSERT INTO positions(practitioner_id,facility_name,facility_type,department,position_name,is_primary,start_date,end_date,weekdays,start_time,end_time,notes) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(practitioner_id,facility_name,facility_type,department,position_name,1 if is_primary else 0,start_date,end_date,weekdays,start_time,end_time,notes))
    return RedirectResponse("/positions",303)


@app.get("/submissions")
def submissions(request: Request):
    require_login(request)
    with db() as con: rows=con.execute("SELECT s.*,COUNT(i.position_id) item_count FROM submissions s LEFT JOIN submission_items i ON i.submission_id=s.id GROUP BY s.id ORDER BY s.id DESC").fetchall()
    body="<h1>Hồ sơ đăng ký gửi Sở Y tế</h1><a class='btn' href='/submissions/new'>Tạo hồ sơ gửi Sở</a><div class='card'><table><tr><th>Số/ký hiệu</th><th>Trích yếu</th><th>Số vị trí</th><th>Ngày gửi</th><th>Trạng thái</th><th>Phản hồi</th></tr>"
    for x in rows:
        body+=f"<tr><td>{h(x['reference_number'])}</td><td>{h(x['subject'])}</td><td>{x['item_count']}</td><td>{h(x['sent_date'])}</td><td>{h(x['status'])}</td><td>{h(x['response_number'])} {h(x['response_date'])}</td></tr>"
    body+="</table></div>"
    return page(request,"Hồ sơ gửi Sở",body)


@app.get("/submissions/new")
def submission_form(request: Request):
    require_login(request)
    with db() as con:
        rows=con.execute("""SELECT x.id,p.full_name,x.position_name,x.facility_name,x.workflow_status FROM positions x JOIN practitioners p ON p.id=x.practitioner_id
        WHERE x.workflow_status IN ('Khoa/phòng đề nghị','TCHC đã kiểm tra','KHNV đã kiểm tra','Lãnh đạo CDC đã duyệt') ORDER BY p.full_name""").fetchall()
    checks="".join(f"<label><input style='width:auto' type='checkbox' name='position_ids' value='{x['id']}'> {h(x['full_name'])} — {h(x['position_name'])} — {h(x['facility_name'])}</label>" for x in rows)
    return page(request,"Tạo hồ sơ gửi Sở",f"""<h1>Tạo hồ sơ đăng ký gửi Sở Y tế</h1><div class='card'><form method='post'>
    <div class='row'><div><label>Số/ký hiệu công văn</label><input name='reference_number'></div><div><label>Ngày gửi</label><input type='date' name='sent_date'></div></div>
    <label>Trích yếu</label><input name='subject' value='Về việc đăng ký hành nghề khám bệnh, chữa bệnh tại Trung tâm Kiểm soát bệnh tật thành phố' required>
    <h3>Chọn vị trí đưa vào danh sách</h3>{checks}<label>Ghi chú</label><textarea name='notes'></textarea><br><button>Tạo hồ sơ</button></form></div>""")


@app.post("/submissions/new")
def submission_create(request: Request, subject: Annotated[str, Form()], reference_number: Annotated[str, Form()]="", sent_date: Annotated[str, Form()]="", notes: Annotated[str, Form()]="", position_ids: Annotated[list[int]|None, Form()]=None):
    require_login(request)
    position_ids=position_ids or []
    with db() as con:
        cur=con.execute("INSERT INTO submissions(reference_number,subject,sent_date,status,notes) VALUES(?,?,?,?,?)",(reference_number,subject,sent_date,"Đã gửi Sở Y tế" if sent_date else "Dự thảo nội bộ",notes))
        sid=cur.lastrowid
        for pid in position_ids:
            con.execute("INSERT OR IGNORE INTO submission_items(submission_id,position_id) VALUES(?,?)",(sid,pid))
            con.execute("UPDATE positions SET workflow_status=? WHERE id=?",("Đã gửi Sở Y tế" if sent_date else "Lãnh đạo CDC đã duyệt",pid))
    return RedirectResponse("/submissions",303)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
