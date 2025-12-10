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
- 彩虹易支付商户账号（商户 ID 和密钥）
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
   - `yipay_url`: 易支付域名（以 `/` 结尾）
   - `yipay_pid` / `yipay_key`: 商户 ID 与密钥
   - `payment_types`: 支付通道映射，例如：
     ```json
     {
       "USDT-TRC20": "usdt_trc20",
       "USDT-BEP20": "usdt_bep20"
     }
     ```
   - 可选项：`notify_url`、`return_url`、`database`（数据库文件名）

> 如需使用自定义路径，设置环境变量 `BOT_CONFIG_PATH=/path/to/your_config.json`。

### 3. 设置机器人权限

在 Discord Developer Portal 中，确保机器人拥有以下权限：

- `bot`
- `applications.commands`
- `Manage Roles`（管理身份组）

### 4. 邀请机器人

使用以下链接邀请机器人（替换 `YOUR_CLIENT_ID` 为你的机器人客户端 ID）：

```
https://discord.com/api/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=268435456&scope=bot%20applications.commands
```

### 5. 配置身份组

1. 在 Discord 服务器设置中创建会员身份组（如：月会员、年会员、合伙人等）
2. **重要**：确保机器人的身份组在这些会员身份组的**上方**，否则机器人无法赋予角色
3. 在服务器设置 > 角色中，将机器人角色拖到会员角色上方

## 使用方法

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

## 易支付配置说明

### 支付通道类型

不同易支付系统的支付通道代码可能不同，常见格式：

- 数字 ID：`"1001"`, `"1002"`
- 字符串代码：`"usdt_trc20"`, `"trc20"`, `"usdt"`

请在易支付后台查看具体的通道代码，并修改 `PAYMENT_TYPES` 字典。

### API 路径

如果易支付的 API 路径不是 `/api.php`，请修改 `YiPay.check_order_status()` 方法中的路径。

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
