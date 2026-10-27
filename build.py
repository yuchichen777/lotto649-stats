"""把 data/<玩法>.json 產生成靜態網站，輸出到 dist/。

用法：
    python build.py
然後執行 python -m http.server -d dist 預覽。
只用 Python 標準函式庫。
"""
import json
import shutil
from collections import Counter
from datetime import date, timedelta
from math import comb
from html import escape
from pathlib import Path

from games import BY_SLUG, DRAW_GAMES, GAMES

ROOT = Path(__file__).parent
OUT = ROOT / "dist"
CFG = json.loads((ROOT / "site.json").read_text(encoding="utf-8"))
WEEKDAYS = "一二三四五六日"
RECENT = 100  # 「近期」統計用的期數
POSITIONS = {3: ["百位", "十位", "個位"], 4: ["千位", "百位", "十位", "個位"]}

pages = []  # 給 sitemap 用


def money(n):
    return f"{n:,}" if n else "—"


def zh_date(s):
    d = date.fromisoformat(s)
    return f"{d.year}/{d.month:02d}/{d.day:02d}（{WEEKDAYS[d.weekday()]}）"


def fmt_nums(game, nums):
    return " ".join(str(n) if game["kind"] == "digits" else f"{n:02d}" for n in nums)


def balls(game, draw, small=False):
    cls = "ball sm" if small else "ball"
    if game["kind"] == "digits":
        return '<div class="balls">' + "".join(
            f'<span class="{cls} digit">{n}</span>' for n in draw["numbers"]) + "</div>"
    html = "".join(f'<span class="{cls}">{n:02d}</span>' for n in draw["numbers"])
    if draw["special"] is not None:
        html += f'<span class="plus">+</span><span class="{cls} sp">{draw["special"]:02d}</span>'
    return f'<div class="balls">{html}</div>'


def mini_balls(nums):
    return '<div class="balls">' + "".join(
        f'<span class="ball sm">{n:02d}</span>' for n in nums) + "</div>"


def page(path, title, body, *, game=None, sub="", description=None, sitemap=True, head=""):
    """寫出一個頁面。path 是相對 dist/ 的路徑，用來算出回到根目錄的 ../"""
    root = "../" * path.count("/")
    full_title = f"{title}｜{CFG['short_name']}" if title else CFG["name"]
    desc = escape(description or CFG["description"])
    url_path = path.removesuffix("index.html")
    canonical = f"{CFG['base_url'].rstrip('/')}/{url_path}"
    if sitemap:
        pages.append(url_path)

    if CFG.get("adsense_client"):
        head += ('<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js'
                 f'?client={escape(CFG["adsense_client"])}" crossorigin="anonymous"></script>\n')
    if CFG.get("ga_measurement_id"):
        gid = escape(CFG["ga_measurement_id"])
        head += (f'<script async src="https://www.googletagmanager.com/gtag/js?id={gid}"></script>\n'
                 "<script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments)}"
                 f"gtag('js',new Date());gtag('config','{gid}');</script>\n")

    nav = "".join(
        f'<a href="{root}{g["slug"]}/"{" class=\"on\"" if game and g is game else ""}>{g["name"]}</a>'
        for g in GAMES)
    subnav = ""
    if game:
        base = f"{root}{game['slug']}/"
        tabs = [("", "最新開獎", "home"), ("check.html", "對獎", "check"),
                ("stats.html", "號碼統計", "stats"), ("history/", "歷史紀錄", "history")]
        if game["kind"] == "combo":  # 統計跟母玩法一樣，不另外做
            tabs = [t for t in tabs if t[2] != "stats"]
        subnav = '<nav class="subnav">' + "".join(
            f'<a href="{base}{href}"{" class=\"on\"" if key == sub else ""}>{label}</a>'
            for href, label, key in tabs) + "</nav>"

    html = f"""<!doctype html>
<html lang="zh-Hant-TW">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(full_title)}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{escape(canonical)}">
<meta property="og:title" content="{escape(full_title)}">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="website">
<link rel="stylesheet" href="{root}static/style.css">
{head}</head>
<body>
<header class="site"><div class="wrap">
  <a class="logo" href="{root or './'}">🎱 {escape(CFG['short_name'])}</a>
  <nav>{nav}</nav>
</div></header>
<main><div class="wrap">
{subnav}
{body}
</div></main>
<footer><div class="wrap">
  <p>資料來源：台灣彩券官方網站，每期開獎後自動更新。開獎結果以台灣彩券公告為準。本站與台灣彩券股份有限公司無關。</p>
  <p>本站統計僅供參考與娛樂，彩券為隨機開獎，過去號碼無法預測未來結果。請量力而為，未滿 18 歲不得購買彩券。</p>
  <p><a href="{root}about.html">關於本站・隱私權政策</a></p>
</div></footer>
<script src="{root}static/app.js"></script>
</body>
</html>
"""
    target = OUT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html, encoding="utf-8")


def redirect(path, to):
    """舊網址轉到新網址（不列入 sitemap）"""
    url = f"{CFG['base_url'].rstrip('/')}/{to}"
    target = OUT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        f'<!doctype html><meta charset="utf-8"><link rel="canonical" href="{url}">'
        f'<meta http-equiv="refresh" content="0; url={url}"><script>location.replace("{url}")</script>'
        f'<a href="{url}">頁面已移到這裡</a>\n', encoding="utf-8")


def prize_table(draw):
    rows = "".join(
        f'<tr><td>{p["name"]}</td><td class="r">{p["winners"]:,}</td>'
        f'<td class="r">{money(p["amount"]) if p["winners"] else "槓龜"}</td></tr>'
        for p in draw["prizes"])
    return ('<div class="scroll"><table><thead><tr><th>獎項</th><th class="r">中獎注數</th>'
            f'<th class="r">每注獎金（元）</th></tr></thead><tbody>{rows}</tbody></table></div>')


def latest_card(game, d, prefix=""):
    order = ""
    if game["kind"] == "pick":
        order = f"開出順序：{fmt_nums(game, d['order'])}　"
        if d["special"] is not None:
            order += f"{game['special_label']}：{d['special']:02d}　"
    return f"""<div class="card">
  {balls(game, d)}
  <p class="meta">{order}銷售金額：{money(d['sales'])} 元</p>
  <div class="row"><a class="btn primary" href="{prefix}check.html">我要對獎 →</a>
  <a class="btn" href="{prefix}draw/{d['period']}.html">本期獎金明細</a></div>
</div>"""


