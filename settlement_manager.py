from __future__ import annotations
import json,re
from datetime import datetime,timezone,timedelta
from pathlib import Path
from html import escape,unescape
from urllib.request import Request,urlopen
from api_football import fetch_context,call
ROOT=Path(__file__).parent;DATA=ROOT/'data';DOCS=ROOT/'docs';CST=timezone(timedelta(hours=8))
def load(p,d):
 try:return json.loads(p.read_text(encoding='utf8'))
 except:return d
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf8')
def parse(s):return datetime.strptime(s,'%Y-%m-%d %H:%M').replace(tzinfo=CST)
RESULT_URL='https://cp.zgzcw.com/dc/getKaijiangFootBall.action'
def clean_html(x):return re.sub(r'\s+',' ',unescape(re.sub(r'<[^>]+>',' ',x))).strip()
def china_results():
    try:
        req=Request(RESULT_URL,headers={'User-Agent':'Mozilla/5.0 (compatible; SportsEVResearch/1.0)'})
        with urlopen(req,timeout=30) as r:raw=r.read().decode('utf-8','replace')
        out={}
        for row in re.findall(r'<tr[^>]*>.*?</tr>',raw,re.I|re.S):
            cells=[clean_html(x) for x in re.findall(r'<td[^>]*>(.*?)</td>',row,re.I|re.S)]
            if not cells or not re.match(r'周[一二三四五六日]\d{3}',cells[0]):continue
            score=next((x for x in cells if re.search(r'\d+\s*:\s*\d+',x)),None)
            if score:
                m=re.search(r'(\d+)\s*:\s*(\d+)',score)
                out[cells[0]]={'home':cells[3] if len(cells)>3 else '', 'away':cells[5] if len(cells)>5 else '', 'home_goals':int(m.group(1)), 'away_goals':int(m.group(2)), 'score':m.group(1)+':'+m.group(2)}
        return out
    except:return {}
def reconcile(ledger):
 reg={x['key']:x for x in load(DATA/'fixture_registry.json',[])};todo=[]
 for r in ledger:
  if not r.get('fixture_id'):
   z=reg.get(r['key'])
   if z:r['fixture_id']=z['fixture_id'];r['reconcile_status']='注册表匹配'
   else:todo.append({'code':r['code'],'kickoff':r['kickoff'],'home':r['home'],'away':r['away']})
 if todo:
  ctx,_=fetch_context(todo)
  for r in ledger:
   if not r.get('fixture_id') and ctx.get(r['code'],{}).get('fixture_id'):
    r['fixture_id']=ctx[r['code']]['fixture_id'];r['reconcile_status']='回补匹配'
   elif not r.get('fixture_id'):r['reconcile_status']=ctx.get(r['code'],{}).get('status','未匹配')
 dump(DATA/'prediction_ledger.json',ledger);return ledger
def proxy_clv(r):
 idx={'主胜':0,'平':1,'客胜':2}.get((r.get('forced') or {}).get('selection'))
 if idx is None:return None
 snaps=load(DATA/'closing_snapshots.json',[]);last=None
 for s in snaps:
  try:before=datetime.fromisoformat(s['captured_at'])<=parse(r['kickoff'])
  except:before=False
  if not before:continue
  for x in s.get('items',[]):
   if x.get('code')==r['code'] and x.get('kickoff')==r['kickoff']:last=x['china'][idx]
 if not last:return None
 return r['forced']['odds']/last-1
def settle(ledger):
 hist=load(DATA/'settlement_history.json',[]);done={x['key'] for x in hist};results=china_results()
 for r in ledger:
  if r['key'] in done:continue
  z=results.get(r['code'])
  if not z:continue
  # China result page is authoritative for China-lottery settlement; score source is home vs away.
  hg=z['home_goals'];ag=z['away_goals'];out='主胜' if hg>ag else '客胜' if ag>hg else '平'
  fp=r.get('forced');rec={'key':r['key'],'score':z['score'],'outcome':out,'settled_at':datetime.now(CST).isoformat(),'settlement_source':'zgzcw_public_result','proxy_clv':proxy_clv(r)}
  if fp:rec['forced']={'selection':fp['selection'],'odds':fp['odds'],'probability':fp['probability'],'win':fp['selection']==out,'profit_units':fp['odds']-1 if fp['selection']==out else -1}
  hist.append(rec)
 dump(DATA/'settlement_history.json',hist);return hist
def inject(ledger,hist):
 by={x['key']:x for x in hist};rows=[];profits=[];clvs=[];briers=[];now=datetime.now(CST)
 for r in ledger:
  s=by.get(r['key']);fp=r.get('forced');lock=fp['selection']+' @ '+str(fp['odds']) if fp else 'PASS'
  if s and fp:
   z=1 if s['forced']['win'] else 0;profits.append(s['forced']['profit_units']);briers.append((fp['probability']-z)**2)
   if s.get('proxy_clv') is not None:clvs.append(s['proxy_clv'])
   res=f"{s['score']} / {'命中' if z else '未命中'} / {s['forced']['profit_units']:+.2f}u"
  elif s:res=s['score']+' / PASS / 0u'
  else:
   try:
    delta=(parse(r['kickoff'])-now).total_seconds()/3600
    res=f'未开赛（约{max(0,delta):.1f}小时后）' if delta>0 else '已开赛/待官方赛果'
   except:res='待赛果'
  clvtxt=f"{s.get('proxy_clv')*100:.1f}%" if s and s.get('proxy_clv') is not None else '—'
  rows.append(f"<tr><td>{escape(r['code'])}</td><td>{escape(r['away'])} vs {escape(r['home'])}</td><td>{escape(lock)}</td><td>{escape(res)}</td><td>{clvtxt}</td></tr>")
 n=len(profits);roi=sum(profits)/n if n else 0;clv=sum(clvs)/len(clvs) if clvs else 0;brier=sum(briers)/len(briers) if briers else 0
 note='样本不足30场，ROI/CLV仅记录，不用于评价系统能力。' if n<30 else '样本达到基础评价门槛，可观察长期趋势。'
 sec=f"<!-- FULL_REVIEW_START --><div class='card'><h2>历史锁定、结算与代理CLV</h2><p><b>累计：</b>已结算强制推荐 {n} 场 ｜ 模拟ROI {roi*100:.1f}% ｜ 平均中国竞彩代理CLV {clv*100:.1f}% ｜ Brier {brier:.4f}</p><p class='small'>{note}</p><table><tr><th>编号</th><th>比赛</th><th>赛前锁定</th><th>结算状态</th><th>中国竞彩代理CLV</th></tr>{''.join(rows) if rows else '<tr><td colspan="5">暂无锁定记录</td></tr>'}</table></div><!-- FULL_REVIEW_END -->"
 p=DOCS/'index.html'
 if p.exists():
  html=p.read_text(encoding='utf8');html=re.sub(r'<!-- FULL_REVIEW_START -->.*?<!-- FULL_REVIEW_END -->','',html,flags=re.S);html=html.replace('</main>',sec+'</main>');p.write_text(html,encoding='utf8')
def main():
 DATA.mkdir(exist_ok=True);DOCS.mkdir(exist_ok=True);ledger=reconcile(load(DATA/'prediction_ledger.json',[]));hist=settle(ledger);inject(ledger,hist)
if __name__=='__main__':main()
