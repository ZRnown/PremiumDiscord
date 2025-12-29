import os
from typing import Optional, Dict
from datetime import datetime
import discord
from discord.ext import commands, tasks

# 兼容不同版本的discord.py
from discord.ext import commands as ext_commands

# 先设置默认值，避免NameError
ENABLE_PRIVILEGED_INTENTS = False  # 默认禁用privileged intents

# 动态检测需要的参数
DISCORD_PY_VERSION = 1
intents = None

try:
    # 首先检查是否有Intents类
    test_intents = discord.Intents.default()
    intents_available = True
except AttributeError:
    intents_available = False

# Bot创建逻辑（将在CONFIG加载后重新配置）
bot = None

def create_bot():
    """创建bot实例，根据配置决定是否启用privileged intents"""
    global bot, intents, DISCORD_PY_VERSION

    try:
        # 尝试discord.py 2.0+风格
        if intents_available:
            intents = discord.Intents.default()
            if ENABLE_PRIVILEGED_INTENTS:
                intents.members = True  # 只有在明确启用时才设置privileged intent
            else:
                intents.members = False
            bot = discord.Bot(intents=intents)
            DISCORD_PY_VERSION = 2
        else:
            raise AttributeError("No Intents available")
    except AttributeError:
        # 回退到commands.Bot
        try:
            if intents_available:
                intents = discord.Intents.default()
                if ENABLE_PRIVILEGED_INTENTS:
                    intents.members = True
                else:
                    intents.members = False  # 默认禁用privileged intents
                bot = ext_commands.Bot(command_prefix='!', intents=intents)
                DISCORD_PY_VERSION = 1.5
            else:
                # 最老的版本
                bot = ext_commands.Bot(command_prefix='!')
                DISCORD_PY_VERSION = 1
        except TypeError:
            # 如果还是失败，尝试最基本的版本
            bot = ext_commands.Bot(command_prefix='!')
            intents = None
            DISCORD_PY_VERSION = 1

# 先创建基本的bot（稍后会重新配置）
create_bot()

# 强制要求Py-cord以支持slash commands
try:
    # 尝试使用Py-cord的语法
    test_command = bot.slash_command(guild_ids=[123456789])  # 测试guild_ids
    HAS_SLASH_COMMANDS = True
    PY_CORD_MODE = True
    print("✅ 检测到Py-cord，支持完整的slash commands和UI组件")
except (AttributeError, TypeError):
    # 不支持Py-cord，强制报错
    HAS_SLASH_COMMANDS = False
    PY_CORD_MODE = False
    print("❌ 未检测到Py-cord！")
    print("💡 Slash commands需要Py-cord库支持")
    print("请运行以下命令安装Py-cord：")
    print("pip uninstall discord.py -y")
    print("pip install py-cord>=2.4.0")
    print("然后重新运行: python3 main.py")

    # 只有在实际运行时才退出，在导入测试时不退出
    import sys
    if __name__ == "__main__":
        exit(1)  # 强制退出，要求用户安装Py-cord

def slash_command(*args, **kwargs):
    """Py-cord slash command装饰器"""
    def decorator(func):
        if PY_CORD_MODE and HAS_SLASH_COMMANDS:
            return bot.slash_command(*args, **kwargs)(func)
        else:
            print(f"❌ 无法注册slash command - 需要Py-cord支持")
            return func
    return decorator

# UI组件兼容性处理
try:
    import discord.ui as ui
    HAS_UI_COMPONENTS = True
except ImportError:
    HAS_UI_COMPONENTS = False
    # 创建兼容性类
    class MockUI:
        class View:
            def __init__(self, *args, **kwargs):
                pass
        class Select:
            def __init__(self, *args, **kwargs):
                pass
    ui = MockUI()

# SelectOption兼容性
try:
    SelectOption = discord.SelectOption
except AttributeError:
    # 创建兼容性类
    class SelectOption:
        def __init__(self, label, value, description=None, default=False):
            self.label = label
            self.value = value
            self.description = description
            self.default = default

# 移除不再需要的Option类

    def __repr__(self):
        return repr(self.type_hint)
import sqlite3
import aiohttp
from aiohttp import web
import hashlib
import time
import json
import urllib.parse
from urllib.parse import urlparse, urlunparse

# ================= 配置区域 =================

def fetch_plans():
    c.execute("SELECT * FROM plans")
    return c.fetchall()

def fetch_plan_by_name(name: str):
    c.execute("SELECT * FROM plans WHERE name = ?", (name,))
    return c.fetchone()

def build_trade_no(user_id: int, prefix: str = "ORD") -> str:
    """生成不超过32字符的订单号，前缀+时间戳+用户ID后6位"""
    ts = int(time.time())
    suffix = str(user_id % 1_000_000).zfill(6)
    trade_no = f"{prefix}{ts}{suffix}"
    return trade_no[:32]

