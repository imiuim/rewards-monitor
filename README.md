# Microsoft Rewards 监控与自动化

> 用 AI 自动化刷 Microsoft Rewards 积分，积分可兑换肯德基/盒马/麦德龙/天猫超市礼品卡，闲鱼变现。

## 架构

```
┌─────────────────┐        ┌──────────────────────┐        ┌─────────────────┐
│  botkeep.cloud   │  POST  │  170.106.115.45      │  JSON  │   监控页面       │
│  (执行 Rewards   │───────>│  server.py :8765     │<───────│  /rewards/      │
│   任务)          │ ingest │  SQLite + API        │        │  dashboard.html │
└─────────────────┘        └──────────────────────┘        └─────────────────┘
                                    │
                                    └── nginx: location /rewards/ → 127.0.0.1:8765
```

## 快速开始

### 1. 部署 API 服务（服务器）

```bash
# 服务器：170.106.115.45（Ubuntu）
ssh ubuntu@170.106.115.45
mkdir -p ~/rewards-monitor
# 上传 server.py, dashboard.html, rewards.db
cd ~/rewards-monitor
(setsid nohup python3 server.py > server.log 2>&1 < /dev/null &)
```

### 2. 配置 nginx 反代

在宝塔 vhost（`/www/server/panel/vhost/nginx/starring-sub.conf`）中加：

```nginx
location /rewards/ {
    proxy_pass http://127.0.0.1:8765/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_read_timeout 86400s;
}
```

然后 `sudo nginx -t && sudo nginx -s reload`。

### 3. 访问

- 监控页：http://170.106.115.45/rewards/
- JSON API：http://170.106.115.45/rewards/api/status

## API

| 端点 | 方法 | 说明 |
|---|---|---|
| `/rewards/api/status` | GET | 返回 {accounts, log, server_time} |
| `/rewards/api/ingest` | POST | bot 回写执行结果 |
| `/rewards/api/add` | POST | 添加账号 |

### ingest 请求体

```json
{
  "email": "Ew0lU2@twinkor.com",
  "tasks_done": 3,
  "points_earned": 65,
  "points": 65,
  "level": "Member",
  "detail": "Bing搜索3次"
}
```

`points`/`level` 可选，传了则更新账号总积分和等级。

## 文件说明

```
rewards-repo/
├── README.md              # 本文件
├── src/
│   ├── server.py          # API 服务（Python 3.8+，纯标准库，端口 8765）
│   ├── dashboard.html     # 监控页面（纯静态，fetch 相对路径 ./api）
│   └── RewardsDashboard.jsx  # Next.js 嵌入组件（备用，嵌入主项目用）
├── docs/
│   └── HANDOVER.md        # 详细交接文档
└── scripts/
    └── ssh_run.py         # SSH/SFTP 工具（paramiko，含 fail2ban 重试）
```

## 账号

| 账号 | 状态 |
|---|---|
| Ew0lU2@twinkor.com | active（免密验证码登录） |
| 6o9e3q3@twinkor.com | pending_login（验证码限流恢复中） |

## 参考项目

- Microsoft-Rewards-Bot：GitHub chiihero/Microsoft-Rewards-Bot（V4-china 分支 v4.3.2.4，TypeScript + Patchright）
- bot 执行平台：botkeep.cloud

## 注意事项

- 微软对验证码登录有限流（"使用此登录方法的次数已达到上限"，约 24h 恢复）
- 账号当前为美区（EN-US），国区礼品卡需用住宅 IP 登录切换
- 自动化做任务属灰色操作，建议控制节奏、勿用主力账号
