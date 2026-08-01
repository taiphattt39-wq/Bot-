import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone
import aiohttp
import json
import os
import asyncio

# ======================== CẤU HÌNH ========================
TOKEN = "MTUzMjk1MDMyNTMwMzE4NTQ2OQ.GQMbdl.hLRfmgxH_IbQ9QrUybc-_849ZMFdCm_v2JD6wA"
BLACKLIST_CHANNEL_ID = 1526861892587356192
LOG_FILE = "command_logs.txt"
DATABASE = "blacklist_rieng.json"
ECONOMY_DB = "kinh_te.json"
PHASE_DB = "phase_rank.json"

# === ID NHÓM ROBLOX ===
MAIN_GROUP_ID = 397506574    # VMNB MAIN
ARMY_GROUP_ID = 689697341    # VMNB ARMY
LINK_MAIN = f"https://www.roblox.com/groups/{MAIN_GROUP_ID}"
LINK_ARMY = f"https://www.roblox.com/groups/{ARMY_GROUP_ID}"

# Quyền Discord
ROLE_PHASE = {"1":1532947750214303836,"2":1532947795957256192,"3":1532947838785425418,"final":1532947899158364382}
ROLE_INS_LOW = 1526883272498352209
ROLE_INS_MID = 1526883180269797376
ROLE_INS_HIGH = 1526883009456898078
ROLE_HIGH_COMMAND = 1526888145273098330

# Tạo file dữ liệu
for f in [LOG_FILE, DATABASE, ECONOMY_DB, PHASE_DB]:
    if not os.path.exists(f):
        with open(f, "w", encoding="utf-8") as f_out:
            f_out.write("")

# Load/Save
def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, type(default)) else default
    except Exception:
        return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

blacklist = load_json(DATABASE, {})
economy = load_json(ECONOMY_DB, {})
phase_data = load_json(PHASE_DB, {})

def save_blacklist(): save_json(DATABASE, blacklist)
def save_econ(): save_json(ECONOMY_DB, economy)
def save_phase(): save_json(PHASE_DB, phase_data)

# ======================== HÀM HỖ TRỢ ========================
def has_perm(i):
    ur = [r.id for r in i.user.roles]
    return i.guild_permissions.administrator or ROLE_HIGH_COMMAND in ur or ROLE_INS_HIGH in ur or ROLE_INS_MID in ur or ROLE_INS_LOW in ur

def perm_high(i):
    ur = [r.id for r in i.user.roles]
    return i.guild_permissions.administrator or ROLE_HIGH_COMMAND in ur or ROLE_INS_HIGH in ur

async def log_cmd(i, name):
    t = datetime.now().astimezone().strftime("%d/%m/%Y %H:%M")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{i.user.display_name}] - [/{name}] - [{t}]\n")

