# GPHN CDC Hải Phòng — phiên bản 0.2

Ứng dụng thử nghiệm nội bộ bằng **FastAPI + SQLite**, giao diện tiếng Việt, phục vụ CDC Hải Phòng quản lý giấy phép của nhân sự thuộc đơn vị và lập hồ sơ đăng ký hành nghề với Sở Y tế.

## Phạm vi nghiệp vụ

CDC thực hiện:

- quản lý hồ sơ người hành nghề thuộc CDC;
- lưu, đối chiếu và theo dõi hiệu lực chứng chỉ/giấy phép đã được cơ quan có thẩm quyền cấp;
- quản lý vị trí công tác hành nghề, khoa/phòng, địa điểm, cơ sở chính/ngoài giờ và lịch làm việc;
- kiểm tra trùng lịch, giấy phép hợp lệ và thông tin cần thiết trước khi đăng ký;
- xử lý luồng nội bộ: Khoa/phòng → TCHC → KHNV → Lãnh đạo CDC;
- lập công văn/danh sách gửi Sở Y tế;
- theo dõi ngày gửi, tiếp nhận, yêu cầu bổ sung và kết quả Sở Y tế ghi nhận;
- quản lý CME, cảnh báo và nhật ký thao tác.

CDC **không** cấp mới, cấp lại, gia hạn, điều chỉnh, đình chỉ hoặc thu hồi giấy phép; không tiếp nhận hồ sơ của các cơ sở khác trong toàn thành phố.

## Chức năng đã có

- Hồ sơ người hành nghề và dữ liệu nhân sự CDC.
- Nhiều giấy phép/chứng chỉ theo lịch sử, tệp scan và trạng thái đối chiếu bản gốc.
- Danh mục địa điểm thuộc CDC và cơ sở ngoài CDC chỉ dùng để khai báo/đối chiếu.
- Vị trí hành nghề, cơ sở chính, khoa/phòng, thời gian hiệu lực và lịch tuần.
- Kiểm tra trùng lịch, trùng cơ sở chính và giấy phép hợp lệ.
- Luồng nội bộ đăng ký hành nghề.
- Gom nhiều vị trí đã duyệt vào một đợt/công văn gửi Sở Y tế.
- Theo dõi phản hồi của Sở và cập nhật trạng thái từng vị trí.
- Theo dõi CME 120 giờ/05 năm, cảnh báo và xuất Excel.
- Nhật ký thao tác.

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

3. Truy cập `http://127.0.0.1:8000`.

Tài khoản dữ liệu mẫu:

```text
Tài khoản: admin
Mật khẩu: Admin@123
```

> Đây chỉ là thông tin đăng nhập dữ liệu mẫu chạy cục bộ. Phải đổi mật khẩu, thiết lập `SESSION_SECRET`, phân quyền và cấu hình bảo mật trước khi sử dụng dữ liệu thật hoặc triển khai trên mạng.

Máy cần Python 3.11 hoặc 3.12.

## Dữ liệu

- SQLite cục bộ: `gphn_manager.db` — không đưa vào Git.
- Tệp đính kèm: `app/uploads/` — không đưa dữ liệu thật vào Git.
- Có thể chuyển PostgreSQL bằng biến môi trường `DATABASE_URL`.

## Kiểm thử

```bash
pytest
```

## Nội dung còn để mở

- danh mục vị trí chuẩn theo từng khoa/phòng và chức danh;
- đơn vị chủ trì thực tế giữa TCHC và KHNV;
- biểu mẫu/công văn đăng ký gửi Sở;
- quy tắc thay đổi vị trí, thời gian, cơ sở ngoài giờ và chấm dứt;
- mốc thời gian phải thông báo Sở khi có biến động;
- chữ ký số, HPNET, nhập Excel hàng loạt và phân quyền nhiều cấp.

Đây là bản thử nghiệm nghiệp vụ, chưa dùng cho dữ liệu thật trên Internet.
