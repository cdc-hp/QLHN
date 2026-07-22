"""Bản hiệu chỉnh vai trò: Phòng Kế hoạch - Nghiệp vụ (KHNV) chủ trì."""
from __future__ import annotations

from typing import Annotated

from fastapi import Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app import app, conflict_count, db, h, page, require_login

LEAD_UNIT = "Phòng Kế hoạch - Nghiệp vụ (KHNV)"
INTERNAL_FLOW = [
    "Khoa/phòng đề nghị",
    "KHNV tiếp nhận",
    "KHNV đã rà soát GPHN và vị trí",
    "TCHC đã phối hợp xác nhận nhân sự",
    "KHNV đã hoàn thiện hồ sơ",
    "Lãnh đạo CDC đã duyệt",
]
FINAL_STATUSES = [
    "Đã gửi Sở Y tế",
    "Sở Y tế yêu cầu bổ sung",
    "Sở Y tế đã ghi nhận",
    "Không gửi Sở",
    "Đã chấm dứt",
]
ALL_STATUSES = INTERNAL_FLOW + FINAL_STATUSES


def _remove_route(path: str, methods: set[str]) -> None:
    app.router.routes[:] = [
        route
        for route in app.router.routes
        if not (
            getattr(route, "path", None) == path
            and methods.intersection(set(getattr(route, "methods", set())))
        )
    ]


with db() as con:
    columns = {row[1] for row in con.execute("PRAGMA table_info(submissions)")}
    if "lead_unit" not in columns:
        con.execute(
            "ALTER TABLE submissions ADD COLUMN lead_unit TEXT NOT NULL "
            "DEFAULT 'Phòng Kế hoạch - Nghiệp vụ (KHNV)'"
        )
    con.execute(
        "UPDATE positions SET workflow_status='TCHC đã phối hợp xác nhận nhân sự' "
        "WHERE workflow_status='TCHC đã kiểm tra'"
    )
    con.execute(
        "UPDATE positions SET workflow_status='KHNV đã hoàn thiện hồ sơ' "
        "WHERE workflow_status='KHNV đã kiểm tra'"
    )


@app.middleware("http")
async def show_khnv_lead(request: Request, call_next):
    response = await call_next(request)
    if "text/html" not in response.headers.get("content-type", ""):
        return response
    body = b"".join([chunk async for chunk in response.body_iterator])
    text = body.decode("utf-8")
    banner = (
        "<div class='alert' style='background:#eff6ff;border-color:#93c5fd'>"
        f"<b>Đơn vị chủ trì: {LEAD_UNIT}</b><br>"
        "KHNV tiếp nhận, rà soát giấy phép, vị trí và lịch hành nghề; "
        "TCHC phối hợp xác nhận thông tin nhân sự; KHNV hoàn thiện hồ sơ "
        "trình Lãnh đạo CDC và gửi Sở Y tế.</div>"
    )
    for heading in (
        "<h1>Tổng quan quản lý hành nghề</h1>",
        "<h1>Vị trí làm việc hành nghề</h1>",
        "<h1>Hồ sơ đăng ký gửi Sở Y tế</h1>",
        "<h1>Tạo hồ sơ đăng ký gửi Sở Y tế</h1>",
    ):
        text = text.replace(heading, heading + banner)
    text = text.replace(
        "Hệ thống nội bộ quản lý giấy phép và đăng ký hành nghề với Sở Y tế.",
        "Hệ thống nội bộ do Phòng KHNV chủ trì quản lý giấy phép và đăng ký hành nghề với Sở Y tế.",
    )
    headers = dict(response.headers)
    headers.pop("content-length", None)
    headers.pop("content-type", None)
    return HTMLResponse(text, status_code=response.status_code, headers=headers)


_remove_route("/positions", {"GET"})


@app.get("/positions")
def positions_khnv(request: Request):
    require_login(request)
    with db() as con:
        rows = con.execute(
            "SELECT x.*,p.full_name FROM positions x "
            "JOIN practitioners p ON p.id=x.practitioner_id ORDER BY x.id DESC"
        ).fetchall()
        data = [(row, conflict_count(con, row)) for row in rows]
    flow = " → ".join(INTERNAL_FLOW) + " → Gửi Sở → Theo dõi phản hồi"
    body = (
        "<h1>Vị trí làm việc hành nghề</h1>"
        f"<div class='card'><b>Luồng do KHNV chủ trì:</b><br><span class='muted'>{h(flow)}</span></div>"
        "<a class='btn' href='/positions/new'>Đăng ký vị trí mới</a>"
        "<div class='card'><table><tr><th>Người hành nghề</th><th>Cơ sở/vị trí</th>"
        "<th>Thời gian</th><th>Trạng thái</th><th>Kiểm tra</th><th>Cập nhật bước</th></tr>"
    )
    for item, count in data:
        check = (
            f"<span class='badge danger'>{count} lịch trùng</span>"
            if count
            else "<span class='badge ok'>Hợp lệ sơ bộ</span>"
        )
        options = "".join(
            f"<option{' selected' if status == item['workflow_status'] else ''}>{h(status)}</option>"
            for status in ALL_STATUSES
        )
        body += (
            f"<tr><td>{h(item['full_name'])}</td>"
            f"<td>{h(item['facility_name'])}<br><b>{h(item['position_name'])}</b></td>"
            f"<td>{h(item['start_date'])} → {h(item['end_date'])}<br>"
            f"{h(item['weekdays'])} {h(item['start_time'])}–{h(item['end_time'])}</td>"
            f"<td>{h(item['workflow_status'])}</td><td>{check}</td>"
            f"<td><form method='post' action='/positions/{item['id']}/status'>"
            f"<select name='workflow_status'>{options}</select><br><br>"
            "<button class='btn'>Lưu trạng thái</button></form></td></tr>"
        )
    body += "</table></div>"
    return page(request, "Vị trí hành nghề", body)


