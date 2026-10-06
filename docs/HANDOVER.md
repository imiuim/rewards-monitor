# Rewards 项目交接文档（2026-10-07）

> 供下一个会话（本地 ZCode 客户端，7:30）接续用。
> 本文尽量详细，照着做即可，不需要额外上下文。

---

## 1. 项目概览

用 AI 自动化刷 Microsoft Rewards 积分，积分兑换礼品卡（肯德基/盒马/麦德龙/天猫超市），闲鱼变现成人民币。

当前状态：**监控壳已完整部署上线**，Rewards Bot 执行端（botkeep.cloud）尚未接入。

### 已完成

- ✅ API 服务（server.py）部署在 170.106.115.45，端口 8765
- ✅ 监控页面上线：http://170.106.115.45/rewards/
- ✅ JSON API 上线：http://170.106.115.45/rewards/api/status
- ✅ bot 回写端点：POST /rewards/api/ingest（已实测通）
- ✅ 两个微软账号入库（Ew0lU2 active、6o9e3q3 pending_login）
- ✅ 交接文档 + 长期记忆已写

### 待完成（7:30 本地 ZCode 会话）

1. Rewards Bot（chiihero/Microsoft-Rewards-Bot V4-china v4.3.2.4）接入 botkeep.cloud 平台
2. botkeep 任务完成后 POST 结果到 ingest 端点
3. 6o9e3q3 账号验证码限流恢复后登录，改 active
4. 监控页按需完善（图表、告警等）

---

## 2. 访问入口

| 用途 | 地址 |
|---|---|
| 监控页（浏览器打开） | http://170.106.115.45/rewards/ |
| JSON API | http://170.106.115.45/rewards/api/status |
| bot 回写 | POST http://170.106.115.45/rewards/api/ingest |
| 添加账号 | POST http://170.106.115.45/rewards/api/add |

监控页功能：统计卡片（账号数/总积分/激活数/待登录数）、账号卡（邮箱/积分/等级/密码点击展开/最近登录/最近执行/备注）、执行日志表。页面每 60 秒自动刷新。

---

## 3. 服务器信息

- **IP**：170.106.115.45（海外 VPS，Ubuntu）
- **SSH**：`ubuntu` / `235428lsy!`
- **注意**：服务器有 fail2ban，SSH 频繁断连属正常，重试即可（沙箱工具 ssh_run.py 内置 25 次重试循环，间隔 10s）
- **部署路径**：`/home/ubuntu/rewards-monitor/`
  - `server.py` — API 服务（端口 8765，纯 Python 标准库，Python 3.8+ 可跑）
  - `dashboard.html` — 前端页面（纯静态，fetch 相对路径 `./api/...`）
  - `rewards.db` — SQLite 数据库（两张表：accounts、run_log）
  - `server.log` — 服务日志

### 服务重启命令（服务器上）

```bash
pkill -f 'python3 server.py'; sleep 2   # 等 2 秒，否则 Address already in use
cd /home/ubuntu/rewards-monitor && (setsid nohup python3 server.py > server.log 2>&1 < /dev/null &)
# 验证
curl -s http://127.0.0.1:8765/api/status
```

---

## 4. nginx 配置

- **配置文件**：`/www/server/panel/vhost/nginx/starring-sub.conf`（宝塔面板，server_name 170.106.115.45）
- **已加**：

```nginx
location /rewards/ {
    proxy_pass http://127.0.0.1:8765/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_read_timeout 86400s;
    proxy_send_timeout 86400s;
}
```

- **备份**：`starring-sub.conf.bak.rewards`
- **⚠️ 关键坑**：同文件已有 `location /api/` → `http://127.0.0.1:3000`（主项目）。所以前端 fetch 必须用相对路径 `./api`，绝不能写死 `/api`，否则会被 starring-sub 的 /api/ 截获转发到 3000 端口。
- **改配置后**：`sudo nginx -t && sudo nginx -s reload`
- **为什么没直接用 8765 端口**：腾讯云安全组未开放 8765，公网访问不到；80 端口已开放，走 nginx 反代。

---

## 5. API 详细说明（botkeep.cloud 对接用）

### GET /rewards/api/status

返回：

```json
{
  "accounts": [
    {
      "id": 1,
      "email": "Ew0lU2@twinkor.com",
      "password": null,
      "passwordless": 1,
      "status": "active",
      "points": 65,
      "level": "Member",
      "last_login": "2026-10-07 06:24:33",
      "last_run": "2026-10-07 06:35:53",
      "note": "已登录，Dashboard 可用（免密验证码）",
      "created_at": "2026-10-07 06:23:24"
    }
  ],
  "log": [
    {
      "id": 1,
      "account_email": "Ew0lU2@twinkor.com",
      "run_at": "2026-10-07 06:35:53",
      "tasks_done": 3,
      "points_earned": 65,
      "detail": "测试：Bing搜索3次"
    }
  ],
  "server_time": "2026-10-07T06:35:53"
}
```

