import discord
import aiohttp
import random
from discord.ext import commands
from datetime import datetime, timezone, timedelta
from flask import Flask
from threading import Thread

# 1. HỆ THỐNG GIỮ BOT ONLINE (KEEP ALIVE)
app = Flask('')

@app.route('/')
def home():
    return "Bot dang chay online!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# 2. KHỞI TẠO INTENTS & BOT
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=".", intents=intents, help_command=None)

# DATABASE LƯU DỮ LIỆU
blacklist_db = {}
user_messages = {}
rollcall_count = 0
bank_db = {}

def get_user_data(user_id):
    if user_id not in bank_db:
        bank_db[user_id] = {"cash": 1000, "bank": 0, "loan": 0}
    return bank_db[user_id]

# --- NÚT BẤM XEM HỒ SƠ ROBLOX ---
class ProfileButton(discord.ui.View):
    def __init__(self, user_id):
        super().__init__()
        self.add_item(discord.ui.Button(
            label="Xem Hồ Sơ Roblox", 
            url=f"https://www.roblox.com/users/{user_id}/profile",
            style=discord.ButtonStyle.link
        ))

# --- NÚT BẤM ĐIỂM DANH ---
class RollCallView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.attended_users = []

    @discord.ui.button(label="✋ Bấm Vào Đây Để Điểm Danh", style=discord.ButtonStyle.success)
    async def roll_call(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id in self.attended_users:
            await interaction.response.send_message("❌ Bạn đã điểm danh trước đó rồi!", ephemeral=True)
        else:
            self.attended_users.append(interaction.user.id)
            await interaction.response.send_message(f"✅ **{interaction.user.display_name}** đã điểm danh thành công!", ephemeral=False)

# --- EVENT KHI BOT SẴN SÀNG & CHỐNG SPAM ---
@bot.event
async def on_ready():
    print(f"🤖 Bot {bot.user.name} đã sẵn sàng!")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    user_id = message.author.id
    now = datetime.now(timezone.utc)
    
    if user_id not in user_messages:
        user_messages[user_id] = []

    user_messages[user_id] = [
        msg_time for msg_time in user_messages[user_id] 
        if (now - msg_time).total_seconds() < 300
    ]

    user_messages[user_id].append(now)

    if len(user_messages[user_id]) > 5:
        user_messages[user_id] = [] 
        await message.channel.send(
            f"⚠️ **Cảnh báo spawm tin nhắn**\n"
            f"Yêu cầu {message.author.mention} bạn hãy giữ bình tĩnh\n"
            f"Thực hiện cách ly 5 phút vì spawm quá 5 tin nhắn trên 5 phút"
        )
        try:
            await message.author.timeout(timedelta(minutes=5), reason="Spam tin nhắn")
        except Exception as e:
            print(f"Không thể timeout {message.author.name}: {e}")

    await bot.process_commands(message)

# --- LỆNH HELP TỰ TẠO ---
@bot.command(name="help", aliases=["trogiup", "menu"])
async def help_command(ctx):
    embed = discord.Embed(
        title="📜 DANH SÁCH LỆNH HỆ THỐNG",
        description="Dưới đây là toàn bộ lệnh hiện có của bot:",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="🏦 **NGÂN HÀNG BLOX**",
        value="• `.sodu`: Xem số dư tiền mặt & tiền ảo\n"
              "• `.nap [tiền/all]`: Nạp tiền mặt vào tài khoản\n"
              "• `.rut [tiền/all]`: Rút tiền ảo thành tiền mặt\n"
              "• `.chuyen @user [số_tiền]`: Chuyển tiền ảo\n"
              "• `.vay [số_tiền]`: Vay ngân hàng (lãi 10%)\n"
              "• `.trano`: Trả khoản nợ đã vay\n"
              "• `.addmoney @user [tiền] [cash/bank]`: Admin cấp tiền",
        inline=False
    )

    embed.add_field(
        name="🎲 **MINI GAME & QUẢN LÝ**",
        value="• `.taixiu [tai/xiu] [tiền/all]`: Cược tài xỉu bằng tiền mặt\n"
              "• `.diemdanh`: Phát thông báo Active Check\n"
              "• `.tracuu [Tên_Roblox]`: Kiểm tra hồ sơ & Blacklist\n"
              "• `.blacklist`: Đăng hồ sơ cấm (Admin)",
        inline=False
    )
    
    embed.set_footer(text=f"Yêu cầu bởi: {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
    await ctx.send(embed=embed)

# --- LỆNH ĐIỂM DANH ---
@bot.command(name="diemdanh")
@commands.has_permissions(administrator=True)
async def diemdanh(ctx):
    global rollcall_count
    rollcall_count += 1
    content_text = f"# ACTIVE CHECK #{rollcall_count}\nTICK ĐỂ KIỂM TRA HOẠT ĐỘNG\n@everyone"
    view = RollCallView()
    await ctx.send(content=content_text, view=view)

# --- NGÂN HÀNG TRUNG ƯƠNG BLOX ---
@bot.command(name="sodu", aliases=["bal", "money", "vi"])
async def sodu(ctx, member: discord.Member = None):
    target = member or ctx.author
    data = get_user_data(target.id)
    embed = discord.Embed(title="🏦 NGÂN HÀNG TRUNG ƯƠNG BLOX", description=f"Hồ sơ tài chính của **{target.display_name}**", color=discord.Color.gold())
    embed.add_field(name="💵 Tiền mặt:", value=f"`{data['cash']:,}` $", inline=True)
    embed.add_field(name="💳 Tiền ảo:", value=f"`{data['bank']:,}` $", inline=True)
    embed.add_field(name="⚠️ Khoản vay:", value=f"`{data['loan']:,}` $", inline=False)
    embed.set_thumbnail(url=target.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command(name="nap", aliases=["gui", "dep"])
async def nap(ctx, amount: str):
    data = get_user_data(ctx.author.id)
    val = data["cash"] if amount.lower() == "all" else int(amount) if amount.isdigit() else 0
    if val <= 0 or data["cash"] < val:
        await ctx.send("❌ Số tiền không hợp lệ hoặc tiền mặt không đủ!")
        return
    data["cash"] -= val
    data["bank"] += val
    await ctx.send(f"✅ Đã nạp `{val:,}` $ tiền mặt vào ngân hàng!")

@bot.command(name="rut", aliases=["with"])
async def rut(ctx, amount: str):
    data = get_user_data(ctx.author.id)
    val = data["bank"] if amount.lower() == "all" else int(amount) if amount.isdigit() else 0
    if val <= 0 or data["bank"] < val:
        await ctx.send("❌ Số tiền không hợp lệ hoặc tiền ảo không đủ!")
        return
    data["bank"] -= val
    data["cash"] += val
    await ctx.send(f"✅ Đã rút `{val:,}` $ tiền ảo thành tiền mặt!")

@bot.command(name="chuyen", aliases=["pay"])
async def chuyen(ctx, member: discord.Member, amount: int):
    if member.id == ctx.author.id or amount <= 0:
        await ctx.send("❌ Lệnh chuyển tiền không hợp lệ!")
        return
    sender, receiver = get_user_data(ctx.author.id), get_user_data(member.id)
    if sender["bank"] < amount:
        await ctx.send("❌ Số dư tiền ảo không đủ!")
        return
    sender["bank"] -= amount
    receiver["bank"] += amount
    await ctx.send(f"💸 Đã chuyển `{amount:,}` $ tiền ảo cho **{member.display_name}**!")

@bot.command(name="vay")
async def vay(ctx, amount: int):
    data = get_user_data(ctx.author.id)
    if amount <= 0 or data["loan"] > 0:
        await ctx.send("❌ Bạn không đủ điều kiện vay hoặc chưa trả xong nợ cũ!")
        return
    data["bank"] += amount
    data["loan"] += int(amount * 1.1)
    await ctx.send(f"🏦 Đã duyệt khoản vay `{amount:,}` $. Cần trả: `{data['loan']:,}` $ (10% lãi).")

@bot.command(name="trano", aliases=["payloan"])
async def trano(ctx):
    data = get_user_data(ctx.author.id)
    if data["loan"] == 0 or data["bank"] < data["loan"]:
        await ctx.send("❌ Không có nợ hoặc tiền ảo không đủ trả!")
        return
    data["bank"] -= data["loan"]
    data["loan"] = 0
    await ctx.send("🎉 Bạn đã trả xong khoản nợ!")

@bot.command(name="addmoney", aliases=["setmoney"])
@commands.has_permissions(administrator=True)
async def addmoney(ctx, member: discord.Member, amount: int, type_money: str = "cash"):
    data = get_user_data(member.id)
    if type_money.lower() in ["bank", "ao", "tienao"]:
        data["bank"] += amount
    else:
        data["cash"] += amount
    await ctx.send(f"👑 **ADMIN:** Đã cấp `{amount:,}` $ cho **{member.display_name}**!")

@bot.command(name="taixiu", aliases=["tx"])
async def taixiu(ctx, choice: str, amount: str):
    data = get_user_data(ctx.author.id)
    bet = data["cash"] if amount.lower() == "all" else int(amount) if amount.isdigit() else 0
    if choice.lower() not in ["tai", "tài", "xiu", "xỉu"] or bet <= 0 or data["cash"] < bet:
        await ctx.send("❌ Đặt cược không hợp lệ!")
        return
    d1, d2, d3 = random.randint(1, 6), random.randint(1, 6), random.randint(1, 6)
    total = d1 + d2 + d3
    res = "tai" if total >= 11 else "xiu"
    user_choice = "tai" if choice.lower() in ["tai", "tài"] else "xiu"
    
    if user_choice == res:
        data["cash"] += bet
        await ctx.send(f"🎲 `{d1}`-`{d2}`-`{d3}` ({total}) -> **{res.upper()}**\n🎉 Bạn thắng `{bet:,}` $ tiền mặt!")
    else:
        data["cash"] -= bet
        await ctx.send(f"🎲 `{d1}`-`{d2}`-`{d3}` ({total}) -> **{res.upper()}**\n💸 Bạn thua `{bet:,}` $ tiền mặt!")

# --- BLACKLIST & ROBLOX ---
@bot.command(name="blacklist", aliases=["bl"])
@commands.has_permissions(administrator=True)
async def blacklist(ctx, roblox_user: str, roblox_id: str, rank: str, punishment: str, approved_by: str, date_range: str, *, reason: str):
    blacklist_db[str(roblox_id)] = {"user": roblox_user, "reason": reason, "punishment": punishment, "approved_by": approved_by, "date": date_range}
    blacklist_db[roblox_user.lower()] = blacklist_db[str(roblox_id)]
    await ctx.send(f"**Username:** {roblox_user}\n**ID:** {roblox_id}\n**Reason:** {reason}\n**Punishment:** {punishment}")

@bot.command(name="tracuu", aliases=["checkrbx", "rbx"])
async def tracuu(ctx, username: str):
    async with aiohttp.ClientSession() as session:
        async with session.post("https://users.roblox.com/v1/usernames/users", json={"usernames": [username], "excludeBannedUsers": False}) as resp:
            data = await resp.json()
            if not data.get("data"):
                await ctx.send(f"❌ Không thấy tài khoản `{username}`!")
                return
            user_id = str(data["data"][0]["id"])
    bl_data = blacklist_db.get(user_id) or blacklist_db.get(username.lower())
    embed = discord.Embed(title=f"Hồ Sơ Roblox: {username}", color=discord.Color.red() if bl_data else discord.Color.green())
    embed.add_field(name="Trạng thái", value="☠️ Blacklist" if bl_data else "✅ Sạch", inline=False)
    await ctx.send(embed=embed, view=ProfileButton(user_id))

# CHẠY BOT
keep_alive()
bot.run("MTUwNDQ0Njg0NDM4MDUxNjQyMg.G7UE0M.-s816mIZnDhZ9kx5S9mBbY7KMtXhhWNIvocpRA	")