# ---------- 統計 ----------

def pick_stats(game, draws):
    total = len(draws)
    pool = range(1, game["pool"] + 1)
    st = {
        "total": total,
        "all": Counter(n for d in draws for n in d["numbers"]),
        "recent": Counter(n for d in draws[:RECENT] for n in d["numbers"]),
        "special": Counter(d["special"] for d in draws if d["special"] is not None),
        "gap_now": {}, "gap_max": {},
    }
    for n in pool:
        run, longest = 0, 0
        for d in reversed(draws):  # 由舊到新
            if n in d["numbers"]:
                longest = max(longest, run)
                run = 0
            else:
                run += 1
        st["gap_now"][n] = run
        st["gap_max"][n] = max(longest, run)
    st["odd_even"] = Counter(sum(n % 2 for n in d["numbers"]) for d in draws)
    st["sum_avg"] = sum(sum(d["numbers"]) for d in draws) / total
    st["consecutive"] = sum(
        any(b - a == 1 for a, b in zip(d["numbers"], d["numbers"][1:])) for d in draws)
    st["jackpot_none"] = sum(1 for d in draws if d["prizes"][0]["winners"] == 0)
    st["hot"] = sorted(pool, key=lambda n: (-st["recent"][n], n))[:game["pick"]]
    st["cold"] = sorted(pool, key=lambda n: (-st["gap_now"][n], n))[:game["pick"]]
    return st


def build_pick_stats(game, draws, st):
    total = st["total"]
    k, pool = game["pick"], game["pool"]
    max_all = max(st["all"].values())
    max_recent = max(st["recent"].values()) or 1
    hot_cut = sorted(st["recent"].values(), reverse=True)[k - 1]
    same_special = game["special"] == "same"
    rows = []
    for n in range(1, pool + 1):
        a, r = st["all"][n], st["recent"][n]
        hot = " hot" if r >= hot_cut else ""
        sp = (f'<td class="r" data-v="{st["special"][n]}">{st["special"][n]}</td>'
              if same_special else "")
        rows.append(
            f'<tr><td data-v="{n}"><span class="ball sm">{n:02d}</span></td>'
            f'<td class="r" data-v="{a}">{a}</td>'
            f'<td class="barcol" data-v="{a}"><div class="bar" style="width:{a / max_all * 100:.0f}%"></div></td>'
            f'<td class="r" data-v="{r}">{r}</td>'
            f'<td class="barcol" data-v="{r}"><div class="bar{hot}" style="width:{r / max_recent * 100:.0f}%"></div></td>'
            f'<td class="r" data-v="{st["gap_now"][n]}">{st["gap_now"][n]}</td>'
            f'<td class="r" data-v="{st["gap_max"][n]}">{st["gap_max"][n]}</td>{sp}</tr>')
    sp_head = f'<th class="r" data-sort="desc">{game["special_label"]}次數</th>' if same_special else ""

    zone_card = ""
    if game["special"] == "zone":
        zmax = max(st["special"].values())
        zrows = "".join(
            f'<tr><td><span class="ball sm sp">{n:02d}</span></td><td class="r">{st["special"][n]}</td>'
            f'<td class="barcol"><div class="bar" style="width:{st["special"][n] / zmax * 100:.0f}%"></div></td></tr>'
            for n in range(1, game["zone_pool"] + 1))
        zone_card = f"""<div class="card"><h2>{game['special_label']}出現次數</h2>
  <table><thead><tr><th>號碼</th><th class="r">次數</th><th class="barcol"></th></tr></thead>
  <tbody>{zrows}</tbody></table>
  <p class="note">理論上每個號碼機率 1/{game['zone_pool']}，期望次數約 {total / game['zone_pool']:,.0f} 次。</p></div>"""

    oe_rows = "".join(
        f'<tr><td>{odd} 單 {k - odd} 雙</td><td class="r">{st["odd_even"][odd]:,}</td>'
        f'<td class="r">{st["odd_even"][odd] / total:.1%}</td></tr>'
        for odd in range(k + 1))

    body = f"""
<h1>{game['name']}號碼統計</h1>
<p class="sub">統計 {draws[-1]['date']} 至 {draws[0]['date']} 共 {total:,} 期開獎資料。點表頭可以排序。</p>
<div class="card">
  <div class="scroll"><table class="sortable">
  <thead><tr>
    <th data-sort="asc">號碼</th>
    <th class="r" data-sort="desc">累計次數</th><th class="barcol"></th>
    <th class="r" data-sort="desc">近 {RECENT} 期</th><th class="barcol"></th>
    <th class="r" data-sort="desc">目前遺漏</th>
    <th class="r" data-sort="desc">最長遺漏</th>{sp_head}
  </tr></thead>
  <tbody>{''.join(rows)}</tbody></table></div>
  <p class="note">「遺漏」＝連續幾期沒有開出。理論上每個號碼每期開出機率都是 {k}/{pool} ≈ {k / pool:.1%}，
  {total:,} 期的期望次數約 {total * k / pool:,.0f} 次。</p>
</div>
<div class="ad"></div>
{zone_card}
<div class="grid2">
  <div class="card">
    <h2>單雙號分布</h2>
    <table><thead><tr><th>組合</th><th class="r">期數</th><th class="r">比例</th></tr></thead>
    <tbody>{oe_rows}</tbody></table>
  </div>
  <div class="card">
    <h2>其他統計</h2>
    <table><tbody>
      <tr><td>{k} 個號碼總和平均</td><td class="r">{st['sum_avg']:.1f}</td></tr>
      <tr><td>理論平均</td><td class="r">{k * (pool + 1) / 2:.1f}</td></tr>
      <tr><td>有連號的期數</td><td class="r">{st['consecutive']:,}（{st['consecutive'] / total:.1%}）</td></tr>
      <tr><td>頭獎槓龜期數</td><td class="r">{st['jackpot_none']:,}（{st['jackpot_none'] / total:.1%}）</td></tr>
    </tbody></table>
  </div>
</div>
<p class="note">統計結果接近理論值，正好說明開獎是隨機的：歷史資料無法提高中獎機率。</p>
"""
    page(f"{game['slug']}/stats.html", f"{game['name']}號碼統計", body, game=game, sub="stats",
         description=f"{game['name']}每個號碼的歷史出現次數、近 {RECENT} 期熱門號碼與遺漏期數統計。")


