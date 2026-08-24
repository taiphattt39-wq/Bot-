# ==============================================
# BOT DISCORD - KIỂM SOÁT QUÂN SỰ KHÔNG QUÂN
# ==============================================

import os
import json
import time
import asyncio
from datetime import datetime
import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
from keep_alive import keep_alive
keep_alive()

# ---------------------- CẤU HÌNH CHÍNH ----------------------
TOKEN = os.getenv("TOKEN", "")
API_KEY_GEMINI = os.getenv("API_KEY_GEMINI", "")

BLACKLIST_CHANNEL_ID = 1529758582042525726

LOG_FILE = "command_logs.txt"
ERROR_LOG = "error_logs.txt"
BLACKLIST_FILE = "blacklist_airforce.json"
ECONOMY_FILE = "kinh_te_airforce.json"

MAIN_GROUP_ID = 397506574
ARMY_GROUP_ID = 689697341

ROLE_ADMIN_IDS = [1479375774711549996]


# ---------------------- KHỞI TẠO FILE ----------------------
for f in [LOG_FILE, ERROR_LOG]:
    if os.path.exists(f):
        with open(f, "w", encoding="utf-8") as fp:
            fp.write("")

# Danh sách đen
if os.path.exists(BLACKLIST_FILE):
    try:
        with open(BLACKLIST_FILE, "r", encoding="utf-8") as f:
            blacklist = json.load(f)
        if not isinstance(blacklist, dict):
            blacklist = {}
    except Exception:
        blacklist = {}
else:
    blacklist = {}

def save_blacklist():
    with open(BLACKLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(blacklist, f, indent=4, ensure_ascii=False)

# Kinh tế
if os.path.exists(ECONOMY_FILE):
    try:
        with open(ECONOMY_FILE, "r", encoding="utf-8") as f:
            economy = json.load(f)
        if not isinstance(economy, dict):
            economy = {}
    except Exception:
        economy = {}
else:
    economy = {}

def save_economy():
    with open(ECONOMY_FILE, "w", encoding="utf-8") as f:
        json.dump(economy, f, indent=4, ensure_ascii=False)


# ---------------------- KHỞI TẠO BOT ----------------------
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)
cay_lenh = bot.tree


# ---------------------- HÀM HỖ TRỢ ----------------------
async def ghi_log_lenh(i: discord.Interaction, ten: str, nd: str = "Thực hiện"):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] | {i.user} | {ten} | {nd}\n")

async def ghi_log_loi(i: discord.Interaction, ten: str, loi: Exception):
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] | {i.user} | {ten} | LỖI: {loi}\n")

def co_quyen_say(i: discord.Interaction) -> bool:
    return i.user.guild_permissions.administrator or i.user.id in ROLE_ADMIN_IDS

def co_quyen_cao(i: discord.Interaction) -> bool:
    return i.user.guild_permissions.administrator

def phan_tich_tg(txt: str):
    try:
        if " - " in txt:
            a, b = txt.split(" - ")
            return datetime.strptime(a.strip(), "%d/%m/%Y"), datetime.strptime(b.strip(), "%d/%m/%Y")
        return datetime.strptime(txt.strip(), "%d/%m/%Y"), None
    except Exception:
        return None, None

def kiem_tra_bl(rid: str):
    data = blacklist.get(str(rid))
    if not data:
        return {"hoat_dong": False, "ghi_chu": "✅ **HỢP LỆ / SẠCH**\nKhông có trong danh sách đen hệ thống"}
    bd, kt = phan_tich_tg(data.get("Date", ""))
    het_han = kt and datetime.now() > kt
    return {
        "hoat_dong": not het_han,
        "ghi_chu": f"⛔ **BỊ XỬ LÝ**\n**Xử lý:** {data.get('Punishment', '')}\n**Lý do:** {data.get('Reason', '')}\n**Ngày:** {data.get('Date', '')}"
    }

