import os
from typing import Optional
import discord
from discord.ext import commands
from discord.commands import Option
import sqlite3
import aiohttp
import hashlib
import time
import json
import urllib.parse

# ================= 配置区域 =================

def load_config(path: Optional[str] = None) -> dict:
    """从配置文件加载设置，默认读取 config.json，可通过环境变量 BOT_CONFIG_PATH 覆盖。"""
    config_path = path or os.getenv("BOT_CONFIG_PATH", "config.json")
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"找不到配置文件: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    required_keys = ["token", "guild_id", "yipay_url", "yipay_pid", "yipay_key", "payment_types"]
    missing = [k for k in required_keys if k not in config]
    if missing:
        raise ValueError(f"配置文件缺少必填字段: {', '.join(missing)}")

    # 标准化 URL，确保以 / 结尾
    yipay_url = config.get("yipay_url", "")
    if not yipay_url.endswith("/"):
        yipay_url = yipay_url + "/"
    config["yipay_url"] = yipay_url

    return config


CONFIG = load_config()

TOKEN = CONFIG["token"]
GUILD_ID = CONFIG["guild_id"]

# 彩虹易支付配置
YIPAY_URL = CONFIG["yipay_url"]
YIPAY_PID = CONFIG["yipay_pid"]
YIPAY_KEY = CONFIG["yipay_key"]

# 支付通道ID (需要在易支付后台查看对应的ID，例如USDT-TRC20可能是 1001)
PAYMENT_TYPES = CONFIG["payment_types"]

# 可选回调与数据库配置
NOTIFY_URL = CONFIG.get("notify_url", "http://localhost/notify")
RETURN_URL = CONFIG.get("return_url", "http://localhost/return")
DB_PATH = CONFIG.get("database", "bot_data.db")

# ================= 数据库初始化 =================
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# 创建套餐表
c.execute('''CREATE TABLE IF NOT EXISTS plans
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT,
              price REAL,
              role_id INTEGER,
              duration_months INTEGER)''') # duration_months: -1 代表永久

# 创建订单表
c.execute('''CREATE TABLE IF NOT EXISTS orders
             (order_id TEXT PRIMARY KEY,
              user_id INTEGER,
              plan_id INTEGER,
              status TEXT,
              created_at INTEGER)''')

# 创建订阅表（用于到期管理）
c.execute('''CREATE TABLE IF NOT EXISTS subscriptions
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER,
              role_id INTEGER,
              plan_id INTEGER,
              expire_date INTEGER,
              created_at INTEGER)''') # expire_date: -1 代表永久

conn.commit()

# ================= 易支付工具类 =================
class YiPay:
    @staticmethod
    def generate_sign(params, key):
        # 易支付签名算法：按键排序，拼接 key=value&...&key=KEY
        sorted_keys = sorted(params.keys())
        sign_str = ""
        for k in sorted_keys:
            if params[k] != "" and k != "sign" and k != "sign_type":
                sign_str += f"{k}={params[k]}&"
        sign_str = sign_str[:-1] + key
        return hashlib.md5(sign_str.encode('utf-8')).hexdigest()

    @staticmethod
    async def create_order(trade_no, name, money, type_code):
        params = {
            "pid": YIPAY_PID,
            "type": type_code,
            "out_trade_no": trade_no,
            "notify_url": NOTIFY_URL, # 机器人通常无公网IP，这里仅作占位
            "return_url": RETURN_URL,
            "name": name,
            "money": f"{money:.2f}",
            "sitename": "Discord Bot"
        }
        params["sign"] = YiPay.generate_sign(params, YIPAY_KEY)
        params["sign_type"] = "MD5"
        
        # 易支付通常是POST表单或GET跳转，这里我们构造支付链接
        # 很多易支付支持直接GET请求获取支付页，或者返回JSON
        # 为了兼容性，我们尝试请求 API 获取跳转链接，如果API不支持，直接拼接URL
        
        # 方法1: 拼接URL让用户跳转 (最通用)
        query_string = urllib.parse.urlencode(params)
        pay_url = f"{YIPAY_URL}submit.php?{query_string}"
        return pay_url

    @staticmethod
    async def check_order_status(trade_no):
        # 查询订单状态
        params = {
            "act": "order",
            "pid": YIPAY_PID,
            "out_trade_no": trade_no,
            "key": YIPAY_KEY
        }
        async with aiohttp.ClientSession() as session:
            try:
                # 注意：不同易支付程序API路径可能不同，常见是 /api.php
                async with session.get(f"{YIPAY_URL}api.php", params=params) as resp:
                    data = await resp.json(content_type=None)
                    # 状态 1 表示支付成功
                    if data.get('code') == 1 and data.get('status') == 1:
                        return True
                    return False
            except Exception as e:
                print(f"API Error: {e}")
                return False