def build_digit_stats(game, draws):
    total = len(draws)
    n = game["digits"]
    pos_names = POSITIONS[n]
    counts = [Counter(d["numbers"][i] for d in draws) for i in range(n)]
    recent = [Counter(d["numbers"][i] for d in draws[:RECENT]) for i in range(n)]
    rows = "".join(
        f'<tr><td><span class="ball sm digit">{v}</span></td>' +
        "".join(f'<td class="r" data-v="{counts[i][v]}">{counts[i][v]:,}'
                f'<span class="meta">（近{RECENT}期 {recent[i][v]}）</span></td>' for i in range(n)) +
        "</tr>" for v in range(10))
    kinds = Counter(len(set(d["numbers"])) for d in draws)
    kind_rows = "".join(
        f'<tr><td>{label}</td><td class="r">{kinds[c]:,}</td><td class="r">{kinds[c] / total:.1%}</td></tr>'
        for c, label in sorted(
            {n: "全部不同", n - 1: "有一組重複", 1: "全部相同",
             **({2: "兩兩重複或三個相同"} if n == 4 else {})}.items(), reverse=True))
    sum_avg = sum(sum(d["numbers"]) for d in draws) / total
    body = f"""
<h1>{game['name']}號碼統計</h1>
<p class="sub">統計 {draws[-1]['date']} 至 {draws[0]['date']} 共 {total:,} 期開獎資料。</p>
<div class="card"><h2>各位數出現次數</h2>
  <div class="scroll"><table>
  <thead><tr><th>數字</th>{''.join(f'<th class="r">{p}</th>' for p in pos_names)}</tr></thead>
  <tbody>{rows}</tbody></table></div>
  <p class="note">理論上每個位數開出 0～9 的機率都是 10%，期望次數約 {total / 10:,.0f} 次。</p>
</div>
<div class="ad"></div>
<div class="grid2">
  <div class="card"><h2>號碼重複情形</h2>
    <table><thead><tr><th>類型</th><th class="r">期數</th><th class="r">比例</th></tr></thead>
    <tbody>{kind_rows}</tbody></table></div>
  <div class="card"><h2>其他統計</h2>
    <table><tbody>
      <tr><td>{n} 個數字總和平均</td><td class="r">{sum_avg:.2f}</td></tr>
      <tr><td>理論平均</td><td class="r">{n * 4.5:.2f}</td></tr>
    </tbody></table></div>
</div>
<p class="note">統計結果接近理論值，正好說明開獎是隨機的：歷史資料無法提高中獎機率。</p>
"""
    page(f"{game['slug']}/stats.html", f"{game['name']}號碼統計", body, game=game, sub="stats",
         description=f"{game['name']}各位數 0～9 歷史出現次數與號碼重複情形統計。")


# ---------- 各玩法頁面 ----------

def build_game_home(game, draws, st):
    latest = draws[0]
    recent_rows = "".join(
        f'<tr><td><a href="draw/{d["period"]}.html">{d["period"]}</a></td>'
        f'<td>{d["date"]}</td><td>{balls(game, d, small=True)}</td></tr>'
        for d in draws[1:11])
    status = "" if game["active"] else '<span class="tag">已停售</span>'
    hot_cold = ""
    if st:
        hot_cold = f"""<div class="grid2">
  <div class="card"><h2>近 {RECENT} 期熱門號碼</h2>{mini_balls(st['hot'])}
    <p class="meta">近 {RECENT} 期出現次數最多的號碼</p></div>
  <div class="card"><h2>目前遺漏最久的號碼</h2>{mini_balls(st['cold'])}
    <p class="meta">最多已連續 {st['gap_now'][st['cold'][0]]} 期沒開出</p></div>
</div>
<p class="note">熱門／冷門號碼只是歷史統計，每期開獎都是獨立事件，不代表下期比較容易開出。<a href="stats.html">看完整統計 →</a></p>"""
    body = f"""
<h1>{game['name']}{'最新' if game['active'] else '最後一期'}開獎號碼{status}</h1>
<p class="sub">第 {latest['period']} 期・{zh_date(latest['date'])}開獎・{game['schedule']}</p>
{latest_card(game, latest)}
<div class="ad"></div>
{hot_cold}
<div class="card">
  <h2>前 10 期開獎號碼</h2>
  <div class="scroll"><table><thead><tr><th>期別</th><th>日期</th><th>號碼</th></tr></thead>
  <tbody>{recent_rows}</tbody></table></div>
  <p><a href="history/">所有歷史開獎紀錄 →</a></p>
</div>
"""
    special = ""
    if latest["special"] is not None:
        special = f"，{game['special_label']} {latest['special']:02d}"
    page(f"{game['slug']}/index.html", f"{game['name']}開獎號碼", body, game=game, sub="home",
         description=f"{game['name']}第 {latest['period']} 期開獎號碼：{fmt_nums(game, latest['numbers'])}"
                     f"{special}。最新開獎、對獎、歷史紀錄與號碼統計。")


def checker_cfg(game):
    cfg = {"kind": game["kind"],
           "tiers": [{"name": name, "conds": conds} for _, name, conds in game["prizes"]]}
    if game["kind"] == "pick":
        cfg.update(pool=game["pool"], pick=game["pick"], special=game["special"],
                   specialLabel=game.get("special_label", ""), price=game["price"],
                   zonePool=game.get("zone_pool"))
    else:
        cfg["digits"] = game["digits"]
    return escape(json.dumps(cfg, ensure_ascii=False))


