#!/usr/bin/env python3
"""JR 사이버스테이션: 2026-10-03 博多→由布院 10:11 ゆふいんの森3号 지정석 빈자리 감시.
(Klook은 봇 차단으로 직접 조회 불가 → 같은 JR 좌석을 JR 쪽에서 조회)"""
import datetime, json, os, time, warnings
warnings.filterwarnings("ignore")
import requests
from bs4 import BeautifulSoup
from bus_watch import push

B = "https://www.jr.cyberstation.ne.jp"
QUERY = {"lang": "ja", "month": "10", "day": "3", "hour": "10", "minute": "00",
         "train": "5", "dep_stnpb": "9050", "arr_stnpb": "9488", "script": "1"}  # 博多→由布院
DEP, NAME = "10:11", "ゆふいんの森"
KLOOK_URL = ("https://www.klook.com/ko/rails-32/1012-japan/search/?date_range_count=120"
             "&origin_position_name=%ED%95%98%EC%B9%B4%ED%83%80&origin_position=5b281d7d-0b49-4b1a-996b-73012433b3f6"
             "&destination_position_name=%EC%9C%A0%ED%9B%84%EC%9D%B8&destination_position=6c2861f4-d8bf-4360-bdcb-833bf3ed2a69"
             "&departure_date=2026-10-03&passengers=%5B%5D&isExternal=1")
HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "state", "jr_state.json")
REMIND_SEC = 30 * 60
JST = datetime.timezone(datetime.timedelta(hours=9))


def check():
    s = requests.Session()
    h = {"User-Agent": "Mozilla/5.0", "Referer": B + "/"}
    s.get(B + "/jcs/VacancyInput.do", headers=h, timeout=30)
    h["Referer"] = B + "/jcs/VacancyInput.do"
    html = s.post(B + "/jcs/Vacancy.do", data=QUERY, headers=h, timeout=30).content
    soup = BeautifulSoup(html, "html.parser")
    for tr in soup.find_all("tr"):
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
        if cells and DEP in cells[0] and NAME in cells[0]:
            return cells[0].replace("　", ""), cells[1]  # 普通車 指定席 기호
    return None, None


def main():
    now_jst = datetime.datetime.now(JST)
    if not (6 <= now_jst.hour < 23 or (now_jst.hour == 23 and now_jst.minute < 50)):
        print(now_jst.strftime("%F %T JST"), "JR 조회 운영시간(6:00~23:50) 외 — 건너뜀")
        return
    train, mark = check()
    print(now_jst.strftime("%F %T JST"), train, mark)
    if train is None:
        raise SystemExit("JR 조회 결과에서 대상 열차를 못 찾음 (페이지 변경/차단)")
    state = json.load(open(STATE)) if os.path.exists(STATE) else {}
    if mark in ("○", "△"):
        if time.time() - state.get("notified", 0) > REMIND_SEC:
            label = "여유 있음" if mark == "○" else "얼마 안 남음"
            push("🚆 유후인노모리 3호 빈자리!",
                 f"10/3 하카타 10:11 → 유후인 12:27 지정석 {label}({mark}). 지금 Klook에서 예약하세요",
                 KLOOK_URL)
            state["notified"] = time.time()
    else:
        state.pop("notified", None)
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    json.dump(state, open(STATE, "w"))


if __name__ == "__main__":
    main()