async def fulfill_order(trade_no: str):
    """在支付确认后为用户发放身份组并写入订阅"""
    c.execute("SELECT user_id, plan_id FROM orders WHERE order_id = ?", (trade_no,))
    order = c.fetchone()
    if not order:
        print(f"[Webhook] 未找到订单 {trade_no}")
        return
    user_id, plan_id = order
    c.execute("SELECT id, name, price, role_id, duration_months FROM plans WHERE id = ?", (plan_id,))
    plan = c.fetchone()
    if not plan:
        print(f"[Webhook] 未找到订单对应套餐 {plan_id}")
        return
    _, _, _, role_id, duration = plan

    guild = bot.get_guild(GUILD_ID)
    if not guild:
        print("[Webhook] 未找到指定的 Guild")
        return
    member = guild.get_member(user_id)
    role = guild.get_role(role_id)
    if not member or not role:
        print(f"[Webhook] 成员或角色缺失 user={user_id} role={role_id}")
        return

    try:
        await member.add_roles(role)
    except Exception as e:
        print(f"[Webhook] 赋予角色失败: {e}")
        return

    current_time = int(time.time())
    expire_date = -1 if duration == -1 else current_time + (duration * 30 * 24 * 60 * 60)
    c.execute("INSERT INTO subscriptions (user_id, role_id, plan_id, expire_date, created_at) VALUES (?, ?, ?, ?, ?)",
              (user_id, role_id, plan_id, expire_date, current_time))
    conn.commit()
    print(f"[Webhook] 已为用户 {user_id} 发放角色 {role_id}，订单 {trade_no}")

def load_config(path: Optional[str] = None) -> dict:
    """从配置文件加载设置，默认读取 config.json，可通过环境变量 BOT_CONFIG_PATH 覆盖。"""
    config_path = path or os.getenv("BOT_CONFIG_PATH", "config.json")
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"找不到配置文件: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    # 根据支付平台确定必填字段
    payment_platform = config.get("payment_platform", "epusdt")

    if payment_platform == "yipay":
        required_keys = [
            "token",
            "guild_id",
            "yipay_url",
            "yipay_pid",
            "yipay_key",
            "payment_methods"
        ]
    elif payment_platform == "epusdt":
        required_keys = [
            "token",
            "guild_id",
            "epusdt_url",
            "epusdt_token",
            "payment_methods"
        ]
    else:
        raise ValueError(f"不支持的支付平台: {payment_platform}")

    missing = [k for k in required_keys if k not in config]
    if missing:
        raise ValueError(f"配置文件缺少必填字段: {', '.join(missing)}")

    # 标准化 URL，确保以 / 结尾
    if payment_platform == "yipay":
        yipay_url = config.get("yipay_url", "")
        if not yipay_url.endswith("/"):
            yipay_url = yipay_url + "/"
        config["yipay_url"] = yipay_url
    elif payment_platform == "epusdt":
        epusdt_url = config.get("epusdt_url", "")
        if not epusdt_url.endswith("/"):
            epusdt_url = epusdt_url + "/"
        config["epusdt_url"] = epusdt_url

    return config


CONFIG = load_config()

TOKEN = CONFIG["token"]
GUILD_ID = CONFIG["guild_id"]
PAYMENT_PLATFORM = CONFIG.get("payment_platform", "epusdt")
ENABLE_PRIVILEGED_INTENTS = CONFIG.get("enable_privileged_intents", False)
DEFAULT_CURRENCY = CONFIG.get("default_currency", "USDT").upper()

# 使用配置重新创建bot
create_bot()

# 支付平台配置
if PAYMENT_PLATFORM == "yipay":
    YIPAY_URL = CONFIG["yipay_url"]
    YIPAY_PID = CONFIG["yipay_pid"]
    YIPAY_KEY = CONFIG["yipay_key"]
elif PAYMENT_PLATFORM == "epusdt":
    EPUSDT_URL = CONFIG["epusdt_url"]
    EPUSDT_TOKEN = CONFIG["epusdt_token"]

# 支付方式映射（显示名 -> 通道代码）
PAYMENT_METHODS: Dict[str, str] = CONFIG["payment_methods"]

# USDT 转 CNY 汇率（用于将 USDT 价格转换为人民币价格）
# 例如：1 USDT = 7.2 CNY，则设置为 7.2
# 如果不设置，默认使用 7.0
USDT_TO_CNY_RATE = CONFIG.get("usdt_to_cny_rate", 7.0)

# 可选回调与数据库配置
RAW_NOTIFY_URL = CONFIG.get("notify_url", "http://localhost/notify")
RETURN_URL = CONFIG.get("return_url", "")
# Webhook 监听端口（可按需放到配置中，这里默认 8080）
WEBHOOK_PORT = CONFIG.get("notify_port", 8080)
DB_PATH = CONFIG.get("database", "bot_data.db")

# 规范化 notify_url，默认补全 /notify
def normalize_notify_url(raw: str) -> str:
    parsed = urlparse(raw)
    scheme = parsed.scheme or "http"
    netloc = parsed.netloc
    path = parsed.path
    if not netloc and parsed.path:
        # 兼容误写成 http://ip:port 这种少了//的情况
        # 重新解析
        reparsed = urlparse(f"http://{raw}")
        netloc = reparsed.netloc
        path = reparsed.path
    if path in ("", "/"):
        path = "/notify"
    normalized = urlunparse((scheme, netloc, path, "", "", ""))
    return normalized

NOTIFY_URL = normalize_notify_url(RAW_NOTIFY_URL)

