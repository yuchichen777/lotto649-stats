"""抓取台灣彩券「大樂透」歷史開獎資料，存成 data/lotto649.json。

第一次執行會從 2007-01 抓到本月；之後只補抓最後一筆資料所在月份到本月（增量更新）。
只用 Python 標準函式庫。

用法：
    python scraper.py          # 增量更新
    python scraper.py --full   # 全部重抓
"""
import json
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path

API = ("https://api.taiwanlottery.com/TLCAPIWeB/Lottery/Lotto649Result"
       "?period&month={month}&pageNum=1&pageSize=50")
DATA_FILE = Path(__file__).parent / "data" / "lotto649.json"
FIRST_MONTH = (2007, 1)

# API 欄位 -> 獎項名稱（依獎項高低排序）
PRIZE_KEYS = [
    ("jackpotAssign", "頭獎"),
    ("secondAssign", "貳獎"),
    ("thirdAssign", "參獎"),
    ("fourthAssign", "肆獎"),
    ("fifthAssign", "伍獎"),
    ("sixthAssign", "陸獎"),
    ("seventhAssign", "柒獎"),
    ("normalAssign", "普獎"),
]


def fetch_month(year, month):
    url = API.format(month=f"{year:04d}-{month:02d}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 lotto649-stats"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                payload = json.load(resp)
            return (payload.get("content") or {}).get("lotto649Res") or []
        except Exception as exc:  # 網路偶發錯誤就重試
            if attempt == 2:
                raise
            print(f"  {year}-{month:02d} 失敗（{exc}），重試中…")
            time.sleep(3)


def parse_draw(raw):
    nums = raw["drawNumberSize"]
    return {
        "period": raw["period"],
        "date": raw["lotteryDate"][:10],
        "numbers": sorted(nums[:6]),
        "special": nums[6],
        "order": raw["drawNumberAppear"][:6],  # 開出順序
        "sales": raw.get("sellAmount"),
        "prizes": [
            {
                "name": name,
                "winners": (raw.get(key) or {}).get("winnerCount", 0),
                "amount": (raw.get(key) or {}).get("perPrize", 0),
            }
            for key, name in PRIZE_KEYS
        ],
    }


def iter_months(start, end):
    y, m = start
    while (y, m) <= end:
        yield y, m
        m += 1
        if m > 12:
            y, m = y + 1, 1


def main():
    full = "--full" in sys.argv
    draws = {}
    if DATA_FILE.exists() and not full:
        for d in json.loads(DATA_FILE.read_text(encoding="utf-8")):
            draws[d["period"]] = d

    if draws:
        last_date = max(d["date"] for d in draws.values())
        start = (int(last_date[:4]), int(last_date[5:7]))
    else:
        start = FIRST_MONTH

    today = date.today()
    before = len(draws)
    for y, m in iter_months(start, (today.year, today.month)):
        rows = fetch_month(y, m)
        for raw in rows:
            d = parse_draw(raw)
            draws[d["period"]] = d
        print(f"{y}-{m:02d}: {len(rows)} 期")
        time.sleep(0.3)  # 對官方伺服器客氣一點

    result = sorted(draws.values(), key=lambda d: d["period"], reverse=True)
    DATA_FILE.parent.mkdir(exist_ok=True)
    DATA_FILE.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")),
                         encoding="utf-8")
    print(f"完成：共 {len(result)} 期（新增 {len(result) - before} 期）")


if __name__ == "__main__":
    main()
