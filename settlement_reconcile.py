from __future__ import annotations
import json
from pathlib import Path
from api_football import fetch_context
ROOT=Path(__file__).parent;DATA=ROOT/'data'
def load(p,d):
 try:return json.loads(p.read_text(encoding='utf8'))
 except:return d
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf8')
def main():
 ledger=load(DATA/'prediction_ledger.json',[]);pending=[{'code':x['code'],'kickoff':x['kickoff'],'home':x['home'],'away':x['away']} for x in ledger if not x.get('fixture_id')]
 ctx,errors=fetch_context(pending) if pending else ({},[]);updated=0;unmatched=[]
 for r in ledger:
  if not r.get('fixture_id'):
   c=ctx.get(r['code'],{})
   if c.get('fixture_id'):r['fixture_id']=c['fixture_id'];r['reconcile_status']='已补匹配';updated+=1
   else:r['reconcile_status']=c.get('status','未匹配');unmatched.append({'code':r['code'],'match':r['away']+' vs '+r['home'],'reason':r['reconcile_status']})
 dump(DATA/'prediction_ledger.json',ledger);dump(DATA/'settlement_audit.json',{'updated':updated,'unmatched':unmatched,'api_errors':errors})
if __name__=='__main__':main()
