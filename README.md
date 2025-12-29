# Discord会员充值机器人

一个功能完整的 Discord 机器人，支持通过聚合支付平台进行会员套餐购买和自动开通。

## 🚀 新功能：灵活货币单位

**核心特性**：每个套餐可以设置不同的货币单位（USDT或CNY）！

### 货币单位说明

- **USDT套餐**：按USDT定价，支付宝/微信支付时自动转换为CNY显示
- **CNY套餐**：直接按人民币定价，所有支付方式使用相同金额

### 使用示例

```bash
# USDT套餐：39 USDT，支付宝支付时显示273 CNY
/set_plan name:月会员 price:39.0 currency:USDT role:@月会员 duration:1

# CNY套餐：199 CNY，所有支付方式都显示199 CNY
/set_plan name:年会员 price:199.0 currency:CNY role:@年会员 duration:12
```

## 📦 安装说明

### 1. 安装依赖

**重要**: 此项目必须使用 **Py-cord** 库。

```bash
# 卸载可能存在的discord.py
pip uninstall discord.py -y

# 安装Py-cord
pip install py-cord>=2.4.0 aiohttp>=3.8.0
```

### 2. 配置机器人

编辑 `config.json`：

```json
{
  "token": "你的Discord机器人令牌",
  "guild_id": 你的服务器ID,
  "yipay_url": "https://feedapp.top/",
  "yipay_pid": "1000",
  "yipay_key": "你的商户密钥",
  "payment_methods": {
    "支付宝": "alipay",
    "微信支付": "wxpay",
    "QQ钱包": "qqpay",
    "USDT": "usdt"
  },
  "enable_privileged_intents": false,
  "default_currency": "CNY"
}
```

**重要配置说明**:
- `default_currency`: 设置默认货币单位 (`"CNY"` 或 `"USDT"`)
- 所有套餐都会使用这个默认货币单位
- 如果设置为 `"CNY"`，所有价格都按人民币计算
- 如果设置为 `"USDT"`，会根据支付方式自动转换为相应货币

## 🎮 使用方法

### 设置套餐

使用 `/set_plan` 命令设置会员套餐：

```
/set_plan name:月会员 price:39.0 role:@月会员 duration:1
/set_plan name:年会员 price:299.0 role:@年会员 duration:12
```

**货币单位**: 所有套餐都使用配置文件中的 `default_currency` 设置

### 发送充值面板

```
/send_panel
```

机器人会显示交互式充值面板，用户可以：
1. 选择套餐（显示正确的货币单位）
2. 选择支付方式
3. 点击支付链接完成支付

### 查看套餐列表

```
/list_plans
```

显示所有已配置的套餐及其货币单位。

## 💰 货币单位工作原理

### USDT套餐 (currency: "USDT")
- 价格按USDT存储
- 显示时：保持USDT单位
- 支付宝/微信支付：自动转换为CNY显示和支付

### CNY套餐 (currency: "CNY")  
- 价格按CNY存储
- 显示时：显示CNY单位
- 所有支付方式：使用相同CNY金额

## ⚙️ 技术特性

- ✅ **Py-cord支持**：完整的slash commands和UI组件
- ✅ **货币智能转换**：根据套餐和支付方式自动转换
- ✅ **数据库迁移**：自动为现有数据库添加currency字段
- ✅ **支付平台集成**：支持聚合支付平台
- ✅ **自动角色管理**：支付成功后自动发放会员角色

## 🔧 故障排除

### Slash Commands不显示
确保安装了Py-cord而不是discord.py：
```bash
pip uninstall discord.py
pip install py-cord>=2.4.0
```

### 货币单位错误
检查套餐设置时是否正确指定了currency参数。

### 支付失败
确认支付平台的配置是否正确。

### 价格计算错误（2100元问题）
如果遇到价格计算错误（如300元显示为2100元），通常是数据库列顺序问题：
1. 确保所有查询都明确指定字段顺序
2. 不要使用 `SELECT *`，而是用 `SELECT id, name, price, currency, role_id, duration_months`
3. 重启机器人后重新发送支付面板

## 📝 更新日志

- ✅ 添加货币单位支持 (USDT/CNY)
- ✅ 智能价格转换和显示
- ✅ 数据库结构升级
- ✅ Py-cord兼容性优化
- ✅ 添加手动处理已支付订单功能
- ✅ 支持后台补单情况的处理
- ✅ 添加默认货币单位配置
- ✅ 简化套餐设置命令
- ✅ 修复价格计算精度问题
- ✅ **修复数据库列顺序错位问题**（重要）

---

**注意**: 此机器人需要Py-cord库支持，请勿使用官方discord.py。
