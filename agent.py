from __future__ import annotations
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from html import escape
from zgzcw_adapter import fetch_football_target_odds
from odds_adapter import external_market_for_event
ROOT=Path(__file__).parent; DATA=ROOT/'data'; DOCS=ROOT/'docs'; CST=timezone(timedelta(hours=8))
def load(p,d):
 try:return json.loads(p.read_text(encoding='utf8'))
 except:return d
def dump(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf8')
def add_history(snapshot):
 p=DATA/'zgzcw_history.json';h=load(p,[]);h.append(snapshot);dump(p,h[-240:])
def pct(p):return f'{p*100:.1f}%'
def market_text(m):
 return ('胜/平/负' if m['market']=='1X2' else '让球 '+str(m['line']))+f"：{m['home_win']:.2f} / {m['draw']:.2f} / {m['away_win']:.2f}"
def report(events, ext, errs, now):
 rows=[]
 for e in events:
  m=next((x for x in e['markets'] if x['market']=='1X2'),None); x=ext.get(e['source_match_id'],{})
  target='<br>'.join(market_text(z) for z in e['markets'])
  if not x.get('available') or not m:
   state='PASS：未取得足够的外部同场 1X2 数据'; exttext='外部市场：不足'
  else:
   p=x['median_fair']; books=len(x['books']); odds=[m['home_win'],m['draw'],m['away_win']]
   ev=[p[i]*odds[i]-1 for i in range(3)]
   # Mandatory conservative haircut: 2 points for non-sharp aggregation/stale-line risk.
   ce=[max(0,p[i]-.02)*odds[i]-1 for i in range(3)]
   labels=['主胜','平','客胜']; best=max(range(3),key=lambda i:ce[i])
   exttext=f"{books} 家外部机构；去水中位概率 {pct(p[0])}/{pct(p[1])}/{pct(p[2])}"
   if books>=3 and ce[best]>=.03:
    state=f"候选：{labels[best]}，保守EV {ce[best]*100:.1f}%"
   else: state=f"PASS：最佳保守EV {ce[best]*100:.1f}%"
  rows.append(f"<tr><td>{escape(e['code'])}</td><td>{escape(e['league'])}</td><td><b>{escape(e['home'])}</b> vs <b>{escape(e['away'])}</b></td><td>{escape(e['kickoff'])}</td><td>{target}</td><td>{escape(exttext)}</td><td>{escape(state)}</td></tr>")
 err='<br>'.join(escape(x) for x in errs) if errs else '中国竞彩公开页面与外部市场本次读取完成。'
 return f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>足球 EV 研究面板</title><style>body{{font-family:"Microsoft YaHei",Arial;background:#f4f7fb;color:#14213d;margin:0}}header{{background:#0c3e85;color:#fff;padding:24px max(16px,calc((100% - 1450px)/2))}}h1{{margin:0 0 8px}}main{{max-width:1450px;margin:20px auto;padding:0 16px}}.card{{background:#fff;padding:18px;border-radius:12px;margin-bottom:15px;box-shadow:0 2px 10px #0001}}table{{width:100%;border-collapse:collapse;font-size:13px}}th,td{{padding:10px;border-bottom:1px solid #e1e9f2;text-align:left;vertical-align:top}}th{{background:#eff6ff}}.warn{{background:#fff7ed;border-left:5px solid #f59e0b;padding:12px;line-height:1.7}}.small{{color:#62748b;font-size:13px;line-height:1.65}}</style><header><h1>足球 EV 研究面板</h1><div>最后采集：{now}（北京时间）</div></header><main><div class="card warn"><b>结论规则：</b>中国竞彩为最终目标价；外部概率为去水中位参考；保守EV会扣除 2 个百分点的信息与时效折扣。外部样本少于 3 家、没有同玩法或同盘口价格时，自动 PASS。The Odds API 不是自动等于 Pinnacle 或 Betfair。</div><div class="card"><h2>中国竞彩目标价 × 外部市场去水参考</h2><table><tr><th>编号</th><th>赛事</th><th>对阵</th><th>开赛</th><th>中国竞彩公开赔率</th><th>外部市场</th><th>EV 状态</th></tr>{''.join(rows)}</table></div><div class="card"><h2>来源状态</h2><p>{err}</p><p class="small">主力判断只使用同场同玩法的外部价格。比分、总进球、半全场仍需建立单独的比分分布模型，不能由 1X2 概率直接推出。</p></div></main>'''
def main():
 DATA.mkdir(exist_ok=True);DOCS.mkdir(exist_ok=True);now=datetime.now(CST).strftime('%Y-%m-%d %H:%M');errors=[];events=[];ext={}
 try:
  snap=fetch_football_target_odds();events=snap['events'];add_history(snap)
  for e in events:
   try:ext[e['source_match_id']]=external_market_for_event(e['home'],e['away'])
   except Exception as x:ext[e['source_match_id']]={'available':False,'errors':[type(x).__name__]}
 except Exception as x:errors.append('中国竞彩公开页读取失败：'+type(x).__name__)
 dump(DATA/'latest_external_markets.json',ext);dump(DATA/'latest_zgzcw.json',{'updated_at':now,'events':events,'errors':errors})
 (DOCS/'index.html').write_text(report(events,ext,errors,now),encoding='utf8')
if __name__=='__main__':main()
