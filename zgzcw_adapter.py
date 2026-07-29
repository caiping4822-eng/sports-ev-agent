"""Low-frequency, public-page adapter for zgzcw.com.
Does not use login, undocumented private APIs, CAPTCHA bypassing, or protected endpoints.
If upstream access fails, callers receive a source error and must not substitute made-up prices.
"""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from hashlib import sha256
import requests
from bs4 import BeautifulSoup

URL='https://cp.zgzcw.com/lottery/jchtplayvsForJsp.action?lotteryId=47&type=jcmini'
CST=timezone(timedelta(hours=8))

def _num(x):
    try:return float(x)
    except:return None

def fetch_football_target_odds():
    r=requests.get(URL,headers={'User-Agent':'Mozilla/5.0 (compatible; SportsEVResearch/1.0)'},timeout=25)
    r.raise_for_status()
    raw=r.text
    soup=BeautifulSoup(raw,'html.parser')
    events=[]
    for row in soup.select('tr.beginBet'):
        home=row.select_one('td.wh-4 a[title]')
        away=row.select_one('td.wh-6 a[title]')
        if not home or not away:continue
        time=''
        for s in row.select('td.wh-3 span'):
            title=s.get('title','')
            if '比赛时间' in title:
                time=title.split(':',1)[-1]
        markets=[]
        for div in row.select('div.tz-area'):
            line_el=div.select_one('em.rq')
            odds=[_num(a.get_text(strip=True)) for a in div.select('a.weisai')]
            if len(odds)!=3 or any(x is None for x in odds):continue
            markets.append({
              'market':'1X2' if 'frq' in (div.get('class') or []) else 'handicap_1x2',
              'line':line_el.get_text(strip=True) if line_el else '0',
              'home_win':odds[0], 'draw':odds[1], 'away_win':odds[2]
            })
        # The public page exposes a displayed European-odds summary. Keep it labelled as display data,
        # never as direct Pinnacle/Betfair odds.
        euro=[]
        for inp in row.select('input.odds_d'):
            v=inp.get('value','').split()
            if len(v)==3:euro.append(v)
        events.append({
          'source':'zgzcw_public_page', 'source_url':URL,
          'captured_at':datetime.now(CST).isoformat(),
          'source_match_id':row.get('id','').replace('tr_',''),
          'code':row.get('mn',''), 'league':row.get('m',''),
          'deadline':row.get('t',''), 'kickoff':time,
          'home':home.get('title'), 'away':away.get('title'),
          'markets':markets, 'display_euro_summary':euro
        })
    return {'events':events,'raw_sha256':sha256(raw.encode('utf-8')).hexdigest(),'source_url':URL}
