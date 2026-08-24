import os
import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask
from threading import Thread

# 1. Khởi tạo Web Server cho Render
app = Flask('')

@app.route('/')
def home():
    return "Bot đang chạy ổn định!"

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ID của Role được miễn nhiễm
IMMUNE_ROLE_ID = 1540185126464393267

# 2. Cấu hình Discord Bot
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.guilds = True          # Cần thiết để quản lý kênh
        intents.guild_messages = True  # Cần thiết để gửi tin nhắn
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("Đã đồng bộ lệnh Slash!")

bot = MyBot()

@bot.event
async def on_ready():
    print(f'Đã kết nối thành công: {bot.user}')

# --- CÁC LỆNH SLASH COMMAND ---

# Lệnh mẫu kiểm tra bot
@bot.tree.command(name="ping", description="Kiểm tra độ trễ của Bot")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"Pong! Độ trễ hiện tại là {latency}ms.")

# LỆNH LOCK ALL KÊNH
@bot.tree.command(name="lockall", description="Khóa toàn bộ kênh chat (trừ Role miễn nhiễm)")
@app_commands.checks.has_permissions(administrator=True) # Chỉ Admin mới dùng được lệnh này
async def lock_all(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True) # Tránh bot bị quá hạn 3 giây khi xử lý nhiều kênh
    
    guild = interaction.guild
    immune_role = guild.get_role(IMMUNE_ROLE_ID)
    
    # Duyệt qua tất cả các kênh văn bản trong server
    for channel in guild.text_channels:
        # Khóa quyền gửi tin nhắn của mọi người (@everyone)
        await channel.set_permissions(guild.default_role, send_messages=False)
        
        # Nếu tìm thấy Role miễn nhiễm, giữ nguyên hoặc cho phép họ nhắn tin
        if immune_role:
            await channel.set_permissions(immune_role, send_messages=True)
            
    await interaction.followup.send("Đã thực hiện khóa toàn bộ kênh thành công!", ephemeral=True)
    # Gửi thông báo công khai tại kênh dùng lệnh
    await interaction.channel.send("Chế độ bảo mật an ninh cấp cao nhất đã được kích hoạt.")

# LỆNH UNLOCK ALL KÊNH
@bot.tree.command(name="unlockall", description="Mở khóa toàn bộ kênh chat")
@app_commands.checks.has_permissions(administrator=True)
async def unlock_all(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    guild = interaction.guild
    
    for channel in guild.text_channels:
        # Đặt lại quyền gửi tin nhắn về trạng thái mặc định (None) hoặc cho phép (True)
        await channel.set_permissions(guild.default_role, send_messages=None)
        
    await interaction.followup.send("Đã thực hiện mở khóa toàn bộ kênh thành công!", ephemeral=True)
    # Gửi thông báo công khai tại kênh dùng lệnh
    await interaction.channel.send("Đã gỡ bảo mật")

# Xử lý lỗi nếu người dùng không phải Admin mà cố tình xài lệnh
@lock_all.error
@unlock_all.error
async def admin_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("Bạn không có quyền Administrator để dùng lệnh này!", ephemeral=True)

# Khởi chạy
if __name__ == "__main__":
    keep_alive()
    token = os.environ.get("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("Lỗi: Không tìm thấy DISCORD_TOKEN.")
                  
# 1. Khởi tạo Web Server cho Render ẩn
app = Flask('')

@app.route('/')
def home():
    return "Bot đang chạy ổn định!"
...
def keep_alive():
    t = Thread(target=run)
    t.start()
    
