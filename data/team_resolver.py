from __future__ import annotations
import json,re
from pathlib import Path
ROOT=Path(__file__).parent

def norm(s):return re.sub(r'[^a-z0-9]','',s.lower())
def load_map():
 try:return json.loads((ROOT/'data'/'team_entity_map.json').read_text(encoding='utf8')).get('teams',{})
 except:return {}
def aliases(cn,mapping):return mapping.get(cn,{}).get('english_aliases',[])
def matches(cn,english,mapping):
 e=norm(english)
 return any(norm(a) in e or e in norm(a) for a in aliases(cn,mapping))
def score_event(event,fixture,mapping):
 # API fixture home/away must align with Chinese-home/away; position is material.
 hname=fixture['teams']['home']['name'];aname=fixture['teams']['away']['name']
 sh=60 if matches(event['home'],hname,mapping) else 0
 sa=60 if matches(event['away'],aname,mapping) else 0
 if not sh or not sa:return 0
 # Both resolved aliases + correct home/away = high-confidence match.
 return sh+sa+20
def unresolved(event,mapping):
 return [x for x in (event['home'],event['away']) if x not in mapping]
