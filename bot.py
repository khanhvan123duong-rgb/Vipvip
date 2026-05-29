#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================================
# TELEGRAM BOT - SPAM OTP VIP - VAN KHANH & MINH THU
# Server: https://vkhanhxhthuminhthu.onrender.com
# Phiên bản: 2.0 - Có chống ngủ đông, lưu dữ liệu tự động,
#            quản lý bật/tắt bot và gửi video kèm kết quả.
# ============================================================

import os, json, time, hashlib, threading, logging, random, glob
import requests
from flask import Flask, render_template_string

# ============================================================
# CONFIG
# ============================================================
BOT_TOKEN  = "7698662964:AAHTjfzdksHrtJ6asdrBAc_5zPkWwwBYOCk"
ADMIN_IDS  = [8401914033]
SERVER_URL = "https://vkhanhxhthuminhthu.onrender.com"
SELF_URL   = "https://vkhanhxhthuminhthu.onrender.com"
BOT_URL    = f"https://api.telegram.org/bot{BOT_TOKEN}"
FOOTER     = "\n\n──────────────────────\n📞 Telegram Hỗ Trợ - Báo Lỗi @vkhanh3010"

# Giới hạn số lần spam
LIMIT_NORMAL = 5    # Không VIP: 1-5
LIMIT_VIP    = 30   # Có VIP:    1-30

# Thư mục chứa file MP4 (cùng thư mục với bot.py)
_BOT_DIR = os.path.dirname(os.path.abspath(__file__))

# Bảng giá VIP
VIP_PRICE_MSG = (
    "\n\n💎 <b>NÂNG CẤP VIP - SPAM KHÔNG GIỚI HẠN</b>\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "💰 <b>Bảng Giá VIP:</b>\n"
    "├ ⏰ 2 Ngày     →   <b>10.000đ</b>\n"
    "├ ⏰ 5 Ngày     →   <b>20.000đ</b>\n"
    "├ 📅 1 Tuần     →   <b>25.000đ</b>\n"
    "├ 🗓️ 1 Tháng    →   <b>35.000đ</b>\n"
    "└ ♾️ Trọn Đời   →   <b>60.000đ</b>\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "📲 Liên hệ mua VIP: @vkhanh3010"
)

# ============================================================
# IMPORT OTP FUNCTIONS FROM TOOL
# ============================================================
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tool as _tool
OTP_FUNCTIONS = _tool.OTP_FUNCTIONS

# ============================================================
# DATA STORAGE (in-memory + JSON file)
# ============================================================
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot_data.json")

def _load_data():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {
        "users": {},
        "admins": list(ADMIN_IDS),
        "seen_users": [],
        "bot_status": {"enabled": True, "off_message": ""},
        "video_cache": {}
    }

_data = _load_data()

# Đảm bảo bot_status tồn tại khi load từ file cũ
if "bot_status" not in _data:
    _data["bot_status"] = {"enabled": True, "off_message": ""}

def _save():
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(_data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

def _get_admins():
    return set(_data.get("admins", list(ADMIN_IDS)))

def _get_seen():
    return set(str(x) for x in _data.get("seen_users", []))

# ============================================================
# BOT STATUS (Bật / Tắt bot)
# ============================================================
def is_bot_enabled() -> bool:
    """Kiểm tra bot có đang bật không."""
    return _data.get("bot_status", {}).get("enabled", True)

def get_bot_off_message() -> str:
    """Lấy lý do tắt bot (nếu có)."""
    return _data.get("bot_status", {}).get("off_message", "")

def set_bot_status(enabled: bool, off_message: str = ""):
    """Đặt trạng thái bot và lưu ngay."""
    _data.setdefault("bot_status", {})
    _data["bot_status"]["enabled"]     = enabled
    _data["bot_status"]["off_message"] = off_message
    _save()

# ============================================================
# VIDEO CACHE (lưu file_id Telegram để tái sử dụng)
# ============================================================
_VIDEO_CACHE: dict = {}

def _load_video_cache():
    global _VIDEO_CACHE
    _VIDEO_CACHE = _data.get("video_cache", {})

def _save_video_cache():
    _data["video_cache"] = _VIDEO_CACHE
    _save()

_load_video_cache()

def get_random_video_path() -> str:
    """Quét thư mục cùng bot.py để lấy file MP4 ngẫu nhiên."""
    mp4_files = glob.glob(os.path.join(_BOT_DIR, "*.mp4"))
    if not mp4_files:
        return ""
    return random.choice(mp4_files)

# ============================================================
# HWID GENERATION (SHA256 of Telegram user_id)
# ============================================================
def make_hwid(user_id: int) -> str:
    return hashlib.sha256(str(user_id).encode()).hexdigest()[:20].upper()

# ============================================================
# SERVER API CALLS
# ============================================================
def api_verify(key: str, hwid: str) -> dict:
    try:
        r = requests.post(f"{SERVER_URL}/api/verify",
                          json={"key": key, "hwid": hwid}, timeout=15)
        return r.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}

def api_check_expiry(key: str, hwid: str) -> dict:
    try:
        r = requests.post(f"{SERVER_URL}/api/check_expiry",
                          json={"key": key, "hwid": hwid}, timeout=15)
        return r.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}

def api_getkey(hwid: str) -> dict:
    try:
        r = requests.get(f"{SERVER_URL}/api/getkey",
                         params={"hwid": hwid}, timeout=15)
        return r.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}

def api_check_device(hwid: str) -> dict:
    try:
        r = requests.post(f"{SERVER_URL}/api/check-device",
                          json={"device_id": hwid}, timeout=15)
        return r.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ============================================================
# USER HELPERS
# ============================================================
def get_user(user_id: int) -> dict:
    return _data.get("users", {}).get(str(user_id), {})

def _get_expiry_from_resp(resp: dict) -> float:
    raw = resp.get("expiry_timestamp")
    if raw is None:
        raw = resp.get("expiry")
    try:
        val = float(raw) if raw is not None else 0.0
        if val < 0:
            return 0.0
        return val
    except (TypeError, ValueError):
        return 0.0

def is_activated(user_id: int):
    u = get_user(user_id)
    uid = str(user_id)
    if not u or not u.get("activated"):
        return False, u
    if u.get("is_permanent"):
        return True, u
    expiry = u.get("expiry", 0)
    if expiry and expiry > 0 and time.time() < expiry:
        return True, u
    _deactivate_user(uid)
    return False, u

def is_vip(user_id: int) -> bool:
    u = get_user(user_id)
    if not u or not u.get("vip"):
        return False
    if u.get("vip_permanent"):
        return True
    vip_expiry = u.get("vip_expiry", 0)
    if vip_expiry and vip_expiry > 0 and time.time() < vip_expiry:
        return True
    return False

def is_banned(user_id: int) -> bool:
    u = get_user(user_id)
    return bool(u.get("banned", False))

def is_admin(user_id: int) -> bool:
    return user_id in _get_admins()

def get_sms_limit(user_id: int) -> int:
    if is_vip(user_id):
        return LIMIT_VIP
    return LIMIT_NORMAL

def _save_user_activation(uid: str, first_name: str, username: str,
                           key: str, expiry: float, is_perm: bool,
                           hwid: str, method: str):
    _data.setdefault("users", {}).setdefault(uid, {}).update({
        "first_name": first_name,
        "username": username,
        "activated": True,
        "key": key,
        "expiry": expiry,
        "is_permanent": is_perm,
        "server_verified": True,
        "activated_at": time.time(),
        "hwid": hwid,
        "activate_method": method,
    })
    _save()

def _deactivate_user(uid: str):
    if uid in _data.get("users", {}):
        _data["users"][uid]["activated"]       = False
        _data["users"][uid]["is_permanent"]    = False
        _data["users"][uid]["server_verified"] = False
        _save()

def format_expiry(user_id: int) -> str:
    u = get_user(user_id)
    if not u:
        return "N/A"
    if u.get("is_permanent"):
        return "♾️ Vĩnh viễn"
    expiry = u.get("expiry", 0)
    if not expiry or expiry <= 0:
        return "⚠️ Hết hạn"
    left = expiry - time.time()
    if left <= 0:
        return "⚠️ Hết hạn"
    d, rem = divmod(int(left), 86400)
    h, rem2 = divmod(rem, 3600)
    m = rem2 // 60
    parts = []
    if d: parts.append(f"{d} ngày")
    if h: parts.append(f"{h} giờ")
    if m: parts.append(f"{m} phút")
    return " ".join(parts) or "< 1 phút"

def format_activate_method(user_id: int) -> str:
    u = get_user(user_id)
    if not u:
        return "❓ Chưa kích hoạt"
    method = u.get("activate_method", "")
    key = u.get("key", "")
    if method == "key" or (key and key != "__da_duyet__"):
        key_disp = key if key else "N/A"
        return f"🔑 Key: <code>{key_disp}</code>"
    elif method == "hwid" or key == "__da_duyet__":
        return "📲 HWID được Admin duyệt"
    return "🔑 Key / HWID"

