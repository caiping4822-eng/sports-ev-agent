from __future__ import annotations
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from html import escape
from zgzcw_adapter import fetch_football_target_odds,fetch_bjzs_average,fetch_total_goal_odds
from odds_adapter import external_market_for_event
from goal_model import summary
ROOT=Path(__file__).parent;DATA=ROOT/'data';DOCS=ROOT/'docs';CST=timezone(timedelta(hours=8))
def load(p,d):
 try:return json.loads(p.read_text(encoding='utf8'))
 except:return d
def dump(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf8')
def novig(o):
 x=[1/v for v in o];s=sum(x);return [v/s for v in x]
def pct(p):return f'{p*100:.1f}%'
def add_history(s):
 p=DATA/'zgzcw_history.json';h=load(p,[]);h.append(s);dump(p,h[-240:])
def market_text(m):return ('胜/平/负' if m['market']=='1X2' else '让球 '+str(m['line']))+f"：{m['home_win']:.2f} / {m['draw']:.2f} / {m['away_win']:.2f}"
def page(events,bjzs,ext,errors,now,notes,goalodds):
 rows=[]
 research=[]
 models=[]
 for e in events:
  target=next((m for m in e['markets'] if m['market']=='1X2'),None); b=bjzs.get(e.get('analysis_match_id') or e['source_match_id']); x=ext.get(e['source_match_id'],{})
  ctext='<br>'.join(market_text(m) for m in e['markets'])
  benchmark='无百家平均参考'; state='PASS：未取得同玩法外部参考'
  if b and target:
   p=novig(b['current']); o=[target['home_win'],target['draw'],target['away_win']]
   gm=summary(p); tg=goalodds.get(e['source_match_id']);
   top=' / '.join(f'{sc} {pr*100:.1f}%' for sc,pr in gm['scores']); total=' / '.join(f'{i}球 {gm["totals"][i]*100:.1f}%' for i in range(4)); cn=('；中国竞彩总进球：'+' / '.join(f'{i}球 {tg[i]:.2f}' for i in range(4))) if tg else ''
   models.append(f"<div class='research'><h3>{escape(e['code'])} 进球分布模型</h3><p><b>预期进球：</b>{gm['lambda_home']:.2f} - {gm['lambda_away']:.2f}</p><p><b>最可能比分：</b>{top}</p><p><b>总进球概率：</b>{total}{cn}</p><p class='small'>仅由百家平均1X2拟合，属于研究参考；未叠加独立大小球、伤停或首发，不产生自动投注建议。</p></div>")
   ev=[max(0,p[i]-.02)*o[i]-1 for i in range(3)];labels=['主胜','平','客胜'];best=max(range(3),key=lambda i:ev[i])
   benchmark=f"百家平均<br>开盘 {b['opening'][0]:.2f}/{b['opening'][1]:.2f}/{b['opening'][2]:.2f}<br>当前 {b['current'][0]:.2f}/{b['current'][1]:.2f}/{b['current'][2]:.2f}<br>去水 {pct(p[0])}/{pct(p[1])}/{pct(p[2])}"
   # Composite public average is a reference layer only, never sufficient alone for a bet.
   state=f"观察：{labels[best]} 保守EV参考 {ev[best]*100:.1f}%；需独立外部源确认"
  if x.get('available') and len(x.get('books',[]))>=3 and target:
   p=x['median_fair'];o=[target['home_win'],target['draw'],target['away_win']];ev=[max(0,p[i]-.02)*o[i]-1 for i in range(3)];labels=['主胜','平','客胜'];best=max(range(3),key=lambda i:ev[i]);benchmark+=f"<br>The Odds {len(x['books'])}家：{pct(p[0])}/{pct(p[1])}/{pct(p[2])}";state=(f"候选：{labels[best]}，保守EV {ev[best]*100:.1f}%" if ev[best]>=.03 else f"PASS：最佳保守EV {ev[best]*100:.1f}%")
  rows.append(f"<tr><td>{escape(e['code'])}</td><td>{escape(e['league'])}</td><td><b>{escape(e['home'])}</b> vs <b>{escape(e['away'])}</b></td><td>{escape(e['kickoff'])}</td><td>{ctext}</td><td>{benchmark}</td><td>{escape(state)}</td></tr>")
  n=notes.get('events',{}).get(e.get('analysis_match_id','')) or notes.get('by_code',{}).get(e['code'])
  if n:
   links=' ｜ '.join(f'<a href="{escape(u)}" target="_blank">{escape(t)}</a>' for t,u in n.get('sources',[]))
   confirmed='；'.join(n.get('confirmed',[]))
   research.append(f"<div class='research'><h3>{escape(e['code'])} {escape(e['home'])} vs {escape(e['away'])}</h3><p><b>研究等级：</b>{escape(n.get('tier',''))}</p><p><b>比赛背景：</b>{escape(n.get('summary',''))}</p><p><b>已核验事项：</b>{escape(confirmed)}</p><p><b>反向风险：</b>{escape(n.get('risk',''))}</p><p class='small'><b>来源：</b>{links}</p></div>")
 errs='<br>'.join(escape(x) for x in errors) if errors else '足彩网竞彩页与百家指数页本次读取成功。'
 return f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>足球 EV 研究面板</title><style>body{{font-family:"Microsoft YaHei",Arial;background:#f4f7fb;color:#14213d;margin:0}}header{{background:#0c3e85;color:#fff;padding:24px max(16px,calc((100% - 1450px)/2))}}h1{{margin:0 0 8px}}main{{max-width:1450px;margin:20px auto;padding:0 16px}}.card{{background:#fff;padding:18px;border-radius:12px;margin-bottom:15px;box-shadow:0 2px 10px #0001}}table{{width:100%;border-collapse:collapse;font-size:13px}}th,td{{padding:10px;border-bottom:1px solid #e1e9f2;text-align:left;vertical-align:top}}th{{background:#eff6ff}}.warn{{background:#fff7ed;border-left:5px solid #f59e0b;padding:12px;line-height:1.7}}.small{{color:#62748b;font-size:13px;line-height:1.65}}.research{{border-left:4px solid #2563eb;background:#f8fbff;padding:10px 14px;margin:10px 0;line-height:1.65}}.research h3{{margin:0 0 5px}}.research p{{margin:5px 0}}</style><header><h1>足球 EV 研究面板</h1><div>最后采集：{now}（北京时间）</div></header><main><div class="card warn"><b>三层规则：</b>中国竞彩是目标成交价；足彩网百家平均仅是公开聚合参考，不足以单独出投注；The Odds API 若返回至少 3 家同场机构，才参与保守EV计算。Pinnacle/Betfair未实际返回时，页面不会声称已接入。</div><div class="card"><h2>中国竞彩目标价 × 百家平均 × 外部市场</h2><table><tr><th>编号</th><th>赛事</th><th>对阵</th><th>开赛</th><th>中国竞彩</th><th>外部参考</th><th>状态</th></tr>{''.join(rows)}</table></div><div class="card"><h2>基本面与伤停研究卡</h2><p class="small">以下是本轮赛前人工核验的事实层；临场首发和最终伤停仍应在开赛前复核。</p>{''.join(research) if research else '暂无已核验研究卡。'}</div><div class="card"><h2>进球与比分分布模型</h2><p class="small">基于百家平均去水1X2拟合的泊松分布；用于校验中国竞彩总进球和比分结构，不单独出投注。</p>{''.join(models) if models else '暂无模型输入。'}</div><div class="card"><h2>来源状态</h2><p>{errs}</p><p class="small">百家平均可用于记录开盘到当前的市场变化；比分、总进球、半全场仍须使用独立分布模型，不从 1X2 直接推导投注。</p></div></main>'''
def main():
 DATA.mkdir(exist_ok=True);DOCS.mkdir(exist_ok=True);now=datetime.now(CST).strftime('%Y-%m-%d %H:%M');errors=[];events=[];bjzs={};ext={};goalodds={};notes=load(DATA/'fundamentals_current.json',{})
 try:
  snap=fetch_football_target_odds();events=snap['events'];add_history(snap)
 except Exception as e:errors.append('竞彩页读取失败：'+type(e).__name__)
 try:bjzs=fetch_bjzs_average()
 except Exception as e:errors.append('百家指数读取失败：'+type(e).__name__)
 try:goalodds=fetch_total_goal_odds()
 except Exception as e:errors.append('总进球读取失败：'+type(e).__name__)
 for e in events:
  try:ext[e['source_match_id']]=external_market_for_event(e['home'],e['away'])
  except Exception as x:ext[e['source_match_id']]={'available':False,'errors':[type(x).__name__]}
 dump(DATA/'latest_external_markets.json',ext);dump(DATA/'latest_bjzs.json',bjzs);dump(DATA/'latest_zgzcw.json',{'updated_at':now,'events':events,'errors':errors})
 (DOCS/'index.html').write_text(page(events,bjzs,ext,errors,now,notes,goalodds),encoding='utf8')
if __name__=='__main__':main()