### POST /rewards/api/ingest

botkeep 任务完成后调用。请求体：

```json
{
  "email": "Ew0lU2@twinkor.com",
  "tasks_done": 3,
  "points_earned": 65,
  "points": 65,
  "level": "Member",
  "detail": "Bing搜索3次+DailySet"
}
```

| 字段 | 必填 | 说明 |
|---|---|---|
| email | ✅ | 账号邮箱 |
| tasks_done | 否 | 本次完成任务数（默认 0） |
| points_earned | 否 | 本次获得积分（默认 0） |
| points | 否 | 当前总积分，传了则更新 |
| level | 否 | 当前等级（Member/Silver/Gold），传了则更新 |
| detail | 否 | 详情描述 |

响应：

```json
{"ok": true, "msg": "Ew0lU2@twinkor.com 结果已入库", "tasks_done": 3, "points_earned": 65}
```

行为：
1. 插入一条 run_log 记录
2. 若传了 points/level，更新 accounts 对应行的 points/level/last_run
3. 否则只更新 last_run

### POST /rewards/api/add

添加账号。请求体：`{"email": "xxx@twinkor.com", "password": "可选"}`

### curl 测试示例

```bash
# 查状态
curl -s http://170.106.115.45/rewards/api/status | python3 -m json.tool

# 回写结果
curl -s -X POST http://170.106.115.45/rewards/api/ingest \
  -H 'Content-Type: application/json' \
  -d '{"email":"Ew0lU2@twinkor.com","tasks_done":3,"points_earned":65,"points":65,"detail":"Bing搜索3次"}'
```

---

## 6. 数据库结构（SQLite）

文件：`/home/ubuntu/rewards-monitor/rewards.db`

### accounts 表

| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER PK | 自增 |
| email | TEXT UNIQUE | 账号邮箱 |
| password | TEXT | 密码（免密账号为 null） |
| passwordless | INTEGER | 1=免密验证码登录 |
| status | TEXT | active / pending_login / registering |
| points | INTEGER | 当前总积分 |
| level | TEXT | Member / Silver / Gold |
| last_login | TEXT | 最近登录时间 |
| last_run | TEXT | 最近执行时间 |
| note | TEXT | 备注 |
| created_at | TEXT | 创建时间 |

### run_log 表

| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER PK | 自增 |
| account_email | TEXT | 账号邮箱 |
| run_at | TEXT | 执行时间（默认 CURRENT_TIMESTAMP） |
| tasks_done | INTEGER | 完成任务数 |
| points_earned | INTEGER | 获得积分 |
| detail | TEXT | 详情 |

---

## 7. 账号清单与凭证

| 账号 | 密码 | 登录方式 | 状态 | 备注 |
|---|---|---|---|---|
| Ew0lU2@twinkor.com | 无 | 免密验证码 | active | 已登录验证，Dashboard 可用 |
| 6o9e3q3@twinkor.com | `Ove6zZlHqez7ZC+1c7` | 密码 | pending_login | 验证码登录今日被限流，约 24h 恢复 |

- 收信域名：twinkor.com（Cloudflare Email Routing 配置，可收信）
- 凭证另备份在沙箱 `rewards-accounts.json`
- **安全提醒**：密码已明文存于 DB 和本文档，注意保管，数据库不要公开

### 6o9e3q3 登录步骤（限流恢复后）

1. 浏览器打开 `https://login.live.com/login.srf?username=6o9e3q3@twinkor.com`
2. 点「发送验证码」，从 twinkor 邮箱取 6 位码
3. 填码登录
4. 登录成功后更新 DB：
   ```sql
   UPDATE accounts SET status='active', last_login=datetime('now','localtime'), note='登录成功' WHERE email='6o9e3q3@twinkor.com';
   ```
5. 打开 https://rewards.bing.com/dashboard 验证 Rewards 可访问

---

## 8. 沙箱侧（CatPaw）资料

沙箱工作目录：`/mnt/data/catpaw/home/.meituan-catpaw/9213145389/desk_default_workspace/rewards-monitor/`

| 文件 | 说明 |
|---|---|
| server.py | API 服务（与服务器上同版本） |
| dashboard.html | 监控页面（与服务器上同版本） |
| rewards.db | SQLite 副本 |
| ssh_run.py | SSH/SFTP 工具 |
| HANDOVER.md | 交接文档（与仓库 docs/ 同） |
| RewardsDashboard.jsx | Next.js 嵌入组件（备用） |
| rewards-accounts.json | 凭证备份 |

### ssh_run.py 用法