@app.post("/positions/{position_id}/status")
def update_position_status(
    position_id: int,
    request: Request,
    workflow_status: Annotated[str, Form()],
):
    require_login(request)
    if workflow_status not in ALL_STATUSES:
        raise HTTPException(400, "Trạng thái không hợp lệ")
    with db() as con:
        if not con.execute("SELECT 1 FROM positions WHERE id=?", (position_id,)).fetchone():
            raise HTTPException(404)
        con.execute(
            "UPDATE positions SET workflow_status=? WHERE id=?",
            (workflow_status, position_id),
        )
    return RedirectResponse("/positions", 303)


_remove_route("/submissions/new", {"GET", "POST"})


@app.get("/submissions/new")
def submission_form_khnv(request: Request):
    require_login(request)
    with db() as con:
        rows = con.execute(
            """SELECT x.id,p.full_name,x.position_name,x.facility_name,x.workflow_status
            FROM positions x JOIN practitioners p ON p.id=x.practitioner_id
            WHERE x.workflow_status IN ('Lãnh đạo CDC đã duyệt','Sở Y tế yêu cầu bổ sung')
            ORDER BY p.full_name"""
        ).fetchall()
    checks = "".join(
        f"<label><input style='width:auto' type='checkbox' name='position_ids' value='{item['id']}'> "
        f"{h(item['full_name'])} — {h(item['position_name'])} — {h(item['facility_name'])} "
        f"<span class='muted'>({h(item['workflow_status'])})</span></label>"
        for item in rows
    )
    if not checks:
        checks = "<div class='alert'>Chưa có vị trí được Lãnh đạo CDC duyệt hoặc cần bổ sung.</div>"
    return page(
        request,
        "Tạo hồ sơ gửi Sở",
        f"""<h1>Tạo hồ sơ đăng ký gửi Sở Y tế</h1><div class='card'><form method='post'>
        <div class='alert'><b>Đơn vị chủ trì: {LEAD_UNIT}</b></div>
        <div class='row'><div><label>Số/ký hiệu công văn</label>
        <input name='reference_number' placeholder='123/CDC-KHNV'></div>
        <div><label>Ngày gửi</label><input type='date' name='sent_date'></div></div>
        <label>Trích yếu</label><input name='subject' value='Về việc đăng ký hành nghề khám bệnh, chữa bệnh tại Trung tâm Kiểm soát bệnh tật thành phố' required>
        <h3>Chọn vị trí đưa vào danh sách</h3>{checks}
        <label>Ghi chú</label><textarea name='notes'></textarea><br>
        <button>Tạo hồ sơ</button></form></div>""",
    )


@app.post("/submissions/new")
def submission_create_khnv(
    request: Request,
    subject: Annotated[str, Form()],
    reference_number: Annotated[str, Form()] = "",
    sent_date: Annotated[str, Form()] = "",
    notes: Annotated[str, Form()] = "",
    position_ids: Annotated[list[int] | None, Form()] = None,
):
    require_login(request)
    position_ids = position_ids or []
    with db() as con:
        if position_ids:
            placeholders = ",".join("?" for _ in position_ids)
            eligible = con.execute(
                f"SELECT id FROM positions WHERE id IN ({placeholders}) "
                "AND workflow_status IN ('Lãnh đạo CDC đã duyệt','Sở Y tế yêu cầu bổ sung')",
                position_ids,
            ).fetchall()
            if {row["id"] for row in eligible} != set(position_ids):
                return page(
                    request,
                    "Lỗi",
                    "<div class='card danger'>Có vị trí chưa được Lãnh đạo CDC duyệt.</div>",
                )
        status = "Đã gửi Sở Y tế" if sent_date else "Dự thảo nội bộ"
        cursor = con.execute(
            "INSERT INTO submissions(reference_number,subject,sent_date,status,notes,lead_unit) "
            "VALUES(?,?,?,?,?,?)",
            (reference_number, subject, sent_date, status, notes, LEAD_UNIT),
        )
        submission_id = cursor.lastrowid
        for position_id in position_ids:
            con.execute(
                "INSERT OR IGNORE INTO submission_items(submission_id,position_id) VALUES(?,?)",
                (submission_id, position_id),
            )
            con.execute(
                "UPDATE positions SET workflow_status=? WHERE id=?",
                ("Đã gửi Sở Y tế" if sent_date else "Lãnh đạo CDC đã duyệt", position_id),
            )
    return RedirectResponse("/submissions", 303)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app_khnv:app", host="127.0.0.1", port=8000, reload=True)
