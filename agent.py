from __future__ import annotations
import json, os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from html import escape
from zgzcw_adapter import fetch_football_target_odds

ROOT=Path(__file__).parent; DATA=ROOT/'data'; DOCS=ROOT/'docs'; CST=timezone(timedelta(hours=8))

def load_json(p, default):
    try:return json.loads(p.read_text(encoding='utf-8'))
    except:return default

def save_json(p,obj): p.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')

def add_snapshot(snapshot):
    p=DATA/'zgzcw_history.json'; h=load_json(p,[])
    h.append(snapshot)
    save_json(p,h[-240:]) # 240 low-frequency snapshots maximum

def odds_row(m):
    if m['market']=='1X2': return f"胜/平/负：{m['home_win']:.2f} / {m['draw']:.2f} / {m['away_win']:.2f}"
    return f"让球 {escape(str(m['line']))}：{m['home_win']:.2f} / {m['draw']:.2f} / {m['away_win']:.2f}"

def render(events, errors, now):
    trs=[]
    for e in events:
        prices='<br>'.join(odds_row(m) for m in e['markets']) or '无可解析公开赔率'
        trs.append(f"<tr><td>{escape(e['code'])}</td><td>{escape(e['league'])}</td><td><b>{escape(e['home'])}</b> vs <b>{escape(e['away'])}</b></td><td>{escape(e['kickoff'])}</td><td>{prices}</td><td>等待外部市场、伤停和模型联合审计</td></tr>")
    if not trs:trs=['<tr><td colspan="6">公开页面当前未返回可售足球赛事。</td></tr>']
    es='<br>'.join(escape(x) for x in errors) if errors else '足彩网公开页面本次读取成功。'
    return f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>足球 EV 研究面板</title><style>body{{font-family:"Microsoft YaHei",Arial;background:#f4f7fb;color:#14213d;margin:0}}header{{background:#0c3e85;color:#fff;padding:24px max(16px,calc((100% - 1250px)/2))}}h1{{margin:0 0 8px}}main{{max-width:1250px;margin:20px auto;padding:0 16px}}.card{{background:#fff;padding:18px;border-radius:12px;margin-bottom:15px;box-shadow:0 2px 10px #0001}}table{{width:100%;border-collapse:collapse;font-size:14px}}th,td{{padding:10px;border-bottom:1px solid #e1e9f2;text-align:left;vertical-align:top}}th{{background:#eff6ff}}.warn{{background:#fff7ed;border-left:5px solid #f59e0b;padding:12px;line-height:1.7}}.small{{color:#62748b;font-size:13px;line-height:1.65}}</style><header><h1>足球 EV 研究面板</h1><div>最后采集：{now}（北京时间）</div></header><main><div class="card warn"><b>数据规则：</b>中国竞彩赔率来自足彩网公开页面的低频快照，仅作为目标成交价参考。它不是官方 API、不是 Pinnacle、不是 Betfair Exchange；访问失败时系统停止并显示错误，不会伪造价格。</div><div class="card"><h2>中国竞彩公开目标价</h2><table><tr><th>编号</th><th>赛事</th><th>对阵</th><th>开赛</th><th>公开页面赔率</th><th>EV 状态</th></tr>{''.join(trs)}</table></div><div class="card"><h2>来源状态</h2><p>{es}</p><p class="small">下一阶段会把该目标价与 The Odds API、公开外部市场、官方伤停和赛制模型对齐。没有同玩法、同盘口的外部参考价时，系统默认 PASS。</p></div></main>'''

def main():
    now=datetime.now(CST).strftime('%Y-%m-%d %H:%M')
    errors=[]; events=[]
    try:
        snap=fetch_football_target_odds();events=snap['events']; add_snapshot(snap)
    except Exception as e:
        errors.append(f'足彩网公开页面本次不可用：{type(e).__name__}。本次不更新目标价。')
    DOCS.mkdir(exist_ok=True);DATA.mkdir(exist_ok=True)
    (DOCS/'index.html').write_text(render(events,errors,now),encoding='utf-8')
    save_json(DATA/'latest_zgzcw.json',{'updated_at':now,'events':events,'errors':errors})
if __name__=='__main__':main()
