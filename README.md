# Discord 会员充值机器人

一个功能完整的 Discord 机器人，支持通过彩虹易支付（YiPay）进行会员套餐购买和自动开通。

## 功能特性

- ✅ 支持多个会员套餐配置（月会员、年会员、永久会员等）
- ✅ 支持多种支付方式（USDT-TRC20、USDT-BEP20）
- ✅ 自动赋予 Discord 身份组
- ✅ 订单状态查询和验证
- ✅ 订阅到期自动管理（定时检查并移除过期身份组）
- ✅ 美观的交互界面（按钮、嵌入消息）

## 前置要求

- Python 3.8 或更高版本
- Discord Bot Token（从 [Discord Developer Portal](https://discord.com/developers/applications) 获取）
- 支付平台商户账号（支持易支付或彩虹易支付）
- Discord 服务器管理员权限

## 安装步骤

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置机器人（外部配置文件）

1. 复制示例配置：
   ```bash
   cp config.example.json config.json
   ```
2. 编辑 `config.json`，填入你的实际值：
   - `token`: Discord Bot Token
   - `guild_id`: 服务器 ID
   - `payment_platform`: 支付平台类型（"yipay" 表示易支付，"epusdt" 表示彩虹易支付）
   - **易支付配置**（当 payment_platform 为 "yipay" 时）：
     - `yipay_url`: 易支付域名（支持自定义，如 "https://feedapp.top/"）
     - `yipay_pid`: 易支付商户ID
     - `yipay_key`: 易支付商户密钥
   - **彩虹易支付配置**（当 payment_platform 为 "epusdt" 时）：
     - `epusdt_url`: 彩虹易支付域名
     - `epusdt_token`: 彩虹易支付签名令牌
   - `payment_methods`: 支付通道映射，例如：
     ```json
     {
       "支付宝": "alipay",
       "微信支付": "wxpay",
       "QQ钱包": "qqpay",
       "USDT": "usdt"
     }
     ```
   - `enable_privileged_intents`: 是否启用特权intents（默认false）
   - 可选项：`notify_url`、`return_url`、`database`（数据库文件名）

> 如需使用自定义路径，设置环境变量 `BOT_CONFIG_PATH=/path/to/your_config.json`。

### 3. 设置机器人权限

在 Discord Developer Portal 中，确保机器人拥有以下权限：

- `bot`
- `applications.commands`
- `Manage Roles`（管理身份组）

### 4. 配置机器人权限

#### 特权Intents设置（重要）

如果你的机器人需要访问成员信息，请在 [Discord开发者门户](https://discord.com/developers/applications/) 中启用特权intents：

1. 进入你的应用页面
2. 点击 "Bot" 标签
3. 在 "Privileged Gateway Intents" 部分启用：
   - ✅ Server Members Intent（服务器成员意图）
   - ✅ Message Content Intent（消息内容意图）

然后在 `config.json` 中设置：
```json
"enable_privileged_intents": true
```

如果不需要这些特权功能，保持默认值 `false` 即可。

### 5. 邀请机器人

使用以下链接邀请机器人（替换 `YOUR_CLIENT_ID` 为你的机器人客户端 ID）：

```
https://discord.com/api/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=268435456&scope=bot%20applications.commands
```

### 5. 配置身份组

1. 在 Discord 服务器设置中创建会员身份组（如：月会员、年会员、合伙人等）
2. **重要**：确保机器人的身份组在这些会员身份组的**上方**，否则机器人无法赋予角色
3. 在服务器设置 > 角色中，将机器人角色拖到会员角色上方

## 使用方法

### 🚀 快速开始

1. **配置检查**: 机器人已配置为使用聚合支付平台 (https://feedapp.top/)
2. **启动机器人**: `python main.py`
3. **发送支付面板**: 使用 `/send_panel` 指令在Discord频道中创建支付界面
4. **测试支付**: 用户可以选择支付宝测试支付（0.01元测试订单已验证成功）

### 📊 API测试结果

- ✅ 商户信息查询：成功
- ✅ 订单创建：成功（支付宝二维码生成正常）
- ✅ 签名验证：MD5算法工作正常
- ✅ 网络连接：API响应正常

### 管理员指令

#### 1. 设置套餐

```
/set_plan name:月会员 price:66.0 role:@月会员 duration:1
/set_plan name:年会员 price:399.0 role:@年会员 duration:12
/set_plan name:合伙人 price:999.0 role:@合伙人 duration:-1
```

参数说明：

- `name`: 套餐名称
- `price`: 价格（USDT）
- `role`: 对应的 Discord 身份组（使用 @ 提及）
- `duration`: 时长（月），`-1` 代表永久

#### 2. 发送充值面板

```
/send_panel
```

在公开频道使用此指令，机器人会发送包含价格表和选择按钮的面板。

#### 3. 查看所有套餐

```
/list_plans
```

#### 4. 删除套餐

```
/delete_plan name:月会员
```

### 用户流程

1. 用户看到充值面板，点击套餐按钮（如：月会员 66.0 USDT）
2. 选择支付网络（USDT-TRC20 或 USDT-BEP20）
3. 点击支付链接，完成支付
4. 支付完成后，点击"✅ 我已完成支付"按钮
5. 机器人自动验证支付并赋予身份组

## 数据库结构

机器人使用 SQLite 数据库（`bot_data.db`），包含以下表：

- **plans**: 存储套餐信息
- **orders**: 存储订单记录
- **subscriptions**: 存储用户订阅信息（用于到期管理）

## 支付平台配置说明

### 支持的支付平台

机器人支持两种主流支付平台：

#### 1. 聚合支付平台 (YiPay)
- **平台地址**: https://feedapp.top/
- **商户ID**: 1000 (已配置)
- **支付方式**: 支付宝、微信支付、QQ钱包
- **签名方式**: MD5 + RSA兼容模式
- **API文档**: https://feedapp.top/

#### 2. 彩虹易支付 (Epusdt)
- **商户注册**: 访问彩虹易支付官网注册账号
- **主要特点**: 专注于USDT支付
- **API特点**: 支持USDT转CNY汇率转换

### 易支付通道配置

易支付的支付通道代码固定如下：

- `alipay`: 支付宝
- `wxpay`: 微信支付
- `qqpay`: QQ钱包
- `bank`: 网银支付
- `jdpay`: 京东支付
- `paypal`: PayPal
- `usdt`: USDT

### 彩虹易支付通道配置

彩虹易支付支持的通道：

- `trc20`: USDT-TRC20
- `bsc`: USDT-BEP20
- 其他自定义通道代码

## 定时任务

机器人会自动每 24 小时检查一次过期订阅，并移除过期的身份组。永久会员（duration=-1）不会过期。

## 注意事项

1. **回调通知**：由于本地运行通常没有公网 IP，本方案采用用户主动点击按钮查询支付状态。如需全自动处理，需要部署到有公网 IP 的服务器并实现回调接口。

2. **时区问题**：订阅到期时间按 30 天/月计算，如需精确计算，可以修改代码使用更精确的日期库。

3. **错误处理**：如果支付成功但赋予身份组失败，请检查：
   - 机器人身份组是否在会员身份组上方
   - 机器人是否有管理身份组权限
   - 用户是否还在服务器中

## 故障排除

### 按钮不响应

确保在 `on_ready()` 事件中调用了 `bot.add_view(PlanSelectView())`，这样重启后按钮仍能正常工作。

### 无法赋予身份组

1. 检查机器人身份组位置
2. 检查机器人权限
3. 检查用户是否还在服务器中

### 支付查询失败

1. 检查易支付 API 地址是否正确
2. 检查商户 ID 和密钥是否正确
3. 检查网络连接

## 许可证

本项目仅供学习和个人使用。

# PremiumDiscord
