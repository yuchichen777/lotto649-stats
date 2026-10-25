"""把 data/lotto649.json 產生成靜態網站，輸出到 dist/。

用法：
    python build.py
然後用瀏覽器開 dist/index.html，或執行 python -m http.server -d dist 預覽。
只用 Python 標準函式庫。
"""
import json
import shutil
from collections import Counter
from datetime import date
from html import escape
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / "dist"
CFG = json.loads((ROOT / "site.json").read_text(encoding="utf-8"))
WEEKDAYS = "一二三四五六日"
RECENT = 100  # 「近期」統計用的期數


def money(n):
    return f"{n:,}" if n else "—"


def zh_date(s):
    d = date.fromisoformat(s)
    return f"{d.year}/{d.month:02d}/{d.day:02d}（{WEEKDAYS[d.weekday()]}）"


def balls(draw, small=False):
    cls = "ball sm" if small else "ball"
    main = "".join(f'<span class="{cls}">{n:02d}</span>' for n in draw["numbers"])
    return (f'<div class="balls">{main}<span class="plus">+</span>'
            f'<span class="{cls} sp">{draw["special"]:02d}</span></div>')


def page(path, title, body, *, nav="", description=None):
    """寫出一個頁面。path 是相對 dist/ 的路徑，用來算出回到根目錄的 ../"""
    depth = path.count("/")
    root = "../" * depth
    full_title = f"{title}｜{CFG['short_name']}" if title else CFG["name"]
    desc = escape(description or CFG["description"])
    canonical = f"{CFG['base_url'].rstrip('/')}/{'' if path == 'index.html' else path}"

    head_extra = ""
    if CFG.get("adsense_client"):
        head_extra += (
            '<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js'
            f'?client={escape(CFG["adsense_client"])}" crossorigin="anonymous"></script>\n')
    if CFG.get("ga_measurement_id"):
        gid = escape(CFG["ga_measurement_id"])
        head_extra += (
            f'<script async src="https://www.googletagmanager.com/gtag/js?id={gid}"></script>\n'
            "<script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments)}"
            f"gtag('js',new Date());gtag('config','{gid}');</script>\n")

    def link(href, label, key):
        on = ' class="on"' if key == nav else ""
        return f'<a href="{root}{href}"{on}>{label}</a>'

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
{head_extra}</head>
<body>
<header class="site"><div class="wrap">
  <a class="logo" href="{root}index.html">🎱 {escape(CFG['short_name'])}</a>
  <nav>
    {link('index.html', '最新開獎', 'home')}
    {link('check.html', '對獎', 'check')}
    {link('stats.html', '號碼統計', 'stats')}
    {link('history/index.html', '歷史紀錄', 'history')}
  </nav>
</div></header>
<main><div class="wrap">
{body}
</div></main>
<footer><div class="wrap">
  <p>資料來源：台灣彩券官方網站，每期開獎後自動更新。開獎結果以台灣彩券公告為準。</p>
  <p>本站統計僅供參考與娛樂，樂透為隨機開獎，過去號碼無法預測未來結果。請量力而為，未滿 18 歲不得購買彩券。</p>
  <p><a href="{root}about.html">關於本站・隱私權政策</a></p>
</div></footer>
<script src="{root}static/app.js"></script>
</body>
</html>
"""
    target = OUT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html, encoding="utf-8")


def prize_table(draw):
    rows = "".join(
        f'<tr><td>{p["name"]}</td><td class="r">{p["winners"]:,}</td>'
        f'<td class="r">{money(p["amount"]) if p["winners"] else "槓龜"}</td></tr>'
        for p in draw["prizes"])
    return ('<div class="scroll"><table><thead><tr><th>獎項</th><th class="r">中獎注數</th>'
            f'<th class="r">每注獎金（元）</th></tr></thead><tbody>{rows}</tbody></table></div>')


def compute_stats(draws):
    """draws 由新到舊排序"""
    total = len(draws)
    all_main = Counter(n for d in draws for n in d["numbers"])
    recent_main = Counter(n for d in draws[:RECENT] for n in d["numbers"])
    special = Counter(d["special"] for d in draws)

    gap_now, gap_max = {}, {}
    for n in range(1, 50):
        # 由舊到新走一遍，計算每個號碼的「遺漏期數」
        run, longest = 0, 0
        for d in reversed(draws):
            if n in d["numbers"]:
                longest = max(longest, run)
                run = 0
            else:
                run += 1
        gap_now[n] = run
        gap_max[n] = max(longest, run)

    odd_even = Counter(sum(n % 2 for n in d["numbers"]) for d in draws)
    sums = [sum(d["numbers"]) for d in draws]
    consecutive = sum(
        any(b - a == 1 for a, b in zip(d["numbers"], d["numbers"][1:])) for d in draws)

    return {
        "total": total,
        "all": all_main, "recent": recent_main, "special": special,
        "gap_now": gap_now, "gap_max": gap_max,
        "odd_even": odd_even,
        "sum_avg": sum(sums) / total,
        "consecutive": consecutive,
    }


def build_home(draws, st):
    latest = draws[0]
    hot = sorted(range(1, 50), key=lambda n: (-st["recent"][n], n))[:6]
    cold = sorted(range(1, 50), key=lambda n: (-st["gap_now"][n], n))[:6]
    recent_rows = "".join(
        f'<tr><td><a href="draw/{d["period"]}.html">{d["period"]}</a></td>'
        f'<td>{d["date"]}</td><td>{balls(d, small=True)}</td></tr>'
        for d in draws[1:11])

    def mini(nums):
        return '<div class="balls">' + "".join(
            f'<span class="ball sm">{n:02d}</span>' for n in nums) + "</div>"

    body = f"""