# ================= 数据库初始化 =================
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# 创建套餐表
c.execute('''CREATE TABLE IF NOT EXISTS plans
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT,
              price REAL,
              currency TEXT DEFAULT 'USDT',
              role_id INTEGER,
              duration_months INTEGER)''') # duration_months: -1 代表永久, currency: 'USDT' 或 'CNY'

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

# 数据库迁移：为plans表添加currency字段
try:
    # 检查currency字段是否存在
    c.execute("PRAGMA table_info(plans)")
    columns = [column[1] for column in c.fetchall()]
    if 'currency' not in columns:
        print("🔄 正在为plans表添加currency字段...")
        c.execute("ALTER TABLE plans ADD COLUMN currency TEXT DEFAULT 'USDT'")
        conn.commit()
        print("✅ 数据库迁移完成")
except Exception as e:
    print(f"⚠️ 数据库迁移检查失败: {e}")

# ================= 支付工具类 =================
class YiPay:
    @staticmethod
    def generate_sign_yipay(params: Dict[str, str], key: str) -> str:
        """易支付MD5签名算法"""
        # 1. 将所有参数按照参数名ASCII码从小到大排序（a-z）
        # 2. 忽略空值与sign、sign_type
        # 3. 拼接成URL键值对的格式 a=b&c=d&e=f
        # 4. 最后拼接上商户密钥KEY
        # 5. MD5加密后转小写
        items = []
        for k in sorted(params.keys()):
            val = str(params[k]) if params[k] is not None else ""
            if val == "" or k in ["sign", "sign_type"]:
                continue
            items.append(f"{k}={val}")
        sign_str = "&".join(items) + key
        return hashlib.md5(sign_str.encode("utf-8")).hexdigest()

    @staticmethod
    def generate_sign_epusdt(params: Dict[str, str], token: str) -> str:
        """彩虹易支付MD5签名算法（保留兼容性）"""
        items = []
        for k in sorted(params.keys()):
            val = params[k]
            if val == "" or val is None or k == "signature":
                continue
            if isinstance(val, float) and val.is_integer():
                val = int(val)
            items.append(f"{k}={val}")
        sign_str = "&".join(items) + token
        return hashlib.md5(sign_str.encode("utf-8")).hexdigest()

    @staticmethod
    async def create_order(trade_no, name, money, type_code):
        """创建支付订单"""
        if PAYMENT_PLATFORM == "yipay":
            return await YiPay._create_yipay_order(trade_no, name, money, type_code)
        elif PAYMENT_PLATFORM == "epusdt":
            return await YiPay._create_epusdt_order(trade_no, name, money, type_code)
        else:
            raise RuntimeError(f"不支持的支付平台: {PAYMENT_PLATFORM}")

    @staticmethod
    async def _create_yipay_order(trade_no, name, money, type_code):
        """易支付订单创建"""
        # 确保金额格式正确
        formatted_money = round(float(money), 2)

        # 检查金额是否超过限制
        if formatted_money > 1000:
            raise RuntimeError(f"支付金额 {formatted_money} CNY 超过平台限制1000元")

        payload = {
            "pid": YIPAY_PID,
            "type": type_code,
            "out_trade_no": trade_no,
            "notify_url": NOTIFY_URL,
            "return_url": RETURN_URL or "",
            "name": name[:127],  # 限制商品名称长度
            "money": f"{formatted_money:.2f}",  # 保留两位小数
            "clientip": "127.0.0.1",  # 默认IP
            "device": "pc",
            "param": "",
            "sign_type": "MD5"
        }

        # 生成签名
        payload["sign"] = YiPay.generate_sign_yipay(payload, YIPAY_KEY)

        # 调用易支付API
        api_url = urllib.parse.urljoin(YIPAY_URL, "mapi.php")
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, data=payload, timeout=15) as resp:
                data = await resp.json(content_type=None)
                if data.get("code") != 1:
                    raise RuntimeError(f"易支付下单失败: {data}")

                # 返回支付链接
                if "payurl" in data:
                    return data["payurl"]
                elif "qrcode" in data:
                    return data["qrcode"]
                elif "urlscheme" in data:
                    return data["urlscheme"]
                else:
                    raise RuntimeError(f"易支付未返回支付链接: {data}")

    @staticmethod
    async def _create_epusdt_order(trade_no, name, money, type_code):
        """彩虹易支付订单创建（保留兼容性）"""
        usdt_price = float(money)
        cny_price = round(usdt_price * USDT_TO_CNY_RATE, 2)

        if cny_price.is_integer():
            amount_val = int(cny_price)
        else:
            amount_val = cny_price

        payload = {
            "order_id": trade_no,
            "amount": amount_val,
            "notify_url": NOTIFY_URL
        }
        if RETURN_URL:
            payload["redirect_url"] = RETURN_URL

        payload["signature"] = YiPay.generate_sign_epusdt(payload, EPUSDT_TOKEN)

        api_url = urllib.parse.urljoin(EPUSDT_URL, "api/v1/order/create-transaction")
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, json=payload, timeout=15) as resp:
                data = await resp.json(content_type=None)
                if data.get("status_code") != 200 or "data" not in data:
                    raise RuntimeError(f"Epusdt 下单失败: {data}")
                payment_url = data["data"].get("payment_url")
                if not payment_url:
                    raise RuntimeError(f"Epusdt 未返回支付链接: {data}")
                return payment_url

    @staticmethod
    async def check_order_status(trade_no):
        """检查订单状态（用于兼容性）"""
        return True