def format_vip_expiry(user_id: int) -> str:
    u = get_user(user_id)
    if not u or not u.get("vip"):
        return "❌ Không có VIP"
    if u.get("vip_permanent"):
        return "♾️ VIP Vĩnh Viễn"
    vip_expiry = u.get("vip_expiry", 0)
    if not vip_expiry or vip_expiry <= 0:
        return "❌ VIP hết hạn"
    left = vip_expiry - time.time()
    if left <= 0:
        return "⚠️ VIP hết hạn"
    d, rem = divmod(int(left), 86400)
    h, rem2 = divmod(rem, 3600)
    m = rem2 // 60
    parts = []
    if d: parts.append(f"{d} ngày")
    if h: parts.append(f"{h} giờ")
    if m: parts.append(f"{m} phút")
    return "💎 VIP còn: " + (" ".join(parts) or "< 1 phút")

def detect_carrier(phone: str) -> str:
    p = phone.lstrip('+').strip()
    if p.startswith('84'):
        p = '0' + p[2:]
    if len(p) < 10:
        return "Không xác định"
    pre3 = p[:3]
    viettel   = {'032','033','034','035','036','037','038','039','086','096','097','098'}
    mobifone  = {'070','076','077','078','079','089','090','093'}
    vinaphone = {'081','082','083','084','085','088','091','094'}
    vietnamob = {'052','056','058','092'}
    gmobile   = {'059','099'}
    if pre3 in viettel:   return "Viettel"
    if pre3 in mobifone:  return "Mobifone"
    if pre3 in vinaphone: return "Vinaphone"
    if pre3 in vietnamob: return "Vietnamobile"
    if pre3 in gmobile:   return "Gmobile"
    return "Không xác định"

def mask_phone(phone: str) -> str:
    p = phone.strip()
    if len(p) <= 6:
        return p
    return p[:4] + "****" + p[-2:]

# ============================================================
# TELEGRAM API HELPERS
# ============================================================
def _tg(method: str, **kwargs) -> dict:
    try:
        r = requests.post(f"{BOT_URL}/{method}", json=kwargs, timeout=30)
        return r.json()
    except Exception:
        return {}

def send(chat_id, text, reply_markup=None, parse_mode="HTML",
         disable_web_page_preview=True) -> dict:
    kw = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode,
          "disable_web_page_preview": disable_web_page_preview}
    if reply_markup:
        kw["reply_markup"] = reply_markup
    return _tg("sendMessage", **kw)

def edit_msg(chat_id, msg_id, text, reply_markup=None, parse_mode="HTML") -> dict:
    kw = {"chat_id": chat_id, "message_id": msg_id, "text": text,
          "parse_mode": parse_mode, "disable_web_page_preview": True}
    if reply_markup:
        kw["reply_markup"] = reply_markup
    return _tg("editMessageText", **kw)

def answer_cb(cb_id, text=None, alert=False) -> dict:
    kw = {"callback_query_id": cb_id}
    if text:
        kw["text"] = text
        kw["show_alert"] = alert
    return _tg("answerCallbackQuery", **kw)

def edit_caption(chat_id, msg_id, caption, parse_mode="HTML") -> dict:
    """Sửa caption của tin nhắn video/ảnh."""
    return _tg("editMessageCaption",
               chat_id=chat_id,
               message_id=msg_id,
               caption=caption,
               parse_mode=parse_mode)

def delete_msg(chat_id, msg_id) -> dict:
    """Xóa một tin nhắn."""
    return _tg("deleteMessage", chat_id=chat_id, message_id=msg_id)

def send_wait(chat_id) -> int:
    """Gửi tin nhắn 'Vui lòng chờ...' và trả về message_id để xóa sau."""
    resp = send(chat_id,
                "⏰ <b>Vui lòng chờ...</b>\n"
                "<i>Bot đang xử lý yêu cầu của bạn.</i>")
    return resp.get("result", {}).get("message_id")

def send_video(chat_id: int, caption: str = "") -> bool:
    """
    Gửi video MP4 ngẫu nhiên đến chat_id kèm caption (nội dung kết quả).
    - Lần đầu: upload file → Telegram trả về file_id → cache lại.
    - Lần sau: dùng file_id đã cache (nhanh hơn, tiết kiệm băng thông).
    Trả về True nếu gửi thành công, False nếu không có video hoặc lỗi.
    """
    global _VIDEO_CACHE
    video_path = get_random_video_path()
    if not video_path:
        logging.warning("[send_video] Không tìm thấy file MP4 nào trong thư mục bot!")
        return False

    filename  = os.path.basename(video_path)
    cached_id = _VIDEO_CACHE.get(filename, "")

    try:
        if cached_id:
            # Gửi bằng file_id đã cache
            r = requests.post(
                f"{BOT_URL}/sendVideo",
                json={
                    "chat_id": chat_id,
                    "video": cached_id,
                    "caption": caption,
                    "parse_mode": "HTML",
                    "supports_streaming": True,
                },
                timeout=60,
            )
            resp = r.json()
            if resp.get("ok"):
                logging.info(f"[send_video] Gửi video bằng cache OK: {filename}")
                return True
            # file_id hết hạn hoặc lỗi → xóa cache, upload lại
            logging.warning(f"[send_video] Cache hết hạn, upload lại: {resp}")
            _VIDEO_CACHE.pop(filename, None)
            _save_video_cache()

        # Upload file lần đầu
        logging.info(f"[send_video] Upload video mới: {filename}")
        with open(video_path, "rb") as vf:
            r = requests.post(
                f"{BOT_URL}/sendVideo",
                data={
                    "chat_id": str(chat_id),
                    "caption": caption,
                    "parse_mode": "HTML",
                    "supports_streaming": "true",
                },
                files={"video": (filename, vf, "video/mp4")},
                timeout=180,
            )
        resp = r.json()
        if resp.get("ok"):
            vid_obj = resp.get("result", {}).get("video", {})
            fid = vid_obj.get("file_id", "")
            if fid:
                _VIDEO_CACHE[filename] = fid
                _save_video_cache()
                logging.info(f"[send_video] Upload thành công, đã cache file_id.")
            return True
        else:
            logging.error(f"[send_video] Lỗi Telegram: {resp}")
    except Exception as e:
        logging.error(f"[send_video] Ngoại lệ: {e}", exc_info=True)
    return False

def notify_admins(text: str, exclude_id: int = None):
    for aid in _get_admins():
        if aid != exclude_id:
            try:
                send(int(aid), text)
            except Exception:
                pass

def broadcast_all(text: str, skip_admins: bool = False) -> int:
    """Gửi thông báo tới tất cả người dùng đã từng dùng bot."""
    users = _data.get("users", {})
    ok = 0
    for uid_s in list(users.keys()):
        try:
            if skip_admins and int(uid_s) in _get_admins():
                continue
            send(int(uid_s), text)
            ok += 1
            time.sleep(0.05)  # tránh flood
        except Exception:
            pass
    return ok

# ============================================================
# KEYBOARDS
# ============================================================
def kb_activation():
    return {"inline_keyboard": [
        [{"text": "🔑 Nhập Key Kích Hoạt",             "callback_data": "act_key"}],
        [{"text": "🔗 Lấy Link Key Miễn Phí (2/ngày)", "callback_data": "act_link"}],
    ]}

def kb_main():
    return {"inline_keyboard": [
        [{"text": "📱 Hướng dẫn /sms",         "callback_data": "help_sms"}],
        [{"text": "👤 Thông tin tài khoản",     "callback_data": "my_info"}],
        [{"text": "🔄 Kiểm tra hạn dùng",      "callback_data": "check_expiry"}],
    ]}

# ============================================================
# STATE MACHINE (per-user multi-step input)
# ============================================================
_user_state: dict = {}

# ============================================================
# RUNNING SPAM TRACKER (dùng cho /stop)
# ============================================================
_running_spam: dict = {}
# Cấu trúc: user_id -> {
#   "event": threading.Event,
#   "phone_masked": str,
#   "carrier": str,
#   "user_disp": str,
#   "vip_user": bool,
#   "count": int,
#   "stop_handled": bool   # True khi cmd_stop đã gửi kết quả
# }

def set_state(user_id: int, state: str):
    _user_state[user_id] = state

def get_state(user_id: int) -> str:
    return _user_state.get(user_id, "")

def clear_state(user_id: int):
    _user_state.pop(user_id, None)

# ============================================================
# BOT MAINTENANCE MESSAGE (gửi khi bot tắt)
# ============================================================
def send_maintenance_msg(chat_id: int):
    """Gửi cảnh báo đỏ khi bot đang tắt."""
    off_msg = get_bot_off_message()
    extra = f"\n\n📋 <i>{off_msg}</i>" if off_msg else ""
    txt = (
        "🔴🔴🔴 <b>BOT ĐANG BẢO TRÌ</b> 🔴🔴🔴\n\n"
        "⚠️ <b>Bot hiện đang tạm ngưng hoạt động.</b>\n"
        "Vui lòng liên hệ Admin để biết thêm thông tin."
        f"{extra}"
        f"{FOOTER}"
    )
    send(chat_id, txt)