<h1>大樂透最新開獎號碼</h1>
<p class="sub">第 {latest['period']} 期・{zh_date(latest['date'])}開獎</p>

<div class="card">
  {balls(latest)}
  <p class="meta">開出順序：{' '.join(f'{n:02d}' for n in latest['order'])}　特別號：{latest['special']:02d}
  本期銷售：{money(latest['sales'])} 元</p>
  <div class="row"><a class="btn primary" href="check.html">我要對獎 →</a>
  <a class="btn" href="draw/{latest['period']}.html">本期獎金明細</a></div>
</div>

<div class="ad"></div>

<div class="grid2">
  <div class="card">
    <h2>近 {RECENT} 期熱門號碼</h2>
    {mini(hot)}
    <p class="meta">近 {RECENT} 期出現次數最多的號碼</p>
  </div>
  <div class="card">
    <h2>目前遺漏最久的號碼</h2>
    {mini(cold)}
    <p class="meta">最多已連續 {st['gap_now'][cold[0]]} 期沒開出</p>
  </div>
</div>
<p class="note">熱門／冷門號碼只是歷史統計，每期開獎都是獨立事件，不代表下期比較容易開出。<a href="stats.html">看完整統計 →</a></p>

<div class="card">
  <h2>前 10 期開獎號碼</h2>
  <div class="scroll"><table><thead><tr><th>期別</th><th>日期</th><th>號碼</th></tr></thead>
  <tbody>{recent_rows}</tbody></table></div>
  <p><a href="history/index.html">所有歷史開獎紀錄 →</a></p>
</div>
"""
    page("index.html", "", body, nav="home",
         description=f"大樂透第 {latest['period']} 期開獎號碼："
                     f"{' '.join(f'{n:02d}' for n in latest['numbers'])}，"
                     f"特別號 {latest['special']:02d}。{CFG['description']}")


def build_check(draws):
    body = f"""
<h1>大樂透對獎</h1>
<p class="sub">選 6 個號碼，馬上知道有沒有中獎；也可以看這組號碼如果從 2007 年買到現在會中幾次。</p>
<div class="card" data-checker data-src="static/draws.json">
  <p>已選 <b class="count">0</b> / 6 個號碼</p>
  <div class="picker"></div>
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
<div class="card">
  <h2>大樂透中獎規則</h2>
  <div class="scroll"><table>
  <thead><tr><th>獎項</th><th>中獎條件</th></tr></thead>
  <tbody>
    <tr><td>頭獎</td><td>6 個號碼全中</td></tr>
    <tr><td>貳獎</td><td>中 5 個號碼 + 特別號</td></tr>
    <tr><td>參獎</td><td>中 5 個號碼</td></tr>
    <tr><td>肆獎</td><td>中 4 個號碼 + 特別號</td></tr>
    <tr><td>伍獎</td><td>中 4 個號碼</td></tr>
    <tr><td>陸獎</td><td>中 3 個號碼 + 特別號</td></tr>
    <tr><td>柒獎</td><td>中 2 個號碼 + 特別號</td></tr>
    <tr><td>普獎</td><td>中 3 個號碼</td></tr>
  </tbody></table></div>
  <p class="note">每注 50 元。實際兌獎以台灣彩券公告為準，高額獎金需扣稅。</p>
