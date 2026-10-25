# LottoTW：台灣彩券開獎查詢・對獎・統計（lottotw.com）

自動更新的台灣彩券開獎靜態網站，靠搜尋流量 + 廣告賺錢。只用 Python 標準函式庫，免費部署在 GitHub Pages。

## 功能

支援的玩法（設定在 `games.py`）：大樂透、威力彩、今彩539、3星彩、4星彩，以及已停售的雙贏彩（歷史資料）。

| 網址 | 內容 |
|---|---|
| `/` | 各玩法最新開獎總覽 |
| `/<玩法>/` | 最新開獎、熱門／遺漏號碼、前 10 期 |
| `/<玩法>/check.html` | 線上對獎、歷史回測 |
| `/<玩法>/stats.html` | 號碼出現次數、遺漏期數等統計 |
| `/<玩法>/history/<年>.html` | 每年開獎紀錄 |
| `/<玩法>/draw/<期別>.html` | 每期號碼與各獎項獎金（長尾流量來源） |
| `about.html` | 免責聲明、隱私權政策（申請 AdSense 需要） |

玩法代號：`lotto649` 大樂透、`superlotto638` 威力彩、`daily539` 今彩539、`3d` 3星彩、`4d` 4星彩、`lotto1224` 雙贏彩。
第一版的舊網址（`/check.html`、`/draw/...`）會自動轉到 `/lotto649/`。

另外會產生 `sitemap.xml`、`robots.txt`；設定 AdSense 後也會產生 `ads.txt`。

## 本機使用

```bash
python scraper.py        # 抓全部玩法（第一次約 10 分鐘，之後只補新的期數）
python scraper.py 3d     # 只更新指定玩法
python build.py          # 產生網站到 dist/
python -m http.server 8649 -d dist   # 開 http://localhost:8649 預覽
```

## 部署到 GitHub Pages（免費）

1. 在 GitHub 建一個新的 repo（例如 `lotto649-stats`），把這個資料夾推上去。
2. repo 的 **Settings → Pages → Source** 選 **GitHub Actions**。
3. 修改 `site.json` 的 `base_url` 為 `https://<你的帳號>.github.io/lotto649-stats`，推上去。
4. 推上去後 Actions 會自動建置。之後每週一至六開獎後會自動抓資料並重新部署，不用管它。

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

- 38／39／49 樂合彩（沿用威力彩、今彩539、大樂透的開獎號碼）
- 賓果賓果（每 5 分鐘一期，需要不同的頁面設計）
- 開獎後自動推播到 LINE／Telegram 頻道，把讀者帶回網站
- 頭獎累積金額、各期銷售趨勢圖

## 注意

- 網站定位是「查詢與統計工具」，**不要宣稱能預測號碼**。這樣不誠實，也可能違反廣告政策。
- 資料以台灣彩券官方公告為準；本站與台灣彩券無關。