# === LẤY AVATAR CHUẨN, KIỂM TRA ĐẦY ĐỦ ===
async def roblox_profile(username):
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as s:
        # Lấy ID người dùng
        async with s.post("https://users.roblox.com/v1/usernames/users", json={"usernames":[username.strip()]}) as r:
            if r.status != 200: return None
            res = await r.json()
            if not res.get("data") or len(res["data"]) == 0: return None
            u = res["data"][0]
            rid = str(u["id"])

        # Thông tin tài khoản
        async with s.get(f"https://users.roblox.com/v1/users/{rid}") as r:
            info = await r.json() if r.status == 200 else {}

        # === CẢI THIỆN LẤY AVATAR, KIỂM TRA TỪNG BƯỚC ===
        avt = None
        try:
            async with s.get(
                f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={rid}&size=420&format=Png&isCircular=false"
            ) as r_avt:
                if r_avt.status == 200:
                    data_avt = await r_avt.json()
                    # Kiểm tra cấu trúc + thành công + link hợp lệ
                    if "data" in data_avt and isinstance(data_avt["data"], list) and len(data_avt["data"]) > 0:
                        first_item = data_avt["data"][0]
                        if first_item.get("success", False) and "imageUrl" in first_item:
                            img_url = first_item["imageUrl"]
                            if img_url.startswith("http"):
                                avt = img_url
        except Exception as e:
            print(f"Lỗi lấy avatar: {e}")

        # Trạng thái & thông tin phụ
        async with s.get(f"https://users.roblox.com/v1/users/{rid}/status") as r:
            status = (await r.json()).get("status", "Không có") if r.status == 200 else "Không xác định"
        async with s.get(f"https://friends.roblox.com/v1/users/{rid}/friends/count") as r:
            friend = (await r.json()).get("count", 0) if r.status == 200 else 0
        async with s.get(f"https://groups.roblox.com/v1/users/{rid}/groups/roles") as r:
            groups = (await r.json()).get("data", []) if r.status == 200 else []

        # Kiểm tra nhóm tách rõ 2 dòng
        main_stt, main_rank = "❌ Chưa tham gia", ""
        army_stt, army_rank = "❌ Chưa tham gia", ""
        for g in groups:
            gid = g["group"]["id"]
            if gid == MAIN_GROUP_ID:
                main_stt = "✅ Đã tham gia"
                main_rank = g["role"]["name"]
            if gid == ARMY_GROUP_ID:
                army_stt = "✅ Đã tham gia"
                army_rank = g["role"]["name"]

    # Tính tuổi tài khoản
    try:
        created = datetime.fromisoformat(info.get("created", "2000-01-01T00:00:00Z").replace("Z", "+00:00"))
    except Exception:
        created = datetime.now(timezone.utc)
    tuoi = (datetime.now(timezone.utc) - created).days
    truc = "🟢 Trực tuyến" if status and status.strip() != "" else "⚫ Ngoại tuyến"

    return {
        "rid": rid, "uname": u["name"], "dname": u["displayName"], "avt": avt,
        "tuoi": tuoi, "truc": truc, "status": status, "friend": friend,
        "main": {"stt": main_stt, "rank": main_rank},
        "army": {"stt": army_stt, "rank": army_rank},
        "bl": blacklist.get(rid), "is_bl": rid in blacklist
    }

# ======================== KHỞI TẠO BOT - SỬA LỖI TIỀN TỐ ========================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
# ✅ Đặt tiền tố trống hợp lệ, tránh lỗi NoneType
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)
tree = bot.tree

# === BLACKLIST + TICK XANH - KHÔNG GỌI process_commands TRỪNG HỢP LÝ ===
@bot.event
async def on_message(m):
    if m.author.bot:
        return
    # Xử lý blacklist
    if m.channel.id == BLACKLIST_CHANNEL_ID:
        txt = m.content.strip()
        req = ["Username:", "Roblox ID:", "Rank:", "Reason:", "Punishment:", "Approved by:", "Date:"]
        if all(x in txt for x in req):
            data = {}
            for line in txt.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    data[k.strip()] = v.strip()
            rid = data.get("Roblox ID", "").strip()
            if rid.isdigit():
                blacklist[rid] = data
                save_blacklist()
                await m.add_reaction("✅")
    # Xử lý lệnh bình thường
    await bot.process_commands(m)

@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ Bot VMNB Sẵn sàng | {bot.user}")

