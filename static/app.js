// 對獎工具 + 表格排序，不依賴任何套件
(function () {
  var PRIZES = ["頭獎", "貳獎", "參獎", "肆獎", "伍獎", "陸獎", "柒獎", "普獎"];

  // 依中獎號碼數 m 與是否中特別號 s 回傳獎項索引，沒中回傳 -1
  function prizeIndex(m, s) {
    if (m === 6) return 0;
    if (m === 5) return s ? 1 : 2;
    if (m === 4) return s ? 3 : 4;
    if (m === 3) return s ? 5 : 7;
    if (m === 2 && s) return 6;
    return -1;
  }

  function fmt(n) { return n.toLocaleString("zh-TW"); }

  function initChecker(box) {
    var picked = [];
    var draws = null;
    var picker = box.querySelector(".picker");
    var select = box.querySelector("select");
    var btnCheck = box.querySelector("[data-act=check]");
    var btnHistory = box.querySelector("[data-act=history]");
    var btnRandom = box.querySelector("[data-act=random]");
    var btnClear = box.querySelector("[data-act=clear]");
    var out = box.querySelector(".result");
    var count = box.querySelector(".count");

    for (var n = 1; n <= 49; n++) {
      var b = document.createElement("button");
      b.type = "button";
      b.textContent = n;
      b.dataset.n = n;
      picker.appendChild(b);
    }

    function refresh() {
      picker.querySelectorAll("button").forEach(function (b) {
        b.classList.toggle("on", picked.indexOf(+b.dataset.n) >= 0);
      });
      count.textContent = picked.length;
      var ready = picked.length === 6 && draws;
      btnCheck.disabled = !ready;
      btnHistory.disabled = !ready;
    }

    picker.addEventListener("click", function (e) {
      var n = +e.target.dataset.n;
      if (!n) return;
      var i = picked.indexOf(n);
      if (i >= 0) picked.splice(i, 1);
      else if (picked.length < 6) picked.push(n);
      refresh();
    });

    btnRandom.addEventListener("click", function () {
      picked = [];
      while (picked.length < 6) {
        var r = 1 + Math.floor(Math.random() * 49);
        if (picked.indexOf(r) < 0) picked.push(r);
      }
      refresh();
    });

    btnClear.addEventListener("click", function () {
      picked = [];
      out.classList.remove("show");
      refresh();
    });

    function balls(nums, special, hits) {
      var h = nums.map(function (n) {
        return '<span class="ball sm' + (hits.indexOf(n) >= 0 ? " hit" : "") + '">' + n + "</span>";
      }).join("");
      return h + '<span class="plus">+</span><span class="ball sm sp' +
        (hits.indexOf(special) >= 0 ? " hit" : "") + '">' + special + "</span>";
    }

    btnCheck.addEventListener("click", function () {
      var d = draws[select.selectedIndex];
      var hits = d[2].filter(function (n) { return picked.indexOf(n) >= 0; });
      var s = picked.indexOf(d[3]) >= 0;
      var p = prizeIndex(hits.length, s);
      var msg = "第 " + d[0] + " 期（" + d[1] + "）：中 " + hits.length + " 個號碼" + (s ? " + 特別號" : "");
      if (p >= 0) {
        var amt = d[4][p];
        msg += ' → <span class="win">' + PRIZES[p] + (amt ? "，每注 " + fmt(amt) + " 元" : "") + "</span>";
      } else {
        msg += " → 沒有中獎";
      }
      out.innerHTML = '<div class="balls">' + balls(d[2], d[3], hits.concat(s ? [d[3]] : [])) +
        "</div><p>" + msg + "</p>";
      out.classList.add("show");
    });

    btnHistory.addEventListener("click", function () {
      var tally = [0, 0, 0, 0, 0, 0, 0, 0];
      var won = 0;
      var best = -1, bestDraw = null;
      draws.forEach(function (d) {
        var m = d[2].filter(function (n) { return picked.indexOf(n) >= 0; }).length;
        var p = prizeIndex(m, picked.indexOf(d[3]) >= 0);
        if (p < 0) return;
        tally[p]++;
        won += d[4][p] || 0;
        if (best < 0 || p < best) { best = p; bestDraw = d; }
      });
      var cost = draws.length * 50;
      var rows = PRIZES.map(function (name, i) {
        return tally[i] ? "<tr><td>" + name + '</td><td class="r">' + tally[i] + " 次</td></tr>" : "";
      }).join("");
      out.innerHTML =
        "<p>如果從 " + draws[draws.length - 1][1] + " 起每期都買這組號碼（共 " + fmt(draws.length) + " 期）：</p>" +
        (rows ? "<table>" + rows + "</table>" : "<p>一次都沒中過。</p>") +
        (bestDraw ? "<p>最好成績：第 " + bestDraw[0] + " 期 " + PRIZES[best] + "</p>" : "") +
        "<p>總花費 " + fmt(cost) + " 元，總獎金約 " + fmt(won) + " 元（未扣稅），" +
        (won >= cost ? '<span class="win">賺 ' + fmt(won - cost) + " 元</span>" : "淨虧 " + fmt(cost - won) + " 元") +
        "。</p>";
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
    table.querySelectorAll("th[data-sort]").forEach(function (th, idx) {
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
