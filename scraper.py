"""抓取台灣彩券各玩法歷史開獎資料，存成 data/<slug>.json。

第一次執行會從各玩法最早的月份抓到本月；之後只補抓最後一筆資料所在月份到本月（增量更新）。
已停售的玩法有資料後就不再抓。賓果賓果每天約 203 期，另外按月存成 data/bingo/<年-月>.json。
樂合彩沒有自己的開獎，不用抓。只用 Python 標準函式庫。

用法：
    python scraper.py                 # 全部玩法增量更新
    python scraper.py daily539 3d     # 只更新指定玩法
    python scraper.py --full lotto649 # 指定玩法全部重抓
    python scraper.py bingo           # 只更新賓果賓果
"""
import json
import sys
import time
import urllib.request
from datetime import date, timedelta
from pathlib import Path

from games import BY_SLUG, DRAW_GAMES

API = ("https://api.taiwanlottery.com/TLCAPIWeB/Lottery/{endpoint}"
       "?period&month={month}&pageNum=1&pageSize=50")
BINGO_API = ("https://api.taiwanlottery.com/TLCAPIWeB/Lottery/BingoResult"
             "?openDate={day}&pageNum=1&pageSize=300")
DATA_DIR = Path(__file__).parent / "data"


def fetch_json(url, label):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 lottotw-stats"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.load(resp)
        except Exception as exc:  # 網路偶發錯誤就重試
            if attempt == 2:
                raise
            print(f"  {label} 失敗（{exc}），重試中…")
            time.sleep(3)


def fetch_month(game, year, month):
    url = API.format(endpoint=game["endpoint"], month=f"{year:04d}-{month:02d}")
    payload = fetch_json(url, f"{game['name']} {year}-{month:02d}")
    return (payload.get("content") or {}).get(game["res_key"]) or []


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


def update_bingo(full=False):
    """每期存成 [期別, 開出順序]；開出順序是 20 個兩位數接起來的字串，最後一個就是超級獎號"""
    game = BY_SLUG["bingo"]
    folder = DATA_DIR / "bingo"
    folder.mkdir(parents=True, exist_ok=True)
    files = sorted(folder.glob("*.json"))
    start = date.fromisoformat(game["first_day"])
    if files and not full:
        last = json.loads(files[-1].read_text(encoding="utf-8"))
        start = date.fromisoformat(max(last))  # 最後一天可能還沒開完，重抓

    months, added, day = {}, 0, start
    while day <= date.today():
        payload = fetch_json(BINGO_API.format(day=day.isoformat()), f"賓果 {day}")
        rows = (payload.get("content") or {}).get("bingoQueryResult") or []
        if rows:
            key = day.isoformat()[:7]
            if key not in months:
                path = folder / f"{key}.json"
                months[key] = json.loads(path.read_text(encoding="utf-8")) if path.exists() and not full else {}
            before = len(months[key].get(day.isoformat(), []))
            months[key][day.isoformat()] = sorted(
                [r["drawTerm"], "".join(r["openShowOrder"])] for r in rows)
            added += len(rows) - before
        day += timedelta(days=1)
        time.sleep(0.2)

    for key, days in months.items():
        (folder / f"{key}.json").write_text(
            json.dumps(dict(sorted(days.items())), separators=(",", ":")), encoding="utf-8")
    print(f"{game['name']}：新增 {added} 期")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    full = "--full" in sys.argv
    games = [BY_SLUG[a] for a in args] if args else DRAW_GAMES + [BY_SLUG["bingo"]]
    for game in games:
        if game["kind"] == "bingo":
            update_bingo(full)
        elif game["kind"] != "combo":
            update(game, full)


if __name__ == "__main__":
    main()