def build_check(game):
    if game["kind"] == "digits":
        inputs = "".join(f'<input inputmode="numeric" maxlength="1" aria-label="{p}">'
                         for p in POSITIONS[game["digits"]])
        picker = f"<p>依序輸入 {game['digits']} 個數字（{'、'.join(POSITIONS[game['digits']])}）</p>" \
                 f'<div class="digits">{inputs}</div>'
        intro = f"輸入你的 {game['digits']} 個數字，比對正彩是否中獎；也可以看這組號碼歷年開出過幾次。"
        rules = """<p>「正彩」須號碼與順序完全相同。「組彩」只要號碼相同、不論順序，獎金依號碼組成而定；
  其他玩法（對彩等）的中獎條件與倍數請以台灣彩券公告為準。</p>"""
    else:
        zone = ""
        if game["special"] == "zone":
            zone = f'<p>{game["special_label"]}選 1 個號碼</p><div class="picker zone"></div>'
        picker = (f'<p>第一區已選 <b class="count">0</b> / {game["pick"]} 個號碼</p>'
                  f'<div class="picker main"></div>{zone}')
        intro = f"選 {game['pick']} 個號碼，馬上知道有沒有中獎；也可以回測這組號碼歷年會中幾次。"
        conds_text = []
        for _, name, conds in game["prizes"]:
            parts = []
            for m, s in conds:
                t = f"中 {m} 個號碼" if m else "一個號碼都沒中"
                if m == game["pick"] and not s:
                    t = f"{m} 個號碼全中"
                if s:
                    t += f" + {game['special_label']}"
                parts.append(t)
            conds_text.append(f"<tr><td>{name}</td><td>{'，或'.join(parts)}</td></tr>")
        rules = (f'<div class="scroll"><table><thead><tr><th>獎項</th><th>中獎條件</th></tr></thead>'
                 f'<tbody>{"".join(conds_text)}</tbody></table></div>'
                 f'<p class="note">每注 {game["price"]} 元。')
        rules += "實際兌獎以台灣彩券公告為準，高額獎金需扣稅。</p>"

    body = f"""
<h1>{game['name']}對獎</h1>
<p class="sub">{intro}</p>
<div class="card" data-checker data-src="draws.json" data-cfg="{checker_cfg(game)}">
  {picker}
  <div class="row">
    <button class="btn" data-act="random" type="button">電腦選號</button>
    <button class="btn" data-act="clear" type="button">清除</button>
  </div>
  <div class="row">
    <select aria-label="選擇期別"><option>資料載入中…</option></select>
    <button class="btn primary" data-act="check" type="button" disabled>對獎</button>
    <button class="btn" data-act="history" type="button" disabled>歷史回測</button>
  </div>
  <div class="result" aria-live="polite"></div>
</div>
<div class="ad"></div>
<div class="card"><h2>{game['name']}中獎規則</h2>{rules}</div>
"""
    page(f"{game['slug']}/check.html", f"{game['name']}對獎", body, game=game, sub="check",
         description=f"{game['name']}線上對獎：輸入號碼立即比對最新或任一期開獎結果，並可回測歷年中獎紀錄。")


def build_history(game, draws):
    years = sorted({d["date"][:4] for d in draws}, reverse=True)
    for y in years:
        pager = "".join(
            f'<a href="{x}.html"{" class=\"on\"" if x == y else ""}>{x}</a>' for x in years)
        rows = "".join(
            f'<tr><td><a href="../draw/{d["period"]}.html">{d["period"]}</a></td>'
            f'<td>{zh_date(d["date"])}</td><td>{balls(game, d, small=True)}</td>'
            f'<td class="r">{money(d["prizes"][0]["amount"]) if d["prizes"][0]["winners"] else "槓龜"}</td></tr>'
            for d in draws if d["date"].startswith(y))
        first = game["prizes"][0][1]
        body = f"""
<h1>{y} 年{game['name']}開獎紀錄</h1>
<p class="sub">點期別可以看該期完整獎金明細。</p>
<div class="pager">{pager}</div>
<div class="card"><div class="scroll"><table>
<thead><tr><th>期別</th><th>開獎日期</th><th>號碼</th><th class="r">{first}每注獎金</th></tr></thead>
<tbody>{rows}</tbody></table></div></div>
"""
        page(f"{game['slug']}/history/{y}.html", f"{y} 年{game['name']}開獎紀錄", body,
             game=game, sub="history",
             description=f"{y} 年{game['name']}每期開獎號碼與{first}獎金一覽。")
    # history/ 首頁直接顯示最新年份，但 canonical 指向該年份頁
    redirect(f"{game['slug']}/history/index.html", f"{game['slug']}/history/{years[0]}.html")


def build_draws(game, draws):
    slug = game["slug"]
    for i, d in enumerate(draws):
        newer = draws[i - 1] if i > 0 else None
        older = draws[i + 1] if i + 1 < len(draws) else None
        nav = '<div class="prevnext">' + (
            f'<a href="{older["period"]}.html">← 第 {older["period"]} 期</a>' if older else "<span></span>") + (
            f'<a href="{newer["period"]}.html">第 {newer["period"]} 期 →</a>' if newer else "<span></span>") + "</div>"
        order = ""
        if game["kind"] == "pick":
            order = f"開出順序：{fmt_nums(game, d['order'])}　"
            if d["special"] is not None:
                order += f"{game['special_label']}：{d['special']:02d}　"
        special = f"，{game['special_label']} {d['special']:02d}" if d["special"] is not None else ""
        body = f"""
<h1>{game['name']}第 {d['period']} 期開獎號碼</h1>
<p class="sub">{zh_date(d['date'])}開獎</p>
<div class="card">
  {balls(game, d)}
  <p class="meta">{order}銷售金額：{money(d['sales'])} 元</p>
</div>
<div class="ad"></div>
<div class="card"><h2>各獎項中獎情形</h2>{prize_table(d)}</div>
{nav}
<p><a href="../check.html">用這期對獎 →</a>　<a href="../history/{d['date'][:4]}.html">{d['date'][:4]} 年所有開獎紀錄</a></p>
"""
        page(f"{slug}/draw/{d['period']}.html", f"{game['name']}第 {d['period']} 期開獎號碼", body,
             game=game, sub="history",
             description=f"{game['name']}第 {d['period']} 期（{d['date']}）開獎號碼 "
                         f"{fmt_nums(game, d['numbers'])}{special}，各獎項中獎注數與獎金。")