# ================= Webhook 监听（异步回调） =================
async def handle_notify(request: web.Request):
    try:
        # 获取请求参数（易支付使用GET方式回调）
        data = dict(await request.post())  # 获取POST数据
        if not data:  # 如果POST为空，尝试GET
            data = dict(request.query)

        if PAYMENT_PLATFORM == "yipay":
            # 易支付回调验证
            signature = data.get("sign")
            local_sign = YiPay.generate_sign_yipay(data, YIPAY_KEY)
            if signature != local_sign:
                return web.Response(text="fail", status=403)

            # trade_status == "TRADE_SUCCESS" 表示支付成功
            if data.get("trade_status") == "TRADE_SUCCESS":
                trade_no = data.get("out_trade_no")  # 商户订单号
                if trade_no:
                    c.execute("UPDATE orders SET status = 'paid' WHERE order_id = ?", (trade_no,))
                    conn.commit()
                    print(f"[Webhook] 易支付订单 {trade_no} 支付成功")
                    # 异步发放身份组
                    bot.loop.create_task(fulfill_order(trade_no))
            return web.Response(text="success")

        elif PAYMENT_PLATFORM == "epusdt":
            # 彩虹易支付回调验证（保留兼容性）
            data = await request.json()
            signature = data.get("signature")
            local_sign = YiPay.generate_sign_epusdt(data, EPUSDT_TOKEN)
            if signature != local_sign:
                return web.Response(text="fail", status=403)

            # status == 2 表示支付成功
            if str(data.get("status")) == "2":
                trade_no = data.get("order_id")
                if trade_no:
                    c.execute("UPDATE orders SET status = 'paid' WHERE order_id = ?", (trade_no,))
                    conn.commit()
                    print(f"[Webhook] Epusdt订单 {trade_no} 支付成功")
                    # 异步发放身份组
                    bot.loop.create_task(fulfill_order(trade_no))
            return web.Response(text="ok")

        else:
            return web.Response(text="unsupported platform", status=400)

    except Exception as e:
        print(f"[Webhook] Error: {e}")
        return web.Response(text="error", status=500)


async def start_web_server():
    global web_runner, web_site
    if web_runner:
        return
    app = web.Application()
    parsed = urlparse(NOTIFY_URL)
    notify_path = parsed.path or "/notify"
    if notify_path == "/":
        notify_path = "/notify"
    app.router.add_post(notify_path, handle_notify)
    web_runner = web.AppRunner(app)
    await web_runner.setup()
    web_site = web.TCPSite(web_runner, "0.0.0.0", WEBHOOK_PORT)
    await web_site.start()
    print(f"🌍 Webhook Server running on 0.0.0.0:{WEBHOOK_PORT} path={notify_path}")

# ================= Discord Bot 设置 =================
# Bot和intents已在导入部分兼容性处理

# webhook server 控制
web_runner: Optional[web.AppRunner] = None
web_site: Optional[web.TCPSite] = None

# ================= UI 交互视图 =================

class PaymentVerifyView(ui.View):
    def __init__(self, trade_no, plan_info, user_id):
        super().__init__(timeout=None)
        self.trade_no = trade_no
        self.plan_info = plan_info # (id, name, price, role_id, duration)
        self.user_id = user_id

    # 已弃用按钮，避免用户手动确认
    # 保留类以兼容旧代码，但不添加按钮

class NetworkSelect(ui.Select):
    def __init__(self, view, plan_info=None):
        # plan_info: (id, name, price, role_id, duration) or None before plan chosen
        self.plan_info = plan_info
        self.code_to_name = {v: k for k, v in PAYMENT_METHODS.items()}
        options = []
        for display_name, type_code in PAYMENT_METHODS.items():
            options.append(
                SelectOption(
                    label=display_name,
                    value=type_code,
                    description=str(type_code)
                )
            )
        super().__init__(
            placeholder="选择支付网络",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="network_select"
        )
        self.parent_view = view

    async def callback(self, interaction: discord.Interaction):
        if not self.parent_view.selected_plan:
            await interaction.response.send_message("请先选择套餐，再选择支付网络。", ephemeral=True)
            return

        # 先defer响应，避免超时
        await interaction.response.defer(ephemeral=True)

        self.plan_info = self.parent_view.selected_plan
        type_code = self.values[0]
        network_name = self.code_to_name.get(type_code, type_code)
        await self.parent_view.generate_payment(interaction, network_name, type_code)


