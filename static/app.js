// 對獎工具 + 表格排序，不依賴任何套件
// 對獎設定由 build.py 寫在 data-cfg 裡；開獎資料格式：[期別, 日期, 號碼, 特別號/第二區, 各獎項每注獎金]
(function () {
  function fmt(n) { return n.toLocaleString("zh-TW"); }
  function pad(n) { return n < 10 ? "0" + n : "" + n; }

  function ballsHtml(cfg, d, hitMain, hitSpecial) {
    if (cfg.kind === "digits") {
      return d[2].map(function (n, i) {
        return '<span class="ball sm digit' + (hitMain[i] ? " hit" : "") + '">' + n + "</span>";
      }).join("");
    }
    var h = d[2].map(function (n) {
      return '<span class="ball sm' + (hitMain.indexOf(n) >= 0 ? " hit" : "") + '">' + pad(n) + "</span>";
    }).join("");
    if (d[3] !== null && cfg.kind !== "combo") {
      h += '<span class="plus">+</span><span class="ball sm sp' + (hitSpecial ? " hit" : "") + '">' +
        pad(d[3]) + "</span>";
    }
    return h;
  }

  function makePicker(el, from, to, max, onChange) {
    var picked = [];
    for (var n = from; n <= to; n++) {
      var b = document.createElement("button");
      b.type = "button";
      b.textContent = n;
      b.dataset.n = n;
      el.appendChild(b);
    }
    function paint() {
      el.querySelectorAll("button").forEach(function (b) {
        b.classList.toggle("on", picked.indexOf(+b.dataset.n) >= 0);
      });
      onChange();
    }
    el.addEventListener("click", function (e) {
      var n = e.target.dataset.n;
      if (n === undefined) return;
      n = +n;
      var i = picked.indexOf(n);
      if (i >= 0) picked.splice(i, 1);
      else if (max === 1) picked = [n];
      else if (picked.length < max) picked.push(n);
      paint();
    });
    return {
      get: function () { return picked.slice(); },
      set: function (arr) { picked = arr.slice(); paint(); },
      random: function () {
        picked = [];
        while (picked.length < max) {
          var r = from + Math.floor(Math.random() * (to - from + 1));
          if (picked.indexOf(r) < 0) picked.push(r);
        }
        paint();
      },
    };
  }

  function initChecker(box) {
    var cfg = JSON.parse(box.dataset.cfg);
    var draws = null;
    var select = box.querySelector("select");
    var btnCheck = box.querySelector("[data-act=check]");
    var btnHistory = box.querySelector("[data-act=history]");
    var out = box.querySelector(".result");
    var count = box.querySelector(".count");
    var main, zone, digitInputs;
    // 樂合彩：選幾個號碼就是幾合
    function play() {
      var n = main.get().length;
      return cfg.plays.filter(function (p) { return p.k === n; })[0];
    }
    if (cfg.kind === "combo") {
      cfg.pick = cfg.plays[cfg.plays.length - 1].k;
      cfg.tiers = cfg.plays;
    }

    function ready() {
      if (!draws) return false;
      if (cfg.kind === "digits") return digitInputs.every(function (i) { return /^\d$/.test(i.value); });
      if (cfg.kind === "combo") return !!play();
      return main.get().length === cfg.pick && (!zone || zone.get().length === 1);
    }
    function refresh() {
      if (count) count.textContent = main.get().length;
      btnCheck.disabled = !ready();
      btnHistory.disabled = !ready();
    }

    if (cfg.kind === "digits") {
      digitInputs = Array.prototype.slice.call(box.querySelectorAll(".digits input"));
      digitInputs.forEach(function (inp, i) {
        inp.addEventListener("input", function () {
          inp.value = inp.value.replace(/\D/g, "").slice(-1);
          if (inp.value && digitInputs[i + 1]) digitInputs[i + 1].focus();
          refresh();
        });
      });
      main = { get: function () { return digitInputs.map(function (i) { return +i.value; }); } };
    } else {
      main = makePicker(box.querySelector(".picker.main"), 1, cfg.pool, cfg.pick, function () { refresh(); });
      if (cfg.special === "zone") {
        zone = makePicker(box.querySelector(".picker.zone"), 1, cfg.zonePool, 1, function () { refresh(); });
      }
    }

    box.querySelector("[data-act=random]").addEventListener("click", function () {
      if (cfg.kind === "combo") {
        // 已經選好幾合就照同樣個數重選，否則選二合
        var k = play() ? main.get().length : cfg.plays[0].k;
        var picked = [];
        while (picked.length < k) {
          var r = 1 + Math.floor(Math.random() * cfg.pool);
          if (picked.indexOf(r) < 0) picked.push(r);
        }
        main.set(picked);
      } else if (cfg.kind === "digits") {
        digitInputs.forEach(function (i) { i.value = Math.floor(Math.random() * 10); });
        refresh();
      } else {
        main.random();
        if (zone) zone.random();
      }
    });
    box.querySelector("[data-act=clear]").addEventListener("click", function () {
      if (cfg.kind === "digits") digitInputs.forEach(function (i) { i.value = ""; });
      else { main.set([]); if (zone) zone.set([]); }
      out.classList.remove("show");
      refresh();
    });

    // 回傳 {tier: 獎項索引或 -1, text, hitMain, hitSpecial}
    function judge(d) {
      if (cfg.kind === "digits") {
        var mine = main.get();
        var hits = d[2].map(function (n, i) { return n === mine[i]; });
        if (hits.every(Boolean)) return { tier: 0, hitMain: hits, text: "號碼與順序完全相同" };
        var same = mine.slice().sort().join() === d[2].slice().sort().join();
        return { tier: -1, hitMain: hits, same: same,
          text: same ? "號碼相同但順序不同（若投注「組彩」可能中獎，獎金依組彩種類而定）" : "" };
      }
      var picked = main.get();
      var hitMain = d[2].filter(function (n) { return picked.indexOf(n) >= 0; });
      if (cfg.kind === "combo") {
        var p = play();
        var all = hitMain.length === picked.length;
        return { tier: all ? cfg.plays.indexOf(p) : -1, hitMain: hitMain, prize: p.prize,
          text: p.name + "：中 " + hitMain.length + " / " + picked.length + " 個號碼" };
      }
      var s = false;
      if (cfg.special === "same") s = picked.indexOf(d[3]) >= 0;
      if (cfg.special === "zone") s = zone.get()[0] === d[3];
      var tier = -1;
      cfg.tiers.forEach(function (t, i) {
        if (tier >= 0) return;
        t.conds.forEach(function (c) {
          if (c[0] === hitMain.length && (c[1] === null || c[1] === s)) tier = i;
        });
      });
      var text = "中 " + hitMain.length + " 個號碼" + (s ? " + " + cfg.specialLabel : "");
      return { tier: tier, hitMain: hitMain, hitSpecial: s, text: text };
    }

    btnCheck.addEventListener("click", function () {
      var d = draws[select.selectedIndex];
      var r = judge(d);
      var msg = "第 " + d[0] + " 期（" + d[1] + "）：" + r.text;
      if (r.tier >= 0) {
        var amt = cfg.kind === "combo" ? r.prize : d[4][r.tier];
        msg += ' → <span class="win">' + cfg.tiers[r.tier].name +
          (amt ? "，每注 " + fmt(amt) + " 元" : "（該期無人中此獎，官方未公布每注獎金）") + "</span>";
      } else if (!r.same) {
        msg += (r.text ? " → " : "") + "沒有中獎";
      }
      out.innerHTML = '<div class="balls">' + ballsHtml(cfg, d, r.hitMain, r.hitSpecial) +
        "</div><p>" + msg + "</p>";
      out.classList.add("show");
    });

    btnHistory.addEventListener("click", function () {
      var tally = cfg.tiers.map(function () { return 0; });
      var won = 0, best = -1, bestDraw = null, same = 0, unknown = 0;
      draws.forEach(function (d) {
        var r = judge(d);
        if (r.same) same++;
        if (r.tier < 0) return;
        tally[r.tier]++;
        var amt = cfg.kind === "combo" ? r.prize : d[4][r.tier];
        if (!amt) unknown++;
        won += amt || 0;
        if (best < 0 || r.tier < best) { best = r.tier; bestDraw = d; }
      });
      var rows = cfg.tiers.map(function (t, i) {
        return tally[i] ? "<tr><td>" + t.name + '</td><td class="r">' + tally[i] + " 次</td></tr>" : "";
      }).join("");
      var html = "<p>如果從 " + draws[draws.length - 1][1] + " 起每期都買這組號碼（共 " +
        fmt(draws.length) + " 期）：</p>" +
        (rows ? "<table>" + rows + "</table>" : "<p>一次都沒中過" + cfg.tiers[0].name + "。</p>") +
        (bestDraw ? "<p>最好成績：第 " + bestDraw[0] + " 期 " + cfg.tiers[best].name + "</p>" : "");
      if (cfg.kind === "digits") {
        html += "<p>另外有 " + same + " 期是號碼相同但順序不同。</p>";
      } else {
        var cost = draws.length * cfg.price;
        html += "<p>總花費 " + fmt(cost) + " 元，總獎金約 " + fmt(won) + " 元（未扣稅），" +
          (won >= cost ? '<span class="win">賺 ' + fmt(won - cost) + " 元</span>" : "淨虧 " + fmt(cost - won) + " 元") + "。</p>";
        if (unknown) html += '<p class="note">其中 ' + unknown + " 次中獎的那期無人中該獎項，官方沒有公布每注獎金，未計入總獎金。</p>";
      }
      out.innerHTML = html;
      out.classList.add("show");
    });

    fetch(box.dataset.src)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        draws = data;
        select.innerHTML = data.map(function (d) {
          return "<option>第 " + d[0] + " 期 " + d[1] + "</option>";
        }).join("");
        refresh();
      });
    refresh();
  }

  // 賓果賓果：選 1～10 個號碼，比對某一天所有期數
  function initBingo(box) {
    var cfg = JSON.parse(box.dataset.cfg);
    var select = box.querySelector("select");
    var btnCheck = box.querySelector("[data-act=check]");
    var out = box.querySelector(".result");
    var count = box.querySelector(".count");
    var days = null;
    var picker = makePicker(box.querySelector(".picker.main"), 1, 80, 10, function () {
      count.textContent = picker.get().length;
      btnCheck.disabled = !days || picker.get().length === 0;
    });
    box.querySelector("[data-act=random]").addEventListener("click", function () { picker.random(); });
    box.querySelector("[data-act=clear]").addEventListener("click", function () {
      picker.set([]);
      out.classList.remove("show");
    });

    function prizeFor(stars, hits) {
      var p = cfg.stars[stars].filter(function (x) { return x[0] === hits; })[0];
      return p ? p[1] : 0;
    }

    btnCheck.addEventListener("click", function () {
      var mine = picker.get();
      var stars = mine.length;
      var day = select.value;
      out.innerHTML = "<p>載入中…</p>";
      out.classList.add("show");
      fetch("days/" + day + ".json")
        .then(function (r) { return r.json(); })
        .then(function (rows) {
          var won = 0, wins = [];
          rows.forEach(function (d) {
            var hits = d[2].filter(function (n) { return mine.indexOf(n) >= 0; }).length;
            var amt = prizeFor(stars, hits);
            if (amt) { won += amt; wins.push([d, hits, amt]); }
          });
          var cost = rows.length * cfg.price;
          var list = wins.slice(0, 50).map(function (w) {
            var d = w[0];
            var nums = d[2].slice().sort(function (a, b) { return a - b; }).map(function (n) {
              return '<span class="ball sm' + (mine.indexOf(n) >= 0 ? " hit" : "") +
                (n === d[2][19] ? " sp" : "") + '">' + pad(n) + "</span>";
            }).join("");
            return "<tr><td>" + d[0] + "</td><td>" + d[1] + "</td><td>中 " + w[1] +
              '</td><td class="r">' + fmt(w[2]) + '</td></tr><tr><td colspan="4"><div class="balls">' +
              nums + "</div></td></tr>";
          }).join("");
          out.innerHTML = "<p>" + day + " 共 " + rows.length + " 期，" + stars + " 星每期各買一注：</p>" +
            "<p>中獎 " + wins.length + " 期，總花費 " + fmt(cost) + " 元，總獎金 " + fmt(won) + " 元（未扣稅），" +
            (won >= cost ? '<span class="win">賺 ' + fmt(won - cost) + " 元</span>" : "淨虧 " + fmt(cost - won) + " 元") +
            "。</p>" +
            (list ? '<div class="scroll"><table><thead><tr><th>期別</th><th>時間</th><th>結果</th>' +
              '<th class="r">獎金</th></tr></thead><tbody>' + list + "</tbody></table></div>" : "") +
            (wins.length > 50 ? '<p class="note">只列出前 50 期。</p>' : "");
        });
    });

    fetch("days.json")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        days = data;
        select.innerHTML = data.map(function (d) { return "<option>" + d + "</option>"; }).join("");
        btnCheck.disabled = picker.get().length === 0;
      });
  }

  function initSort(table) {
    var tbody = table.tBodies[0];
    table.querySelectorAll("th[data-sort]").forEach(function (th) {
      var col = Array.prototype.indexOf.call(th.parentNode.children, th);
      var asc = th.dataset.sort === "asc";
      th.addEventListener("click", function () {
        var rows = Array.prototype.slice.call(tbody.rows);
        rows.sort(function (a, b) {
          var x = +a.cells[col].dataset.v, y = +b.cells[col].dataset.v;
          return asc ? x - y : y - x;
        });
        asc = !asc;
        rows.forEach(function (r) { tbody.appendChild(r); });
      });
    });
  }

  document.querySelectorAll("[data-checker]").forEach(initChecker);
  document.querySelectorAll("[data-bingo]").forEach(initBingo);
  document.querySelectorAll("table.sortable").forEach(initSort);
})();
