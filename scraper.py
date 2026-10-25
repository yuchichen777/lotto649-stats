"""抓取台灣彩券各玩法歷史開獎資料，存成 data/<slug>.json。

第一次執行會從各玩法最早的月份抓到本月；之後只補抓最後一筆資料所在月份到本月（增量更新）。
已停售的玩法有資料後就不再抓。只用 Python 標準函式庫。

用法：
    python scraper.py                 # 全部玩法增量更新
    python scraper.py daily539 3d     # 只更新指定玩法
    python scraper.py --full lotto649 # 指定玩法全部重抓
"""
import json
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path

from games import BY_SLUG, GAMES

API = ("https://api.taiwanlottery.com/TLCAPIWeB/Lottery/{endpoint}"
       "?period&month={month}&pageNum=1&pageSize=50")
DATA_DIR = Path(__file__).parent / "data"


def fetch_month(game, year, month):
    url = API.format(endpoint=game["endpoint"], month=f"{year:04d}-{month:02d}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 lottotw-stats"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                payload = json.load(resp)
            return (payload.get("content") or {}).get(game["res_key"]) or []
        except Exception as exc:  # 網路偶發錯誤就重試
            if attempt == 2:
                raise
            print(f"  {game['name']} {year}-{month:02d} 失敗（{exc}），重試中…")
            time.sleep(3)


def parse_draw(game, raw):
    appear = raw.get("drawNumberAppear") or []
    if game["kind"] == "digits":
        numbers, special, order = list(appear), None, list(appear)
    else:
        nums = raw.get("drawNumberSize") or sorted(appear)
        k = game["pick"]
        numbers = sorted(nums[:k])
        special = nums[k] if game["special"] else None
        order = appear[:k]

    prizes = []
    for key, name, _ in game["prizes"]:
        p = raw.get(key) or {}
        if p.get("bonus"):
            name = f"{name}（{p['bonus']}）"
        prizes.append({"name": name, "winners": p.get("winnerCount") or 0,
                       "amount": p.get("perPrize") or 0})

    return {
        "period": raw["period"],
        "date": raw["lotteryDate"][:10],
        "numbers": numbers,
        "special": special,
        "order": order,
        "sales": raw.get("sellAmount"),
        "prizes": prizes,
    }


def iter_months(start, end):
    y, m = start
    while (y, m) <= end:
        yield y, m
        m += 1
        if m > 12:
            y, m = y + 1, 1


def update(game, full=False):
    path = DATA_DIR / f"{game['slug']}.json"
    draws = {}
    if path.exists() and not full:
        for d in json.loads(path.read_text(encoding="utf-8")):
            draws[d["period"]] = d

    if draws and not game["active"]:
        print(f"{game['name']}：已停售，略過")
        return

    if draws:
        last_date = max(d["date"] for d in draws.values())
        start = (int(last_date[:4]), int(last_date[5:7]))
    else:
        start = game["first_month"]

    today = date.today()
    before = len(draws)
    for y, m in iter_months(start, (today.year, today.month)):
        for raw in fetch_month(game, y, m):
            d = parse_draw(game, raw)
            draws[d["period"]] = d
        time.sleep(0.3)  # 對官方伺服器客氣一點

    result = sorted(draws.values(), key=lambda d: d["period"], reverse=True)
    DATA_DIR.mkdir(exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")),
                    encoding="utf-8")
    print(f"{game['name']}：共 {len(result)} 期（新增 {len(result) - before} 期）")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    games = [BY_SLUG[a] for a in args] if args else GAMES
    for game in games:
        update(game, full="--full" in sys.argv)


if __name__ == "__main__":
    main()