async def lay_rb(tentk: str):
    async with aiohttp.ClientSession() as s:
        try:
            res = await s.post("https://users.roblox.com/v1/usernames/users", json={"usernames": [tentk]})
            d = await res.json()
            if not d.get("data"):
                return None
            rid = str(d["data"][0]["id"])
            ten_hien = d["data"][0]["displayName"]
            ten_tk = d["data"][0]["name"]

            res2 = await s.get(f"https://users.roblox.com/v1/users/{rid}")
            d2 = await res2.json()
            ngay_tao = datetime.fromisoformat(d2["created"].replace("Z", "+00:00:00")).date()
            so_ngay = (datetime.now().date() - ngay_tao).days
            avatar = f"https://www.roblox.com/headshot-thumbnail/image?userId={rid}&width=420&height=420&format=png"

            main, army = ("❌ Chưa tham gia", ""), ("❌ Chưa tham gia", "")
            resg = await s.get(f"https://groups.roblox.com/v1/users/{rid}/groups/roles")
            dg = await resg.json()
            for gr in dg.get("data", []):
                gid = gr["group"]["id"]
                if gid == MAIN_GROUP_ID:
                    main = ("✅ Đã tham gia", gr["role"]["name"])
                if gid == ARMY_GROUP_ID:
                    army = ("✅ Đã tham gia", gr["role"]["name"])

            return {"rid": rid, "ten_hien": ten_hien, "ten_tk": ten_tk, "so_ngay": so_ngay, "avatar": avatar, "main": main, "army": army}
        except Exception:
            return None


# ---------------------- SỰ KIỆN ----------------------
@bot.event
async def on_ready():
    await cay_lenh.sync()
    print(f"\n✅ BOT SẴN SÀNG | AIRFORCE | {bot.user}\n")

@bot.event
async def on_message(msg: discord.Message):
    if msg.author.bot:
        return
    if msg.channel.id == BLACKLIST_CHANNEL_ID:
        lines = [x.strip() for x in msg.content.splitlines() if x.strip()]
        fields = ["Tên người dùng:", "ID Roblox:", "Cấp bậc:", "Lý do:", "Hình phạt:", "Được phê duyệt bởi:", "Ngày:"]
        ok = all(any(l.startswith(f) for l in lines) for f in fields)
        if ok:
            data = {}
            for l in lines:
                for f in fields:
                    if l.startswith(f):
                        data[f.strip(":")] = l[len(f):].strip()
            if "ID Roblox" in data:
                blacklist[data["ID Roblox"]] = data
                save_blacklist()
                await msg.add_reaction("✅")
    await bot.process_commands(msg)


# ---------------------- LỆNH ----------------------
@cay_lenh.command(name="help", description="Danh sách lệnh hệ thống")
async def help_cmd(i: discord.Interaction):
    em = discord.Embed(title="📖 DANH SÁCH LỆNH | AIRFORCE", color=0x3498DB)
    em.add_field(name="/profile <tên_roblox>", value="Tra cứu hồ sơ chi tiết", inline=False)
    em.add_field(name="/say <nội dung> [ảnh_url] [ping_all] [embed] [màu]",
                 value="Quản lý: gửi nội dung, ảnh (tùy), ping (tùy)", inline=False)
    em.add_field(name="/kiemtraloi [số_dòng]", value="Xem log lỗi (chỉ quản lý)", inline=False)
    em.add_field(name="/vi", value="Xem số dư cá nhân", inline=False)
    em.add_field(name="/chuyentien <người> <số_tiền>", value="Chuyển tiền cho thành viên", inline=False)
    em.add_field(name="Blacklist Tự Động", value=f"Gửi đúng định dạng vào kênh <#{BLACKLIST_CHANNEL_ID}> → Bot tick xanh", inline=False)
    await i.response.send_message(embed=em)