# ======================== LỆNH PROFILE - AVATAR + TÁCH 2 HÀNG ========================
@tree.command(name="profile", description="Tra hồ sơ Roblox - Kiểm tra VMNB MAIN & ARMY")
@app_commands.describe(ten_tk="Tên tài khoản Roblox")
async def profile(i, ten_tk: str):
    await log_cmd(i, "profile")
    await i.response.defer()
    u = await roblox_profile(ten_tk)
    if not u:
        return await i.followup.send(f"❌ Không tìm thấy tài khoản: `{ten_tk}`")

    if u["is_bl"]:
        clr = discord.Color.red()
        an = f"""🛡️ TRẠNG THÁI AN NINH
❌ **BỊ BLACKLIST**
• Cấp bậc: {u['bl'].get('Rank','-')}
• Lý do: {u['bl'].get('Reason','-')}
• Hình phạt: {u['bl'].get('Punishment','-')}
• Người duyệt: {u['bl'].get('Approved by','-')}
• Ngày: {u['bl'].get('Date','-')}"""
    else:
        clr = discord.Color.green()
        an = """🛡️ TRẠNG THÁI AN NINH
✅ **HỢP LỆ / SẠCH**
Không có trong danh sách đen hệ thống"""

    embed = discord.Embed(
        title="**HỆ THỐNG TRUY XUẤT HỒ SƠ ROBLOX | VMNB**",
        color=clr,
        timestamp=datetime.now()
    )

    # === ĐẶT AVATAR NẾU CÓ LINK HỢP LỆ ===
    if u["avt"]:
        embed.set_thumbnail(url=u["avt"])

    embed.add_field(name="📋 THÔNG SỐ ĐỊNH DANH", value=f"""[+] Tên hiển thị: `{u['dname']}`
[+] Tên tài khoản: `@{u['uname']}`
[+] Mã ID: `{u['rid']}`
[+] Tuổi tài khoản: `{u['tuoi']}` Ngày
`{'🟢 Đủ điều kiện (>30 ngày)' if u['tuoi']>=30 else '🔴 Chưa đủ điều kiện'}`""", inline=False)

    embed.add_field(name="🌐 TRẠNG THÁI HOẠT ĐỘNG", value=f"""[+] Tình trạng: `{u['truc']}`
[+] Bạn bè: `{u['friend']}` người
[+] Hoạt động: `{u['status'] or 'Không có'}`""", inline=False)

    # Tách rõ 2 dòng tổ chức
    embed.add_field(name="🎖️ CẤP BẬC TỔ CHỨC (KIỂM TRA TỰ ĐỘNG)", value=f"""**VMNB MAIN**: {u['main']['stt']} `{u['main']['rank']}`
**VMNB ARMY**: {u['army']['stt']} `{u['army']['rank']}`
[🔗 Xem Nhóm VMNB MAIN]({LINK_MAIN}) | [🔗 Xem Nhóm VMNB ARMY]({LINK_ARMY})""", inline=False)

    embed.add_field(name="", value=an, inline=False)
    embed.set_footer(text=f"Tra cứu: {i.user.display_name} • VMNB Core")
    await i.followup.send(embed=embed)

# --- Các lệnh phụ giữ nguyên ---
@tree.command(name="phase", description="Quản lý nâng cấp/Tốt nghiệp")
@app_commands.describe(mem="Thành viên Discord", hanh="nâng/totnghiep", cap="1/2/3/final", ly_do="Lý do")
async def phase(i, mem: discord.Member, hanh: str, cap: str, ly_do: str = "Không có"):
    await log_cmd(i,"phase")
    if not perm_high(i): return await i.response.send_message("❌ Chỉ Quyền Cao/Admin dùng được!",ephemeral=True)
    hanh,cap=hanh.lower(),cap.lower()
    if hanh=="nâng" and cap in ["1","2","3"]: rid,tieu,mau=ROLE_PHASE[cap],f"📈 NÂNG PHASE {cap}",discord.Color.gold()
    elif hanh=="totnghiep" and cap=="final": rid,tieu,mau=ROLE_PHASE["final"],"🎓 TỐT NGHIỆP",discord.Color.teal()
    else: return await i.response.send_message("⚠️ Cách dùng: /phase @người nâng 1/2/3 | totnghiep final",ephemeral=True)
    role=i.guild.get_role(rid)
    if not role: return await i.response.send_message("❌ Không tìm thấy Role!",ephemeral=True)
    await mem.remove_roles(*[i.guild.get_role(r) for r in ROLE_PHASE.values() if i.guild.get_role(r) in mem.roles])
    await mem.add_roles(role, reason=f"{tieu}: {ly_do}")
    uid=str(mem.id)
    phase_data[uid]={"ten":mem.display_name,"cap_cu":phase_data.get(uid,{}).get("cap_moi","Chưa có"),"cap_moi":f"Phase {cap}" if hanh=="nâng" else "Đã tốt nghiệp","ngay":datetime.now().strftime("%d/%m/%Y"),"nguoi_duyet":i.user.display_name,"ly_do":ly_do}
    save_phase()
    emb=discord.Embed(title=tieu,color=mau,timestamp=datetime.now())
    emb.set_thumbnail(url=mem.display_avatar.url)
    emb.add_field(name="👤 Thành viên",value=f"{mem.mention}\n`{mem.display_name}`",inline=False)
    emb.add_field(name="🏷️ Trạng thái",value=role.mention,inline=True)
    emb.add_field(name="👮 Người duyệt",value=i.user.mention,inline=True)
    emb.add_field(name="📝 Lý do",value=f"`{ly_do}`",inline=False)
    await i.response.send_message(emb)