# ============================================================
# SPAM RUNNER
# ============================================================
def _safe_call(fn, sdt: str) -> bool:
    try:
        fn(sdt)
        return True
    except Exception:
        return False

def run_spam(sdt: str, rounds: int):
    """Run all OTP_FUNCTIONS <rounds> times. Returns (ok, fail)."""
    total_ok = total_fail = 0
    for _ in range(rounds):
        results = []
        lock = threading.Lock()
        def _worker(fn, phone, res, lk):
            ok = _safe_call(fn, phone)
            with lk:
                res.append(ok)
        threads = [threading.Thread(target=_worker, args=(fn, sdt, results, lock), daemon=True)
                   for fn in OTP_FUNCTIONS]
        for t in threads: t.start()
        for t in threads: t.join()
        ok = sum(1 for r in results if r)
        total_ok += ok
        total_fail += len(results) - ok
    return total_ok, total_fail

# ============================================================
# SERVER VERIFICATION HELPER
# ============================================================
def verify_with_server(user_id: int, chat_id: int) -> bool:
    uid = str(user_id)
    u = get_user(user_id)
    hwid = make_hwid(user_id)
    key_stored = u.get("key", "")
    use_key = key_stored and key_stored != "__da_duyet__"

    if use_key:
        resp = api_check_expiry(key_stored, hwid)
        st = resp.get("status", "")
        if st == "valid":
            new_exp = _get_expiry_from_resp(resp)
            is_perm = bool(resp.get("is_permanent", False))
            _data["users"][uid]["expiry"]       = new_exp
            _data["users"][uid]["is_permanent"] = is_perm
            _save()
            return True
        elif st == "expired":
            _deactivate_user(uid)
            send(chat_id,
                 "❌ <b>Key của bạn đã hết hạn!</b>\n\n"
                 f"🗝️ Key: <code>{key_stored}</code>\n"
                 "Vui lòng kích hoạt lại bằng key mới hoặc liên hệ Admin."
                 f"{FOOTER}", reply_markup=kb_activation())
            return False
        elif st == "invalid":
            _deactivate_user(uid)
            send(chat_id,
                 "❌ <b>Key không còn tồn tại trên server!</b>\n\n"
                 f"🗝️ Key: <code>{key_stored}</code>\n"
                 "Key có thể đã bị Admin xóa. Vui lòng kích hoạt lại."
                 f"{FOOTER}", reply_markup=kb_activation())
            return False
        elif st in ("not_activated", "device_not_found"):
            resp2 = api_verify(key_stored, hwid)
            st2 = resp2.get("status", "")
            if st2 == "success":
                new_exp = _get_expiry_from_resp(resp2)
                is_perm = bool(resp2.get("is_permanent", False))
                _data["users"][uid]["expiry"]       = new_exp
                _data["users"][uid]["is_permanent"] = is_perm
                _save()
                return True
            elif st2 == "expired":
                _deactivate_user(uid)
                send(chat_id,
                     "❌ <b>Key của bạn đã hết hạn!</b>\n\n"
                     "Vui lòng kích hoạt lại bằng key mới hoặc liên hệ Admin."
                     f"{FOOTER}", reply_markup=kb_activation())
                return False
            elif st2 == "device_limit":
                send(chat_id,
                     "❌ <b>Key đã đạt giới hạn thiết bị!</b>\n\n"
                     f"Key này chỉ hỗ trợ tối đa <b>{resp2.get('max_devices','?')}</b> thiết bị.\n"
                     "Liên hệ Admin để được hỗ trợ."
                     f"{FOOTER}")
                return False
            else:
                _deactivate_user(uid)
                send(chat_id,
                     "❌ <b>Không thể xác minh key với server!</b>\n\n"
                     "Vui lòng kích hoạt lại hoặc liên hệ Admin."
                     f"{FOOTER}", reply_markup=kb_activation())
                return False
        elif st == "error":
            logging.warning(f"[verify_with_server] Server error for user {user_id}: {resp.get('message')}")
            return True
        else:
            _deactivate_user(uid)
            send(chat_id,
                 "❌ Tài khoản không còn hợp lệ. Vui lòng kích hoạt lại."
                 f"{FOOTER}", reply_markup=kb_activation())
            return False
    else:
        resp = api_check_device(hwid)
        st = resp.get("status", "")
        if st == "approved":
            new_exp = _get_expiry_from_resp(resp)
            is_perm = bool(resp.get("is_permanent", False))
            _data["users"][uid]["expiry"]       = new_exp
            _data["users"][uid]["is_permanent"] = is_perm
            _save()
            return True
        elif st == "expired":
            _deactivate_user(uid)
            send(chat_id,
                 "❌ <b>Tài khoản của bạn đã hết hạn!</b>\n\n"
                 "Vui lòng liên hệ Admin để gia hạn hoặc kích hoạt lại bằng key mới."
                 f"{FOOTER}", reply_markup=kb_activation())
            return False
        elif st in ("not_found",):
            _deactivate_user(uid)
            send(chat_id,
                 "❌ <b>Tài khoản không còn hợp lệ!</b>\n\n"
                 "Vui lòng kích hoạt lại bằng key hoặc liên hệ Admin."
                 f"{FOOTER}", reply_markup=kb_activation())
            return False
        elif st == "error":
            logging.warning(f"[verify_with_server] Server error HWID for user {user_id}: {resp.get('message')}")
            return True
        else:
            _deactivate_user(uid)
            send(chat_id,
                 "❌ Tài khoản không hợp lệ. Vui lòng kích hoạt lại."
                 f"{FOOTER}", reply_markup=kb_activation())
            return False

# ============================================================
# COMMAND HANDLERS
# ============================================================

def cmd_start(msg: dict):
    user_id    = msg["from"]["id"]
    uid        = str(user_id)
    first_name = msg["from"].get("first_name", "Bạn")
    username   = msg["from"].get("username", "")
    chat_id    = msg["chat"]["id"]

    # Bot bảo trì - admin vẫn dùng được
    if not is_bot_enabled() and not is_admin(user_id):
        return send_maintenance_msg(chat_id)

    if is_banned(user_id):
        return send(chat_id, "🚫 Tài khoản của bạn đã bị cấm sử dụng bot." + FOOTER)

    _data.setdefault("users", {}).setdefault(uid, {
        "first_name": first_name, "username": username,
        "first_seen": time.time(), "activated": False
    })
    _data["users"][uid]["first_name"] = first_name
    _data["users"][uid]["username"]   = username
    _save()

    seen = _get_seen()
    if uid not in seen:
        _data.setdefault("seen_users", []).append(uid)
        _save()
        hwid = make_hwid(user_id)
        notify_admins(
            f"🆕 <b>Người dùng mới!</b>\n"
            f"👤 Tên: {first_name}\n"
            f"🆔 ID: <code>{user_id}</code>\n"
            f"📛 Username: @{username or 'N/A'}\n"
            f"🔑 HWID: <code>{hwid}</code>",
            exclude_id=user_id if user_id in _get_admins() else None
        )

    act, uinfo = is_activated(user_id)
    vip_status = is_vip(user_id)
    limit = get_sms_limit(user_id)

    if not act:
        txt = (
            f"👋 Xin chào <b>{first_name}</b>!\n\n"
            f"🔒 Bạn cần <b>kích hoạt tài khoản</b> trước khi sử dụng bot.\n\n"
            f"Vui lòng chọn phương thức kích hoạt bên dưới:"
            f"{FOOTER}"
        )
        send(chat_id, txt, reply_markup=kb_activation())
    else:
        vip_line = format_vip_expiry(user_id) if vip_status else "❌ Chưa có VIP"
        txt = (
            f"✅ Xin chào <b>{first_name}</b>! Tài khoản đã kích hoạt.\n\n"
            f"🔓 Kích hoạt bằng: {format_activate_method(user_id)}\n"
            f"⏳ Hạn dùng: {format_expiry(user_id)}\n"
            f"💎 VIP: {vip_line}\n"
            f"📊 Giới hạn SMS: 1–{limit} lần\n\n"
            f"▸ /sms [SĐT] [Số lần] — Spam OTP\n"
            f"▸ /help — Hướng dẫn\n"
            f"▸ /info — Thông tin tài khoản"
            f"{FOOTER}"
        )
        send(chat_id, txt, reply_markup=kb_main())


