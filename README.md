# 大樂透開獎查詢・統計站

自動更新的大樂透靜態網站，靠搜尋流量 + 廣告賺錢。只用 Python 標準函式庫，免費部署在 GitHub Pages。

## 功能

| 頁面 | 內容 | 目標搜尋字 |
|---|---|---|
| `index.html` | 最新開獎、熱門／遺漏號碼、前 10 期 | 大樂透開獎、大樂透號碼 |
| `check.html` | 點選號碼對獎、歷史回測（從 2007 年買到現在會中幾次） | 大樂透對獎 |
| `stats.html` | 1～49 出現次數、近 100 期、遺漏期數、特別號、單雙分布 | 大樂透統計、冷熱號 |
| `history/<年>.html` | 每年開獎紀錄 | 2025 大樂透開獎紀錄 |
| `draw/<期別>.html` | 每期號碼與各獎項獎金（約 2,000 頁，長尾流量來源） | 大樂透 115000099 |
| `about.html` | 免責聲明、隱私權政策（申請 AdSense 需要） | |

另外會產生 `sitemap.xml`、`robots.txt`；設定 AdSense 後也會產生 `ads.txt`。

## 本機使用

```bash
python scraper.py        # 抓資料（第一次約 2 分鐘，之後只補新的期數）
python build.py          # 產生網站到 dist/
python -m http.server 8649 -d dist   # 開 http://localhost:8649 預覽
```

## 部署到 GitHub Pages（免費）

1. 在 GitHub 建一個新的 repo（例如 `lotto649-stats`），把這個資料夾推上去。
2. repo 的 **Settings → Pages → Source** 選 **GitHub Actions**。
3. 修改 `site.json` 的 `base_url` 為 `https://<你的帳號>.github.io/lotto649-stats`，推上去。
4. 推上去後 Actions 會自動建置。之後每週二、五開獎後會自動抓資料並重新部署，不用管它。

> GitHub Actions 的機器在國外。如果台灣彩券 API 擋掉國外 IP，scraper 會失敗。
> 這時可以改成在自己電腦用「工作排程器」定時跑 `python scraper.py`，再 `git push`。

## 開始賺錢的步驟

1. **買網域（強烈建議）**：約 NT$300～400／年。自訂網域比 github.io 更容易通過 AdSense，SEO 也比較好。
   在 Pages 設定填 Custom domain，並把 `site.json` 的 `base_url` 改成新網域。
2. **Google Search Console**：驗證網站，提交 `sitemap.xml`，讓 Google 開始收錄。
3. **Google Analytics**（選用）：把評估 ID（`G-XXXX`）填進 `site.json` 的 `ga_measurement_id`。
4. **申請 AdSense**：網站上線並有一些流量後（通常要幾週）申請。通過後把發布商 ID（`ca-pub-XXXX`）
   填進 `site.json` 的 `adsense_client`，網站會自動加上廣告程式碼和 `ads.txt`。
   之後在 AdSense 後台開「自動廣告」即可；頁面裡的 `<div class="ad">` 是保留給手動廣告版位的位置。

## 之後可以加的東西

- 威力彩、今彩 539（API 結構類似，流量更大）
- 開獎後自動推播到 LINE／Telegram 頻道，把讀者帶回網站
- 頭獎累積金額、各期銷售趨勢圖

## 注意

- 網站定位是「查詢與統計工具」，**不要宣稱能預測號碼**。這樣不誠實，也可能違反廣告政策。
- 資料以台灣彩券官方公告為準；本站與台灣彩券無關。
