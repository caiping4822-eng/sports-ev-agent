"""Cloud scheduler for the beginner-friendly Sports EV dashboard.
Only public schedule data and a user-provided, legal odds API key are used.
No scraping of gated betting sites. No bet recommendation is made without a verified target price.
"""
from __future__ import annotations
import csv, html, json, os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode

ROOT=Path(__file__).parent
DOCS=ROOT/'docs'; DATA=ROOT/'data'
CST=timezone(timedelta(hours=8))
NOW=datetime.now(CST)
TODAY=NOW.strftime('%Y%m%d')

LEAGUES=[
 ('WNBA','basketball','wnba'),
 ('英超','soccer','eng.1'),('西甲','soccer','esp.1'),('意甲','soccer','ita.1'),
 ('德甲','soccer','ger.1'),('法甲','soccer','fra.1'),
]

def get_json(url: str):
    req=Request(url, headers={'User-Agent':'Mozilla/5.0 SportsEV-Agent/1.0'})
    with urlopen(req, timeout=30) as res:
        return json.loads(res.read().decode('utf-8'))

def espn_events():
    output=[]; errors=[]
    for cname,sport,league in LEAGUES:
        u=f'https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard?dates={TODAY}'
        try:
            body=get_json(u)
            for e in body.get('events',[]):
                comp=(e.get('competitions') or [{}])[0]
                cs=comp.get('competitors',[])
                home=next((x for x in cs if x.get('homeAway')=='home'),{})
                away=next((x for x in cs if x.get('homeAway')=='away'),{})
                output.append({
                  'key':f'{cname}:{e.get("id")}', 'league':cname, 'start':e.get('date',''),
                  'away':away.get('team',{}).get('displayName','未知客队'),
                  'home':home.get('team',{}).get('displayName','未知主队'),
                  'status':e.get('status',{}).get('type',{}).get('description','未确认'),
                  'source':u,
                })
        except Exception as ex:
            errors.append(f'{cname}公开赛程抓取失败：{type(ex).__name__}')
    return output,errors

def odds_api_status():
    key=os.getenv('ODDS_API_KEY','').strip()
    if not key:
        return [], '未连接。请在 GitHub Secrets 中配置合法的 The Odds API Key。', []
    result=[]; errors=[]
    # Core codes; unavailable sports simply return an API error that is shown in the report.
    for sport_key,label in [('basketball_wnba','WNBA'),('soccer_epl','英超'),('soccer_spain_la_liga','西甲'),('soccer_italy_serie_a','意甲'),('soccer_germany_bundesliga','德甲'),('soccer_france_ligue_one','法甲')]:
        try:
            qs=urlencode({'apiKey':key,'regions':'us','markets':'h2h,spreads,totals','oddsFormat':'decimal'})
            data=get_json(f'https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?{qs}')
            result.extend({'league':label,'event':f"{x.get('away_team','')} vs {x.get('home_team','')}", 'bookmakers':len(x.get('bookmakers',[]))} for x in data)
        except Exception as ex:
            errors.append(f'{label}赔率暂不可用：{type(ex).__name__}')
    return result, ('已连接 The Odds API。仅作为主流市场参考；未接入 Pinnacle/Betfair 时，不会把它当作锐利盘。'), errors

def load_target_prices():
    # A guarded interface: target price must exist before a final EV result can ever be emitted.
    p=DATA/'china_odds.csv'; values=[]
    if not p.exists(): return values
    with p.open(encoding='utf-8') as f:
        for row in csv.DictReader(line for line in f if not line.startswith('#')):
            if row.get('target_decimal_odds'): values.append(row)
    return values