```bash
cd /mnt/data/catpaw/home/.meituan-catpaw/9213145389/desk_default_workspace/rewards-monitor/
python3 ssh_run.py "uname -a"                          # 执行远程命令
python3 ssh_run.py put ./server.py /home/ubuntu/rewards-monitor/server.py   # 传文件
```

内置 paramiko，SSH 连接失败自动重试 25 次（间隔 10s），应对 fail2ban 限流。

### 沙箱里的 Cloudflare Tunnel（备用）

之前用 cloudflared quick tunnel 暴露过沙箱 API（URL 每次重启会变，不稳定）。现在正式环境走服务器 nginx 反代，tunnel 仅作开发调试用。如需启用：

```bash
/tmp/cloudflared tunnel --url http://localhost:8765
# 输出中的 *.trycloudflare.com 即公网 URL
```

---

## 9. Rewards Bot 接入指南（待办）

### 参考项目

- GitHub：chiihero/Microsoft-Rewards-Bot
- 分支：V4-china，版本 v4.3.2.4
- 技术栈：TypeScript + Patchright（Playwright 反检测分支）
- 执行平台：**botkeep.cloud**

### 接入步骤

1. 在 botkeep.cloud 平台创建自动化任务
2. 配置微软账号凭证（email + password）
3. 任务流程：登录 rewards.bing.com → 跑 Bing 搜索 → Daily Set → Quiz → 退出
4. 任务完成后，botkeep 调用 POST http://170.106.115.45/rewards/api/ingest 回写结果
5. 监控页自动刷新展示

### botkeep 配置要点

- 任务调度：建议每天固定时间跑（微软任务每日刷新）
- 失败重试：网络抖动时重试 1~2 次
- 结果回写：即使部分成功也要回写已完成的 tasks_done/points_earned
- 风控：控制节奏，别短时间高频操作；别用主力账号

---

## 10. 已知限制与风险

1. **验证码登录限流**：微软对验证码登录有次数限制（"使用此登录方法的次数已达到上限"），约 24h 恢复。Ew0lU2 是免密账号不受影响；6o9e3q3 需等恢复。
2. **区域**：账号当前是美区（EN-US）。国区礼品卡（肯德基/盒马/麦德龙/天猫超市）需要用住宅 IP（中国）登录才会切到国区。服务器机房 IP 可能被微软判定异常。
3. **自动化合规**：自动化做 Rewards 任务属灰色操作，微软有风控，频繁/异常行为可能导致积分清零或封号。控制节奏、别用主力账号。
4. **quick tunnel 不稳定**：cloudflared 无认证 tunnel 无 uptime 保证，仅供调试。
5. **沙箱非持久**：CatPaw 沙箱重启后后台进程（server.py、cloudflared）会丢，需要手动拉起。服务器上的服务不受影响（setsid 脱离会话）。

---

## 11. 踩过的坑（按时间顺序）

1. **twinkor.com 能收信，twxxx.com 不能**：twxxx.com 是占位符不是真域名；收信用 twinkor.com。
2. **微软注册有「个人数据导出许可」页**（mkt=ZH-CN 时）：需点「同意并继续」。
3. **生日选择器是自定义下拉**：不是原生 select，paramiko/playwright 要先点 combobox 展开 listbox 再点 option。
4. **注册最后有 CAPTCHA**（「证明你不是机器人」iframe）：自动化过不去，需要人工在预览面板点。
5. **验证码登录限流**：频繁发码触发上限，24h 恢复。
6. **SFTP 不展开 `~`**：ssh_run.py 的 put 要用绝对路径 `/home/ubuntu/...`。
7. **pkill 后立即启动报 "Address already in use"**：等 2 秒再启动。
8. **8765 端口公网不通**：腾讯云安全组未开放；改用 nginx 80 端口反代 `/rewards/`。
9. **宝塔 nginx 配置路径**：`/www/server/panel/vhost/nginx/`，不是 `/etc/nginx/conf.d/`。
10. **80 端口默认站点陷阱**：0.default.conf 是 server_name _ 的兜底，但 IP 访问时精确匹配 starring-sub.conf（server_name 170.106.115.45），所以 /rewards/ 要加在 starring-sub.conf 里。
11. **location /api/ 冲突**：starring-sub.conf 已有 /api/ → 3000 端口，前端 fetch 必须用相对路径 `./api`。
12. **curl HEAD 请求 501**：Python http.server 简单实现不支持 HEAD，用 GET 测试。

---

## 12. 一句话现状

监控壳（页面 + API + DB + nginx 反代）已在 170.106.115.45 上线并公网可访问；botkeep.cloud 的 Rewards Bot 尚未接入，接入后 POST /rewards/api/ingest 即可让监控页自动展示每日积分。