def build_game(game, draws):
    st = pick_stats(game, draws) if game["kind"] == "pick" else None
    build_game_home(game, draws, st)
    build_check(game)
    if st:
        build_pick_stats(game, draws, st)
    else:
        build_digit_stats(game, draws)
    build_history(game, draws)
    build_draws(game, draws)
    # 給對獎工具用的精簡資料：[期別, 日期, 號碼, 特別號/第二區, 各獎項每注獎金]
    slim = [[d["period"], d["date"], d["numbers"], d["special"],
             [p["amount"] for p in d["prizes"]]] for d in draws]
    (OUT / game["slug"] / "draws.json").write_text(
        json.dumps(slim, separators=(",", ":")), encoding="utf-8")


# ---------- 樂合彩 ----------

def combo_rules(game):
    parent = BY_SLUG[game["parent"]]
    rows = "".join(
        f'<tr><td>{name}</td><td>選 {k} 個號碼，全部在開出的 {game["drawn"]} 個號碼中</td>'
        f'<td class="r">{prize:,}</td><td class="r">1/{comb(game["pool"], k) / comb(game["drawn"], k):,.0f}</td></tr>'
        for k, name, prize in game["plays"])
    return f"""<div class="scroll"><table><thead><tr><th>玩法</th><th>中獎條件</th>
<th class="r">每注獎金（元）</th><th class="r">中獎機率</th></tr></thead><tbody>{rows}</tbody></table></div>
<p class="note">每注 {game['price']} 元，從 1～{game['pool']} 選號，用{parent['name']}開出的號碼對獎
（{'不含第二區' if parent['special'] == 'zone' else '不含特別號' if parent['special'] else '五個號碼'}）。
選幾個號碼就玩幾合，選的號碼必須全部開出才算中獎，例如三合只中 2 個不算中獎。
各玩法為固定獎金，但中獎注數過多、總獎金超過上限時會改為均分，促銷期間也可能加碼，實際以台灣彩券公告為準。</p>"""


def build_combo(game, draws):
    parent = BY_SLUG[game["parent"]]
    pslug = f"../{parent['slug']}/"
    plain = [{**d, "special": None} for d in draws]  # 樂合彩不看特別號／第二區
    latest = plain[0]
    recent_rows = "".join(
        f'<tr><td><a href="{pslug}draw/{d["period"]}.html">{d["period"]}</a></td>'
        f'<td>{d["date"]}</td><td>{balls(parent, d, small=True)}</td></tr>'
        for d in plain[1:11])
    body = f"""
<h1>{game['name']}最新開獎號碼</h1>
<p class="sub">第 {latest['period']} 期・{zh_date(latest['date'])}開獎・{game['schedule']}</p>
<div class="card">
  {balls(parent, latest)}
  <p class="meta">{game['name']}使用{parent['name']}同一期的開獎號碼。</p>
  <div class="row"><a class="btn primary" href="check.html">我要對獎 →</a>
  <a class="btn" href="{pslug}draw/{latest['period']}.html">{parent['name']}本期明細</a></div>
</div>
<div class="ad"></div>
<div class="card"><h2>{game['name']}玩法與獎金</h2>{combo_rules(game)}</div>
<div class="card">
  <h2>前 10 期開獎號碼</h2>
  <div class="scroll"><table><thead><tr><th>期別</th><th>日期</th><th>號碼</th></tr></thead>
  <tbody>{recent_rows}</tbody></table></div>
  <p><a href="history/">所有歷史開獎紀錄 →</a>　<a href="{pslug}stats.html">號碼出現次數統計 →</a></p>
</div>
"""
    page(f"{game['slug']}/index.html", f"{game['name']}開獎號碼", body, game=game, sub="home",
         description=f"{game['name']}第 {latest['period']} 期開獎號碼：{fmt_nums(parent, latest['numbers'])}。"
                     f"{game['name']}玩法、獎金、中獎機率與線上對獎。")

    cfg = escape(json.dumps({"kind": "combo", "pool": game["pool"], "price": game["price"],
                             "plays": [{"k": k, "name": n, "prize": p} for k, n, p in game["plays"]]},
                            ensure_ascii=False))
    ks = [k for k, _, _ in game["plays"]]
    body = f"""
<h1>{game['name']}對獎</h1>
<p class="sub">選 {ks[0]}～{ks[-1]} 個號碼（選幾個就是幾合），馬上知道有沒有中獎；也可以回測這組號碼歷年會中幾次。</p>
<div class="card" data-checker data-src="{pslug}draws.json" data-cfg="{cfg}">
  <p>已選 <b class="count">0</b> 個號碼（{'、'.join(f'{k} 個＝{n}' for k, n, _ in game['plays'])}）</p>
  <div class="picker main"></div>
  <div class="row">
    <button class="btn" data-act="random" type="button">電腦選號</button>
    <button class="btn" data-act="clear" type="button">清除</button>
  </div>
  <div class="row">
    <select aria-label="選擇期別"><option>資料載入中…</option></select>
    <button class="btn primary" data-act="check" type="button" disabled>對獎</button>
    <button class="btn" data-act="history" type="button" disabled>歷史回測</button>
  </div>
  <div class="result" aria-live="polite"></div>
</div>
<div class="ad"></div>
<div class="card"><h2>{game['name']}中獎規則</h2>{combo_rules(game)}</div>
"""
    page(f"{game['slug']}/check.html", f"{game['name']}對獎", body, game=game, sub="check",
         description=f"{game['name']}線上對獎：二合、三合、四合立即比對任一期開獎結果，並可回測歷年中獎紀錄。")

    years = sorted({d["date"][:4] for d in plain}, reverse=True)
    for y in years:
        pager = "".join(
            f'<a href="{x}.html"{" class=\"on\"" if x == y else ""}>{x}</a>' for x in years)
        rows = "".join(
            f'<tr><td><a href="../{pslug}draw/{d["period"]}.html">{d["period"]}</a></td>'
            f'<td>{zh_date(d["date"])}</td><td>{balls(parent, d, small=True)}</td></tr>'
            for d in plain if d["date"].startswith(y))
        body = f"""
<h1>{y} 年{game['name']}開獎紀錄</h1>
<p class="sub">{game['name']}的號碼就是{parent['name']}開出的號碼，點期別可以看該期完整明細。</p>
<div class="pager">{pager}</div>
<div class="card"><div class="scroll"><table>
<thead><tr><th>期別</th><th>開獎日期</th><th>號碼</th></tr></thead>
<tbody>{rows}</tbody></table></div></div>
"""
        page(f"{game['slug']}/history/{y}.html", f"{y} 年{game['name']}開獎紀錄", body,
             game=game, sub="history", description=f"{y} 年{game['name']}每期開獎號碼一覽。")
    redirect(f"{game['slug']}/history/index.html", f"{game['slug']}/history/{years[0]}.html")


