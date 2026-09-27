#!/usr/bin/env python3
"""highwaybus.com 유후인→후쿠오카공항 2026-10-04 10:30 / 11:00 편 빈자리 감시."""
import json, os, re, time, warnings
warnings.filterwarnings("ignore")
import requests
from bs4 import BeautifulSoup

URL = ("https://www.highwaybus.com/gp/reservation/rsvPlanList?mode=search&route=166&lineId=482"
       "&nearCheckOnStation=&nearCheckOffStation=&onStationCd=1227&offStationCd=1139&bordingDate=20261004"
       "&danseiNum=1&zyoseiNum=1&adultMen=1&adultWomen=1&childMen=0&childWomen=0"
       "&handicapAdultMen=0&handicapAdultWomen=0&handicapChildMen=0&handicapChildWomen=0")
TARGETS = ["10:30", "11:00"]
HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "state", "bus_state.json")
REMIND_SEC = 30 * 60  # 계속 빈자리면 30분마다 재알림


NTFY_TOPIC = os.environ["NTFY_TOPIC"]  # GitHub Secret


def push(title, msg, url):
    try:
        requests.post("https://ntfy.sh/", timeout=15, json={
            "topic": NTFY_TOPIC, "title": title, "message": msg, "priority": 5, "click": url})
    except Exception as e:
        print("ntfy 실패:", e)


def notify(title, msg, url):
    push(title, msg, url)


def check():
    html = requests.get(URL, timeout=30, headers={"User-Agent": "Mozilla/5.0"}).text
    soup = BeautifulSoup(html, "html.parser")
    result = {}
    for item in soup.select("section.busSvclistItem"):
        t = item.select_one("li.dep p.time")
        if not t:
            continue
        dep = re.search(r"\d{1,2}:\d{2}", t.get_text()).group()
        if dep not in TARGETS:
            continue
        plans = item.select("section.busSvclistItem_howToBuy span[name^=span_]")
        avail = []
        for p in plans:
            name = p.select_one("li p").get_text(strip=True)
            seat = p.select_one("input[class^=seat_]")  # value 2 = 満席
            btn = p.select_one("button")
            if seat and seat.get("value") != "2":
                avail.append(f"{name}: {btn.get_text(strip=True) if btn else '空席'}")
        result.setdefault(dep, []).extend(avail)
    return result


def main():
    state = json.load(open(STATE)) if os.path.exists(STATE) else {}
    res = check()
    now = time.time()
    print(time.strftime("%F %T"), {k: (v or "매진") for k, v in res.items()})
    missing = [t for t in TARGETS if t not in res]
    if missing:
        print("경고: 페이지에서 편을 못 찾음", missing)
        if len(missing) == len(TARGETS):
            raise SystemExit("페이지 구조 변경 또는 로드 실패")
    for dep, avail in res.items():
        if avail and now - state.get(dep, 0) > REMIND_SEC:
            notify("🚌 고속버스 빈자리!", f"10/4 유후인 {dep} 발: " + " / ".join(avail), URL)
            state[dep] = now
        elif not avail:
            state.pop(dep, None)
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    json.dump(state, open(STATE, "w"))


if __name__ == "__main__":
    main()