class NetworkSelectView(ui.View):
    def __init__(self, plan_info):
        super().__init__(timeout=120)
        self.plan_info = plan_info # (id, name, price, role_id, duration)
        self.add_item(NetworkSelect(self, plan_info))

    async def generate_payment(self, interaction, network_name, type_code):
        user_id = interaction.user.id
        plan_id, plan_name, price, currency, _, _ = self.plan_info

        # 生成订单号
        trade_no = build_trade_no(user_id)

        # 存入数据库
        c.execute("INSERT INTO orders VALUES (?, ?, ?, ?, ?)",
                  (trade_no, user_id, plan_id, 'pending', int(time.time())))
        conn.commit()

        # 根据套餐货币单位和支付方式决定传递给支付平台的金额
        if currency == 'CNY':
            # 套餐是CNY定价，直接使用价格
            payment_amount = round(float(price), 2)
            display_currency = "CNY"
            display_price = payment_amount
        else:  # USDT
            # 套餐是USDT定价，需要根据支付方式转换
            if type_code in ['alipay', 'wxpay', 'qqpay']:
                # 人民币支付：转换USDT到CNY
                payment_amount = round(float(price) * float(USDT_TO_CNY_RATE), 2)
                display_currency = "CNY"
                display_price = payment_amount
            else:
                # USDT支付：直接使用USDT金额
                payment_amount = round(float(price), 2)
                display_currency = "USDT"
                display_price = payment_amount

        # 获取支付链接
        pay_url = await YiPay.create_order(trade_no, f"Plan-{plan_name}", payment_amount, type_code)
        
        embed = discord.Embed(title="💳 订单已创建", description=f"请点击下方链接支付 **{display_price} {display_currency}**", color=0xF6C344)
        embed.add_field(name="套餐", value=plan_name, inline=True)
        embed.add_field(name="网络", value=network_name, inline=True)
        embed.add_field(name="🔗 支付链接", value=f"[👉 点击前往支付]({pay_url})", inline=False)
        embed.set_footer(text='支付完成后，系统会自动开通会员')
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


class PlanSelect(ui.Select):
    def __init__(self, view, plans):
        # plans: list of (id, name, price, currency, role_id, duration)
        self.plan_map = {str(p[0]): p for p in plans}
        options = []
        for p in plans[:25]:  # 限制最多25个选项
            plan_id, name, price, currency, _, duration = p
            if duration == -1:
                suffix = "永久"
            elif duration == 1:
                suffix = "月"
            elif duration == 12:
                suffix = "年"
            else:
                suffix = f"{duration}个月"

            # 确保价格格式化正确
            formatted_price = f"{round(float(price), 2):g}"  # 移除不必要的.0

            # 创建更清晰的标签格式
            if duration == -1:
                duration_text = "永久"
            elif duration == 1:
                duration_text = "月度"
            elif duration == 12:
                duration_text = "年度"
            else:
                duration_text = f"{duration}个月"

            # 标签格式：套餐名 - 价格 - 时长
            label = f"{name} - {formatted_price} {currency} - {duration_text}"

            # 确保label长度不超过100字符（Discord限制）
            if len(label) > 100:
                label = label[:97] + "..."

            options.append(
                SelectOption(
                    label=label,
                    value=str(plan_id),
                    description=f"时长: {suffix}"
                )
            )

        # 如果没有选项，添加一个占位符
        if not options:
            options.append(
                SelectOption(
                    label="暂无套餐",
                    value="no_plans",
                    description="请管理员配置套餐"
                )
            )
        super().__init__(
            placeholder="选择会员套餐",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="plan_select"
        )
        self.parent_view = view

    async def callback(self, interaction: discord.Interaction):
        selected_id = self.values[0]
        plan = self.plan_map.get(selected_id)
        if not plan:
            await interaction.response.send_message("❌ 未找到该套餐，请重试。", ephemeral=True)
            return
        self.parent_view.selected_plan = plan
        # 启用网络选择并更新消息
        if hasattr(self.parent_view, "network_select"):
            self.parent_view.network_select.disabled = False
            self.parent_view.network_select.placeholder = "选择支付网络"
            self.parent_view.network_select.plan_info = plan
        # 高亮已选套餐
        for opt in self.options:
            opt.default = (opt.value == selected_id)
        self.placeholder = f"已选：{plan[1]}"
        await interaction.response.edit_message(content=f"已选择套餐：**{plan[1]}**，请继续选择支付网络。", view=self.parent_view)


