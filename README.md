# GPHN CDC Hải Phòng — phiên bản 0.2.1

Ứng dụng thử nghiệm nội bộ bằng **FastAPI + SQLite**, giao diện tiếng Việt, phục vụ CDC Hải Phòng quản lý giấy phép của nhân sự thuộc đơn vị và lập hồ sơ đăng ký hành nghề với Sở Y tế.

## Đơn vị chủ trì

**Phòng Kế hoạch - Nghiệp vụ (KHNV)** là đầu mối chủ trì:

- tiếp nhận thông tin từ các khoa/phòng;
- rà soát giấy phép, phạm vi hành nghề, vị trí và lịch hành nghề;
- phối hợp Phòng Tổ chức - Hành chính xác nhận thông tin nhân sự khi cần;
- hoàn thiện danh sách và công văn trình Lãnh đạo CDC;
- gửi hồ sơ đăng ký hành nghề đến Sở Y tế;
- theo dõi yêu cầu bổ sung và kết quả Sở Y tế ghi nhận.

Luồng nội bộ dự kiến:

```text
Khoa/phòng đề nghị
→ KHNV tiếp nhận
→ KHNV rà soát GPHN và vị trí
→ TCHC phối hợp xác nhận nhân sự
→ KHNV hoàn thiện hồ sơ
→ Lãnh đạo CDC duyệt
→ Gửi Sở Y tế
→ Theo dõi phản hồi
```

## Phạm vi nghiệp vụ

CDC thực hiện:

- quản lý hồ sơ người hành nghề thuộc CDC;
- lưu, đối chiếu và theo dõi hiệu lực chứng chỉ/giấy phép đã được cơ quan có thẩm quyền cấp;
- quản lý vị trí công tác hành nghề, khoa/phòng, địa điểm, cơ sở chính/ngoài giờ và lịch làm việc;
- kiểm tra trùng lịch, giấy phép hợp lệ và thông tin cần thiết trước khi đăng ký;
- lập công văn/danh sách gửi Sở Y tế;
- theo dõi ngày gửi, tiếp nhận, yêu cầu bổ sung và kết quả Sở Y tế ghi nhận;
- quản lý cảnh báo và lịch sử trạng thái hồ sơ.

CDC **không** cấp mới, cấp lại, gia hạn, điều chỉnh, đình chỉ hoặc thu hồi giấy phép; không tiếp nhận hồ sơ của các cơ sở khác trong toàn thành phố.

## Chức năng đã có

- Hồ sơ người hành nghề và dữ liệu nhân sự CDC.
- Nhiều giấy phép/chứng chỉ theo lịch sử và trạng thái đối chiếu bản gốc.
- Vị trí hành nghề, cơ sở chính, khoa/phòng, thời gian hiệu lực và lịch tuần.
- Kiểm tra sơ bộ trùng lịch và giấy phép hợp lệ.
- Luồng nội bộ do KHNV chủ trì, có bước TCHC phối hợp.
- Cập nhật trạng thái từng vị trí hành nghề.
- Chỉ đưa vị trí đã được Lãnh đạo CDC duyệt vào hồ sơ gửi Sở.
- Gom nhiều vị trí vào một công văn/đợt đăng ký gửi Sở Y tế.
- Theo dõi phản hồi của Sở và cập nhật trạng thái từng vị trí.

## Chạy trên Windows

1. Tạo môi trường ảo và cài thư viện:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

2. Chạy ứng dụng:

```powershell
run.bat
```

Tệp `run.bat` chạy điểm vào `app_khnv.py`, là phiên bản đã hiệu chỉnh đúng vai trò KHNV chủ trì.

3. Truy cập `http://127.0.0.1:8000`.

Tài khoản dữ liệu mẫu:

```text
Tài khoản: admin
Mật khẩu: Admin@123
```

> Đây chỉ là thông tin đăng nhập dữ liệu mẫu chạy cục bộ. Phải đổi mật khẩu, thiết lập `SESSION_SECRET`, phân quyền và cấu hình bảo mật trước khi sử dụng dữ liệu thật hoặc triển khai trên mạng.

Máy cần Python 3.11 hoặc 3.12.

## Dữ liệu

- SQLite cục bộ: `qlhn.db` — không đưa vào Git.
- Không đưa dữ liệu nhân sự, số định danh hoặc bản scan giấy phép thật lên GitHub.
- Có thể chuyển PostgreSQL trong giai đoạn triển khai chính thức.

## Nội dung cần tiếp tục rà soát

- danh mục vị trí chuẩn theo từng khoa/phòng và chức danh;
- biểu mẫu và cấu trúc danh sách đăng ký gửi Sở;
- quy tắc thay đổi vị trí, thời gian, cơ sở ngoài giờ và chấm dứt;
- mốc thời gian phải thông báo Sở khi có biến động;
- phân quyền người nhập tại khoa/phòng, KHNV, TCHC và Lãnh đạo CDC;
- chữ ký số, HPNET và nhập Excel hàng loạt.

Đây là bản thử nghiệm nghiệp vụ, chưa dùng cho dữ liệu thật trên Internet.
