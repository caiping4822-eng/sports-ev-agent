from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).parent;DATA=ROOT/'data'
def load(p,d):
 try:return json.loads(p.read_text(encoding='utf8'))
 except:return d
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf8')
def main():
 ctx=load(DATA/'api_context.json',{});latest=load(DATA/'latest_zgzcw.json',{});old=load(DATA/'fixture_registry.json',[]);keys={x['key'] for x in old}
 for e in latest.get('events',[]):
  c=ctx.get(e['code'],{});fid=c.get('fixture_id')
  key=e['code']+'|'+e['kickoff']
  if fid and key not in keys:
   old.append({'key':key,'code':e['code'],'kickoff':e['kickoff'],'home':e['home'],'away':e['away'],'fixture_id':fid,'home_team_id':c.get('home_team_id'),'away_team_id':c.get('away_team_id'),'league':c.get('league'),'source':'api_football_matched'})
 dump(DATA/'fixture_registry.json',old)
if __name__=='__main__':main()