class PlanAndNetworkView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.selected_plan = None
        self.reload_selects()

    def reload_selects(self):
        self.clear_items()
        plans = fetch_plans()

        if not plans:
            # 创建一个有占位符选项的禁用选择器
            disabled_select = ui.Select(
                placeholder="暂无套餐，管理员请先配置 /set_plan",
                options=[
                    SelectOption(
                        label="请先配置套餐",
                        value="no_plans",
                        description="使用 /set_plan 命令添加套餐"
                    )
                ],
                disabled=True,
                custom_id="plan_select_disabled"
            )
            self.add_item(disabled_select)
            return

        plan_select = PlanSelect(self, plans)
        self.add_item(plan_select)

        # 网络下拉默认禁用，待选择套餐后启用
        network_select = NetworkSelect(self, None)
        network_select.disabled = True
        network_select.placeholder = "请先选择套餐，再选择支付网络"
        self.network_select = network_select
        self.add_item(network_select)

    async def generate_payment(self, interaction, network_name, type_code):
        if not self.selected_plan:
            await interaction.response.send_message("请先选择套餐。", ephemeral=True)
            return
        user_id = interaction.user.id
        plan_id, plan_name, price, currency, _, _ = self.selected_plan

        # 生成订单号
        trade_no = build_trade_no(user_id)

        # 存入数据库
        c.execute("INSERT INTO orders VALUES (?, ?, ?, ?, ?)",
                  (trade_no, user_id, plan_id, 'pending', int(time.time())))
        conn.commit()

        # 根据套餐货币单位和支付方式决定传递给支付平台的金额
        if currency == 'CNY':
            # 套餐是CNY定价，直接使用价格
            payment_amount = round(float(price), 2)
            display_currency = "CNY"
            display_price = payment_amount
        else:  # USDT
            # 套餐是USDT定价，需要根据支付方式转换
            if type_code in ['alipay', 'wxpay', 'qqpay']:
                # 人民币支付：转换USDT到CNY
                payment_amount = round(float(price) * float(USDT_TO_CNY_RATE), 2)
                display_currency = "CNY"
                display_price = payment_amount
            else:
                # USDT支付：直接使用USDT金额
                payment_amount = round(float(price), 2)
                display_currency = "USDT"
                display_price = payment_amount

        # 获取支付链接
        pay_url = await YiPay.create_order(trade_no, f"Plan-{plan_name}", payment_amount, type_code)

        embed = discord.Embed(title="💳 订单已创建", description=f"请点击下方链接支付 **{display_price} {display_currency}**", color=0xF6C344)
        embed.add_field(name="套餐", value=plan_name, inline=True)
        embed.add_field(name="支付方式", value=network_name, inline=True)
        embed.add_field(name="🔗 支付链接", value=f"[👉 点击前往支付]({pay_url})", inline=False)
        embed.set_footer(text='支付完成后，系统会自动开通会员')

        await interaction.followup.send(embed=embed, ephemeral=True)

# ================= 斜杠指令 (Admin) =================

@slash_command(guild_ids=[GUILD_ID], description="添加或更新会员套餐")
@commands.has_permissions(administrator=True)
async def set_plan(
    ctx,
    name: str,
    price: float,
    role: discord.Role,
    duration: int
):
    # 使用配置文件中的默认货币单位
    currency = DEFAULT_CURRENCY
    print(f"调试: set_plan - 名称:{name}, 价格:{price}, 货币:{currency}, 时长:{duration}")

    # 检查价格是否合理
    if currency == 'CNY' and price > 1000:
        await ctx.respond(f"❌ CNY价格不能超过1000元！当前价格: {price} CNY", ephemeral=True)
        return
    elif currency == 'USDT' and price * USDT_TO_CNY_RATE > 1000:
        cny_equivalent = round(price * USDT_TO_CNY_RATE, 2)
        await ctx.respond(f"❌ USDT价格转换后超过1000元！{price} USDT = {cny_equivalent} CNY", ephemeral=True)
        return

    # 检查是否已存在同名套餐，存在则更新，不存在则插入
    c.execute("SELECT id FROM plans WHERE name = ?", (name,))
    data = c.fetchone()
    if data:
        c.execute("UPDATE plans SET price=?, currency=?, role_id=?, duration_months=? WHERE name=?",
                  (price, currency, role.id, duration, name))
        action = "更新"
    else:
        c.execute("INSERT INTO plans (name, price, currency, role_id, duration_months) VALUES (?, ?, ?, ?, ?)",
                  (name, price, currency, role.id, duration))
        action = "添加"
    conn.commit()

    print(f"调试: {action}套餐成功 - {name}: {price} {currency}")
    await ctx.respond(f"✅ 已{action}套餐 **{name}**: {price} {currency.upper()} -> {role.mention}", ephemeral=True)

@slash_command(guild_ids=[GUILD_ID], description="发送充值面板")
@commands.has_permissions(administrator=True)
async def send_panel(ctx):
    # 权限自检，避免 Missing Access
    channel = ctx.channel
    me = ctx.guild.me
    perms = channel.permissions_for(me)
    if not (perms.send_messages and perms.embed_links and perms.view_channel):
        await ctx.respond("❌ 机器人在此频道缺少发送消息或嵌入权限，请管理员为机器人开启：发送消息、嵌入链接。", ephemeral=True)
        return

    # 构建主 Embed (价格表)
    embed_main = discord.Embed(
        title="LEVEL UP YOUR TRADING 🚀",
        description="选择套餐 → 选择支付方式 → 支付 → 自动开通会员",
        color=0xF6C344  # 黄色边框
    )
    
    # 动态从数据库读取价格显示在 Embed 中
    c.execute("SELECT name, price, currency, duration_months FROM plans")
    plans = c.fetchall()
    price_text = ""
    for p in plans:
        duration = p[3]
        if duration == -1:
            duration_str = "/永久"
        elif duration == 1:
            duration_str = "/月"
        elif duration == 12:
            duration_str = "/年"
        else:
            duration_str = f"/{duration}个月"
            
        price_text += f"**{p[0]}**：{p[1]} {p[2]}{duration_str}\n"
    
    if not price_text:
        price_text = "暂无套餐配置，请使用管理员指令配置。"

    steps_text = "```\n✅ 选套餐 + 支付方式\n💳 点击前往支付\n🔗 完成支付\n🎉 自动开通会员\n```"

    embed_main.add_field(name="💰 会员价格", value=price_text, inline=False)
    embed_main.add_field(name="📌 开通步骤", value=steps_text, inline=False)
    embed_main.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/3135/3135715.png") # 示例图标

    # 在slash command中直接回复包含embed和view的消息
    view = PlanAndNetworkView()
    await ctx.respond(embed=embed_main, view=view)