def page(events, schedule_errors, odds, odds_note, odds_errors, targets):
    rows=[]
    for e in events:
        start=e['start'].replace('T',' ')[:16]
        rows.append(f"<tr><td>{html.escape(e['league'])}</td><td><b>{html.escape(e['away'])}</b> vs <b>{html.escape(e['home'])}</b></td><td>{html.escape(start)}</td><td>{html.escape(e['status'])}</td><td class='pass'>PASS</td><td>当前尚未对齐中国竞彩目标赔率与锐利/交易所参考价；不输出猜测型推荐。</td></tr>")
    if not rows: rows.append("<tr><td colspan='6' class='muted'>今天此公开赛程源未返回匹配比赛。Agent 已完成检查。</td></tr>")
    notices=schedule_errors+odds_errors
    notice_html=''.join(f'<li>{html.escape(x)}</li>' for x in notices) or '<li>所有公开数据连接正常。</li>'
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>篮球足球 EV 智能助手</title><style>
body{{font-family:"Microsoft YaHei",Arial,sans-serif;background:#f3f7fb;color:#15253f;margin:0}}header{{background:linear-gradient(120deg,#073b79,#2563eb);color:#fff;padding:28px max(20px,calc((100% - 1250px)/2))}}h1{{margin:0 0 8px;font-size:27px}}header p{{margin:0;opacity:.9}}main{{max-width:1250px;margin:20px auto;padding:0 18px}}.card{{background:white;border-radius:14px;padding:20px;margin:16px 0;box-shadow:0 3px 14px #17376012}}.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}}.metric{{background:#eff6ff;border-radius:10px;padding:14px;line-height:1.7}}.metric b{{color:#075985}}table{{width:100%;border-collapse:collapse;font-size:14px}}th,td{{padding:12px 10px;text-align:left;border-bottom:1px solid #e6edf5;vertical-align:top}}th{{background:#edf5ff;color:#23446c}}.pass{{font-weight:bold;color:#b91c1c}}.muted{{color:#64748b}}.notice{{background:#fff7ed;border-left:5px solid #f59e0b;padding:12px 15px;line-height:1.7}}ul{{margin:7px 0;padding-left:20px}}@media(max-width:700px){{.grid{{grid-template-columns:1fr}}table{{font-size:12px}}}}
</style></head><body><header><h1>篮球足球 EV 智能助手</h1><p>云端自动运行 · 最后更新：{NOW.strftime('%Y-%m-%d %H:%M')}（北京时间）</p></header><main>
<div class="card"><h2>今天先看这里</h2><div class="grid"><div class="metric"><b>赛程状态</b><br>自动检查到 {len(events)} 场 WNBA / 五大联赛比赛。</div><div class="metric"><b>赔率状态</b><br>{html.escape(odds_note)}</div><div class="metric"><b>最终规则</b><br>没有中国竞彩目标价格、锐利/交易所价格和伤停确认，就一律 PASS。</div></div></div>
<div class="card"><h2>自动分析结果</h2><div class="notice"><b>说明：</b>这不是“每天强行推荐”的页面。只有保守 EV 通过阈值后才会显示“可投候选”；当前未完成完整价格对齐时，显示 PASS 是正确的风险控制。</div><div style="overflow:auto"><table><tr><th>联赛</th><th>比赛</th><th>开赛时间</th><th>状态</th><th>结论</th><th>原因</th></tr>{''.join(rows)}</table></div></div>
<div class="card"><h2>数据连接与日志</h2><ul>{notice_html}</ul><p class="muted">公开源：ESPN 赛程。赔率：仅在你配置合法 The Odds API Key 后抓取。Pinnacle/PS3838、Betfair 交易所、正式中国竞彩目标价均需合法授权数据源，系统不会伪造这些数据。</p></div>
</main></body></html>'''

def main():
    events, se=espn_events()
    odds,onote,oe=odds_api_status()
    targets=load_target_prices()
    DOCS.mkdir(exist_ok=True); DATA.mkdir(exist_ok=True)
    (DOCS/'index.html').write_text(page(events,se,odds,onote,oe,targets),encoding='utf-8')
    (DATA/'latest.json').write_text(json.dumps({'updated_at':NOW.isoformat(),'events':events,'odds_status':onote,'odds_events':odds,'errors':se+oe},ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__': main()