</div>
"""
    page("check.html", "對獎", body, nav="check",
         description="大樂透線上對獎：選號後立即比對最新或任一期開獎號碼，並可回測歷年中獎紀錄。")


def build_stats(draws, st):
    max_all = max(st["all"].values())
    max_recent = max(st["recent"].values()) or 1
    hot_cut = sorted(st["recent"].values(), reverse=True)[5]
    rows = []
    for n in range(1, 50):
        a, r = st["all"][n], st["recent"][n]
        hot = " hot" if r >= hot_cut else ""
        rows.append(
            f'<tr><td data-v="{n}"><span class="ball sm">{n:02d}</span></td>'
            f'<td class="r" data-v="{a}">{a}</td>'
            f'<td class="barcol" data-v="{a}"><div class="bar" style="width:{a / max_all * 100:.0f}%"></div></td>'
            f'<td class="r" data-v="{r}">{r}</td>'
            f'<td class="barcol" data-v="{r}"><div class="bar{hot}" style="width:{r / max_recent * 100:.0f}%"></div></td>'
            f'<td class="r" data-v="{st["gap_now"][n]}">{st["gap_now"][n]}</td>'
            f'<td class="r" data-v="{st["gap_max"][n]}">{st["gap_max"][n]}</td>'
            f'<td class="r" data-v="{st["special"][n]}">{st["special"][n]}</td></tr>')

    total = st["total"]
    oe_rows = "".join(
        f'<tr><td>{odd} 單 {6 - odd} 雙</td><td class="r">{st["odd_even"][odd]:,}</td>'
        f'<td class="r">{st["odd_even"][odd] / total:.1%}</td></tr>'
        for odd in range(7))

    body = f"""
<h1>大樂透號碼統計</h1>
<p class="sub">統計 {draws[-1]['date']} 至 {draws[0]['date']} 共 {total:,} 期開獎資料。點表頭可以排序。</p>
<div class="card">
  <div class="scroll"><table class="sortable">
  <thead><tr>
    <th data-sort="asc">號碼</th>
    <th class="r" data-sort="desc">累計次數</th><th class="barcol"></th>
    <th class="r" data-sort="desc">近 {RECENT} 期</th><th class="barcol"></th>
    <th class="r" data-sort="desc">目前遺漏</th>
    <th class="r" data-sort="desc">最長遺漏</th>
    <th class="r" data-sort="desc">特別號次數</th>
  </tr></thead>
  <tbody>{''.join(rows)}</tbody></table></div>
  <p class="note">「遺漏」＝連續幾期沒有開出（不含特別號）。理論上每個號碼每期開出機率都是 6/49 ≈ 12.2%，
  {total:,} 期的期望次數約 {total * 6 / 49:,.0f} 次。</p>
</div>
<div class="ad"></div>
<div class="grid2">
  <div class="card">
    <h2>單雙號分布</h2>
    <table><thead><tr><th>組合</th><th class="r">期數</th><th class="r">比例</th></tr></thead>
    <tbody>{oe_rows}</tbody></table>
  </div>
  <div class="card">
    <h2>其他統計</h2>
    <table><tbody>
      <tr><td>6 個號碼總和平均</td><td class="r">{st['sum_avg']:.1f}</td></tr>
      <tr><td>理論平均</td><td class="r">150.0</td></tr>
      <tr><td>有連號的期數</td><td class="r">{st['consecutive']:,}（{st['consecutive'] / total:.1%}）</td></tr>
      <tr><td>頭獎槓龜期數</td><td class="r">{sum(1 for d in draws if d['prizes'][0]['winners'] == 0):,}</td></tr>
    </tbody></table>
  </div>
</div>
<p class="note">統計結果接近理論值，正好說明開獎是隨機的：歷史資料無法提高中獎機率。</p>
"""
    page("stats.html", "號碼出現次數統計", body, nav="stats",
         description=f"大樂透 1～49 每個號碼的歷史出現次數、近 {RECENT} 期熱門號碼、遺漏期數與特別號統計。")


def build_history(draws):
    years = sorted({d["date"][:4] for d in draws}, reverse=True)
    for y in years:
        pager = "".join(
            f'<a href="{x}.html"{" class=\"on\"" if x == y else ""}>{x}</a>' for x in years)
        rows = "".join(
            f'<tr><td><a href="../draw/{d["period"]}.html">{d["period"]}</a></td>'
            f'<td>{zh_date(d["date"])}</td><td>{balls(d, small=True)}</td>'
            f'<td class="r">{money(d["prizes"][0]["amount"]) if d["prizes"][0]["winners"] else "槓龜"}</td></tr>'
            for d in draws if d["date"].startswith(y))
        body = f"""