def cmd_help(msg: dict):
    user_id = msg["from"]["id"]
    chat_id = msg["chat"]["id"]

    if not is_bot_enabled() and not is_admin(user_id):
        return send_maintenance_msg(chat_id)

    if is_banned(user_id):
        return send(chat_id, "🚫 Tài khoản của bạn đã bị cấm sử dụng bot." + FOOTER)

    act, _ = is_activated(user_id)
    if not act:
        return send(chat_id,
            "🔒 Bạn chưa kích hoạt! Dùng /start để kích hoạt." + FOOTER,
            reply_markup=kb_activation())

    vip_status = is_vip(user_id)
    limit = get_sms_limit(user_id)

    txt = (
        "📖 <b>HƯỚNG DẪN SỬ DỤNG BOT</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📱 <b>Lệnh chính:</b>\n"
        "▸ /sms [SĐT] [Số lần] — Gửi OTP spam\n"
        "  Ví dụ: <code>/sms 0912345678 3</code>\n\n"
        "▸ /info — Thông tin tài khoản\n"
        "▸ /help — Hướng dẫn\n"
        "▸ /start — Menu chính\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 <b>Giới hạn:</b>\n"
        f"• Không VIP: tối đa <b>{LIMIT_NORMAL} lần</b> mỗi lần gửi\n"
        f"• Có VIP 💎: tối đa <b>{LIMIT_VIP} lần</b> mỗi lần gửi\n"
        f"• Bạn hiện tại: 1–<b>{limit}</b> lần\n\n"
        "⏳ <b>Cooldown:</b>\n"
        f"• Không VIP: chờ 60 giây sau mỗi lần dùng\n"
        f"• Có VIP 💎: không bị delay"
        f"{FOOTER}"
    )
    send(chat_id, txt)


def cmd_info(msg: dict):
    user_id = msg["from"]["id"]
    chat_id = msg["chat"]["id"]

    if not is_bot_enabled() and not is_admin(user_id):
        return send_maintenance_msg(chat_id)

    if is_banned(user_id):
        return send(chat_id, "🚫 Tài khoản của bạn đã bị cấm sử dụng bot." + FOOTER)

    act, uinfo = is_activated(user_id)
    if not act:
        return send(chat_id,
            "🔒 Chưa kích hoạt! Dùng /start để kích hoạt." + FOOTER,
            reply_markup=kb_activation())

    vip_status = is_vip(user_id)
    limit = get_sms_limit(user_id)
    vip_line = format_vip_expiry(user_id) if vip_status else "❌ Chưa có VIP"

    txt = (
        "👤 <b>THÔNG TIN TÀI KHOẢN</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 Tên: {uinfo.get('first_name','N/A')}\n"
        f"🆔 Telegram ID: <code>{user_id}</code>\n"
        f"🔓 Kích hoạt bằng: {format_activate_method(user_id)}\n"
        f"⏳ Hạn sử dụng: {format_expiry(user_id)}\n"
        f"💎 VIP: {vip_line}\n"
        f"📊 Giới hạn SMS: 1–{limit} lần\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━"
        f"{FOOTER}"
    )
    send(chat_id, txt)


def cmd_sms(msg: dict):
    user_id    = msg["from"]["id"]
    uid        = str(user_id)
    chat_id    = msg["chat"]["id"]
    first_name = msg["from"].get("first_name", "User")
    username   = msg["from"].get("username", "")

    # Bot bảo trì
    if not is_bot_enabled() and not is_admin(user_id):
        return send_maintenance_msg(chat_id)

    if is_banned(user_id):
        return send(chat_id, "🚫 Tài khoản của bạn đã bị cấm sử dụng bot." + FOOTER)

    act, uinfo = is_activated(user_id)
    if not act:
        return send(chat_id,
            "🔒 Bạn chưa kích hoạt! Dùng /start để kích hoạt." + FOOTER,
            reply_markup=kb_activation())

    parts = msg.get("text", "").split()
    if len(parts) < 3:
        return send(chat_id,
            "❌ <b>Sai cú pháp!</b>\n"
            "Dùng: <code>/sms [SĐT] [Số lần]</code>\n"
            "Ví dụ: <code>/sms 0912345678 3</code>"
            f"{FOOTER}")

    phone = parts[1].strip()
    vip_user = is_vip(user_id)
    limit = get_sms_limit(user_id)

    try:
        count = int(parts[2])
        if not (1 <= count <= limit):
            raise ValueError()
    except ValueError:
        if vip_user:
            return send(chat_id,
                f"❌ Số lần không hợp lệ.\n"
                f"💎 VIP: nhập từ 1 đến {limit}."
                f"{FOOTER}")
        else:
            return send(chat_id,
                f"❌ <b>Bạn chỉ được spam tối đa {LIMIT_NORMAL} lần!</b>\n\n"
                f"Tài khoản thường bị giới hạn <b>{LIMIT_NORMAL} lần</b> mỗi lần sử dụng.\n"
                f"Nâng cấp VIP để spam không giới hạn (tối đa {LIMIT_VIP} lần)."
                f"{VIP_PRICE_MSG}"
                f"{FOOTER}")

    # Kiểm tra cooldown 60 giây (chỉ không VIP)
    if not vip_user:
        last_sms = uinfo.get("last_sms_time", 0)
        if last_sms and last_sms > 0:
            elapsed = time.time() - last_sms
            if elapsed < 60:
                remaining = int(60 - elapsed)
                return send(chat_id,
                    f"⏳ <b>Bạn cần chờ thêm {remaining} giây!</b>\n\n"
                    f"Tài khoản thường phải chờ <b>60 giây</b> giữa mỗi lần sử dụng.\n"
                    f"Nâng cấp VIP để spam liên tục không giới hạn!"
                    f"{VIP_PRICE_MSG}"
                    f"{FOOTER}")

    # Xác minh với server trước khi chạy spam
    if not verify_with_server(user_id, chat_id):
        return

    _data.setdefault("users", {}).setdefault(uid, {})["last_sms_time"] = time.time()
    _save()

    hwid        = make_hwid(user_id)
    carrier     = detect_carrier(phone)
    user_disp   = f"{first_name} (@{username})" if username else first_name
    act_method  = format_activate_method(user_id)
    phone_masked = mask_phone(phone)

    notify_admins(
        f"📨 <b>YÊU CẦU /sms MỚI</b>\n"
        f"👤 {user_disp} [<code>{user_id}</code>]\n"
        f"📱 SĐT: <code>{phone}</code>\n"
        f"🔢 Số lần: {count}\n"
        f"💎 VIP: {'✅' if vip_user else '❌'}\n"
        f"🔑 HWID: <code>{hwid}</code>"
    )

    # Caption video gửi NGAY LẬP TỨC khi bắt đầu
    init_caption = (
        f"🔥 <b>ĐANG TẤN CÔNG...</b>\n\n"
        f"📞 Nạn Nhân: <b>{phone_masked}</b>\n"
        f"👤 Người Dùng : <b>{user_disp}</b> 👇\n"
        f"💎 Gói: <b>{'✨ VIP' if vip_user else '👤 Thường'}</b>\n"
        f"📡 Nhà Mạng: <b>{carrier}</b>\n"
        f"🔄 COUNT: <b>{count}</b>\n"
        f"⚡ Trạng Thái: 🔄 <i>Đang gửi...</i>\n"
        f"/stop để dừng"
        f"{FOOTER}"
    )

    # Dừng spam đang chạy (nếu có) trước khi bắt đầu mới
    if user_id in _running_spam:
        _running_spam[user_id]["event"].set()

    stop_event = threading.Event()
    _running_spam[user_id] = {
        "event":        stop_event,
        "phone_masked": phone_masked,
        "carrier":      carrier,
        "user_disp":    user_disp,
        "vip_user":     vip_user,
        "count":        count,
        "stop_handled": False,
    }

    # Gửi VIDEO NGAY với caption "ĐANG TẤN CÔNG"
    video_msg_id = None
    sent_video = send_video(chat_id, caption=init_caption)
    if not sent_video:
        # Fallback: gửi text nếu không có file MP4
        resp = send(chat_id, init_caption)
        video_msg_id = resp.get("result", {}).get("message_id")

    threading.Thread(
        target=_do_spam,
        args=(chat_id, video_msg_id, user_id, phone, phone_masked, count,
              carrier, user_disp, vip_user, stop_event),
        daemon=True
    ).start()


