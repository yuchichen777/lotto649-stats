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
    if (d[3] !== null) {
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

    function ready() {
      if (!draws) return false;
      if (cfg.kind === "digits") return digitInputs.every(function (i) { return /^\d$/.test(i.value); });
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
      if (cfg.kind === "digits") {
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
        var amt = d[4][r.tier];
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
        if (!d[4][r.tier]) unknown++;
        won += d[4][r.tier] || 0;
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
  document.querySelectorAll("table.sortable").forEach(initSort);
})();