@tree.command(name="theonganh", description="Xem thẻ cấp bậc đào tạo")
@app_commands.describe(nguoi="Thành viên")
async def theonganh(i, nguoi: discord.Member=None):
    await log_cmd(i,"theonganh")
    nguoi=nguoi or i.user
    d=phase_data.get(str(nguoi.id),{"ten":nguoi.display_name,"cap_cu":"Không có","cap_moi":"Chưa đăng ký","ngay":"---","nguoi_duyet":"---"})
    emb=discord.Embed(title="🎖️ THẺ NGÀNH - VMNB",color=discord.Color.teal(),timestamp=datetime.now())
    emb.set_thumbnail(url=nguoi.display_avatar.url)
    emb.add_field(name="Họ & Tên",value=f"`{d['ten']}`",inline=False)
    emb.add_field(name="Cấp hiện tại",value=f"`{d['cap_moi']}`",inline=False)
    emb.add_field(name="Trước đó",value=f"`{d['cap_cu']}`",inline=False)
    emb.add_field(name="Cập nhật",value=f"`{d['ngay']}`",inline=False)
    emb.add_field(name="Người duyệt",value=f"`{d['nguoi_duyet']}`",inline=False)
    await i.response.send_message(emb)

@tree.command(name="chambai", description="Chấm bài kiểm tra/đào tạo")
@app_commands.describe(hv="Học viên", ten="Tên bài", link="Link bài làm", d1="Điểm lý thuyết", d2="Thực hành", d3="Thái độ", nhan="Nhận xét")
async def chambai(i, hv: discord.Member, ten: str, link: str, d1: int, d2: int, d3: int, nhan: str="Không có"):
    await log_cmd(i,"chambai")
    if not has_perm(i): return await i.response.send_message("❌ Không đủ quyền!",ephemeral=True)
    if not all(0<=x<=10 for x in [d1,d2,d3]): return await i.response.send_message("⚠️ Điểm từ 0-10!",ephemeral=True)
    tong=d1+d2+d3; xep,mau=("Xuất sắc",0xf1c40f)if tong>=27 else("Tốt",0x2ecc71)if tong>=24 else("Đạt",0x3498db)if tong>=18 else("Chưa đạt",0xe74c3c)
    emb=discord.Embed(title="📝 KẾT QUẢ CHẤM BÀI",color=mau,timestamp=datetime.now())
    emb.set_thumbnail(url=hv.display_avatar.url)
    emb.add_field(name="👤 Học viên",value=f"{hv.mention}\n`{hv.display_name}`",inline=False)
    emb.add_field(name="📌 Bài",value=f"`{ten}`",inline=False)
    emb.add_field(name="🔗 Bài làm",value=f"[Xem bài làm]({link})",inline=False)
    emb.add_field(name="📊 Tổng điểm: {tong}/30 → {xep}",inline=False)
    emb.add_field(name="💬 Nhận xét",value=f"```{nhan}```",inline=False)
    emb.add_field(name="👨‍🏫 Người chấm",value=i.user.mention,inline=True)
    await i.response.send_message(emb)

# === HỆ KINH TẾ ===
def get_balance(uid): return economy.setdefault(str(uid),{"ten":"","tien":1000})

