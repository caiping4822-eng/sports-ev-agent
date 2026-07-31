from __future__ import annotations
import json,re
from datetime import datetime,timezone,timedelta
from pathlib import Path
from html import escape
from api_football import fetch_context,call
ROOT=Path(__file__).parent;DATA=ROOT/'data';DOCS=ROOT/'docs';CST=timezone(timedelta(hours=8))
def load(p,d):
 try:return json.loads(p.read_text(encoding='utf8'))
 except:return d
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf8')
def parse(s):return datetime.strptime(s,'%Y-%m-%d %H:%M').replace(tzinfo=CST)
def reconcile(ledger):
 pending=[{'code':r['code'],'kickoff':r['kickoff'],'home':r['home'],'away':r['away']} for r in ledger if not r.get('fixture_id')]
 ctx,_=fetch_context(pending) if pending else ({},[])
 for r in ledger:
  if not r.get('fixture_id'):
   c=ctx.get(r['code'],{})
   if c.get('fixture_id'):
    r['fixture_id']=c['fixture_id'];r['reconcile_status']='已按主客队/日期/别名匹配'
   else:r['reconcile_status']=c.get('status','未匹配')
 dump(DATA/'prediction_ledger.json',ledger);return ledger
def last_proxy(r):
 idx={'主胜':0,'平':1,'客胜':2}.get((r.get('forced') or {}).get('selection'))
 if idx is None:return None
 last=None
 for s in load(DATA/'closing_snapshots.json',[]):
  try:before=datetime.fromisoformat(s['captured_at'])<=parse(r['kickoff'])
  except:before=False
  if before:
   for x in s.get('items',[]):
    if x.get('code')==r['code'] and x.get('kickoff')==r['kickoff']:last=x['china'][idx]
 return r['forced']['odds']/last-1 if last else None
def settle(ledger):
 # Remove all old settlements made by China weekly code alone; they are not identity-safe.
 hist=[x for x in load(DATA/'settlement_history.json',[]) if x.get('settlement_source')=='api_identity_verified'];done={x['key'] for x in hist}
 for r in ledger:
  if r['key'] in done or not r.get('fixture_id'):continue
  try:
   f=call('/fixtures',{'id':r['fixture_id']}).get('response',[])
   if not f:continue
   f=f[0]
   if f['fixture']['status']['short'] not in ('FT','AET','PEN'):continue
   # For China football settlement use 90-minute fulltime score, not extra-time final score.
   sc=f.get('score',{}).get('fulltime',{});hg=sc.get('home');ag=sc.get('away')
   if hg is None or ag is None:continue
   out='主胜' if hg>ag else '客胜' if ag>hg else '平';fp=r.get('forced') if isinstance(r.get('forced'),dict) else None
   rec={'key':r['key'],'score':f'{hg}:{ag}','outcome':out,'settled_at':datetime.now(CST).isoformat(),'settlement_source':'api_identity_verified','proxy_clv':last_proxy(r),'forced':None}
   if fp:rec['forced']={'selection':fp['selection'],'odds':fp['odds'],'probability':fp['probability'],'win':fp['selection']==out,'profit_units':fp['odds']-1 if fp['selection']==out else -1}
   hist.append(rec)
  except:continue
 dump(DATA/'settlement_history.json',hist);return hist
def render(ledger,hist):
 by={x['key']:x for x in hist};rows=[];profits=[];clvs=[];briers=[];now=datetime.now(CST)
 for r in ledger:
  s=by.get(r['key']);fp=r.get('forced') if isinstance(r.get('forced'),dict) else None;lock=(fp.get('selection','-')+' @ '+str(fp.get('odds','-'))) if fp else 'PASS'
  if s:
   sf=s.get('forced') if isinstance(s.get('forced'),dict) else None
   if fp and sf:
    z=1 if sf['win'] else 0;profits.append(sf['profit_units']);briers.append((fp['probability']-z)**2)
    if s.get('proxy_clv') is not None:clvs.append(s['proxy_clv'])
    result=f"{s['score']}（{s['outcome']}）/ {'命中' if z else '未命中'} / {sf['profit_units']:+.2f}u"
   else:result=f"{s['score']}（{s['outcome']}）/ PASS / 0u"
  else:
   try:result=f"未开赛（约{max(0,(parse(r['kickoff'])-now).total_seconds()/3600):.1f}小时后）" if parse(r['kickoff'])>now else '已结束，待身份匹配赛果'
   except:result='待赛果'
  clv=f"{s.get('proxy_clv')*100:.1f}%" if s and s.get('proxy_clv') is not None else '—'
  rows.append(f"<tr><td>{escape(r['code'])}</td><td>{escape(r['home'])} vs {escape(r['away'])}</td><td>{escape(lock)}</td><td>{escape(result)}</td><td>{clv}</td></tr>")
 n=len(profits);roi=sum(profits)/n if n else 0;clvavg=sum(clvs)/len(clvs) if clvs else 0;brier=sum(briers)/len(briers) if briers else 0
 sec=f"<!-- FULL_REVIEW_START --><div class='card'><h2>历史锁定、身份校验赛果与代理CLV</h2><p><b>结算规则：</b>只使用主队+客队+日期+fixture_id身份校验后的90分钟比分。历史周编号不再直接结算。</p><p><b>累计：</b>已身份校验结算 {n} 场 ｜ 模拟ROI {roi*100:.1f}% ｜ 平均中国竞彩代理CLV {clvavg*100:.1f}% ｜ Brier {brier:.4f} ｜ 样本不足30场，不评价系统能力。</p><table><tr><th>编号</th><th>中国竞彩对阵</th><th>赛前锁定</th><th>身份校验结算</th><th>中国竞彩代理CLV</th></tr>{''.join(rows)}</table></div><!-- FULL_REVIEW_END -->"
 p=DOCS/'index.html'
 if p.exists():
  h=p.read_text(encoding='utf8');h=re.sub(r'<!-- FULL_REVIEW_START -->.*?<!-- FULL_REVIEW_END -->','',h,flags=re.S);h=h.replace('</main>',sec+'</main>');p.write_text(h,encoding='utf8')
def main():
 DATA.mkdir(exist_ok=True);DOCS.mkdir(exist_ok=True);ledger=reconcile(load(DATA/'prediction_ledger.json',[]));hist=settle(ledger);render(ledger,hist)
if __name__=='__main__':main()
