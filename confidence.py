def assess(event,bjzs,external,notes,goalodds,movement,daily_by=None,ai_by=None,api_ctx=None):
 target=next((m for m in event.get("markets",[]) if m.get("market")=="1X2"),None)
 b=bjzs.get(event.get("analysis_match_id") or event.get("source_match_id"));ext=external.get(event.get("source_match_id"),{})
 daily=(daily_by or {}).get(event["code"],{});ai=(ai_by or {}).get(event["code"],{});api=(api_ctx or {}).get(event["code"],{})
 n=len(ext.get("books",[])) if ext.get("available") else 0;ai_sources=len(ai.get("sources",[]));confirmed=ai.get("research",{}).get("confirmed",[])
 hs=daily.get("home_stats",{});as_=daily.get("away_stats",{});stats_ok=hs.get("form") not in (None,"-","源未返回","") or as_.get("form") not in (None,"-","源未返回","")
 breakdown={"中国竞彩":20 if target else 0,"百家平均":15 if b else 0,"进球模型":10 if event.get("source_match_id") in goalodds else 0,"API赛程":10 if str(api.get("status","")).startswith("已匹配") else 0,"AI搜索":10 if ai_sources else 0,"AI事实":5 if confirmed else 0,"外部机构":25 if n>=6 else 20 if n>=3 else 8 if n>=1 else 0,"盘口变化":5 if not movement.startswith("首次") else 0,"首发确认":0}
 score=sum(breakdown.values());level="高" if score>=75 else "中" if score>=50 else "低"
 flags={"china":"已读取" if target else "未读取","average":"已读取" if b else "未读取","external":f"{n}家" if n else "0家","fundamental":f"AI已读取({ai_sources}源)" if ai_sources else ("API统计已读取" if stats_ok else "源未返回"),"injury":"AI已提取" if confirmed else (f"API条目 主{daily.get('injury_home','-')}/客{daily.get('injury_away','-')}" if daily else "源未返回"),"movement":"首次快照" if movement.startswith("首次") else ("可能滞后" if "可能滞后" in movement else "已同步/待观察"),"model":"已生成" if breakdown["进球模型"] else "未生成"}
 kelly=0.0
 if target and n>=3:
  ps=ext.get("median_fair",[]);od=[target["home_win"],target["draw"],target["away_win"]]
  if len(ps)==3:kelly=min(max([max(0,(max(0,p-.02)*o-1)/(o-1))*.25 for p,o in zip(ps,od)]),.01)
 return {"score":score,"level":level,"kelly":kelly,"flags":flags,"breakdown":breakdown,"forced_cap":.0025}
