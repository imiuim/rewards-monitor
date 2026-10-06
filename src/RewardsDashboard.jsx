'use client';

import { useEffect, useState, useCallback } from 'react';

/**
 * Rewards 监控面板 — Next.js 页面组件
 * 
 * 嵌入方式：
 *   1. 复制本文件到主项目的 app/rewards/page.jsx（App Router）或 pages/rewards.jsx（Pages Router）
 *   2. 构造时传入 apiUrl 即可，例如：<RewardsDashboard apiUrl="https://xxx.trycloudflare.com/api/status" />
 *   3. 也可通过环境变量 NEXT_PUBLIC_REWARDS_API 注入
 * 
 * 数据源：本地 rewards-monitor/server.py 提供的 GET /api/status
 * 需要 Cloudflare Tunnel 把 localhost:8765 暴露为公网地址
 */

const FALLBACK_API = 'http://localhost:8765/api/status';

export default function RewardsDashboard({ apiUrl }) {
  const URL = apiUrl || process.env.NEXT_PUBLIC_REWARDS_API || FALLBACK_API;
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);
  const [ts, setTs] = useState(null);

  const load = useCallback(async () => {
    try {
      const r = await fetch(URL, { cache: 'no-store' });
      if (!r.ok) throw new Error('HTTP ' + r.status);
      const j = await r.json();
      setData(j);
      setTs(new Date());
      setErr(null);
    } catch (e) {
      setErr(e.message);
    }
  }, [URL]);

  useEffect(() => {
    load();
    const t = setInterval(load, 60000); // 每分钟刷新
    return () => clearInterval(t);
  }, [load]);

  if (err && !data) return <Shell ts={ts} onRefresh={load}><ErrorBox err={err} url={URL} /></Shell>;
  if (!data) return <Shell ts={ts} onRefresh={load}><Loading /></Shell>;

  return (
    <Shell ts={ts} onRefresh={load}>
      <StatsRow accounts={data.accounts} />
      <SectionTitle>账号详情</SectionTitle>
      <div className="grid">
        {data.accounts.map(a => <AccountCard key={a.email} a={a} />)}
      </div>
      <SectionTitle>执行日志</SectionTitle>
      <LogTable log={data.log} />
    </Shell>
  );
}

/* ---------- 布局 ---------- */
function Shell({ children, ts, onRefresh }) {
  return (
    <div style={S.page}>
      <header style={S.header}>
        <div>
          <h1 style={S.h1}>🎁 Rewards 监控</h1>
          <div style={S.sub}>{ts ? '更新于 ' + ts.toLocaleString('zh-CN') : '加载中…'}</div>
        </div>
        <button style={S.btn} onClick={onRefresh}>刷新</button>
      </header>
      <main style={S.main}>{children}</main>
    </div>
  );
}

function StatsRow({ accounts }) {
  const total = accounts.reduce((s, a) => s + (a.points || 0), 0);
  const active = accounts.filter(a => a.status === 'active').length;
  const pending = accounts.filter(a => a.status === 'pending_login').length;
  return (
    <div style={S.statsRow}>
      <StatCard label="账号总数" value={accounts.length} accent="#58a6ff" />
      <StatCard label="总积分" value={total.toLocaleString('en-US')} accent="#3fb950" />
      <StatCard label="激活" value={active} accent="#3fb950" />
      <StatCard label="待登录" value={pending} accent="#d29922" />
    </div>
  );
}

function StatCard({ label, value, accent }) {
  return (
    <div style={{ ...S.statCard, borderTop: `3px solid ${accent}` }}>
      <div style={{ ...S.statValue, color: accent }}>{value}</div>
      <div style={S.statLabel}>{label}</div>
    </div>
  );
}

function AccountCard({ a }) {
  const [showPw, setShowPw] = useState(false);
  const lvlMap = { Member: '普通', Silver: '白银', Gold: '黄金' };
  const lvl = lvlMap[a.level] || a.level || '-';
  const statusMap = { active: ['激活', '#3fb950', '#1b4332'], pending_login: ['待登录', '#d29922', '#3d2e00'], registering: ['注册中', '#d29922', '#3d2e00'] };
  const [stLabel, stClr, stBg] = statusMap[a.status] || [a.status, '#8b949e', '#21262d'];

  return (
    <div style={S.card}>
      <div style={S.cardHead}>
        <span style={S.email}>{a.email}</span>
        <span style={{ ...S.badge, color: stClr, background: stBg }}>{stLabel}</span>
      </div>
      <div style={S.pts}>{a.points?.toLocaleString('en-US') || 0}<span style={S.ptsUnit}> 积分 · {lvl}</span></div>
      <div style={S.kvs}>
        <Row k="密码" v={a.password ? (showPw ? a.password : '••••••••') : a.passwordless ? '免密' : '-'}
             clickable={!!a.password} onClick={() => setShowPw(!showPw)} />
        <Row k="登录方式" v={a.passwordless ? '免密验证码' : '密码'} />
        <Row k="最近登录" v={a.last_login || '-'} />
        <Row k="最近执行" v={a.last_run || '-'} />
      </div>
      {a.note && <div style={S.note}>{a.note}</div>}
    </div>
  );
}