def _do_spam(chat_id, video_msg_id, user_id, phone, phone_masked, count,
             carrier, user_disp, vip_user=False, stop_event=None):
    """
    Chạy spam OTP. Nếu stop_event được set → dừng giữa chừng.
    Video đã được gửi TRƯỚC khi hàm này chạy — chỉ cập nhật caption,
    KHÔNG gửi thêm video nào.
    """
    if stop_event is None:
        stop_event = threading.Event()

    total_ok = total_fail = 0

    for round_i in range(count):
        if stop_event.is_set():
            break
        # Chạy tất cả OTP_FUNCTIONS song song cho 1 vòng
        results = []
        lock = threading.Lock()
        def _worker(fn, phone_n, res, lk):
            ok = _safe_call(fn, phone_n)
            with lk:
                res.append(ok)
        threads = [
            threading.Thread(target=_worker, args=(fn, phone, results, lock), daemon=True)
            for fn in OTP_FUNCTIONS
        ]
        for t in threads: t.start()
        for t in threads: t.join()
        ok = sum(1 for r in results if r)
        total_ok  += ok
        total_fail += len(results) - ok

    # Lấy cờ stop_handled TRƯỚC khi xóa khỏi dict
    ctx = _running_spam.get(user_id, {})
    stop_handled = ctx.get("stop_handled", False)

    # Xóa khỏi danh sách đang chạy
    _running_spam.pop(user_id, None)

    was_stopped = stop_event.is_set()

    if was_stopped:
        # Bị dừng bởi /stop — cmd_stop đã gửi kết quả rồi (stop_handled=True)
        # Chỉ cần cập nhật caption video (nếu có), KHÔNG gửi thêm tin nhắn text
        if not stop_handled:
            # Trường hợp hiếm: /stop gọi sau khi _do_spam vừa xong — gửi bình thường
            stop_time = time.strftime("%H giờ %M phút")
            stop_txt = (
                f"⛔ <b>ĐÃ DỪNG TẤN CÔNG!</b>\n\n"
                f"📞 Nạn Nhân: <b>{phone_masked}</b>\n"
                f"👤 Người Dùng : <b>{user_disp}</b>\n"
                f"💎 Gói: <b>{'✨ VIP' if vip_user else '👤 Thường'}</b>\n"
                f"📡 Nhà Mạng: <b>{carrier}</b>\n"
                f"📊 Kết Quả tạm: ✅ <b>{total_ok}</b> OK"
                f" / ❌ <b>{total_fail}</b> FAIL\n"
                f"⚡ Trạng Thái: ⛔ <b>Đã dừng theo yêu cầu</b>"
                f"{FOOTER}"
            )
            if video_msg_id:
                edit_msg(chat_id, video_msg_id, stop_txt)
            else:
                send(chat_id, stop_txt)
    else:
        # Hoàn thành tự nhiên — cập nhật caption video đã gửi, KHÔNG gửi thêm video
        done_caption = (
            f"✅ <b>TẤN CÔNG HOÀN TẤT!</b>\n\n"
            f"📞 Nạn Nhân: <b>{phone_masked}</b>\n"
            f"👤 Người Dùng : <b>{user_disp}</b>\n"
            f"💎 Gói: <b>{'✨ VIP' if vip_user else '👤 Thường'}</b>\n"
            f"📡 Nhà Mạng: <b>{carrier}</b>\n"
            f"🔄 COUNT: <b>{count}</b>\n"
            f"⚡ Trạng Thái: ✅ <b>Hoàn thành</b>\n"
            f"📊 Kết Quả: ✅ <b>{total_ok}</b> thành công"
            f" / ❌ <b>{total_fail}</b> thất bại"
            f"{FOOTER}"
        )
        # Ưu tiên editMessageCaption (nếu video đã gửi thành công)
        # video_msg_id = None khi video gửi OK (không cần edit gì — caption tự cập nhật
        # qua editMessageCaption nếu chúng ta lưu video_msg_id)
        # Nếu là fallback text: edit text message
        if video_msg_id:
            edit_msg(chat_id, video_msg_id, done_caption)
        else:
            send(chat_id, done_caption)


# ============================================================
# CALLBACK QUERY HANDLER
# ============================================================
def handle_callback(cb: dict):
    cb_id      = cb["id"]
    user_id    = cb["from"]["id"]
    uid        = str(user_id)
    chat_id    = cb["message"]["chat"]["id"]
    msg_id     = cb["message"]["message_id"]
    data       = cb.get("data", "")
    first_name = cb["from"].get("first_name", "Bạn")
    username   = cb["from"].get("username", "")

    answer_cb(cb_id)
    hwid = make_hwid(user_id)

    # Bot bảo trì
    if not is_bot_enabled() and not is_admin(user_id):
        return send_maintenance_msg(chat_id)

    if is_banned(user_id):
        return send(chat_id, "🚫 Tài khoản của bạn đã bị cấm sử dụng bot." + FOOTER)

    if data == "act_key":
        set_state(user_id, "waiting_key")
        send(chat_id,
            f"🔑 <b>NHẬP KEY KÍCH HOẠT</b>\n\n"
            f"Hãy nhập Key của bạn vào đây:"
            f"{FOOTER}")

    elif data == "act_link":
        wait_id = send_wait(chat_id)
        resp = api_getkey(hwid)
        if wait_id:
            delete_msg(chat_id, wait_id)
        st = resp.get("status", "")
        if st == "success":
            link = resp.get("link", "")
            txt = (f"🔗 <b>Link nhận Key miễn phí:</b>\n\n"
                   f"{link}\n\n"
                   f"⚠️ Tối đa 2 link/ngày. Link hết hạn sau 24 giờ.")
        elif st == "limit":
            txt = "❌ Đã đạt giới hạn 2 link/ngày. Thử lại vào ngày mai."
        else:
            txt = f"❌ Lỗi: {resp.get('message','Không xác định')}"
        send(chat_id, txt + FOOTER, reply_markup=kb_activation())

    elif data == "check_expiry":
        act, uinfo = is_activated(user_id)
        if not act:
            send(chat_id,
                 "❌ <b>Tài khoản đã hết hạn hoặc chưa kích hoạt!</b>\n\n"
                 "Vui lòng kích hoạt lại bằng key mới."
                 f"{FOOTER}", reply_markup=kb_activation())
            return
        key_stored = uinfo.get("key", "")
        use_key = key_stored and key_stored != "__da_duyet__"
        wait_id = send_wait(chat_id)
        if use_key:
            resp = api_check_expiry(key_stored, hwid)
            if wait_id: delete_msg(chat_id, wait_id)
            st = resp.get("status", "")
            if st == "valid":
                new_exp  = _get_expiry_from_resp(resp)
                is_perm  = bool(resp.get("is_permanent", False))
                _data["users"][uid]["expiry"]       = new_exp
                _data["users"][uid]["is_permanent"] = is_perm
                _save()
                exp_txt = format_expiry(user_id)
                send(chat_id,
                     f"✅ <b>Key còn hợp lệ!</b>\n\n"
                     f"🗝️ Key: <code>{key_stored}</code>\n"
                     f"⏳ Hạn dùng: {exp_txt}\n"
                     f"📅 Hết hạn: {resp.get('expiry_str','N/A')}"
                     f"{FOOTER}")
            elif st == "expired":
                _deactivate_user(uid)
                send(chat_id,
                     "❌ <b>Key đã hết hạn!</b>\n\n"
                     f"🗝️ Key: <code>{key_stored}</code>\n"
                     f"📅 Hết hạn: {resp.get('expiry_str','N/A')}\n"
                     "Vui lòng kích hoạt lại bằng key mới."
                     f"{FOOTER}", reply_markup=kb_activation())
            else:
                send(chat_id,
                     f"⚠️ Không thể kiểm tra từ server: {resp.get('message','Không xác định')}\n"
                     f"⏳ Theo dữ liệu cục bộ: {format_expiry(user_id)}"
                     f"{FOOTER}")
        else:
            resp = api_check_device(hwid)
            if wait_id: delete_msg(chat_id, wait_id)
            st = resp.get("status", "")
            if st == "approved":
                new_exp = _get_expiry_from_resp(resp)
                is_perm = bool(resp.get("is_permanent", False))
                _data["users"][uid]["expiry"]       = new_exp
                _data["users"][uid]["is_permanent"] = is_perm
                _save()
                send(chat_id,
                     f"✅ <b>Tài khoản còn hợp lệ!</b>\n\n"
                     f"⏳ Còn lại: {resp.get('time_left','N/A')}\n"
                     f"📅 Hết hạn: {resp.get('expiry_str','N/A')}"
                     f"{FOOTER}")
            elif st == "expired":
                _deactivate_user(uid)
                send(chat_id,
                     "❌ <b>Tài khoản đã hết hạn!</b>\n\n"
                     f"📅 Hết hạn: {resp.get('expiry_str','N/A')}\n"
                     "Vui lòng liên hệ Admin hoặc kích hoạt lại."
                     f"{FOOTER}", reply_markup=kb_activation())
            else:
                send(chat_id,
                     f"⏳ Theo dữ liệu cục bộ: {format_expiry(user_id)}"
                     f"{FOOTER}")

    elif data == "help_sms":
        act, _ = is_activated(user_id)
        if not act:
            return send(chat_id, "🔒 Bạn chưa kích hoạt! Dùng /start để kích hoạt." + FOOTER,
                        reply_markup=kb_activation())
        vip_user = is_vip(user_id)
        limit = get_sms_limit(user_id)
        txt = (
            "📖 <b>HƯỚNG DẪN /sms</b>\n\n"
            "Cú pháp: <code>/sms [SĐT] [Số lần]</code>\n"
            "Ví dụ: <code>/sms 0912345678 3</code>\n\n"
            f"💎 VIP của bạn: {'✅ Có' if vip_user else '❌ Không'}\n"
            f"📊 Giới hạn: 1–{limit} lần\n\n"
            f"Bot sẽ gửi OTP tới {len(OTP_FUNCTIONS)}+ dịch vụ.\n"
            "Kết quả tự cập nhật sau khi hoàn thành."
        )
        send(chat_id, txt + FOOTER)

    elif data == "my_info":
        act, uinfo = is_activated(user_id)
        if act and uinfo:
            vip_user = is_vip(user_id)
            limit = get_sms_limit(user_id)
            vip_line = format_vip_expiry(user_id) if vip_user else "❌ Chưa có VIP"
            txt = (
                f"👤 <b>THÔNG TIN</b>\n"
                f"🔓 Kích hoạt bằng: {format_activate_method(user_id)}\n"
                f"⏳ Hạn: {format_expiry(user_id)}\n"
                f"💎 VIP: {vip_line}\n"
                f"📊 Giới hạn SMS: 1–{limit} lần"
            )
        else:
            txt = "🔒 Tài khoản đã hết hạn hoặc chưa kích hoạt."
        send(chat_id, txt + FOOTER, reply_markup=kb_activation() if not act else None)