# ---------- 賓果賓果 ----------

def load_bingo():
    """回傳由新到舊的 [{term, date, time, order, numbers, super, big, odd}]"""
    draws = []
    for path in sorted((ROOT / "data" / "bingo").glob("*.json")):
        for day, rows in json.loads(path.read_text(encoding="utf-8")).items():
            first = rows[0][0]
            for term, s in rows:
                order = [int(s[i:i + 2]) for i in range(0, 40, 2)]
                minutes = 7 * 60 + 5 + (term - first) * 5  # 每天 07:05 第一期，之後每 5 分鐘一期
                big = sum(n > 40 for n in order)
                odd = sum(n % 2 for n in order)
                draws.append({
                    "term": term, "date": day, "time": f"{minutes // 60:02d}:{minutes % 60:02d}",
                    "order": order, "numbers": sorted(order), "super": order[-1],
                    "big": "大" if big >= 13 else "小" if big <= 7 else "－",
                    "odd": "單" if odd >= 13 else "雙" if odd <= 7 else "－",
                })
    draws.sort(key=lambda d: d["term"], reverse=True)
    return draws


def bingo_balls(d, small=True):
    cls = "ball sm" if small else "ball"
    return '<div class="balls">' + "".join(
        f'<span class="{cls}{" sp" if n == d["super"] else ""}">{n:02d}</span>' for n in d["numbers"]) + "</div>"


def bingo_text(d):
    """表格裡用純文字，一天 203 期都畫成號碼球的話頁面太大"""
    return " ".join(f"<b>{n:02d}</b>" if n == d["super"] else f"{n:02d}" for n in d["numbers"])


def bingo_rows(draws):
    return "".join(
        f'<tr><td>{d["term"]}</td><td>{d["time"]}</td>'
        f'<td class="bingo-nums">{bingo_text(d)}</td><td class="r">{d["super"]:02d}</td>'
        f'<td>{d["big"]}</td><td>{d["odd"]}</td></tr>' for d in draws)


BINGO_HEAD = ('<thead><tr><th>期別</th><th>時間</th><th>開出號碼（紅色為超級獎號）</th>'
              '<th class="r">超級獎號</th><th>大小</th><th>單雙</th></tr></thead>')


def bingo_rules(game):
    rows = "".join(
        f'<tr><td>{s} 星</td><td>' + "、".join(
            f'中 {k}：{p:,}' if k else f'全沒中：{p:,}' for k, p in pays) + "</td></tr>"
        for s, pays in sorted(game["stars"].items()))
    return f"""<div class="scroll"><table><thead><tr><th>星數</th><th>中獎條件與每注獎金（元）</th></tr></thead>
<tbody>{rows}</tbody></table></div>
<p class="note">每注 {game['price']} 元，從 1～80 選 1～10 個號碼（選幾個就是幾星），每期開出 20 個號碼。
最後開出的號碼是「超級獎號」。猜大小：20 個號碼中 41～80 有 13 個以上為「大」，1～40 有 13 個以上為「小」；
猜單雙同理（13 個以上單號為「單」）。獎金以台灣彩券公告為準。</p>"""