@tree.command(name="vi", description="Xem số dư ví")
@app_commands.describe(nguoi="Thành viên")
async def vi(i, nguoi: discord.Member=None):
    await log_cmd(i,"vi")
    nguoi=nguoi or i.user
    d=get_balance(nguoi.id); d["ten"]=nguoi.display_name; save_econ()
    emb=discord.Embed(title="💳 VÍ THÀNH VIÊN VMNB",color=0xf1c40f,timestamp=datetime.now())
    emb.set_thumbnail(url=nguoi.display_avatar.url)
    emb.add_field(name="Chủ tài khoản",value=f"`{d['ten']}`",inline=False)
    emb.add_field(name="Số dư hiện tại",value=f"`{d['tien']:,} VNĐ`",inline=False)
    await i.response.send_message(emb)

@tree.command(name="chuyentien", description="Chuyển tiền cho người khác")
@app_commands.describe(nguoi_nhan="Người nhận", so="Số tiền")
async def chuyentien(i, nguoi_nhan: discord.Member, so: int):
    await log_cmd(i,"chuyentien")
    if so<=0 or nguoi_nhan==i.user: return await i.response.send_message("⚠️ Số tiền >0, không tự chuyển cho mình!",ephemeral=True)
    gui,nhan=get_balance(i.user.id),get_balance(nguoi_nhan.id)
    if gui["tien"]<so: return await i.response.send_message("❌ Không đủ số dư!",ephemeral=True)
    gui["tien"]-=so; nhan["tien"]+=so; save_econ()
    emb=discord.Embed(title="💸 GIAO DỊCH THÀNH CÔNG",color=0x2ecc71,timestamp=datetime.now())
    emb.add_field(name="Người gửi",value=i.user.mention)
    emb.add_field(name="Người nhận",value=nguoi_nhan.mention)
    emb.add_field(name="Số tiền",value=f"`{so:,} VNĐ`")
    await i.response.send_message(emb)

@tree.command(name="naptien", description="Nạp tiền (Quyền quản lý)")
@app_commands.describe(nguoi="Thành viên", so="Số tiền")
async def naptien(i, nguoi: discord.Member, so: int):
    await log_cmd(i,"naptien")
    if not perm_high(i): return await i.response.send_message("❌ Không đủ quyền!",ephemeral=True)
    if so<=0: return await i.response.send_message("⚠️ Số tiền >0!",ephemeral=True)
    d=get_balance(nguoi.id); d["tien"]+=so; d["ten"]=nguoi.display_name; save_econ()
    await i.response.send_message(f"✅ Nạp thành công `{so:,} VNĐ` cho {nguoi.mention}")

@tree.command(name="ruttien", description="Rút tiền (Quyền quản lý)")
@app_commands.describe(nguoi="Thành viên", so="Số tiền")
async def ruttien(i, nguoi: discord.Member, so: int):
    await log_cmd(i,"ruttien")
    if not perm_high(i): return await i.response.send_message("❌ Không đủ quyền!",ephemeral=True)
    d=get_balance(nguoi.id)
    if so<=0 or d["tien"]<so: return await i.response.send_message("❌ Số tiền không hợp lệ/không đủ dư!",ephemeral=True)
    d["tien"]-=so; d["ten"]=nguoi.display_name; save_econ()
    await i.response.send_message(f"✅ Rút thành công `{so:,} VNĐ` khỏi tài khoản {nguoi.mention}")

@tree.command(name="bxh", description="Bảng xếp hạng tài sản")
async def bxh(i):
    await log_cmd(i,"bxh")
    top=sorted(economy.items(),key=lambda x:x[1].get("tien",0),reverse=True)[:10]
    txt="\n".join(f"`#{n}` {inf.get('ten','Không rõ')}: `{inf.get('tien',0):,} VNĐ`" for n,(uid,inf) in enumerate(top,1)) or "Chưa có dữ liệu"
    emb=discord.Embed(title="🏆 BXH TÀI SẢN VMNB",description=txt,color=0xf1c40f,timestamp=datetime.now())
    await i.response.send_message(emb)

bot.run(TOKEN)
      
