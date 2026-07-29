"""Dependency-free low-frequency adapter for the public zgzcw football page."""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from hashlib import sha256
from html import unescape
import re
from urllib.request import Request, urlopen

URL='https://cp.zgzcw.com/lottery/jchtplayvsForJsp.action?lotteryId=47&type=jcmini'
CST=timezone(timedelta(hours=8))

def clean(x):
    return re.sub(r'\s+',' ',unescape(re.sub(r'<[^>]+>',' ',x))).strip()
def attr(s,name):
    m=re.search(r'\b'+re.escape(name)+r'="([^"]*)"',s,re.I)
    return unescape(m.group(1)) if m else ''
def number(x):
    try:return float(x)
    except:return None

def fetch_football_target_odds():
    req=Request(URL,headers={'User-Agent':'Mozilla/5.0 (compatible; SportsEVResearch/1.0)'})
    with urlopen(req,timeout=25) as res:
        raw=res.read().decode('utf-8','replace')
    events=[]
    # Each current football event is contained in a tr whose class includes beginBet.
    for row in re.findall(r'<tr\b[^>]*class="[^"]*beginBet[^"]*"[^>]*>.*?</tr>',raw,re.I|re.S):
        code=attr(row,'mn'); league=attr(row,'m')
        if not code:continue
        home_m=re.search(r'<td\s+class="wh-4[^>]*>.*?<a\b[^>]*title="([^"]+)"',row,re.I|re.S)
        away_m=re.search(r'<td\s+class="wh-6[^>]*>.*?<a\b[^>]*title="([^"]+)"',row,re.I|re.S)
        if not home_m or not away_m:continue
        kickoff_m=re.search(r'title="比赛时间:([^"]+)"',row)
        markets=[]
        for d in re.findall(r'<div\b[^>]*class="([^"]*tz-area[^"]*)"[^>]*>.*?</div>',row,re.I|re.S):
            classes=d[0]
            body=d[1] if isinstance(d,tuple) else ''
            # fallback because findall above returns groups only with the supplied pattern
        # Extract actual div blocks independently to preserve their bodies.
        divs=re.findall(r'(<div\b[^>]*class="[^"]*tz-area[^"]*"[^>]*>.*?</div>)',row,re.I|re.S)
        for div in divs:
            classes=attr(div,'class')
            line_m=re.search(r'<em\b[^>]*class="rq[^>]*>(.*?)</em>',div,re.I|re.S)
            vals=[number(clean(x)) for x in re.findall(r'<a\b[^>]*class="weisai[^"]*"[^>]*>(.*?)<s>',div,re.I|re.S)]
            if len(vals)==3 and all(x is not None for x in vals):
                markets.append({'market':'1X2' if 'frq' in classes else 'handicap_1x2',
                                'line':clean(line_m.group(1)) if line_m else '0',
                                'home_win':vals[0],'draw':vals[1],'away_win':vals[2]})
        events.append({'source':'zgzcw_public_page','source_url':URL,
                       'captured_at':datetime.now(CST).isoformat(),
                       'source_match_id':attr(row,'id').replace('tr_',''),
                       'code':code,'league':league,'deadline':attr(row,'t'),
                       'kickoff':kickoff_m.group(1) if kickoff_m else '',
                       'home':unescape(home_m.group(1)),'away':unescape(away_m.group(1)),
                       'markets':markets})
    return {'events':events,'raw_sha256':sha256(raw.encode('utf-8')).hexdigest(),'source_url':URL}
