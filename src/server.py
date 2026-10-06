#!/usr/bin/env python3
"""Rewards 监控服务：SQLite + JSON API + Web 页面"""
import json, os, sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rewards.db")
PORT = 8765

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT,
            passwordless INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active',
            points INTEGER DEFAULT 0,
            level TEXT,
            last_login TEXT,
            last_run TEXT,
            note TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS run_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_email TEXT,
            run_at TEXT DEFAULT CURRENT_TIMESTAMP,
            tasks_done INTEGER DEFAULT 0,
            points_earned INTEGER DEFAULT 0,
            detail TEXT
        )
    """)
    accounts = [
        ("Ew0lU2@twinkor.com", None, 1, "active", 0, None,
         "已登录验证，Dashboard 可用，免密验证码登录"),
        ("6o9e3q3@twinkor.com", "Ove6zZlHqez7ZC+1c7", 0, "pending_login", 0, None,
         "已注册，验证码登录今日被限流，需明天重试"),
    ]
    for a in accounts:
        conn.execute(
            """INSERT OR IGNORE INTO accounts
               (email,password,passwordless,status,points,last_login,note) VALUES (?,?,?,?,?,?,?)""", a)
    conn.commit()
    conn.close()

def query(sql, params=()):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def execute_sql(sql, params=()):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(sql, params)
    conn.commit()
    last = cur.lastrowid
    conn.close()
    return last

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Rewards 监控</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#0f1117;color:#e1e4e8;padding:24px;line-height:1.5}
h1{font-size:22px;margin-bottom:4px;color:#58a6ff}
.sub{color:#8b949e;font-size:13px;margin-bottom:24px}
.warp{max-width:900px;margin:0 auto}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px;margin-bottom:32px}
.card{background:linear-gradient(180deg,#161b22 0%,#13171d 100%);border:1px solid #30363d;border-radius:12px;padding:20px}
.card h3{font-size:13px;color:#8b949e;text-transform:uppercase;letter-spacing:.5px;margin-bottom:12px}
.kv{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #21262d;font-size:14px}
.kv:last-child{border-bottom:none}
.kv .k{color:#8b949e}
.kv .v{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;color:#e1e4e8;word-break:break-all}
.badge{display:inline-block;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600}
.badge.active{background:#1b4332;color:#3fb950}
.badge.pending_login{background:#3d2e00;color:#d29922}
.pts{font-size:32px;font-weight:700;color:#58a6ff;margin:4px 0 2px}
.pts-unit{font-size:12px;color:#8b949e}
.section-title{font-size:18px;margin:28px 0 12px;color:#c9d1d9}
.btn{background:#238636;color:#fff;border:0;padding:8px 16px;border-radius:6px;cursor:pointer;font-size:13px;margin-right:8px}
.btn:hover{background:#2ea043}
.btn-sec{background:#21262d;border:1px solid #30363d;color:#c9d1d9}
.toolbar{margin-bottom:20px}
.run-log{width:100%;border-collapse:collapse;font-size:13px}
.run-log th,.run-log td{text-align:left;padding:10px 12px;border-bottom:1px solid #21262d}
.run-log th{color:#8b949e;font-weight:500;font-size:12px;text-transform:uppercase}
.tag{display:inline-block;padding:1px 6px;border-radius:4px;font-size:11px;background:#1c2d40;color:#79c0ff}
.toast{position:fixed;bottom:24px;right:24px;background:#238636;color:#fff;padding:12px 20px;border-radius:8px;font-size:13px;display:none;z-index:99}
</style>
</head>
<body>
<div class="warp">
<h1>Rewards 监控面板</h1>
<div class="sub" id="ts">加载中…</div>
<div class="toolbar">
  <button class="btn" onclick="refresh()">刷新</button>
  <button class="btn btn-sec" onclick="addPrompt()">+ 添加账号</button>
</div>
<div class="cards" id="cards"></div>
<div class="section-title">执行日志</div>
<table class="run-log" id="log">
  <tr><th>账号</th><th>时间</th><th>完成任务</th><th>获得积分</th><th>详情</th></tr>
</table>
</div>
<div class="toast" id="toast"></div>
<script>
const $=id=>document.getElementById(id);
const API='./api';
async function api(method,body){
  const r=await fetch(API+(method==='status'?'/status':'/'+method),{method:body?'POST':'GET',
    headers:{'Content-Type':'application/json'},
    body:body?JSON.stringify(body):null});
  return r.json();
}
function mask(s){return s?'••••••••':'-'}
function showPw(el,pw){if(!pw)return;el.textContent=pw;el.classList.remove('masked')}
async function load(){
  const d=await api('status');
  $('ts').textContent='更新于 '+new Date().toLocaleString('zh-CN');
  const cards=$('cards');cards.innerHTML='';
  for(const a of d.accounts){
    const lvl=(a.level||'-').replace('Member','普通').replace('Silver','白银').replace('Gold','黄金');
    const pw=a.password||'';
    cards.innerHTML+=`
    <div class="card">
      <h3>${a.email}</h3>
      <div class="pts">${a.points.toLocaleString('en-US')}<span class="pts-unit"> 积分 · ${lvl}</span></div>
      <span class="badge ${a.status}">${a.status}</span>
      <div style="margin-top:14px">
        <div class="kv"><span class="k">状态</span><span class="v">${a.note||'-'}</span></div>
        <div class="kv"><span class="k">密码</span>
          <span class="v pw masked" data-pw="${pw}" onclick="showPw(this,this.dataset.pw)">${pw?mask(pw):'-'}</span>
        </div>
        ${a.passwordless?'<div class="kv"><span class="k">登录方式</span><span class="v">免密验证码</span></div>':''}
        <div class="kv"><span class="k">最近登录</span><span class="v">${a.last_login||'-'}</span></div>
        <div class="kv"><span class="k">最近执行</span><span class="v">${a.last_run||'-'}</span></div>
      </div>
    </div>`;
  }
  const log=$('log');
  log.innerHTML='<tr><th>账号</th><th>时间</th><th>完成任务</th><th>获得积分</th><th>详情</th></tr>';
  for(const r of d.log){
    log.innerHTML+=`<tr><td><span class="tag">${r.account_email}</span></td><td>${r.run_at}</td><td>${r.tasks_done}</td><td>${r.points_earned}</td><td>${r.detail||'-'}</td></tr>`;
  }
}
async function refresh(){await load();showToast('已刷新')}
function addPrompt(){
  const e=prompt('邮箱：');if(!e)return;
  const p=prompt('密码（可留空）：');
  api('add',{email:e,password:p||null}).then(r=>{showToast(r.msg||'done');load()});
}
function showToast(t){const o=$('toast');o.textContent=t;o.style.display='block';setTimeout(()=>o.style.display='none',2500)}
load();
</script>
</body>
</html>"""

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def _json(self, code, data):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _html(self, html):
        body = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/dashboard.html":
            return self._html(DASHBOARD_HTML)
        if u.path in ("/", "/index.html"):
            return self._html(DASHBOARD_HTML)
        if u.path == "/api/status":
            accounts = query("SELECT * FROM accounts ORDER BY id")
            log = query("SELECT * FROM run_log ORDER BY id DESC LIMIT 10")
            return self._json(200, {"accounts": accounts, "log": log, "server_time": datetime.now().isoformat()})
        self._json(404, {"error": "not found"})

    def do_POST(self):
        u = urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(body)
        except Exception:
            data = {}
        if u.path == "/api/ingest":
            # botkeep.cloud 或本地 bot 回写执行结果
            # body: {email, tasks_done, points_earned, detail, points(当前总积分), level}
            email = (data.get("email") or "").strip()
            tasks_done = int(data.get("tasks_done") or 0)
            points_earned = int(data.get("points_earned") or 0)
            detail = data.get("detail") or ""
            cur_points = data.get("points")
            level = data.get("level")
            if not email:
                return self._json(400, {"error": "email required"})
            execute_sql(
                "INSERT INTO run_log (account_email,tasks_done,points_earned,detail) VALUES (?,?,?,?)",
                (email, tasks_done, points_earned, detail))
            if cur_points is not None or level:
                execute_sql(
                    "UPDATE accounts SET points=COALESCE(?,points), level=COALESCE(?,level), last_run=datetime('now','localtime') WHERE email=?",
                    (cur_points, level, email))
            else:
                execute_sql(
                    "UPDATE accounts SET last_run=datetime('now','localtime') WHERE email=?",
                    (email,))
            return self._json(200, {"ok": True, "msg": f"{email} 结果已入库", "tasks_done": tasks_done, "points_earned": points_earned})
        if u.path == "/api/add":
            email = (data.get("email") or "").strip()
            pw = data.get("password")
            if not email:
                return self._json(400, {"error": "email required"})
            execute_sql("INSERT OR IGNORE INTO accounts (email,password,note) VALUES (?,?,?)",
                        (email, pw, "手动添加"))
            return self._json(200, {"ok": True, "msg": email + " 已添加"})
        self._json(404, {"error": "not found"})

if __name__ == "__main__":
    init_db()
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), H)
    print("LISTEN :" + str(PORT), flush=True)
    srv.serve_forever()