def build_bingo(game, draws):
    slug = "bingo"
    latest = draws[0]
    days = sorted({d["date"] for d in draws}, reverse=True)
    by_day = {}
    for d in draws:
        by_day.setdefault(d["date"], []).append(d)

    body = f"""
<h1>賓果賓果最新開獎號碼</h1>
<p class="sub">第 {latest['term']} 期・{zh_date(latest['date'])} {latest['time']}・{game['schedule']}</p>
<div class="card">
  {bingo_balls(latest, small=False)}
  <p class="meta">超級獎號：{latest['super']:02d}　猜大小：{latest['big']}　猜單雙：{latest['odd']}
  開出順序：{' '.join(f'{n:02d}' for n in latest['order'])}</p>
  <div class="row"><a class="btn primary" href="check.html">我要對獎 →</a>
  <a class="btn" href="day/{latest['date']}.html">{latest['date']} 全部期數</a></div>
</div>
<p class="note">本站每天自動更新兩次（晚上 10:30、早上 8:30），最新幾期請以台灣彩券官網為準。</p>
<div class="ad"></div>
<div class="card"><h2>最近 20 期</h2>
  <div class="scroll"><table>{BINGO_HEAD}<tbody>{bingo_rows(draws[1:21])}</tbody></table></div>
  <p><a href="history/">依日期查詢所有開獎紀錄 →</a></p>
</div>
<div class="card"><h2>賓果賓果玩法與獎金</h2>{bingo_rules(game)}</div>
"""
    page(f"{slug}/index.html", "賓果賓果開獎號碼", body, game=game, sub="home",
         description=f"賓果賓果第 {latest['term']} 期開獎號碼、超級獎號 {latest['super']:02d}。"
                     "每天開獎紀錄、線上對獎、號碼統計。")

    # 每天一頁
    out_days = OUT / slug / "days"
    out_days.mkdir(parents=True, exist_ok=True)
    for i, day in enumerate(days):
        rows = by_day[day]
        newer = days[i - 1] if i > 0 else None
        older = days[i + 1] if i + 1 < len(days) else None
        nav = '<div class="prevnext">' + (
            f'<a href="{older}.html">← {older}</a>' if older else "<span></span>") + (
            f'<a href="{newer}.html">{newer} →</a>' if newer else "<span></span>") + "</div>"
        supers = Counter(d["super"] for d in rows).most_common(3)
        body = f"""
<h1>{zh_date(day)}賓果賓果開獎號碼</h1>
<p class="sub">共 {len(rows)} 期（第 {rows[-1]['term']}～{rows[0]['term']} 期），由新到舊排列。</p>
{nav}
<div class="card"><div class="scroll"><table>{BINGO_HEAD}<tbody>{bingo_rows(rows)}</tbody></table></div></div>
<p class="meta">當天開出次數最多的超級獎號：{'、'.join(f'{n:02d}（{c} 次）' for n, c in supers)}</p>
{nav}
<p><a href="../check.html">用這天的號碼對獎 →</a>　<a href="../history/{day[:4]}.html">{day[:4]} 年所有日期</a></p>
"""
        page(f"{slug}/day/{day}.html", f"{day} 賓果賓果開獎號碼", body, game=game, sub="history",
             description=f"{day} 賓果賓果全部 {len(rows)} 期開獎號碼、超級獎號、猜大小與單雙結果。")
        (out_days / f"{day}.json").write_text(json.dumps(
            [[d["term"], d["time"], d["order"]] for d in rows], separators=(",", ":")), encoding="utf-8")
    (OUT / slug / "days.json").write_text(json.dumps(days), encoding="utf-8")

    # 依年份列出日期
    years = sorted({d[:4] for d in days}, reverse=True)
    for y in years:
        pager = "".join(f'<a href="{x}.html"{" class=\"on\"" if x == y else ""}>{x}</a>' for x in years)
        months = {}
        for day in days:
            if day.startswith(y):
                months.setdefault(day[:7], []).append(day)
        blocks = "".join(
            f'<div class="card"><h2>{int(m[5:])} 月</h2><div class="pager">' +
            "".join(f'<a href="../day/{day}.html">{int(day[8:])} 日</a>' for day in sorted(ds)) +
            "</div></div>" for m, ds in months.items())
        body = f"""
<h1>{y} 年賓果賓果開獎紀錄</h1>
<p class="sub">選擇日期，查看當天每一期的開獎號碼。</p>
<div class="pager">{pager}</div>
{blocks}
"""
        page(f"{slug}/history/{y}.html", f"{y} 年賓果賓果開獎紀錄", body, game=game, sub="history",
             description=f"{y} 年每天的賓果賓果開獎號碼查詢。")
    redirect(f"{slug}/history/index.html", f"{slug}/history/{years[0]}.html")

    # 統計
    recent_days = days[:30]
    recent = [d for d in draws if d["date"] in set(recent_days)]
    all_c = Counter(n for d in draws for n in d["numbers"])
    rec_c = Counter(n for d in recent for n in d["numbers"])
    sup_c = Counter(d["super"] for d in draws)
    gap = {}
    for n in range(1, 81):
        gap[n] = next((i for i, d in enumerate(draws) if n in d["numbers"]), len(draws))
    max_all, max_rec = max(all_c.values()), max(rec_c.values())
    rows = "".join(
        f'<tr><td data-v="{n}"><span class="ball sm">{n:02d}</span></td>'
        f'<td class="r" data-v="{all_c[n]}">{all_c[n]:,}</td>'
        f'<td class="barcol" data-v="{all_c[n]}"><div class="bar" style="width:{all_c[n] / max_all * 100:.0f}%"></div></td>'
        f'<td class="r" data-v="{rec_c[n]}">{rec_c[n]:,}</td>'
        f'<td class="barcol" data-v="{rec_c[n]}"><div class="bar" style="width:{rec_c[n] / max_rec * 100:.0f}%"></div></td>'
        f'<td class="r" data-v="{sup_c[n]}">{sup_c[n]:,}</td>'
        f'<td class="r" data-v="{gap[n]}">{gap[n]}</td></tr>' for n in range(1, 81))
    total = len(draws)

    def dist(key, labels):
        c = Counter(d[key] for d in draws)
        return "".join(f'<tr><td>{l}</td><td class="r">{c[l]:,}</td><td class="r">{c[l] / total:.1%}</td></tr>'
                       for l in labels)
    body = f"""
<h1>賓果賓果號碼統計</h1>
<p class="sub">統計 {draws[-1]['date']} 至 {latest['date']} 共 {total:,} 期；「近 30 天」為 {recent_days[-1]} 起 {len(recent):,} 期。點表頭可以排序。</p>
<div class="card">
  <div class="scroll"><table class="sortable">
  <thead><tr>
    <th data-sort="asc">號碼</th>
    <th class="r" data-sort="desc">累計次數</th><th class="barcol"></th>
    <th class="r" data-sort="desc">近 30 天</th><th class="barcol"></th>
    <th class="r" data-sort="desc">當超級獎號</th>
    <th class="r" data-sort="desc">目前遺漏</th>
  </tr></thead>
  <tbody>{rows}</tbody></table></div>
  <p class="note">每期開出 20 個號碼，每個號碼開出機率都是 20/80 = 25%，{total:,} 期的期望次數約 {total / 4:,.0f} 次；
  當超級獎號的機率是 1/80，期望約 {total / 80:,.0f} 次。「目前遺漏」＝最近連續幾期沒開出。</p>
</div>
<div class="ad"></div>
<div class="grid2">
  <div class="card"><h2>猜大小結果</h2>
    <table><thead><tr><th>結果</th><th class="r">期數</th><th class="r">比例</th></tr></thead>
    <tbody>{dist('big', ['大', '小', '－'])}</tbody></table></div>
  <div class="card"><h2>猜單雙結果</h2>
    <table><thead><tr><th>結果</th><th class="r">期數</th><th class="r">比例</th></tr></thead>
    <tbody>{dist('odd', ['單', '雙', '－'])}</tbody></table></div>
</div>
<p class="note">「－」代表兩邊都沒有達到 13 個，該期大小（或單雙）無人中獎。統計結果接近理論值，說明開獎是隨機的。</p>
"""
    page(f"{slug}/stats.html", "賓果賓果號碼統計", body, game=game, sub="stats",
         description="賓果賓果 1～80 每個號碼的歷史出現次數、近 30 天熱門號碼、超級獎號次數與猜大小單雙統計。")

    cfg = escape(json.dumps({"price": game["price"],
                             "stars": {s: pays for s, pays in game["stars"].items()}}))
    body = f"""
<h1>賓果賓果對獎</h1>
<p class="sub">選 1～10 個號碼（選幾個就是幾星），再選日期，一次比對當天所有期數。</p>
<div class="card" data-bingo data-cfg="{cfg}">
  <p>已選 <b class="count">0</b> / 10 個號碼</p>
  <div class="picker main bingo"></div>
  <div class="row">
    <button class="btn" data-act="random" type="button">電腦選 10 個</button>
    <button class="btn" data-act="clear" type="button">清除</button>
  </div>
  <div class="row">
    <select aria-label="選擇日期"><option>資料載入中…</option></select>
    <button class="btn primary" data-act="check" type="button" disabled>對獎</button>
  </div>
  <div class="result" aria-live="polite"></div>
</div>
<div class="ad"></div>
<div class="card"><h2>賓果賓果中獎規則</h2>{bingo_rules(game)}</div>
"""
    page(f"{slug}/check.html", "賓果賓果對獎", body, game=game, sub="check",
         description="賓果賓果線上對獎：選 1～10 星號碼，一次比對某天所有期數，算出中獎期數與總獎金。")