# ============================================================
# TEXT MESSAGE HANDLER (multi-step activation)
# ============================================================
def handle_text(msg: dict):
    user_id    = msg["from"]["id"]
    uid        = str(user_id)
    chat_id    = msg["chat"]["id"]
    text_in    = msg.get("text", "").strip()
    first_name = msg["from"].get("first_name", "")
    username   = msg["from"].get("username", "")
    state      = get_state(user_id)

    # Xử lý "no mandatory" — admin tắt bot
    if text_in.lower() == "no mandatory" and is_admin(user_id):
        set_bot_status(False, "")
        send(chat_id, "✅ Bot đã được <b>TẮT</b>. Tất cả người dùng sẽ nhận thông báo." + FOOTER)
        threading.Thread(
            target=broadcast_all,
            args=("🔴 <b>THÔNG BÁO HỆ THỐNG</b>\n\nBot hiện đang <b>tạm ngưng hoạt động</b>.\nVui lòng liên hệ Admin @vkhanh3010 để biết thêm thông tin." + FOOTER,),
            daemon=True
        ).start()
        return

    # Bot bảo trì — cho qua nếu đang chờ key và admin
    if not is_bot_enabled() and not is_admin(user_id):
        return send_maintenance_msg(chat_id)

    if is_banned(user_id):
        return send(chat_id, "🚫 Tài khoản của bạn đã bị cấm sử dụng bot." + FOOTER)

    if state == "waiting_key":
        clear_state(user_id)
        hwid = make_hwid(user_id)
        wait_id = send_wait(chat_id)
        resp = api_verify(text_in, hwid)
        if wait_id:
            delete_msg(chat_id, wait_id)
        st = resp.get("status", "")
        if st == "success":
            expiry  = _get_expiry_from_resp(resp)
            is_perm = bool(resp.get("is_permanent", False))
            _save_user_activation(uid, first_name, username,
                                   text_in, expiry, is_perm, hwid, "key")
            notify_admins(
                f"🔑 <b>Key kích hoạt thành công!</b>\n"
                f"👤 {first_name} [<code>{user_id}</code>]\n"
                f"🔑 Key: <code>{text_in}</code>\n"
                f"🆔 HWID: <code>{hwid}</code>"
            )
            exp_str  = resp.get("expiry_str", "N/A")
            left_str = resp.get("time_left", "N/A")
            if is_perm:
                exp_str  = "♾️ Vĩnh viễn"
                left_str = "♾️ Vĩnh viễn"
            txt = (
                f"✅ <b>KÍCH HOẠT THÀNH CÔNG!</b>\n\n"
                f"🔓 Kích hoạt bằng: 🔑 Key\n"
                f"🗝️ Key: <code>{text_in}</code>\n"
                f"⏳ Còn lại: {left_str}\n"
                f"📅 Hết hạn: {exp_str}\n\n"
                f"🎉 Dùng /sms để bắt đầu spam OTP!"
                f"{FOOTER}"
            )
            send(chat_id, txt, reply_markup=kb_main())
        else:
            msgs = {
                "expired":      f"❌ Key đã hết hạn! Hết hạn: {resp.get('expiry_str','N/A')}",
                "device_limit": f"❌ Key đạt giới hạn thiết bị tối đa ({resp.get('max_devices','?')} thiết bị).",
                "invalid":      "❌ Key không tồn tại! Kiểm tra lại.",
            }
            txt = msgs.get(st, f"❌ Lỗi: {resp.get('message','Không xác định')}")
            send(chat_id, txt + FOOTER, reply_markup=kb_activation())
        return

    act, _ = is_activated(user_id)
    if not act:
        send(chat_id,
            "🔒 Bạn chưa kích hoạt hoặc key đã hết hạn! Dùng /start để kích hoạt." + FOOTER,
            reply_markup=kb_activation())


# ============================================================
# ADMIN COMMANDS
# ============================================================
def _parse_vip_duration(val_str: str, unit_str: str):
    """Trả về (vip_expiry: float, vip_permanent: bool)"""
    unit_lower = unit_str.lower().strip()
    if unit_lower in ("forever", "vinhvien", "vinh-vien", "vinh_vien", "permanent"):
        return 0.0, True
    try:
        val = float(val_str)
    except ValueError:
        return 0.0, False
    multipliers = {
        "ngay": 86400, "gio": 3600, "thang": 2592000,
        "day": 86400, "hour": 3600, "month": 2592000,
    }
    mult = multipliers.get(unit_lower, 86400)
    return time.time() + val * mult, False

