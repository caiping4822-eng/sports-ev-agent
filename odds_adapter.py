"""The Odds API public-market adapter. Uses only the user's ODDS_API_KEY secret."""
from __future__ import annotations
import json, os, statistics
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE='https://api.the-odds-api.com/v4'
# Chinese public-page names -> common international labels returned by odds feeds.
ALIASES={
 '图凯拉特':['kairat','kairat almaty'], '奥莫尼亚':['omonia','omonia nicosia'],
 '波兹莱赫':['lech poznan','lech poznań'], '奥胡斯':['agf','aarhus','agf aarhus'],
 '米拉索':['mirassol'], '雷莫':['remo'], '巴西国际':['internacional'],
 '弗拉门戈':['flamengo'], '弗鲁米嫩':['fluminense'], '巴伊亚':['bahia'],
 '维多利亚':['vitoria','vitória'], '帕梅拉斯':['palmeiras']
}
PREFERRED={'pinnacle','betfair_ex_uk','betfair_sb_uk','bet365','williamhill','unibet','marathonbet','betano','188bet','sbo'}

def get_json(url):
    req=Request(url,headers={'User-Agent':'SportsEVResearch/1.0'})
    with urlopen(req,timeout=30) as r:return json.loads(r.read().decode('utf-8'))
def query(path,params):
    key=os.getenv('ODDS_API_KEY','').strip()
    if not key: raise RuntimeError('ODDS_API_KEY is not configured')
    params={**params,'apiKey':key}
    return get_json(BASE+path+'?'+urlencode(params))
def norm(s):return s.lower().replace('fc','').strip()
def compatible(cn,feed):
    v=norm(feed)
    return any(a in v for a in ALIASES.get(cn,[norm(cn)]))
def find_event(events,home,away):
    for e in events:
        if compatible(home,e.get('home_team','')) and compatible(away,e.get('away_team','')):return e
    return None
def no_vig(h,d,a):
    r=[1/h,1/d,1/a]; s=sum(r); return [x/s for x in r]
def external_market_for_event(home,away):
    # These are standard The Odds API soccer keys. Unsupported sports are handled gracefully.
    sports=['soccer_uefa_champs_league','soccer_brazil_campeonato']
    found=None; errors=[]
    for sport in sports:
        try:
            events=query('/sports/'+sport+'/odds/',{'regions':'eu,uk','markets':'h2h,spreads,totals','oddsFormat':'decimal'})
            found=find_event(events,home,away)
            if found:break
        except Exception as e: errors.append(f'{sport}:{type(e).__name__}')
    if not found:return {'available':False,'errors':errors}
    rows=[]
    for b in found.get('bookmakers',[]):
        key=b.get('key',''); title=b.get('title',key)
        h2h=next((m for m in b.get('markets',[]) if m.get('key')=='h2h'),None)
        if not h2h:continue
        vals={o.get('name'):o.get('price') for o in h2h.get('outcomes',[])}
        h=vals.get(found.get('home_team')); a=vals.get(found.get('away_team')); d=vals.get('Draw')
        if all(isinstance(x,(int,float)) and x>1 for x in (h,d,a)):
            p=no_vig(h,d,a)
            rows.append({'book':title,'key':key,'home_odds':h,'draw_odds':d,'away_odds':a,'p':p,'preferred':key in PREFERRED})
    if not rows:return {'available':False,'errors':errors+['no complete h2h odds']}
    # Median prevents one soft-book outlier from dominating the probability proxy.
    probs=[statistics.median([r['p'][i] for r in rows]) for i in range(3)]
    return {'available':True,'event_home':found.get('home_team'),'event_away':found.get('away_team'),'books':rows,'median_fair':probs,'errors':errors}