# ================= Discord Bot 设置 =================
intents = discord.Intents.default()
intents.members = True # 必须开启，用于赋予身份组
bot = discord.Bot(intents=intents)

# ================= UI 交互视图 =================

class PaymentVerifyView(discord.ui.View):
    def __init__(self, trade_no, plan_info, user_id):
        super().__init__(timeout=None)
        self.trade_no = trade_no
        self.plan_info = plan_info # (id, name, price, role_id, duration)
        self.user_id = user_id

    @discord.ui.button(label="✅ 我已完成支付", style=discord.ButtonStyle.success)
    async def check_payment(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.defer()
        
        # 检查支付状态
        is_paid = await YiPay.check_order_status(self.trade_no)
        
        if is_paid:
            # 检查订单是否已经处理过
            c.execute("SELECT status FROM orders WHERE order_id = ?", (self.trade_no,))
            order = c.fetchone()
            if order and order[0] == 'paid':
                await interaction.followup.send("⚠️ 该订单已经处理过了。", ephemeral=True)
                return
            
            # 支付成功逻辑
            role_id = self.plan_info[3]
            guild = interaction.guild
            role = guild.get_role(role_id)
            member = guild.get_member(self.user_id)
            
            if role and member:
                try:
                    await member.add_roles(role)
                    
                    # 更新数据库订单状态
                    c.execute("UPDATE orders SET status = 'paid' WHERE order_id = ?", (self.trade_no,))
                    
                    # 计算过期时间并存入订阅表
                    plan_id = self.plan_info[0]
                    duration = self.plan_info[4]
                    current_time = int(time.time())
                    
                    if duration == -1:
                        expire_date = -1  # 永久
                    else:
                        # 计算过期时间戳（duration个月后）
                        expire_date = current_time + (duration * 30 * 24 * 60 * 60)  # 简单按30天/月计算
                    
                    c.execute("INSERT INTO subscriptions (user_id, role_id, plan_id, expire_date, created_at) VALUES (?, ?, ?, ?, ?)",
                              (self.user_id, role_id, plan_id, expire_date, current_time))
                    
                    conn.commit()
                    
                    await interaction.followup.send(f"🎉 **支付成功！** 您已自动获得 {role.mention} 身份组！", ephemeral=True)
                    # 禁用按钮
                    button.disabled = True
                    button.label = "已开通"
                    await interaction.edit_original_response(view=self)
                except Exception as e:
                    await interaction.followup.send(f"⚠️ 支付成功，但在赋予身份组时出错：{e}，请联系管理员。", ephemeral=True)
            else:
                await interaction.followup.send("⚠️ 未找到对应的身份组或用户，请联系管理员。", ephemeral=True)
        else:
            await interaction.followup.send("⏳ 尚未查询到支付成功记录，请支付稍等片刻后再试。", ephemeral=True)

class NetworkSelectView(discord.ui.View):
    def __init__(self, plan_info):
        super().__init__(timeout=120)
        self.plan_info = plan_info # (id, name, price, role_id, duration)

    async def generate_payment(self, interaction, network_name, type_code):
        user_id = interaction.user.id
        plan_name = self.plan_info[1]
        price = self.plan_info[2]
        
        # 生成订单号
        trade_no = f"ORDER_{int(time.time())}_{user_id}"
        
        # 存入数据库
        c.execute("INSERT INTO orders VALUES (?, ?, ?, ?, ?)", 
                  (trade_no, user_id, self.plan_info[0], 'pending', int(time.time())))
        conn.commit()
        
        # 获取支付链接
        pay_url = await YiPay.create_order(trade_no, f"Plan-{plan_name}", price, type_code)
        
        embed = discord.Embed(title="💳 订单已创建", description=f"请点击下方链接支付 **{price} USDT**", color=0x00ff00)
        embed.add_field(name="套餐", value=plan_name, inline=True)
        embed.add_field(name="网络", value=network_name, inline=True)
        embed.add_field(name="🔗 支付链接", value=f"[👉 点击前往支付]({pay_url})", inline=False)
        embed.set_footer(text='支付完成后，请务必点击下方的"我已完成支付"按钮')
        
        await interaction.response.send_message(embed=embed, view=PaymentVerifyView(trade_no, self.plan_info, user_id), ephemeral=True)

    @discord.ui.button(label="USDT - TRC20", style=discord.ButtonStyle.primary, emoji="🔗")
    async def trc20_pay(self, button, interaction):
        await self.generate_payment(interaction, "TRC20", PAYMENT_TYPES["USDT-TRC20"])

    @discord.ui.button(label="USDT - BEP20", style=discord.ButtonStyle.primary, emoji="🔗")
    async def bep20_pay(self, button, interaction):
        await self.generate_payment(interaction, "BEP20", PAYMENT_TYPES["USDT-BEP20"])

class PlanSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        # 从数据库加载按钮
        self.reload_buttons()

    def reload_buttons(self):
        self.clear_items()
        c.execute("SELECT * FROM plans")
        plans = c.fetchall()
        
        for plan in plans:
            # plan: (id, name, price, role_id, duration)
            label = f"{plan[1]} ({plan[2]} USDT)"
            custom_id = f"plan_{plan[0]}"
            
            button = discord.ui.Button(
                label=label,
                style=discord.ButtonStyle.secondary,
                custom_id=custom_id,
                emoji="💎"
            )
            # 绑定回调
            button.callback = self.create_callback(plan)
            self.add_item(button)

    def create_callback(self, plan):
        async def callback(interaction: discord.Interaction):
            # 弹出选择网络
            await interaction.response.send_message(
                f"您选择了 **{plan[1]}**，请选择支付网络：", 
                view=NetworkSelectView(plan), 
                ephemeral=True
            )
        return callback

# ================= 斜杠指令 (Admin) =================

@bot.slash_command(guild_ids=[GUILD_ID], description="添加或更新会员套餐")
@commands.has_permissions(administrator=True)
async def set_plan(
    ctx, 
    name: Option(str, "套餐名称 (如: 月会员)"),
    price: Option(float, "价格 (USDT)"),
    role: Option(discord.Role, "对应的身份组"),
    duration: Option(int, "时长(月)，输入 -1 代表永久")
):
    # 检查是否已存在同名套餐，存在则更新，不存在则插入
    c.execute("SELECT id FROM plans WHERE name = ?", (name,))
    data = c.fetchone()
    if data:
        c.execute("UPDATE plans SET price=?, role_id=?, duration_months=? WHERE name=?", 
                  (price, role.id, duration, name))
        action = "更新"
    else:
        c.execute("INSERT INTO plans (name, price, role_id, duration_months) VALUES (?, ?, ?, ?)",
                  (name, price, role.id, duration))
        action = "添加"
    conn.commit()
    await ctx.respond(f"✅ 已{action}套餐 **{name}**: {price} USDT -> {role.mention}", ephemeral=True)

@bot.slash_command(guild_ids=[GUILD_ID], description="发送充值面板")
@commands.has_permissions(administrator=True)
async def send_panel(ctx):
    # 构建主 Embed (价格表)
    embed_main = discord.Embed(
        title="LEVEL UP YOUR TRADING 🚀",
        description="提升您的交易体验，获取独家内幕与分析。",
        color=0x2b2d31
    )
    
    # 动态从数据库读取价格显示在 Embed 中
    c.execute("SELECT name, price, duration_months FROM plans")
    plans = c.fetchall()
    price_text = ""
    for p in plans:
        duration = p[2]
        if duration == -1:
            duration_str = "/永久"
        elif duration == 1:
            duration_str = "/月"
        elif duration == 12:
            duration_str = "/年"
        else:
            duration_str = f"/{duration}个月"
            
        price_text += f"**{p[0]}**：{p[1]} USDT{duration_str}\n"
    
    if not price_text:
        price_text = "暂无套餐配置，请使用管理员指令配置。"

    embed_main.add_field(name="💰 会员价格", value=price_text, inline=False)
    embed_main.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/3135/3135715.png") # 示例图标

    # 构建副 Embed (流程说明) - 这就是你要的"二次嵌入"效果，其实是第二个Embed
    embed_steps = discord.Embed(
        title="🎯 快速开通步骤",
        description=(
            "✅ **选套餐 + 网络**\n"
            "💳 **点击前往支付**\n"
            "🔗 **完成支付**\n"
            "🎉 **自动开通会员**"
        ),
        color=0x5865F2
    )
    
    view = PlanSelectView()
    # 同时发送两个 Embeds
    await ctx.send(embeds=[embed_main, embed_steps], view=view)
    await ctx.respond("✅ 面板已发送", ephemeral=True)

@bot.slash_command(guild_ids=[GUILD_ID], description="删除套餐")
@commands.has_permissions(administrator=True)
async def delete_plan(
    ctx,
    name: Option(str, "要删除的套餐名称")
):
    c.execute("SELECT id FROM plans WHERE name = ?", (name,))
    data = c.fetchone()
    if data:
        c.execute("DELETE FROM plans WHERE name = ?", (name,))
        conn.commit()
        await ctx.respond(f"✅ 已删除套餐 **{name}**", ephemeral=True)
    else:
        await ctx.respond(f"❌ 未找到套餐 **{name}**", ephemeral=True)

@bot.slash_command(guild_ids=[GUILD_ID], description="查看所有套餐")
@commands.has_permissions(administrator=True)
async def list_plans(ctx):
    c.execute("SELECT name, price, duration_months FROM plans")
    plans = c.fetchall()
    if plans:
        plan_list = "\n".join([f"**{p[0]}**: {p[1]} USDT (时长: {p[2]}个月)" for p in plans])
        await ctx.respond(f"📋 **当前套餐列表：**\n{plan_list}", ephemeral=True)
    else:
        await ctx.respond("❌ 暂无套餐配置", ephemeral=True)

# ================= 定时任务：检查到期订阅 =================
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    # 重启后保持按钮监听状态
    bot.add_view(PlanSelectView())
    
    # 启动定时任务检查到期订阅
    check_expired_subscriptions.start()

@bot.tasks.loop(hours=24)  # 每24小时检查一次
async def check_expired_subscriptions():
    """检查并移除过期的订阅"""
    current_time = int(time.time())
    c.execute("SELECT user_id, role_id, id FROM subscriptions WHERE expire_date != -1 AND expire_date < ?", (current_time,))
    expired = c.fetchall()
    
    for user_id, role_id, sub_id in expired:
        # 尝试从所有服务器中移除角色
        for guild in bot.guilds:
            member = guild.get_member(user_id)
            role = guild.get_role(role_id)
            if member and role:
                try:
                    await member.remove_roles(role)
                    print(f"已移除用户 {user_id} 在服务器 {guild.id} 的身份组 {role_id}")
                except Exception as e:
                    print(f"移除身份组失败: {e}")
        
        # 从数据库删除过期订阅记录
        c.execute("DELETE FROM subscriptions WHERE id = ?", (sub_id,))
    
    conn.commit()
    print(f"检查完成，处理了 {len(expired)} 个过期订阅")

@check_expired_subscriptions.before_loop
async def before_check_expired():
    await bot.wait_until_ready()

if __name__ == "__main__":
    bot.run(TOKEN)