def cmd_admin(msg: dict):
    user_id = msg["from"]["id"]
    chat_id = msg["chat"]["id"]
    if not is_admin(user_id):
        return send(chat_id, "❌ Bạn không có quyền Admin!" + FOOTER)

    text  = msg.get("text", "").strip()
    parts = text.split(None, 4)
    cmd   = parts[0].lstrip('/').split('@')[0].lower()

    # ── /admin — Bảng lệnh ──
    if cmd == "admin":
        users  = _data.get("users", {})
        act_ct = sum(1 for u in users.values() if u.get("activated"))
        vip_ct = sum(1 for uid_s, u in users.items()
                     if u.get("vip") and is_vip(int(uid_s)))
        ban_ct = sum(1 for u in users.values() if u.get("banned"))
        bot_st = "🟢 Đang bật" if is_bot_enabled() else "🔴 Đang tắt"
        txt = (
            "👑 <b>ADMIN PANEL</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"🤖 Trạng thái bot: {bot_st}\n"
            f"👥 Tổng users: {len(users)}\n"
            f"✅ Đã kích hoạt: {act_ct}\n"
            f"💎 Đang có VIP: {vip_ct}\n"
            f"🚫 Bị cấm: {ban_ct}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<b>Lệnh Admin:</b>\n"
            "/bot off [lý do] — Tắt bot (thông báo tất cả)\n"
            "/bot on — Bật bot (thông báo tất cả)\n"
            "/addvip [ID] [val] [unit] — Thêm VIP\n"
            "  Ví dụ: /addvip 123456789 30 ngay\n"
            "  VIP vĩnh viễn: /addvip 123456789 0 forever\n"
            "/delvip [ID] — Xóa VIP\n"
            "/banuser [ID] — Cấm user\n"
            "/unban [ID] — Bỏ cấm user\n"
            "/listuser — Danh sách người dùng\n"
            "/broadcast [nội dung] — Gửi tới tất cả"
        )
        send(chat_id, txt + FOOTER)

    # ── /bot off [lý do] hoặc /bot on ──
    elif cmd == "bot":
        if len(parts) < 2:
            current = "🟢 Đang bật" if is_bot_enabled() else "🔴 Đang tắt"
            return send(chat_id,
                f"🤖 Trạng thái bot hiện tại: {current}\n\n"
                f"Dùng: /bot off [lý do] để tắt\n"
                f"Dùng: /bot on để bật" + FOOTER)

        sub = parts[1].lower().strip()

        if sub == "off":
            # Lấy lý do (nếu có)
            reason = " ".join(parts[2:]).strip() if len(parts) > 2 else ""
            set_bot_status(False, reason)
            reason_txt = f"\n📋 Lý do: <i>{reason}</i>" if reason else ""
            send(chat_id,
                 f"✅ Bot đã <b>TẮT</b> thành công!{reason_txt}\n\n"
                 f"Tất cả người dùng sẽ nhận thông báo ngay." + FOOTER)
            # Thông báo tất cả người dùng
            bc_msg = (
                "🔴 <b>THÔNG BÁO HỆ THỐNG</b>\n\n"
                "⚠️ Bot hiện đang <b>tạm ngưng hoạt động</b>.\n"
                + (f"📋 Lý do: <i>{reason}</i>\n" if reason else "")
                + "Vui lòng liên hệ Admin @vkhanh3010 để biết thêm thông tin."
                + FOOTER
            )
            threading.Thread(target=broadcast_all, args=(bc_msg,), daemon=True).start()

        elif sub == "on":
            set_bot_status(True, "")
            send(chat_id,
                 "✅ Bot đã <b>BẬT</b> trở lại!\n\n"
                 "Tất cả người dùng sẽ nhận thông báo ngay." + FOOTER)
            # Thông báo tất cả người dùng
            bc_msg = (
                "🟢 <b>THÔNG BÁO HỆ THỐNG</b>\n\n"
                "✅ Bot đã hoạt động trở lại bình thường!\n"
                "Dùng /start để bắt đầu."
                + FOOTER
            )
            threading.Thread(target=broadcast_all, args=(bc_msg,), daemon=True).start()

        else:
            send(chat_id,
                 "❌ Lệnh không hợp lệ.\n"
                 "Dùng: /bot off [lý do] hoặc /bot on" + FOOTER)

    # ── /addvip [ID] [val] [unit] ──
    elif cmd == "addvip":
        if len(parts) < 4:
            return send(chat_id,
                "Dùng: /addvip [ID] [val] [unit]\n"
                "Ví dụ: /addvip 123456789 30 ngay\n"
                "VIP vĩnh viễn: /addvip 123456789 0 forever" + FOOTER)
        try:
            target_id = int(parts[1])
        except ValueError:
            return send(chat_id, "❌ ID không hợp lệ!" + FOOTER)
        val_str  = parts[2]
        unit_str = parts[3]
        vip_expiry, vip_perm = _parse_vip_duration(val_str, unit_str)
        uid_s = str(target_id)
        existing = _data.setdefault("users", {}).get(uid_s)
        if not existing:
            _data["users"][uid_s] = {
                "first_name": "N/A", "username": "",
                "first_seen": time.time(), "activated": False
            }
        _data["users"][uid_s]["vip"]          = True
        _data["users"][uid_s]["vip_permanent"] = vip_perm
        _data["users"][uid_s]["vip_expiry"]    = vip_expiry
        _save()
        if vip_perm:
            exp_txt = "♾️ Vĩnh viễn"
        else:
            left = vip_expiry - time.time()
            d = int(left // 86400); h = int((left % 86400) // 3600)
            exp_txt = f"{d} ngày {h} giờ"
        is_act = _data["users"][uid_s].get("activated", False)
        txt = (
            f"✅ <b>Đã thêm VIP!</b>\n"
            f"🆔 User ID: <code>{target_id}</code>\n"
            f"💎 Hạn VIP: {exp_txt}\n"
            f"📊 Giới hạn SMS khi dùng: 1–{LIMIT_VIP} lần\n"
            f"{'✅ User đã kích hoạt, VIP có hiệu lực ngay.' if is_act else '⚠️ User chưa kích hoạt key — VIP chỉ có hiệu lực sau khi kích hoạt.'}"
        )
        send(chat_id, txt + FOOTER)
        try:
            if is_act:
                send(target_id,
                    f"🎉 <b>Bạn đã được cấp VIP!</b>\n\n"
                    f"💎 Hạn VIP: {exp_txt}\n"
                    f"📊 Giới hạn SMS nâng lên: 1–{LIMIT_VIP} lần\n"
                    f"⚡ Không bị delay 60 giây nữa!\n\n"
                    f"Dùng /info để xem thông tin tài khoản."
                    f"{FOOTER}")
            else:
                send(target_id,
                    f"🎉 <b>Bạn đã được cấp VIP!</b>\n\n"
                    f"💎 Hạn VIP: {exp_txt}\n"
                    f"⚠️ Vui lòng kích hoạt key trước khi sử dụng.\n\n"
                    f"Dùng /start để kích hoạt."
                    f"{FOOTER}")
        except Exception:
            pass

    # ── /delvip [ID] ──
    elif cmd == "delvip":
        if len(parts) < 2:
            return send(chat_id, "Dùng: /delvip [ID]" + FOOTER)
        try:
            target_id = int(parts[1])
        except ValueError:
            return send(chat_id, "❌ ID không hợp lệ!" + FOOTER)
        uid_s = str(target_id)
        if uid_s in _data.get("users", {}):
            _data["users"][uid_s]["vip"]          = False
            _data["users"][uid_s]["vip_permanent"] = False
            _data["users"][uid_s]["vip_expiry"]    = 0
            _save()
        send(chat_id, f"✅ Đã xóa VIP của user <code>{target_id}</code>." + FOOTER)
        try:
            send(target_id,
                f"ℹ️ VIP của bạn đã bị thu hồi bởi Admin.\n"
                f"Giới hạn SMS: 1–{LIMIT_NORMAL} lần.\n"
                f"Liên hệ Admin nếu có thắc mắc.{FOOTER}")
        except Exception:
            pass

    # ── /banuser [ID] ──
    elif cmd == "banuser":
        if len(parts) < 2:
            return send(chat_id, "Dùng: /banuser [ID]" + FOOTER)
        try:
            target_id = int(parts[1])
        except ValueError:
            return send(chat_id, "❌ ID không hợp lệ!" + FOOTER)
        uid_s = str(target_id)
        if uid_s not in _data.setdefault("users", {}):
            _data["users"][uid_s] = {
                "first_name": "N/A", "username": "",
                "first_seen": time.time(), "activated": False
            }
        _data["users"][uid_s]["banned"] = True
        _save()
        send(chat_id, f"🚫 Đã cấm user <code>{target_id}</code> sử dụng bot." + FOOTER)
        try:
            send(target_id, f"🚫 Tài khoản của bạn đã bị Admin cấm sử dụng bot." + FOOTER)
        except Exception:
            pass

    # ── /unban [ID] ──
    elif cmd == "unban":
        if len(parts) < 2:
            return send(chat_id, "Dùng: /unban [ID]" + FOOTER)
        try:
            target_id = int(parts[1])
        except ValueError:
            return send(chat_id, "❌ ID không hợp lệ!" + FOOTER)
        uid_s = str(target_id)
        if uid_s in _data.get("users", {}):
            _data["users"][uid_s]["banned"] = False
            _save()
        send(chat_id, f"✅ Đã bỏ cấm user <code>{target_id}</code>." + FOOTER)
        try:
            send(target_id,
                f"✅ Tài khoản của bạn đã được bỏ cấm.\n"
                f"Dùng /start để tiếp tục.{FOOTER}")
        except Exception:
            pass

    # ── /listuser ──
    elif cmd == "listuser":
        users = _data.get("users", {})
        if not users:
            return send(chat_id, "Chưa có người dùng nào." + FOOTER)
        lines = ["👥 <b>DANH SÁCH NGƯỜI DÙNG (tối đa 30):</b>"]
        for uid_s, u in list(users.items())[:30]:
            act_icon = "✅" if u.get("activated") else "❌"
            vip_icon = "💎" if (u.get("vip") and is_vip(int(uid_s))) else ""
            ban_icon = "🚫" if u.get("banned") else ""
            name = u.get("first_name", "?")
            lines.append(f"{act_icon}{vip_icon}{ban_icon} <code>{uid_s}</code> — {name}")
        send(chat_id, "\n".join(lines) + FOOTER)

    # ── /broadcast [text] ──
    elif cmd == "broadcast":
        if len(parts) < 2:
            return send(chat_id, "Dùng: /broadcast [tin nhắn]" + FOOTER)
        bc_text = text.split(None, 1)[1] if ' ' in text else ""
        users = _data.get("users", {})
        ok = 0
        for uid_s in users:
            try:
                send(int(uid_s), bc_text)
                ok += 1
            except Exception:
                pass
        send(chat_id, f"✅ Broadcast gửi tới {ok}/{len(users)} người dùng." + FOOTER)


# ============================================================
# /stop COMMAND
# ============================================================
def cmd_stop(msg: dict):
    user_id = msg["from"]["id"]
    chat_id = msg["chat"]["id"]

    if not is_bot_enabled() and not is_admin(user_id):
        return send_maintenance_msg(chat_id)

    if is_banned(user_id):
        return send(chat_id, "🚫 Tài khoản của bạn đã bị cấm sử dụng bot." + FOOTER)

    if user_id in _running_spam:
        ctx = _running_spam[user_id]
        ctx["event"].set()
        ctx["stop_handled"] = True
        stop_time = time.strftime("%H giờ %M phút")
        phone_masked = ctx.get("phone_masked", "N/A")
        carrier      = ctx.get("carrier", "N/A")
        user_disp    = ctx.get("user_disp", "N/A")
        vip_user     = ctx.get("vip_user", False)
        count        = ctx.get("count", 0)
        send(chat_id,
             f"⛔ <b>ĐÃ DỪNG TẤN CÔNG!</b>\n\n"
             f"📞 Nạn Nhân: <b>{phone_masked}</b>\n"
             f"👤 Người Dùng : <b>{user_disp}</b>\n"
             f"💎 Gói: <b>{'✨ VIP' if vip_user else '👤 Thường'}</b>\n"
             f"📡 Nhà Mạng: <b>{carrier}</b>\n"
             f"🔄 COUNT đặt: <b>{count}</b>\n"
             f"⚡ Trạng Thái: ⛔ <b>Đã dừng theo yêu cầu</b>"
             + FOOTER)
    else:
        send(chat_id,
             "ℹ️ Không có tiến trình nào đang chạy để dừng." + FOOTER)


ADMIN_CMDS = {
    "admin", "addvip", "delvip", "banuser", "unban", "listuser", "broadcast", "bot"
}

def dispatch(update: dict):
    try:
        if "callback_query" in update:
            handle_callback(update["callback_query"])
            return

        msg = update.get("message")
        if not msg:
            return
        text = msg.get("text", "")
        if not text:
            return

        if text.startswith('/'):
            raw_cmd = text.split()[0].lstrip('/').split('@')[0].lower()
            if   raw_cmd == "start":    cmd_start(msg)
            elif raw_cmd == "help":     cmd_help(msg)
            elif raw_cmd == "info":     cmd_info(msg)
            elif raw_cmd == "sms":      cmd_sms(msg)
            elif raw_cmd == "stop":     cmd_stop(msg)
            elif raw_cmd in ADMIN_CMDS: cmd_admin(msg)
            else:                       handle_text(msg)
        else:
            handle_text(msg)

    except Exception as e:
        logging.error(f"[dispatch] {e}", exc_info=True)


# ============================================================
# FLASK WEB SERVER
# ============================================================
app = Flask(__name__)

_LOVE_HTML = """<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Văn Khánh ❤️ Minh Thư</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  min-height:100vh;
  background:linear-gradient(135deg,#ff6b6b 0%,#ee5a24 25%,#ff6b6b 50%,#fd79a8 75%,#e84393 100%);
  background-size:400% 400%;
  animation:bgShift 8s ease infinite;
  display:flex;align-items:center;justify-content:center;
  font-family:'Georgia',serif;overflow:hidden;
}
@keyframes bgShift{0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%}}
.hearts-bg{position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:0;overflow:hidden}
.hp{position:absolute;animation:floatUp linear infinite;opacity:0}
@keyframes floatUp{0%{transform:translateY(100vh) scale(.5) rotate(-10deg);opacity:0}10%{opacity:.8}90%{opacity:.5}100%{transform:translateY(-10vh) scale(1.2) rotate(15deg);opacity:0}}
.card{
  position:relative;z-index:1;
  background:rgba(255,255,255,.15);
  backdrop-filter:blur(20px);
  border:2px solid rgba(255,255,255,.3);
  border-radius:30px;
  padding:60px 50px;
  text-align:center;
  max-width:520px;
  width:90%;
  box-shadow:0 25px 50px rgba(0,0,0,.2),inset 0 1px 0 rgba(255,255,255,.3);
}
.big-heart{font-size:5rem;animation:hb 1.2s ease-in-out infinite;display:block;margin-bottom:20px;filter:drop-shadow(0 0 20px rgba(255,100,100,.8))}
@keyframes hb{0%,100%{transform:scale(1)}14%{transform:scale(1.15)}28%{transform:scale(1)}42%{transform:scale(1.15)}70%{transform:scale(1)}}
h1{color:#fff;font-size:1.9rem;text-shadow:0 2px 10px rgba(0,0,0,.3);margin-bottom:15px;line-height:1.4}
.divider{width:60px;height:3px;background:rgba(255,255,255,.6);margin:20px auto;border-radius:2px}
.sub{color:rgba(255,255,255,.85);font-size:1rem;letter-spacing:1px;font-style:italic;margin-top:10px}
.sparkle{font-size:1.5rem;animation:sp 2s ease-in-out infinite;display:inline-block}
@keyframes sp{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.5;transform:scale(.8)}}
</style>
</head>
<body>
<div class="hearts-bg" id="hb"></div>
<div class="card">
  <span class="big-heart">❤️</span>
  <h1>Tôi là Văn Khánh<br>yêu Minh Thư</h1>
  <div class="divider"></div>
  <p class="sub">Mãi mãi bên nhau 💕</p>
  <div style="margin-top:20px">
    <span class="sparkle">✨</span>
    <span class="sparkle" style="animation-delay:.4s">💝</span>
    <span class="sparkle" style="animation-delay:.8s">✨</span>
  </div>
</div>
<script>
const hs=['❤️','💕','💗','💓','💞','🌹','💖'];
const c=document.getElementById('hb');
function mkH(){
  const e=document.createElement('div');
  e.className='hp';
  e.textContent=hs[Math.floor(Math.random()*hs.length)];
  e.style.left=Math.random()*100+'%';
  e.style.fontSize=(1+Math.random()*1.5)+'rem';
  const dur=4+Math.random()*4;
  e.style.animationDuration=dur+'s';
  e.style.animationDelay=Math.random()*2+'s';
  c.appendChild(e);
  setTimeout(()=>e.remove(),(dur+2)*1000);
}
setInterval(mkH,500);
</script>
</body>
</html>"""

@app.route('/')
def index():
    return render_template_string(_LOVE_HTML)

@app.route('/ping')
def ping():
    return "pong", 200

@app.route('/health')
def health():
    return {"status": "ok", "bot_enabled": is_bot_enabled(), "timestamp": time.time()}, 200


# ============================================================
# KEEP-ALIVE WORKERS (chống Render ngủ đông)
# 4 worker, mỗi worker ping mỗi 10 phút, lệch nhau 2.5 phút
# → server nhận ping mỗi ~2.5 phút, không bao giờ ngủ
# ============================================================
def _keep_alive_worker(start_delay: int, worker_id: int):
    """Ping server định kỳ để ngăn Render hibernate."""
    time.sleep(start_delay)
    cycle = 10 * 60  # 10 phút mỗi vòng
    while True:
        try:
            r = requests.get(f"{SELF_URL}/ping", timeout=10)
            if r.status_code == 200:
                logging.info(f"[KA-{worker_id}] ping OK")
            else:
                logging.warning(f"[KA-{worker_id}] ping status {r.status_code}")
        except Exception as e:
            logging.warning(f"[KA-{worker_id}] ping thất bại: {e}")
        time.sleep(cycle)

def start_keep_alive():
    # 4 workers lệch nhau 150 giây (2.5 phút) → ping mỗi 2.5 phút
    offsets = [0, 150, 300, 450]
    for idx, offset in enumerate(offsets):
        t = threading.Thread(
            target=_keep_alive_worker,
            args=(offset, idx + 1),
            daemon=True
        )
        t.start()
    logging.info("Keep-alive: 4 workers khởi động (chu kỳ 10 phút, lệch 2.5 phút)")


# ============================================================
# AUTO-SAVE WORKER (lưu dữ liệu định kỳ mỗi 5 phút)
# Đảm bảo data không mất khi server bị restart đột ngột
# ============================================================
def _auto_save_worker():
    """Lưu bot_data.json mỗi 5 phút để bảo toàn dữ liệu."""
    while True:
        time.sleep(300)  # 5 phút
        try:
            _save()
            logging.info("[AutoSave] Dữ liệu đã được lưu tự động.")
        except Exception as e:
            logging.warning(f"[AutoSave] Lỗi: {e}")

def start_auto_save():
    t = threading.Thread(target=_auto_save_worker, daemon=True)
    t.start()
    logging.info("AutoSave: worker khởi động (chu kỳ 5 phút)")


# ============================================================
# TELEGRAM LONG-POLL LOOP
# ============================================================
_last_update_id = 0

def _poll_loop():
    global _last_update_id
    logging.info("Telegram polling started…")
    while True:
        try:
            r = requests.get(f"{BOT_URL}/getUpdates",
                             params={"offset": _last_update_id + 1, "timeout": 30},
                             timeout=35)
            data = r.json()
            if data.get("ok"):
                for upd in data.get("result", []):
                    _last_update_id = upd["update_id"]
                    threading.Thread(target=dispatch, args=(upd,), daemon=True).start()
        except Exception as e:
            logging.warning(f"[poll] {e}")
            time.sleep(5)

def start_polling():
    t = threading.Thread(target=_poll_loop, daemon=True)
    t.start()
    logging.info("Polling thread started")


# ============================================================
# ENTRY POINT
# ============================================================
if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )

    logging.info("=== BOT SPAM OTP VIP - KHỞI ĐỘNG ===")
    logging.info(f"Dữ liệu: {DATA_FILE}")
    logging.info(f"Thư mục video: {_BOT_DIR}")
    mp4s = glob.glob(os.path.join(_BOT_DIR, "*.mp4"))
    logging.info(f"Video MP4 tìm thấy: {len(mp4s)} file(s) — {[os.path.basename(f) for f in mp4s]}")

    start_keep_alive()
    start_auto_save()
    start_polling()

    port = int(os.environ.get('PORT', 5000))
    logging.info(f"Flask starting on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
