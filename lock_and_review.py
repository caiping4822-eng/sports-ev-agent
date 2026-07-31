from __future__ import annotations
import json, os, re
from datetime import datetime,timezone,timedelta
from pathlib import Path
from html import escape
from api_football import fetch_context,call
ROOT=Path(__file__).parent;DATA=ROOT/'data';DOCS=ROOT/'docs';CST=timezone(timedelta(hours=8))
def load(p,d):
 try:return json.loads(p.read_text(encoding='utf8'))
 except:return d
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf8')
def no_vig(a,b,c):
 x=[1/a,1/b,1/c];s=sum(x);return [v/s for v in x]
def make_forced(events,bjzs):
 all=[]
 for e in events:
  t=next((m for m in e.get('markets',[]) if m.get('market')=='1X2'),None);b=bjzs.get(e.get('analysis_match_id') or e.get('source_match_id'))
  if not t or not b:continue
  p=no_vig(*b['current']);odds=[t['home_win'],t['draw'],t['away_win']]
  for i,label in enumerate(['主胜','平','客胜']):
   if odds[i]>=1.8:all.append((max(0,p[i]-.02),e,label,odds[i],p[i]))
 return max(all,key=lambda z:(z[0],z[0]*z[3]-1)) if all else None
def lock():
 latest=load(DATA/'latest_zgzcw.json',{});events=latest.get('events',[]);errors=latest.get('errors',[])
 if not events or any('已停售' in str(x) for x in errors):return []
 bjzs=load(DATA/'latest_bjzs.json',{});ledger=load(DATA/'prediction_ledger.json',[]);existing={x['key'] for x in ledger}
 ctx,_=fetch_context(events);forced=make_forced(events,bjzs);now=datetime.now(CST).isoformat();new=[]
 for e in events:
  key=e['code']+'|'+e['kickoff']
  if key in existing:continue
  t=next((m for m in e['markets'] if m.get('market')=='1X2'),None);b=bjzs.get(e.get('analysis_match_id') or e.get('source_match_id'))
  rec={'key':key,'locked_at':now,'status':'locked','code':e['code'],'kickoff':e['kickoff'],'home':e['home'],'away':e['away'],'china_1x2':[t['home_win'],t['draw'],t['away_win']] if t else None,'avg_1x2':b.get('current') if b else None,'fixture_id':ctx.get(e['code'],{}).get('fixture_id'),'forced':None}
  if forced and forced[1]['code']==e['code']:
   rec['forced']={'selection':forced[2],'odds':forced[3],'probability':forced[0],'ev':forced[0]*forced[3]-1,'stake_units':1}
  ledger.append(rec);new.append(rec)
 dump(DATA/'prediction_ledger.json',ledger);return new
def reconcile_fixture_ids(ledger):
    pending=[{'code':r['code'],'kickoff':r['kickoff'],'home':r['home'],'away':r['away']} for r in ledger if not r.get('fixture_id')]
    if not pending:return ledger
    ctx,_=fetch_context(pending)
    for r in ledger:
        if not r.get('fixture_id') and ctx.get(r['code'],{}).get('fixture_id'):
            r['fixture_id']=ctx[r['code']]['fixture_id']
    dump(DATA/'prediction_ledger.json',ledger)
    return ledger
def settle():
 ledger=reconcile_fixture_ids(load(DATA/'prediction_ledger.json',[]));settled=load(DATA/'settlement_history.json',[]);done={x['key'] for x in settled};out=[]
 for r in ledger:
  if r['key'] in done or not r.get('fixture_id'):continue
  try:
   f=call('/fixtures',{'id':r['fixture_id']}).get('response',[])
   if not f:continue
   f=f[0];status=f['fixture']['status']['short']
   if status not in ('FT','AET','PEN'):continue
   hg=f['goals']['home'];ag=f['goals']['away'];actual='主胜' if hg>ag else '客胜' if ag>hg else '平'
   rec={'key':r['key'],'settled_at':datetime.now(CST).isoformat(),'score':f'{hg}-{ag}','outcome':actual,'forced':None}
   if r.get('forced'):
    fp=r['forced'];win=fp['selection']==actual;profit=(fp['odds']-1) if win else -1
    rec['forced']={'selection':fp['selection'],'odds':fp['odds'],'probability':fp['probability'],'win':win,'profit_units':profit}
   out.append(rec)
  except:continue
 if out:settled+=out;dump(DATA/'settlement_history.json',settled)
 return settled
