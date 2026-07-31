from __future__ import annotations
import json,re
from collections import defaultdict
from datetime import datetime,timezone,timedelta
from pathlib import Path
from html import escape
ROOT=Path(__file__).parent;DATA=ROOT/'data';DOCS=ROOT/'docs';CST=timezone(timedelta(hours=8))
def load(p,d):
 try:return json.loads(p.read_text(encoding='utf8'))
 except:return d
def odds_band(o):
 if o<2:return '1.80—1.99'
 if o<3:return '2.00—2.99'
 if o<5:return '3.00—4.99'
 return '5.00+'
def rate(rows):
 n=len(rows);wins=sum(1 for x in rows if x['win']);roi=sum(x['profit'] for x in rows)/n if n else 0;avg=sum(x['odds'] for x in rows)/n if n else 0
 return n,wins/n if n else 0,roi,avg
def main():
 ledger=load(DATA/'prediction_ledger.json',[]);settled={x.get('key'):x for x in load(DATA/'settlement_history.json',[]) if isinstance(x,dict)}
 real=[];sim=[]
 for r in ledger:
  s=settled.get(r.get('key'));fp=r.get('forced') if isinstance(r.get('forced'),dict) else None
  if not s or not fp or not isinstance(s.get('forced'),dict):continue
  item={'date':str(s.get('settled_at',''))[:10] or '未知日期','league':r.get('league','历史未记录'),'odds':float(fp.get('odds',0)),'win':bool(s['forced'].get('win')),'profit':float(s['forced'].get('profit_units',0)),'type':'历史回放' if fp.get('type')=='historical_simulation' else '真实锁定'}
  (sim if item['type']=='历史回放' else real).append(item)
 def table(rows,key):
  groups=defaultdict(list)
  for x in rows:groups[x[key]].append(x)
  out=[]
  for k,v in sorted(groups.items(),key=lambda z:str(z[0])):
   n,hit,roi,avg=rate(v);out.append(f'<tr><td>{escape(str(k))}</td><td>{n}</td><td>{hit*100:.1f}%</td><td>{roi*100:.1f}%</td><td>{avg:.2f}</td></tr>')
  return ''.join(out) or '<tr><td colspan="5">暂无可统计样本</td></tr>'
 nr,hr,rr,ar=rate(real);ns,hs,rs,as_=rate(sim)
 section=f'''<!-- STATS_START --><div class="card"><h2>分联赛、赔率区间与样本统计</h2><p><b>真实锁定：</b>{nr}场 ｜ 命中率 {hr*100:.1f}% ｜ ROI {rr*100:.1f}% ｜ 平均赔率 {ar:.2f}</p><p><b>历史回放：</b>{ns}场 ｜ 命中率 {hs*100:.1f}% ｜ 模拟ROI {rs*100:.1f}% ｜ 平均赔率 {as_:.2f} ｜ 不计入真实系统表现</p><p class="small">样本门槛：0—29场只记录；30—99场观察；100场以上才开始评价联赛/赔率区间策略。</p><h3>真实锁定：按联赛</h3><table><tr><th>联赛</th><th>场数</th><th>命中率</th><th>ROI</th><th>平均赔率</th></tr>{table(real,'league')}</table><h3>真实锁定：按赔率区间</h3><table><tr><th>赔率区间</th><th>场数</th><th>命中率</th><th>ROI</th><th>平均赔率</th></tr>{table([{**x,'band':odds_band(x['odds'])} for x in real],'band')}</table><h3>历史回放：按联赛（研究用）</h3><table><tr><th>联赛</th><th>场数</th><th>命中率</th><th>模拟ROI</th><th>平均赔率</th></tr>{table(sim,'league')}</table></div><!-- STATS_END -->'''
 DATA.mkdir(exist_ok=True);dump={'real':real,'historical_simulation':sim};(DATA/'performance_by_segment.json').write_text(json.dumps(dump,ensure_ascii=False,indent=2),encoding='utf8')
 p=DOCS/'index.html'
 if p.exists():
  h=p.read_text(encoding='utf8');h=re.sub(r'<!-- STATS_START -->.*?<!-- STATS_END -->','',h,flags=re.S);h=h.replace('</main>',section+'</main>');p.write_text(h,encoding='utf8')
if __name__=='__main__':main()
