from __future__ import annotations
import json
from datetime import datetime,timezone,timedelta
from pathlib import Path
from zgzcw_adapter import fetch_football_target_odds,fetch_bjzs_average
ROOT=Path(__file__).parent;DATA=ROOT/'data';CST=timezone(timedelta(hours=8))
def load(p,d):
 try:return json.loads(p.read_text(encoding='utf8'))
 except:return d
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf8')
def main():
 DATA.mkdir(exist_ok=True);now=datetime.now(CST).isoformat()
 try:
  snap=fetch_football_target_odds();events=snap.get('events',[])
  if not events:return
  avg=fetch_bjzs_average();items=[]
  for e in events:
   t=next((m for m in e.get('markets',[]) if m.get('market')=='1X2'),None);b=avg.get(e.get('analysis_match_id') or e.get('source_match_id'))
   if t:items.append({'code':e['code'],'kickoff':e['kickoff'],'china':[t['home_win'],t['draw'],t['away_win']],'average':b.get('current') if b else None})
  hist=load(DATA/'closing_snapshots.json',[]);hist.append({'captured_at':now,'items':items,'source':'zgzcw_public_low_frequency'});dump(DATA/'closing_snapshots.json',hist[-500:])
 except Exception:pass
if __name__=='__main__':main()