@slash_command(guild_ids=[GUILD_ID], description="删除套餐")
@commands.has_permissions(administrator=True)
async def delete_plan(
    ctx,
    name: str
):
    c.execute("SELECT id FROM plans WHERE name = ?", (name,))
    data = c.fetchone()
    if data:
        c.execute("DELETE FROM plans WHERE name = ?", (name,))
        conn.commit()
        await ctx.respond(f"✅ 已删除套餐 **{name}**", ephemeral=True)
    else:
        await ctx.respond(f"❌ 未找到套餐 **{name}**", ephemeral=True)

@slash_command(guild_ids=[GUILD_ID], description="查看所有套餐")
@commands.has_permissions(administrator=True)
async def list_plans(ctx):
    c.execute("SELECT name, price, currency, duration_months FROM plans")
    plans = c.fetchall()
    if plans:
        plan_list = "\n".join([f"**{p[0]}**: {p[1]} {p[2]} (时长: {p[3]}个月)" for p in plans])
        await ctx.respond(f"📋 **当前套餐列表：**\n{plan_list}", ephemeral=True)
    else:
        await ctx.respond("❌ 暂无套餐配置", ephemeral=True)

@slash_command(guild_ids=[GUILD_ID], description="手动授予用户会员（管理员）")
@commands.has_permissions(administrator=True)
async def grant_member(
    ctx,
    user: discord.Member,
    plan_name: str
):
    plan = fetch_plan_by_name(plan_name)
    if not plan:
        await ctx.respond(f"❌ 未找到套餐 **{plan_name}**，请确认名称是否一致。", ephemeral=True)
        return

    plan_id, name, price, role_id, duration = plan
    role = ctx.guild.get_role(role_id)
    if not role:
        await ctx.respond(f"❌ 未找到套餐对应的身份组（role_id={role_id}），请检查配置。", ephemeral=True)
        return

    try:
        await user.add_roles(role)
    except Exception as e:
        await ctx.respond(f"⚠️ 授予身份组失败：{e}", ephemeral=True)
        return

    # 写入订单和订阅记录，状态设为手动付费
    trade_no = f"MANUAL_{int(time.time())}_{user.id}"
    current_time = int(time.time())
    if duration == -1:
        expire_date = -1
    else:
        expire_date = current_time + (duration * 30 * 24 * 60 * 60)

    c.execute("INSERT INTO orders VALUES (?, ?, ?, ?, ?)",
              (trade_no, user.id, plan_id, 'paid', current_time))
    c.execute("INSERT INTO subscriptions (user_id, role_id, plan_id, expire_date, created_at) VALUES (?, ?, ?, ?, ?)",
              (user.id, role_id, plan_id, expire_date, current_time))
    conn.commit()

    expire_text = "永久" if duration == -1 else f"{duration} 个月"
    await ctx.respond(f"✅ 已为 {user.mention} 授予 {role.mention}（{expire_text}）。", ephemeral=True)

@slash_command(guild_ids=[GUILD_ID], description="测试回调功能（模拟支付成功，无需真实支付）")
@commands.has_permissions(administrator=True)
async def test_callback(
    ctx,
    order_id: str
):
    """模拟 Epusdt 回调，测试支付成功流程"""
    # 检查订单是否存在
    c.execute("SELECT user_id, plan_id, status FROM orders WHERE order_id = ?", (order_id,))
    order = c.fetchone()
    if not order:
        await ctx.respond(f"❌ 未找到订单 **{order_id}**。请先创建一个订单（通过购买流程）。", ephemeral=True)
        return
    
    user_id, plan_id, current_status = order
    if current_status == 'paid':
        await ctx.respond(f"⚠️ 订单 **{order_id}** 已经是已支付状态。", ephemeral=True)
        return
    
    # 获取套餐信息以构造回调数据
    c.execute("SELECT name, price FROM plans WHERE id = ?", (plan_id,))
    plan = c.fetchone()
    if not plan:
        await ctx.respond(f"❌ 未找到订单对应的套餐信息。", ephemeral=True)
        return
    
    plan_name, price = plan
    
    # 构造模拟的回调数据（按照 Epusdt 回调格式）
    mock_callback_data = {
        "trade_id": f"TEST_{int(time.time())}",
        "order_id": order_id,
        "amount": float(price),
        "actual_amount": float(price),
        "token": "TEST_TOKEN",
        "block_transaction_id": f"TEST_BLOCK_{int(time.time())}",
        "status": 2  # 2 表示支付成功
    }
    
    # 生成签名
    mock_callback_data["signature"] = YiPay.generate_sign_epusdt(mock_callback_data, EPUSDT_TOKEN)
    
    # 模拟调用 handle_notify 的逻辑
    try:
        # 更新订单状态
        c.execute("UPDATE orders SET status = 'paid' WHERE order_id = ?", (order_id,))
        conn.commit()
        
        # 异步发放身份组
        await fulfill_order(order_id)
        
        member = ctx.guild.get_member(user_id)
        if member:
            await ctx.respond(
                f"✅ **测试回调成功！**\n"
                f"订单号：`{order_id}`\n"
                f"用户：{member.mention}\n"
                f"状态：已支付 → 身份组已发放\n\n"
                f"📋 回调数据签名：`{mock_callback_data['signature']}`",
                ephemeral=True
            )
        else:
            await ctx.respond(
                f"✅ **测试回调成功！**\n"
                f"订单号：`{order_id}`\n"
                f"用户ID：{user_id}\n"
                f"状态：已支付 → 身份组已发放\n\n"
                f"⚠️ 注意：用户不在当前服务器中，无法验证身份组发放。",
                ephemeral=True
            )
    except Exception as e:
        await ctx.respond(f"❌ 测试回调时出错：{e}", ephemeral=True)