function Row({ k, v, clickable, onClick }) {
  return (
    <div style={S.kv}>
      <span style={S.kk}>{k}</span>
      <span style={{ ...S.vv, cursor: clickable ? 'pointer' : 'default', color: clickable ? '#3fb950' : '#e1e4e8' }}
            onClick={onClick} title={clickable ? '点击显示/隐藏' : ''}>{v}</span>
    </div>
  );
}

function LogTable({ log }) {
  if (!log?.length) return <div style={S.empty}>暂无执行日志</div>;
  return (
    <table style={S.tbl}>
      <thead><tr>
        <th style={S.th}>账号</th><th style={S.th}>时间</th>
        <th style={S.th}>完成任务</th><th style={S.th}>积分</th><th style={S.th}>详情</th>
      </tr></thead>
      <tbody>
        {log.map(r => (
          <tr key={r.id}>
            <td style={S.td}><span style={S.tag}>{r.account_email}</span></td>
            <td style={S.td}>{r.run_at}</td>
            <td style={S.td}>{r.tasks_done}</td>
            <td style={S.td}>{r.points_earned}</td>
            <td style={S.td}>{r.detail || '-'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function SectionTitle({ children }) { return <h2 style={S.secTitle}>{children}</h2>; }
function Loading() { return <div style={S.empty}>加载中…</div>; }
function ErrorBox({ err, url }) { return <div style={S.empty}>⚠️ 数据源不可达：{err}<br /><span style={{ color: '#8b949e', fontSize: 12 }}>{url}</span><br /><span style={{ color: '#8b949e', fontSize: 12 }}>请先运行 server.py 并确认 Cloudflare Tunnel 已启动，或传入 apiUrl</span></div>; }

/* ---------- 样式（纯内联，嵌入主项目零依赖） ---------- */
const S = {
  page: { minHeight: '100vh', background: '#0f1117', color: '#e1e4e8', padding: '24px', fontFamily: '-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', maxWidth: '960px', margin: '0 auto 24px' },
  h1: { fontSize: 22, margin: 0, color: '#58a6ff' },
  sub: { color: '#8b949e', fontSize: 13, marginTop: 4 },
  main: { maxWidth: 960, margin: '0 auto' },
  btn: { background: '#238636', color: '#fff', border: 0, padding: '8px 18px', borderRadius: 6, cursor: 'pointer', fontSize: 14 },
  statsRow: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(150px,1fr))', gap: 16, marginBottom: 32 },
  statCard: { background: '#161b22', border: '1px solid #30363d', borderRadius: 12, padding: 20 },
  statValue: { fontSize: 28, fontWeight: 700 },
  statLabel: { color: '#8b949e', fontSize: 12, marginTop: 2 },
  secTitle: { fontSize: 18, margin: '28px 0 12px', color: '#c9d1d9' },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(300px,1fr))', gap: 16 },
  card: { background: 'linear-gradient(180deg,#161b22,#13171d)', border: '1px solid #30363d', borderRadius: 12, padding: 20 },
  cardHead: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
  email: { fontFamily: 'ui-monospace,SFMono-Regular,Menlo,monospace', fontSize: 14, color: '#e1e4e8' },
  badge: { padding: '2px 8px', borderRadius: 12, fontSize: 11, fontWeight: 600 },
  pts: { fontSize: 28, fontWeight: 700, color: '#58a6ff', margin: '4px 0 14px' },
  ptsUnit: { fontSize: 12, color: '#8b949e', fontWeight: 400 },
  kvs: { borderTop: '1px solid #21262d', paddingTop: 8 },
  kv: { display: 'flex', justifyContent: 'space-between', padding: '6px 0', fontSize: 14 },
  kk: { color: '#8b949e' },
  vv: { fontFamily: 'ui-monospace,SFMono-Regular,Menlo,monospace' },
  note: { marginTop: 10, paddingTop: 8, borderTop: '1px dashed #30363d', color: '#8b949e', fontSize: 12 },
  tbl: { width: '100%', borderCollapse: 'collapse', fontSize: 13 },
  th: { textAlign: 'left', padding: '10px 12px', borderBottom: '1px solid #21262d', color: '#8b949e', fontWeight: 500, fontSize: 12, textTransform: 'uppercase' },
  td: { padding: '10px 12px', borderBottom: '1px solid #21262d' },
  tag: { padding: '1px 6px', borderRadius: 4, fontSize: 11, background: '#1c2d40', color: '#79c0ff' },
  empty: { textAlign: 'center', padding: 60, color: '#8b949e' },
};