@cay_lenh.command(name="say", description="Quản lý: Gửi tin nhắn, ảnh, ping tùy chọn")
@app_commands.describe(
    noidung="Nội dung tin nhắn gửi (bắt buộc)",
    anh_url="Link ảnh đính kèm (không bắt buộc)",
    ping_all="Ping @everyone? Đúng/Sai (mặc định: Sai)",
    gui_embed="Gửi dạng Embed? Đúng/Sai (mặc định: Sai)",
    mau="Màu embed: xanh/đỏ/xanh_duong/vang/tim/xam"
)
async def lenh_say(i: discord.Interaction, noidung: str, anh_url: str = "", ping_all: bool = False, gui_embed: bool = False, mau: str = "xanh"):
    try:
        await ghi_log_lenh(i, "/say", noidung[:60])
        if not co_quyen_say(i):
            return await i.response.send_message("❌ Không có quyền dùng lệnh này!", ephemeral=True)

        bangmau = {
            "xanh": 0x2ECC71, "đỏ": 0xE74C3C, "do": 0xE74C3C,
            "xanh_duong": 0x3498DB, "vang": 0xF1C40F, "vàng": 0xF1C40F,
            "tim": 0x9B59B6, "tím": 0x9B59B6, "xam": 0x95A5A6, "xám": 0x95A5A6
        }
        noi_dung_gui = "@everyone\n" + noidung if ping_all else noidung

        if gui_embed:
            em = discord.Embed(description=noi_dung_gui, color=bangmau.get(mau.lower(), 0x2ECC71), timestamp=datetime.now())
            if anh_url:
                em.set_image(url=anh_url.strip())
            em.set_footer(text=f"Gửi bởi: {i.user.display_name} | AIRFORCE")
            await i.channel.send(embed=em)
        else:
            file = None
            if anh_url and anh_url.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
                try:
                    async with aiohttp.ClientSession() as s:
                        res = await s.get(anh_url)
                        if res.status == 200:
                            data_anh = await res.read()
                            with open("temp_anh.png", "wb") as f:
                                f.write(data_anh)
                            file = discord.File("temp_anh.png")
                except Exception:
                    pass
            await i.channel.send(content=noi_dung_gui, file=file)
            if file and os.path.exists("temp_anh.png"):
                os.remove("temp_anh.png")

        await i.response.send_message("✅ Đã gửi tin nhắn thành công!", ephemeral=True)
    except Exception as e:
        await ghi_log_loi(i, "/say", e)
        await i.response.send_message("❌ Lỗi gửi tin nhắn!", ephemeral=True)

@cay_lenh.command(name="profile", description="Tra cứu hồ sơ Roblox")
@app_commands.describe(tentk="Tên tài khoản Roblox")
async def lenh_profile(i: discord.Interaction, tentk: str):
    try:
        await ghi_log_lenh(i, "/profile", tentk)
        await i.response.defer()
        data = await lay_rb(tentk)
        if not data:
            return await i.followup.send("❌ Không tìm thấy tài khoản!", ephemeral=True)
        bl = kiem_tra_bl(data["rid"])
        mau = discord.Color.green() if not bl["hoat_dong"] else discord.Color.red()
        dk = "✅ Đủ điều kiện (>30 ngày)" if data["so_ngay"] > 30 else "❌ Chưa đủ điều kiện (>30 ngày)"

        em = discord.Embed(title="HỆ THỐNG TRUY XUẤT HỒ SƠ ROBLOX | AIRFORCE", color=mau, timestamp=datetime.now())
        em.set_thumbnail(url=data["avatar"])
        em.add_field(name="📋 THÔNG SỐ ĐỊNH DANH", value=f"""[+] Tên hiển thị: `{data['ten_hien']}`
[+] Tên tài khoản: `@{data['ten_tk']}`
[+] ID Mã: `{data['rid']}`
[+] Tuổi tài khoản: `{data['so_ngay']} Ngày`
{dk}""", inline=False)
        em.add_field(name="🌐 TRẠNG THÁI HOẠT ĐỘNG", value="[+] Tình trạng: 🟢 Trực tuyến\n[+] Bạn bè: `185 người`\n[+] Hoạt động: `Không xác định`", inline=False)
        em.add_field(name="🎖️ CẤP BẬC TỔ CHỨC", value=f"""🏛️ AIRFORCE MAIN: {data['main'][0]} | `{data['main'][1]}`
⚔️ KHÔNG QUÂN LỤC QUÂN: {data['army'][0]} | `{data['army'][1]}`
[Xem CHÍNH](https://www.roblox.com/groups/{MAIN_GROUP_ID})
[Xem ARMY](https://www.roblox.com/groups/{ARMY_GROUP_ID})""", inline=False)
        em.add_field(name="🛡️ TRẠNG THÁI AN NINH", value=bl["ghi_chu"], inline=False)
        em.set_footer(text=f"Tra cứu: {i.user.display_name} | AIRFORCE Core")
        await i.followup.send(embed=em)
    except Exception as e:
        await ghi_log_loi(i, "/profile", e)
        await i.followup.send("❌ Lỗi lấy hồ sơ!", ephemeral=True)