@slash_command(guild_ids=[GUILD_ID], description="手动处理已支付订单")
@commands.has_permissions(administrator=True)
async def process_paid_order(
    ctx,
    order_id: str
):
    """手动处理后台补单的情况，将订单标记为已支付并发放会员权限"""
    # 检查订单是否存在
    c.execute("SELECT user_id, plan_id, status FROM orders WHERE order_id = ?", (order_id,))
    order = c.fetchone()

    if not order:
        # 如果订单不存在，尝试查找相似的订单号
        c.execute("SELECT order_id, user_id, plan_id, status FROM orders WHERE order_id LIKE ? LIMIT 5", (f'%{order_id}%',))
        similar_orders = c.fetchall()

        if similar_orders:
            order_list = "\n".join([f"`{o[0]}` - 用户:{o[1]} - 状态:{o[3]}" for o in similar_orders])
            await ctx.respond(f"❌ 未找到订单 `{order_id}`，但找到相似订单：\n{order_list}", ephemeral=True)
        else:
            await ctx.respond(f"❌ 未找到订单 `{order_id}`", ephemeral=True)
        return

    user_id, plan_id, current_status = order

    if current_status == 'paid':
        await ctx.respond(f"✅ 订单 `{order_id}` 已经是已支付状态", ephemeral=True)
        return

    # 将订单标记为已支付
    c.execute("UPDATE orders SET status = 'paid' WHERE order_id = ?", (order_id,))
    conn.commit()

    # 获取用户信息
    member = ctx.guild.get_member(user_id)
    user_mention = f"<@{user_id}>" if not member else member.mention

    try:
        # 调用fulfill_order来发放会员权限
        await fulfill_order(order_id)
        await ctx.respond(f"✅ 已手动处理订单 `{order_id}`\n用户: {user_mention}\n状态: 已支付 → 已发放会员权限", ephemeral=True)
    except Exception as e:
        await ctx.respond(f"⚠️ 订单 `{order_id}` 已标记为已支付，但发放权限时出错: {e}", ephemeral=True)
    """查看订单记录"""
    if status:
        c.execute("SELECT order_id, user_id, plan_id, status, created_at FROM orders WHERE status = ? ORDER BY created_at DESC LIMIT 20", (status,))
    else:
        c.execute("SELECT order_id, user_id, plan_id, status, created_at FROM orders ORDER BY created_at DESC LIMIT 20")
    
    orders = c.fetchall()
    if not orders:
        await ctx.respond("❌ 暂无订单记录", ephemeral=True)
        return
    
    order_list = []
    for order in orders:
        order_id, user_id, plan_id, order_status, created_at = order
        c.execute("SELECT name FROM plans WHERE id = ?", (plan_id,))
        plan_name = c.fetchone()
        plan_name_str = plan_name[0] if plan_name else "未知套餐"
        
        # 格式化时间
        time_str = datetime.fromtimestamp(created_at).strftime("%Y-%m-%d %H:%M:%S")
        
        status_emoji = "✅" if order_status == "paid" else "⏳"
        order_list.append(f"{status_emoji} `{order_id}` - {plan_name_str} - <@{user_id}> - {order_status} - {time_str}")
    
    await ctx.respond(
        f"📋 **订单记录**（最近20条）\n\n" + "\n".join(order_list),
        ephemeral=True
    )

# ================= 定时任务：检查到期订阅 =================
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    # 同步slash commands (仅在官方discord.py模式下需要)
    if HAS_SLASH_COMMANDS and not PY_CORD_MODE:
        try:
            # 同步命令树到指定服务器
            guild = discord.Object(id=GUILD_ID)
            bot.tree.copy_global_to(guild=guild)
            await bot.tree.sync(guild=guild)
            print("✅ 已同步slash commands到服务器")
        except Exception as e:
            print(f"⚠️ 同步slash commands失败: {e}")

    # 重启后保持按钮监听状态
    if HAS_UI_COMPONENTS:
        bot.add_view(PlanAndNetworkView())
    else:
        print("⚠️ UI组件不支持，跳过按钮注册")

    # 启动 webhook 服务器（用于接收 Epusdt 回调）
    await start_web_server()

    # 启动定时任务检查到期订阅
    check_expired_subscriptions.start()
    # 启动时立即跑一次过期检查
    await process_expired_subscriptions()

async def process_expired_subscriptions():
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

@tasks.loop(minutes=60)  # 每小时检查一次
async def check_expired_subscriptions():
    await process_expired_subscriptions()

@check_expired_subscriptions.before_loop
async def before_check_expired():
    await bot.wait_until_ready()

if __name__ == "__main__":
    bot.run(TOKEN)

