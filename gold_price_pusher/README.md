# 黄金价格定时推送脚本

从极速API获取伦敦金价格，定时推送到微信。

## 功能特点

- 🥇 获取伦敦金实时价格
- 💱 自动换算为人民币/克
- ⏰ 定时推送（上午9-12点，下午14-21点，每15分钟）
- 📱 推送到微信（通过OpenClaw）
- 🔄 自动重试机制
- 📝 完整日志记录

## 安装依赖

```bash
pip install requests schedule
```

## 配置

### 1. 配置文件 (config.json)

```json
{
    "wechat_user_id": "YOUR_WECHAT_USER_ID",
    "api_url": "https://api.jisuapi.com/gold/london",
    "api_key": "33c976a06affe275",
    "schedule": {
        "morning": {
            "start_hour": 9,
            "end_hour": 12,
            "interval_minutes": 15
        },
        "afternoon": {
            "start_hour": 14,
            "end_hour": 21,
            "interval_minutes": 15
        }
    },
    "retry": {
        "max_attempts": 3,
        "delay_seconds": 5
    },
    "conversion": {
        "ounces_to_grams": 31.1035,
        "usd_to_cny": 6.8859
    }
}
```

### 2. 配置微信用户ID

有两种方式配置微信用户ID：

**方式一：环境变量（推荐）**
```bash
# Windows CMD
set WECHAT_USER_ID=your_wechat_user_id

# Windows PowerShell
$env:WECHAT_USER_ID="your_wechat_user_id"

# Linux/Mac
export WECHAT_USER_ID=your_wechat_user_id
```

**方式二：修改配置文件**
编辑 `config.json`，将 `wechat_user_id` 改为你的微信用户ID。

## 使用方法

### 测试API连接
```bash
python gold_price_pusher.py --test
```

### 执行一次推送
```bash
python gold_price_pusher.py --once
```

### 启动定时服务
```bash
python gold_price_pusher.py
```

### 指定配置文件
```bash
python gold_price_pusher.py --config /path/to/config.json
```

## 推送消息格式

```
💰 黄金价格播报
📅 时间: 2026-04-05 10:00:00

🥇 伦敦金: $2345.67/盎司
💴 人民币: ¥519.23/克
📈 涨跌幅: +0.5%
🟢 较上次: +2.35 (+0.46%)

--- 黄金价格定时推送 ---
```

## 价格换算公式

```
人民币/克 = 美元/盎司 ÷ 31.1035 × 6.8859
```

- 1盎司 = 31.1035克
- 美元汇率按6.8859计算（可在配置文件中调整）

## 定时推送时间

| 时段 | 时间范围 | 频率 |
|------|----------|------|
| 上午 | 09:00 - 12:00 | 每15分钟 |
| 下午 | 14:00 - 21:00 | 每15分钟 |

## 日志

日志同时输出到控制台和文件 `gold_price_pusher.log`。

## 前提条件

确保已安装并配置 OpenClaw：
```bash
# 验证OpenClaw是否可用
openclaw --version
```

## 作为服务运行

### Windows (使用任务计划程序)

创建启动脚本 `start_pusher.bat`：
```batch
@echo off
cd /d C:\path\to\gold_price_pusher
set WECHAT_USER_ID=your_wechat_user_id
python gold_price_pusher.py
```

### Linux (使用 systemd)

创建服务文件 `/etc/systemd/system/gold-pusher.service`：
```ini
[Unit]
Description=Gold Price Pusher
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/gold_price_pusher
Environment=WECHAT_USER_ID=your_wechat_user_id
ExecStart=/usr/bin/python3 gold_price_pusher.py
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
sudo systemctl enable gold-pusher
sudo systemctl start gold-pusher
```

## 故障排查

1. **API调用失败**：检查网络连接和API密钥是否有效
2. **消息发送失败**：确认OpenClaw已正确安装，微信用户ID配置正确
3. **定时任务不执行**：检查系统时间是否正确，日志中查看定时任务列表