@cay_lenh.command(name="kiemtraloi", description="Xem log lỗi hệ thống (chỉ quản lý)")
@app_commands.describe(sodong="Số dòng xem (tối đa 20)")
async def lenh_kiemtraloi(i: discord.Interaction, sodong: int = 10):
    try:
        await ghi_log_lenh(i, "/kiemtraloi")
        if not co_quyen_cao(i):
            return await i.response.send_message("❌ Chỉ quản lý mới được dùng!", ephemeral=True)
        with open(ERROR_LOG, "r", encoding="utf-8") as f:
            lines = f.readlines()
        if not lines:
            return await i.response.send_message("✅ Không có lỗi nào!", ephemeral=True)
        sl = min(max(sodong, 1), 20)
        nd = "".join(lines[-sl:])[:3900]
        em = discord.Embed(title="📋 NHẬT KÝ LỖI HỆ THỐNG | AIRFORCE", description=f"```\n{nd}\n```", color=0xE74C3C, timestamp=datetime.now())
        em.set_footer(text=f"{sl} dòng cuối | Yêu cầu: {i.user.display_name}")
        await i.response.send_message(embed=em, ephemeral=True)
    except Exception as e:
        await ghi_log_loi(i, "/kiemtraloi", e)
        await i.response.send_message("❌ Không đọc được file log!", ephemeral=True)

@cay_lenh.command(name="vi", description="Xem số dư tài khoản cá nhân")
async def lenh_vi(i: discord.Interaction):
    uid = str(i.user.id)
    if uid not in economy:
        economy[uid] = {"ten": i.user.display_name, "tien": 1000}
    save_economy()
    await i.response.send_message(f"💰 **Tài chính | AIRFORCE**\n{i.user.mention}\nSố dư: `{economy[uid]['tien']:,} VNĐ`", ephemeral=True)

@cay_lenh.command(name="chuyentien", description="Chuyển tiền cho thành viên")
@app_commands.describe(nguoi="Người nhận", sotien="Số tiền")
async def lenh_chuyentien(i: discord.Interaction, nguoi: discord.Member, sotien: int):
    if sotien <= 0:
        return await i.response.send_message("❌ Số tiền phải > 0!", ephemeral=True)
    gid, nid = str(i.user.id), str(nguoi.id)
    if gid == nid:
        return await i.response.send_message("❌ Không tự chuyển cho mình!", ephemeral=True)
    if gid not in economy:
        economy[gid] = {"ten": i.user.display_name, "tien": 1000}
    if nid not in economy:
        economy[nid] = {"ten": nguoi.display_name, "tien": 1000}
    if economy[gid]["tien"] < sotien:
        return await i.response.send_message("❌ Không đủ số dư!", ephemeral=True)
    economy[gid]["tien"] -= sotien
    economy[nid]["tien"] += sotien
    save_economy()
    await i.response.send_message(f"✅ Chuyển thành công!\nTừ: {i.user.mention} → {nguoi.mention}\nSố tiền: `{sotien:,} VNĐ`", ephemeral=True)


# ---------------------- CHẠY BOT ----------------------
def chay_bot_ben():
    while True:
        try:
            print("🔄 KHỞI ĐỘNG BOT...")
            bot.run(TOKEN)
        except discord.errors.LoginFailure:
            print("\n❌ SAI TOKEN! Kiểm tra lại token bot, dừng hoàn toàn.\n")
            break
        except Exception as e:
            print(f"\n⚠️ MẤT KẾT NỐI/LỖI: {e}")
            print("🔄 Đang khôi phục sau 10 giây...")
            time.sleep(10)
            continue
        else:
            break
# ==================== ĐÁNH THỨC & CHẠY BOT ====================
from keep_alive import keep_alive

if __name__ == "__main__":
    print("🔄 ĐANG KHỞI ĐỘNG...")
    keep_alive()       # ← Bật web giữ bot treo
    chay_bot_ben()     # ← Khởi động bot Discord
    
