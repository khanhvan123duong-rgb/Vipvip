================================================================
  BOT SPAM OTP VIP - VĂN KHÁNH & MINH THƯ - PHIÊN BẢN 2.0
================================================================

CÁC TÍNH NĂNG MỚI:
  ✅ Gửi video MP4 ngẫu nhiên 100% kèm kết quả /sms
  ✅ Chống ngủ đông Render.com (4 worker ping mỗi 2.5 phút)
  ✅ Tự động lưu dữ liệu mỗi 5 phút + lưu ngay sau mỗi thao tác
  ✅ Admin bật/tắt bot: /bot off [lý do] | /bot on
  ✅ Lệnh tắt nhanh: gõ "no mandatory" (chỉ admin)
  ✅ Cảnh báo đỏ khi bot tắt và user cố dùng
  ✅ Thông báo broadcast tới tất cả user khi bật/tắt bot

================================================================
CÁCH DEPLOY LÊN RENDER.COM:
================================================================

1. Đăng nhập GitHub → tạo repository mới (private).
2. Upload TẤT CẢ các file trong thư mục này vào repository:
     - bot.py
     - tool.py
     - requirements.txt
     - runtime.txt
     - Procfile
     - render.yaml
     - *.mp4  (tất cả file video)

3. Đăng nhập Render.com → New → Web Service
4. Chọn repository GitHub vừa tạo
5. Render sẽ tự đọc render.yaml và deploy

HOẶC dùng lệnh Git:
  git init
  git add .
  git commit -m "Bot v2.0"
  git remote add origin https://github.com/USERNAME/REPO.git
  git push -u origin main

================================================================
LỆNH ADMIN:
================================================================

  /admin              — Xem bảng lệnh và trạng thái
  /bot off [lý do]    — Tắt bot, thông báo tất cả user
  /bot on             — Bật bot, thông báo tất cả user
  no mandatory        — Tắt nhanh (gõ text, chỉ admin)
  /addvip [ID] [val] [unit]  — Thêm VIP
  /delvip [ID]        — Xóa VIP
  /banuser [ID]       — Cấm user
  /unban [ID]         — Bỏ cấm
  /listuser           — Danh sách user
  /broadcast [text]   — Broadcast tới tất cả

================================================================
LƯU Ý QUAN TRỌNG:
================================================================

  • File *.mp4 phải đặt CÙNG THƯ MỤC với bot.py
  • bot_data.json tự tạo khi chạy lần đầu
  • Dữ liệu tự lưu mỗi 5 phút và ngay sau mỗi thao tác
  • Khi restart, data được load lại từ bot_data.json
  • Server URL trong bot.py: https://vkhanhxhthuminhthu.onrender.com

================================================================
HỖ TRỢ: @vkhanh3010
================================================================