<h1>{y} 年大樂透開獎紀錄</h1>
<p class="sub">點期別可以看該期完整獎金明細。</p>
<div class="pager">{pager}</div>
<div class="card"><div class="scroll"><table>
<thead><tr><th>期別</th><th>開獎日期</th><th>號碼</th><th class="r">頭獎獎金</th></tr></thead>
<tbody>{rows}</tbody></table></div></div>
"""
        page(f"history/{y}.html", f"{y} 年開獎紀錄", body, nav="history",
             description=f"{y} 年大樂透每期開獎號碼、特別號與頭獎獎金一覽。")

    # history/index.html 直接顯示最新年份
    shutil.copy(OUT / f"history/{years[0]}.html", OUT / "history/index.html")
    return years


def build_draws(draws):
    for i, d in enumerate(draws):
        newer = draws[i - 1] if i > 0 else None
        older = draws[i + 1] if i + 1 < len(draws) else None
        nav = '<div class="prevnext">' + (
            f'<a href="{older["period"]}.html">← 第 {older["period"]} 期</a>' if older else "<span></span>") + (
            f'<a href="{newer["period"]}.html">第 {newer["period"]} 期 →</a>' if newer else "<span></span>") + "</div>"
        nums = " ".join(f"{n:02d}" for n in d["numbers"])
        body = f"""
<h1>大樂透第 {d['period']} 期開獎號碼</h1>
<p class="sub">{zh_date(d['date'])}開獎</p>
<div class="card">
  {balls(d)}
  <p class="meta">開出順序：{' '.join(f'{n:02d}' for n in d['order'])}　特別號：{d['special']:02d}
  銷售金額：{money(d['sales'])} 元</p>
</div>
<div class="ad"></div>
<div class="card"><h2>各獎項中獎情形</h2>{prize_table(d)}</div>
{nav}
<p><a href="../check.html">用這期對獎 →</a>　<a href="../history/{d['date'][:4]}.html">{d['date'][:4]} 年所有開獎紀錄</a></p>
"""
        page(f"draw/{d['period']}.html", f"第 {d['period']} 期開獎號碼", body, nav="history",
             description=f"大樂透第 {d['period']} 期（{d['date']}）開獎號碼 {nums}，"
                         f"特別號 {d['special']:02d}，各獎項中獎注數與獎金。")


def build_about():
    body = f"""
<h1>關於本站</h1>
<div class="card">
  <p>{escape(CFG['name'])}整理台灣彩券公開的大樂透開獎資料，提供開獎查詢、對獎與統計功能。
  資料於每期開獎後自動更新，若與官方公告不同，以台灣彩券公告為準。</p>
  <p>本站與台灣彩券股份有限公司無任何關係。所有統計僅供參考與娛樂，樂透開獎為隨機結果，
  本站不提供任何「預測」或「明牌」，也不保證任何中獎機率。</p>
  <h2>隱私權政策</h2>
  <p>本站不要求註冊，對獎時選的號碼只在你的瀏覽器中計算，不會傳回伺服器。</p>
  <p>本站可能使用 Google Analytics 分析流量，並使用 Google AdSense 等第三方廣告服務。
  這些服務可能使用 Cookie 依據你過去造訪本站或其他網站的紀錄顯示廣告。
  你可以到 <a href="https://adssettings.google.com/" rel="nofollow">Google 廣告設定</a> 停用個人化廣告。</p>
</div>
"""
    page("about.html", "關於本站", body, description="關於本站與隱私權政策。")


def build_extras(draws, years):
    base = CFG["base_url"].rstrip("/")
    urls = ["", "check.html", "stats.html", "about.html", "history/index.html"]
    urls += [f"history/{y}.html" for y in years]
    urls += [f"draw/{d['period']}.html" for d in draws]
    lastmod = draws[0]["date"]
    sitemap = "".join(f"<url><loc>{base}/{u}</loc><lastmod>{lastmod}</lastmod></url>\n" for u in urls)
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

    # 給對獎工具用的精簡資料：[期別, 日期, [6 號碼], 特別號, [8 個獎項每注獎金]]
    slim = [[d["period"], d["date"], d["numbers"], d["special"],
             [p["amount"] for p in d["prizes"]]] for d in draws]
    (OUT / "static/draws.json").write_text(
        json.dumps(slim, separators=(",", ":")), encoding="utf-8")


def main():
    draws = json.loads((ROOT / "data/lotto649.json").read_text(encoding="utf-8"))
    draws.sort(key=lambda d: d["period"], reverse=True)
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(ROOT / "static", OUT / "static")

    st = compute_stats(draws)
    build_home(draws, st)
    build_check(draws)
    build_stats(draws, st)
    years = build_history(draws)
    build_draws(draws)
    build_about()
    build_extras(draws, years)
    print(f"網站已產生在 {OUT}（{len(draws)} 期，{len(list(OUT.rglob('*.html')))} 個頁面）")


if __name__ == "__main__":
    main()
