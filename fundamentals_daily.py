from __future__ import annotations
import json,re
from datetime import datetime,timezone,timedelta
from pathlib import Path
from html import escape
from api_football import call
ROOT=Path(__file__).parent;DATA=ROOT/'data';DOCS=ROOT/'docs';CST=timezone(timedelta(hours=8))
def load(p,d):
 try:return json.loads(p.read_text(encoding='utf8'))
 except:return d
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf8')
def stat(team,league,season):
 try:
  r=call('/teams/statistics',{'league':league,'season':season,'team':team}).get('response',{})
  fx=r.get('fixtures',{});g=r.get('goals',{})
  return {'form':r.get('form','-'),'played':fx.get('played',{}).get('total','-'),'wins':fx.get('wins',{}).get('total','-'),'draws':fx.get('draws',{}).get('total','-'),'losses':fx.get('loses',{}).get('total','-'),'gf':g.get('for',{}).get('total',{}).get('total','-'),'ga':g.get('against',{}).get('total',{}).get('total','-')}
 except:return {'form':'源未返回','played':'-','wins':'-','draws':'-','losses':'-','gf':'-','ga':'-'}
def h2h(home,away):
 try:
  r=call('/fixtures/headtohead',{'h2h':str(home)+'-'+str(away),'last':5}).get('response',[])
  return len(r)
 except:return '-'
def section(data):
 rows=[]
 for x in data.get('events',[]):
  h=x['home_stats'];a=x['away_stats']
  rows.append(f"<tr><td>{escape(x['code'])}</td><td>{escape(x['league'])}<br>{escape(x['venue'])}</td><td>{escape(h['form'])}<br>{h['wins']}W {h['draws']}D {h['losses']}L<br>GF {h['gf']} / GA {h['ga']}</td><td>{escape(a['form'])}<br>{a['wins']}W {a['draws']}D {a['losses']}L<br>GF {a['gf']} / GA {a['ga']}</td><td>主 {x['injury_home']} / 客 {x['injury_away']}<br>{escape(x['injury_note'])}</td><td>近5次交锋：{x['h2h_count']} 场<br>主场/客场：已确认</td></tr>")
 return "<!-- FUND_START --><div class='card'><h2>每日基本面采集</h2><p class='small'>只处理当天中国竞彩可售白名单比赛；09:00 深度缓存，下午不重复抓取。伤停“0条”仅代表 API 当前无条目，不代表确认全员健康。</p><table><tr><th>编号</th><th>联赛/场地</th><th>主队赛季表现</th><th>客队赛季表现</th><th>伤停</th><th>对阵</th></tr>"+(''.join(rows) if rows else '<tr><td colspan="6">暂无可匹配的 API-Football 基本面数据。</td></tr>')+"</table></div><!-- FUND_END -->"
def main():
 DATA.mkdir(exist_ok=True);DOCS.mkdir(exist_ok=True);today=datetime.now(CST).strftime('%Y-%m-%d');cache=load(DATA/'fundamentals_daily.json',{})
 # Cache per China day: no repeat full stats collection in 14:00 scan.
 if cache.get('date')==today:data=cache
 else:
  ctx=load(DATA/'api_context.json',{});latest=load(DATA/'latest_zgzcw.json',{});events=[]
  by={e['code']:e for e in latest.get('events',[])}
  for code,c in ctx.items():
   if not str(c.get('status','')).startswith('已匹配'):continue
   e=by.get(code)
   if not e or not c.get('league_id') or not c.get('season'):continue
   hs=stat(c['home_team_id'],c['league_id'],c['season']);as_=stat(c['away_team_id'],c['league_id'],c['season'])
   events.append({'code':code,'league':c.get('league','-'),'venue':c.get('venue') or '-','home_stats':hs,'away_stats':as_,'injury_home':c.get('injury_home','-'),'injury_away':c.get('injury_away','-'),'injury_note':'API当前伤停条目','h2h_count':h2h(c['home_team_id'],c['away_team_id'])})
  data={'date':today,'updated_at':datetime.now(CST).isoformat(),'events':events};dump(DATA/'fundamentals_daily.json',data)
 p=DOCS/'index.html'
 if p.exists():
  html=p.read_text(encoding='utf8');html=re.sub(r'<!-- FUND_START -->.*?<!-- FUND_END -->','',html,flags=re.S);html=html.replace('</main>',section(data)+'</main>');p.write_text(html,encoding='utf8')
if __name__=='__main__':main()