def review_html():
 ledger=reconcile_fixture_ids(load(DATA/'prediction_ledger.json',[]));settled=load(DATA/'settlement_history.json',[]);by={x['key']:x for x in settled}
 rows=[];profits=[];briers=[]
 for r in ledger:
  s=by.get(r['key']);fp=r.get('forced')
  if not s:rows.append(f"<tr><td>{escape(r['code'])}</td><td>{escape(r['away'])} vs {escape(r['home'])}</td><td>{escape(fp['selection'])+' @ '+str(fp['odds']) if fp else 'PASS'}</td><td>等待赛果</td><td>—</td></tr>");continue
  if fp:
   z=1 if s['forced']['win'] else 0;profits.append(s['forced']['profit_units']);briers.append((fp['probability']-z)**2)
   rows.append(f"<tr><td>{escape(r['code'])}</td><td>{escape(r['away'])} vs {escape(r['home'])}</td><td>{escape(fp['selection'])} @ {fp['odds']:.2f}</td><td>{s['score']}（{escape(s['outcome'])}）</td><td>{'命中' if z else '未命中'} / {s['forced']['profit_units']:+.2f}u</td></tr>")
  else:rows.append(f"<tr><td>{escape(r['code'])}</td><td>{escape(r['away'])} vs {escape(r['home'])}</td><td>PASS</td><td>{s['score']}（{escape(s['outcome'])}）</td><td>0u</td></tr>")
 roi=sum(profits)/len(profits) if profits else 0;brier=sum(briers)/len(briers) if briers else 0
 return f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>足球 EV 昨日复盘</title><style>body{{font-family:"Microsoft YaHei",Arial;background:#f4f7fb;color:#14213d;margin:0}}header{{background:#0c3e85;color:#fff;padding:24px max(16px,calc((100% - 1100px)/2))}}main{{max-width:1100px;margin:20px auto;padding:0 16px}}.card{{background:#fff;padding:18px;border-radius:12px;margin-bottom:15px}}table{{width:100%;border-collapse:collapse}}th,td{{padding:11px;border-bottom:1px solid #e1e9f2;text-align:left}}th{{background:#eff6ff}}.note{{background:#fff7ed;border-left:5px solid #f59e0b;padding:12px}}</style><header><h1>足球 EV 昨日复盘</h1></header><main><div class="card note">强制娱乐推荐按 1u 模拟结算；严格 EV 候选只有在未来满足外部机构和正 EV 门槛后才会出现。代理 CLV 需要最后可售赔率快照累积后才计算。</div><div class="card"><h2>累计指标</h2><p>强制推荐已结算：{len(profits)} 场 ｜ 模拟 ROI：{roi*100:.1f}% ｜ Brier Score：{brier:.4f} ｜ 严格 EV：尚无已结算候选</p></div><div class="card"><h2>锁定与结算记录</h2><table><tr><th>编号</th><th>比赛</th><th>赛前锁定</th><th>赛果</th><th>模拟结算</th></tr>{''.join(rows) if rows else '<tr><td colspan="5">尚未有锁定记录。下一次中国竞彩开售时会自动建立。</td></tr>'}</table></div></main>'''
def review_section():
 ledger=reconcile_fixture_ids(load(DATA/'prediction_ledger.json',[]));settled=load(DATA/'settlement_history.json',[]);by={x['key']:x for x in settled}
 rows=[];profits=[];briers=[]
 for r in ledger:
  s=by.get(r['key']);fp=r.get('forced')
  if not s:
   rows.append(f"<tr><td>{escape(r['code'])}</td><td>{escape(r['away'])} vs {escape(r['home'])}</td><td>{escape(fp['selection'])+' @ '+str(fp['odds']) if fp else 'PASS'}</td><td>等待赛果</td><td>—</td></tr>");continue
  if fp:
   z=1 if s['forced']['win'] else 0;profits.append(s['forced']['profit_units']);briers.append((fp['probability']-z)**2
   )
   rows.append(f"<tr><td>{escape(r['code'])}</td><td>{escape(r['away'])} vs {escape(r['home'])}</td><td>{escape(fp['selection'])} @ {fp['odds']:.2f}</td><td>{s['score']}（{escape(s['outcome'])}）</td><td>{'命中' if z else '未命中'} / {s['forced']['profit_units']:+.2f}u</td></tr>")
  else: rows.append(f"<tr><td>{escape(r['code'])}</td><td>{escape(r['away'])} vs {escape(r['home'])}</td><td>PASS</td><td>{s['score']}（{escape(s['outcome'])}）</td><td>0u</td></tr>")
 roi=sum(profits)/len(profits) if profits else 0;brier=sum(briers)/len(briers) if briers else 0
 return f"<!-- REVIEW_START --><div class='card'><h2>昨日复盘与累计表现</h2><p class='small'>强制娱乐推荐按1u模拟结算；严格EV候选仅在未来满足外部机构与正EV门槛后出现。代理CLV需最后可售赔率快照累积后计算。</p><p><b>累计指标：</b>强制推荐已结算 {len(profits)} 场 ｜ 模拟ROI {roi*100:.1f}% ｜ Brier Score {brier:.4f} ｜ 严格EV：尚无已结算候选</p><table><tr><th>编号</th><th>比赛</th><th>赛前锁定</th><th>赛果</th><th>模拟结算</th></tr>{''.join(rows) if rows else '<tr><td colspan="5">尚未有锁定记录。下一次中国竞彩开售时会自动建立。</td></tr>'}</table></div><!-- REVIEW_END -->"
def inject_review():
 p=DOCS/'index.html'
 if not p.exists():return
 html=p.read_text(encoding='utf8');section=review_section()
 html=re.sub(r'<!-- REVIEW_START -->.*?<!-- REVIEW_END -->','',html,flags=re.S)
 html=html.replace('</main>',section+'</main>')
 p.write_text(html,encoding='utf8')
def main():
 DATA.mkdir(exist_ok=True);DOCS.mkdir(exist_ok=True);lock();settle();(DOCS/'review.html').write_text(review_html(),encoding='utf8');inject_review()
if __name__=='__main__':main()