# ---------- 全站頁面 ----------

def build_home(all_draws):
    cards = []
    for g in GAMES:
        draws = all_draws.get(g.get("parent", g["slug"]))
        if not draws:
            continue
        d = draws[0]
        tag = "" if g["active"] else '<span class="tag">已停售</span>'
        if g["kind"] == "bingo":
            when = f"第 {d['term']} 期・{zh_date(d['date'])} {d['time']}"
            nums = bingo_balls(d)
        elif g["kind"] == "combo":
            when = f"第 {d['period']} 期・{zh_date(d['date'])}"
            nums = balls(BY_SLUG[g["parent"]], {**d, "special": None}, small=True)
        else:
            when = f"第 {d['period']} 期・{zh_date(d['date'])}"
            nums = balls(g, d, small=True)
        stats = "" if g["kind"] == "combo" else f'<a class="btn" href="{g["slug"]}/stats.html">統計</a>'
        cards.append(f"""<div class="card">
  <h2><a href="{g['slug']}/">{g['name']}</a>{tag}</h2>
  <p class="meta">{when}</p>
  {nums}
  <p class="meta">{g['schedule']}</p>
  <div class="row" style="margin-top:0">
    <a class="btn" href="{g['slug']}/check.html">對獎</a>
    {stats}
    <a class="btn" href="{g['slug']}/history/">歷史</a>
  </div>
</div>""")
    body = f"""
<h1>台灣彩券開獎號碼查詢</h1>
<p class="sub">大樂透、威力彩、今彩539、賓果賓果、3星彩、4星彩、38／39／49 樂合彩最新開獎結果，每期開獎後自動更新。</p>
<div class="games">{''.join(cards)}</div>
<div class="ad"></div>
<div class="card">
  <h2>本站提供</h2>
  <p>各玩法最新開獎號碼、線上對獎與歷史回測（看看一組號碼從過去買到現在會中幾次）、每期獎金明細、
  歷年開獎紀錄，以及號碼出現次數、遺漏期數等統計。</p>
  <p class="note">統計只是整理過去的結果，彩券每期都是獨立隨機開獎，任何方法都無法預測號碼。</p>
</div>
"""
    page("index.html", "", body)


def build_about():
    body = f"""
<h1>關於本站</h1>
<div class="card">
  <p>{escape(CFG['name'])}整理台灣彩券公開的開獎資料，提供開獎查詢、對獎與統計功能。
  資料於每期開獎後自動更新，若與官方公告不同，以台灣彩券公告為準。</p>
  <p>本站與台灣彩券股份有限公司無任何關係。所有統計僅供參考與娛樂，彩券開獎為隨機結果，
  本站不提供任何「預測」或「明牌」，也不保證任何中獎機率。</p>
  <h2>隱私權政策</h2>
  <p>本站不要求註冊，對獎時輸入的號碼只在你的瀏覽器中計算，不會傳回伺服器。</p>
  <p>本站可能使用 Google Analytics 分析流量，並使用 Google AdSense 等第三方廣告服務。
  這些服務可能使用 Cookie 依據你過去造訪本站或其他網站的紀錄顯示廣告。
  你可以到 <a href="https://adssettings.google.com/" rel="nofollow">Google 廣告設定</a> 停用個人化廣告。</p>
</div>
"""
    page("about.html", "關於本站", body, description="關於本站與隱私權政策。")


def build_legacy_redirects(lotto649):
    """第一版網站只有大樂透、放在根目錄，舊網址轉到 lotto649/"""
    redirect("check.html", "lotto649/check.html")
    redirect("stats.html", "lotto649/stats.html")
    redirect("history/index.html", "lotto649/history/")
    for y in {d["date"][:4] for d in lotto649}:
        redirect(f"history/{y}.html", f"lotto649/history/{y}.html")
    for d in lotto649:
        redirect(f"draw/{d['period']}.html", f"lotto649/draw/{d['period']}.html")


def build_extras(lastmod):
    base = CFG["base_url"].rstrip("/")
    sitemap = "".join(f"<url><loc>{base}/{escape(u)}</loc><lastmod>{lastmod}</lastmod></url>\n"
                      for u in pages)
    (OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{sitemap}</urlset>\n',
        encoding="utf-8")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n",
                                    encoding="utf-8")
    client = CFG.get("adsense_client", "")
    if client.startswith("ca-pub-"):
        (OUT / "ads.txt").write_text(
            f"google.com, {client.removeprefix('ca-')}, DIRECT, f08c47fec0942fa0\n", encoding="utf-8")
    (OUT / ".nojekyll").write_text("")


def main():
    all_draws = {}
    for g in DRAW_GAMES:
        path = ROOT / "data" / f"{g['slug']}.json"
        if path.exists():
            draws = json.loads(path.read_text(encoding="utf-8"))
            draws.sort(key=lambda d: d["period"], reverse=True)
            if draws:
                all_draws[g["slug"]] = draws

    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(ROOT / "static", OUT / "static")

    bingo = load_bingo()
    if bingo:
        all_draws["bingo"] = bingo

    build_home(all_draws)
    for g in GAMES:
        draws = all_draws.get(g.get("parent", g["slug"]))
        if not draws:
            continue
        if g["kind"] == "bingo":
            build_bingo(g, draws)
        elif g["kind"] == "combo":
            build_combo(g, draws)
        else:
            build_game(g, draws)
        print(f"{g['name']}：{len(draws)} 期")
    build_about()
    if "lotto649" in all_draws:
        build_legacy_redirects(all_draws["lotto649"])
    build_extras(max(d[0]["date"] for d in all_draws.values()))
    print(f"網站已產生在 {OUT}（{len(pages)} 個頁面）")


if __name__ == "__main__":
    main()
