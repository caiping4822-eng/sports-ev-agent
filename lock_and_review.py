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
def forced_for_event(e,bjzs):
 t=next((m for m in e.get('markets',[]) if m.get('market')=='1X2'),None);b=bjzs.get(e.get('analysis_match_id') or e.get('source_match_id'))
 if not t:return None
 odds=[t['home_win'],t['draw'],t['away_win']];labels=['主胜','平','客胜']
 if b and b.get('current'):
  p=no_vig(*b['current']);penalty=.02;source='百家平均'
 else:
  # Fallback is explicitly lower quality: devig China price only and apply 4pp penalty.
  p=no_vig(*odds);penalty=.04;source='中国竞彩内部去水代理'
 c=[]
 for i,o in enumerate(odds):
  if o>=1.8:c.append((max(0,p[i]-penalty),i,o))
 if not c:return None
 pc,i,o=max(c,key=lambda x:(x[0],x[0]*x[2]-1))
 return {'selection':labels[i],'odds':o,'probability':pc,'ev':pc*o-1,'stake_units':1,'type':'per_match','probability_source':source}
def lock():
 latest=load(DATA/'latest_zgzcw.json',{});events=latest.get('events',[]);errors=latest.get('errors',[])
 if not events or any('已停售' in str(x) for x in errors):return []
 bjzs=load(DATA/'latest_bjzs.json',{});ledger=load(DATA/'prediction_ledger.json',[]);existing={x['key'] for x in ledger}
 ctx,_=fetch_context(events);global_forced=make_forced(events,bjzs);now=datetime.now(CST).isoformat();new=[]
 for e in events:
  key=e['code']+'|'+e['kickoff']
  if key in existing:continue
  t=next((m for m in e['markets'] if m.get('market')=='1X2'),None);b=bjzs.get(e.get('analysis_match_id') or e.get('source_match_id'))
  rec={'key':key,'locked_at':now,'status':'locked','code':e['code'],'league':e.get('league','未知联赛'),'kickoff':e['kickoff'],'home':e['home'],'away':e['away'],'china_1x2':[t['home_win'],t['draw'],t['away_win']] if t else None,'avg_1x2':b.get('current') if b else None,'fixture_id':ctx.get(e['code'],{}).get('fixture_id'),'forced':None}
  local=forced_for_event(e,bjzs)
  if local:
   local['is_global']=bool(global_forced and global_forced[1]['code']==e['code'] and global_forced[2]==local['selection'])
   rec['forced']=local
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
def review_rows(ledger,settled):
 by={x.get('key'):x for x in settled if isinstance(x,dict)};rows=[];profits=[];briers=[]
 for r in ledger:
  if not isinstance(r,dict):continue
  st=by.get(r.get('key'));fp=r.get('forced') if isinstance(r.get('forced'),dict) else None
  match=escape(str(r.get('away','-')))+' vs '+escape(str(r.get('home','-')))
  lock=(escape(str(fp.get('selection','-')))+' @ '+str(fp.get('odds','-'))) if fp else 'PASS'
  if not isinstance(st,dict):
   rows.append(f"<tr><td>{escape(str(r.get('code','-')))}</td><td>{match}</td><td>{lock}</td><td>等待赛果</td><td>—</td></tr>");continue
  score=escape(str(st.get('score','-')));out=escape(str(st.get('outcome','-')))
  sfp=st.get('forced') if isinstance(st.get('forced'),dict) else None
  if fp and sfp:
   z=1 if sfp.get('win') else 0;profit=float(sfp.get('profit_units',0));profits.append(profit);briers.append((float(fp.get('probability',0))-z)**2)
   rows.append(f"<tr><td>{escape(str(r.get('code','-')))}</td><td>{match}</td><td>{lock}</td><td>{score}（{out}）</td><td>{'命中' if z else '未命中'} / {profit:+.2f}u</td></tr>")
  elif fp:
   rows.append(f"<tr><td>{escape(str(r.get('code','-')))}</td><td>{match}</td><td>历史补录：{lock}</td><td>{score}（{out}）</td><td>历史补录，不计入ROI</td></tr>")
  else:
   rows.append(f"<tr><td>{escape(str(r.get('code','-')))}</td><td>{match}</td><td>PASS</td><td>{score}（{out}）</td><td>0u</td></tr>")
 return rows,profits,briers
def review_html():
 ledger=reconcile_fixture_ids(load(DATA/'prediction_ledger.json',[]));settled=load(DATA/'settlement_history.json',[]);rows,profits,briers=review_rows(ledger,settled)
 roi=sum(profits)/len(profits) if profits else 0;brier=sum(briers)/len(briers) if briers else 0
 return f"<html><meta charset='utf-8'><body><h1>足球 EV 昨日复盘</h1><p>已结算逐场强制推荐 {len(profits)} 场 ｜ 模拟ROI {roi*100:.1f}% ｜ Brier {brier:.4f}</p><table>{''.join(rows)}</table></body></html>"
def review_section():
 ledger=reconcile_fixture_ids(load(DATA/'prediction_ledger.json',[]));settled=load(DATA/'settlement_history.json',[]);rows,profits,briers=review_rows(ledger,settled)
 roi=sum(profits)/len(profits) if profits else 0;brier=sum(briers)/len(briers) if briers else 0
 return f"<!-- REVIEW_START --><div class='card'><h2>昨日复盘与累计表现</h2><p><b>累计：</b>已结算逐场强制推荐 {len(profits)} 场 ｜ 模拟ROI {roi*100:.1f}% ｜ Brier {brier:.4f} ｜ 样本不足30场，不评价系统能力</p><table><tr><th>编号</th><th>比赛</th><th>赛前锁定</th><th>赛果</th><th>模拟结算</th></tr>{''.join(rows) if rows else '<tr><td colspan=5>暂无锁定记录</td></tr>'}</table></div><!-- REVIEW_END -->"
def inject_review():
 p=DOCS/'index.html'
 if not p.exists():return
 html=p.read_text(encoding='utf8');section=review_section()
 html=re.sub(r'<!-- REVIEW_START -->.*?<!-- REVIEW_END -->','',html,flags=re.S)
 html=html.replace('</main>',section+'</main>')
 p.write_text(html,encoding='utf8')
def backfill_per_match_simulation():
 ledger=load(DATA/'prediction_ledger.json',[]);changed=False
 for r in ledger:
  if r.get('forced') is not None:continue
  if not r.get('china_1x2'):continue
  odds=r['china_1x2'];avg=r.get('avg_1x2');p=no_vig(*(avg if avg else odds));pen=.02 if avg else .04;labels=['主胜','平','客胜'];c=[]
  for i,o in enumerate(odds):
   if o>=1.8:c.append((max(0,p[i]-pen),i,o))
  if c:
   pc,i,o=max(c,key=lambda x:(x[0],x[0]*x[2]-1))
   r['forced']={'selection':labels[i],'odds':o,'probability':pc,'ev':pc*o-1,'stake_units':1,'type':'historical_simulation','is_global':False,'probability_source':'历史补录，不计入真实ROI'};changed=True
 if changed:dump(DATA/'prediction_ledger.json',ledger)
def main():
 DATA.mkdir(exist_ok=True);DOCS.mkdir(exist_ok=True);backfill_per_match_simulation();lock();settle();(DOCS/'review.html').write_text(review_html(),encoding='utf8');inject_review()
if __name__=='__main__':main()
