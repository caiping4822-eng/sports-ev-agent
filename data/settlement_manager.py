from __future__ import annotations
import json,re
from datetime import datetime,timezone,timedelta
from pathlib import Path
from html import escape
from result_verifier import result_for
ROOT=Path(__file__).parent;DATA=ROOT/'data';DOCS=ROOT/'docs';CST=timezone(timedelta(hours=8))
def load(p,d):
 try:return json.loads(p.read_text(encoding='utf8'))
 except:return d
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf8')
def parse(s):return datetime.strptime(s,'%Y-%m-%d %H:%M').replace(tzinfo=CST)
def proxy(r):
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
def main():
 ledger=load(DATA/'prediction_ledger.json',[]);hist=[]
 for r in ledger:
  result=result_for(r);fp=r.get('forced') if isinstance(r.get('forced'),dict) else None
  if result:
   rec={'key':r['key'],'score':result['score'],'outcome':result['outcome'],'source':result['source'],'verified':result['verified'],'proxy_clv':proxy(r),'forced':None}
   if fp:rec['forced']={'selection':fp['selection'],'odds':fp['odds'],'probability':fp['probability'],'win':fp['selection']==result['outcome'],'profit_units':fp['odds']-1 if fp['selection']==result['outcome'] else -1,'historical':fp.get('type')=='historical_simulation'}
   hist.append(rec)
 dump(DATA/'settlement_history.json',hist);by={x['key']:x for x in hist};rows=[];profits=[];clvs=[];briers=[];now=datetime.now(CST)
 for r in ledger:
  s=by.get(r['key']);fp=r.get('forced') if isinstance(r.get('forced'),dict) else None
  if s:
   sf=s.get('forced');kind='历史补录' if sf and sf.get('historical') else '赛前锁定'
   if sf and not sf.get('historical') and s['verified']:
    z=1 if sf['win'] else 0;profits.append(sf['profit_units']);briers.append((sf['probability']-z)**2)
    if s.get('proxy_clv') is not None:clvs.append(s['proxy_clv'])
    settle=f"{s['score']}（{s['outcome']}）/ {'命中' if z else '未命中'} / {sf['profit_units']:+.2f}u"
   else:settle=f"{s['score']}（{s['outcome']}）/ {kind}，不计入ROI"
   source=s['source']+('（双源核验）' if s['verified'] else '（单源待复核）')
  else:
   try:settle='未开赛（约%.1f小时后）'%max(0,(parse(r['kickoff'])-now).total_seconds()/3600) if parse(r['kickoff'])>now else '已结束，待身份校验赛果'
   except:settle='待赛果'
   source='—'
  rows.append(f"<tr><td>{escape(r['code'])}</td><td>{escape(r['home'])} vs {escape(r['away'])}</td><td>{escape((fp or {}).get('selection','PASS'))}</td><td>{escape(settle)}</td><td>{escape(source)}</td></tr>")
 roi=sum(profits)/len(profits) if profits else 0;clv=sum(clvs)/len(clvs) if clvs else 0;brier=sum(briers)/len(briers) if briers else 0
 sec=f"<!-- FULL_REVIEW_START --><div class='card'><h2>历史锁定、身份校验赛果与代理CLV</h2><p><b>累计：</b>双源身份校验结算 {len(profits)} 场 ｜ 模拟ROI {roi*100:.1f}% ｜ 平均中国竞彩代理CLV {clv*100:.1f}% ｜ Brier {brier:.4f} ｜ 样本不足30场，不评价系统能力。</p><table><tr><th>编号</th><th>中国竞彩对阵</th><th>赛前选择</th><th>90分钟身份校验结算</th><th>赛果来源</th></tr>{''.join(rows)}</table></div><!-- FULL_REVIEW_END -->"
 p=DOCS/'index.html'
 if p.exists():
  h=p.read_text(encoding='utf8');h=re.sub(r'<!-- FULL_REVIEW_START -->.*?<!-- FULL_REVIEW_END -->','',h,flags=re.S);h=h.replace('</main>',sec+'</main>');p.write_text(h,encoding='utf8')
if __name__=='__main__':main()
