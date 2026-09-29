/* Kiểm Mua — giao diện đọc docs/data/latest.json (job/run_daily.py ghi lúc 16:30).
   Bố cục theo trang mẫu v2 đã duyệt 26/09/2026; khung push chép từ wyckoff-radar/docs/app.js. */
(() => {
  const CFG = window.KM_CONFIG || {};
  const G = {
    A: ["Tin UBCKNN", "ssc.gov.vn · qua KingStock", "#3B1A78"], B: ["Nến & xu hướng", "candle-radar", "#7DBA2F"],
    C: ["Vùng giá & dòng tiền", "price-path", "#0F3B34"], D: ["Wyckoff", "wyckoff-radar", "#6A2FBF"],
    E: ["Order flow", "order-flow", "#2F9D4E"],
  };
  const SRC = [["kingstock", "KingStock"], ["ssc", "UBCKNN"], ["candle", "Candle"], ["pricepath", "Price Path"], ["wyckoff", "Wyckoff"], ["orderflow", "Order Flow"]];
  const GLYPH = { ok: "✓", no: "✕", warn: "!", na: "–", info: "i" };
  const EVN = { sc: "SC", spring3: "Spring #3", test: "Test" };
  const HI = 10;  // tô vàng (lưới Tra mã, ô điểm) khi đạt từ ngần này tiêu chí — anh chốt 29/09/2026; báo điện thoại từ 15 (job PUSH_MIN)

  const $ = (s) => document.querySelector(s);
  const vn = (x, d = 2) => (x == null ? "–" : x.toLocaleString("vi-VN", { minimumFractionDigits: d, maximumFractionDigits: d }));
  const dm = (s) => (s ? s.slice(8, 10) + "/" + s.slice(5, 7) : "–");
  const cls = (c) => (c == null ? "" : c > 0 ? "up" : c < 0 ? "down" : "ref");
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const chg = (b) => (b.chg == null ? "" : `<span class="${cls(b.chg)}">${b.chg > 0 ? "+" : ""}${vn(b.chg, 1)}%</span>`);
  const store = { get(k, d) { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch (_) { return d; } },
                  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (_) { /* không sao */ } } };
  let D = null;

  // ---------------------------------------------------------------- thẻ & nến mini
  // Mỗi tiêu chí là một nến nhỏ: đạt = nến xanh đặc, chưa đạt = nến xám rỗng, cảnh báo = nến đỏ, thiếu = bóng mờ.
  function mini(s) {
    const c = { ok: ["#2F9D4E", "#2F9D4E", 22], no: ["none", "#B9B2CC", 14], warn: ["#D6312B", "#D6312B", 22], na: ["none", "#DAD4E8", 10] }[s];
    const h = c[2], y = 26 - h - 3;
    return `<svg width="10" height="28" viewBox="0 0 10 28"><line x1="5" y1="${y - 3}" x2="5" y2="${y + h + 2}" stroke="${c[1]}" stroke-width="1.4"/><rect x="1.2" y="${y}" width="7.6" height="${h}" rx="1" fill="${c[0]}" stroke="${c[1]}" stroke-width="1.4" ${s === "na" ? 'stroke-dasharray="2 2"' : ""}/></svg>`;
  }
  const minis = (b) => `<div class="minis" aria-hidden="true">${Object.values(b.groups).map((v) => `<span class="g">${v.filter((x) => x.s !== "info").map((x) => mini(x.s)).join("")}</span>`).join("")}</div>`;
  const scoreBox = (b, lab = "đạt") => `<div class="score${b.pass >= HI ? " hi" : ""}"><b>${b.pass}/${b.total}</b><small>${lab}</small></div>`;
  const bos = (label, right) => `<div class="bos"><div class="ln"></div><div class="lab"><b>${label}</b><span>${right}</span></div></div>`;

  function card(sym, a) {
    const b = D.board[sym];
    if (!b) return "";
    return `<button class="card" type="button" data-sym="${esc(sym)}">
      <div class="l"><span class="sym">${esc(sym)}</span><span class="px mono">${vn(b.price)} ${chg(b)}</span></div>${scoreBox(b)}
      ${minis(b)}
      ${a ? `<div class="ks"><span class="tag">▲ MUA</span><span class="mono">${(a.at || "").slice(11, 16)} · %K ${vn(a.k, 1)} · giá báo ${vn(a.price)}</span>${b.warn ? `<span class="wtag">${b.warn} cảnh báo</span>` : ""}</div>` : ""}
    </button>`;
  }

  // ---------------------------------------------------------------- các tab
  function renderToday() {
    $("#kDate").textContent = dm(D.trade_date) + "/" + D.trade_date.slice(0, 4);
    $("#src").innerHTML = SRC.map(([k, n]) => {
      const s = D.sources[k] || {}, bad = !s.ok || s.stale;
      return `<span title="${esc(s.stale || s.error || "")}"><i class="${bad ? "off" : ""}"></i>${n}<small>${s.ok ? dm(s.date) || "ok" : "lỗi"}</small></span>`;
    }).join("");
    const al = D.alerts;
    let h = al.length
      ? bos(`Báo MUA ${dm(D.trade_date)}`, `${al.length} mã`) + `<div class="cards">${al.map((a) => card(a.sym, a)).join("")}</div>`
      : `<div class="empty"><b>Phiên ${dm(D.trade_date)} KingStock không báo MUA mã nào</b>Vẫn xem được bảng soát của bất kỳ mã nào ở tab Tra mã.</div>`;
    const prev = (D.history || []).find((d) => d.alerts.length);
    if (prev) h += bos(`Báo MUA ${dm(prev.date)}`, "phiên trước · điểm ngày đó") + `<div class="cards">${prev.alerts.map((a) =>
      `<div class="hrow"><span class="sym">${esc(a.sym)}</span><span class="px mono">báo ${(a.at || "").slice(11, 16)} · giá ${vn(a.price)}</span><span class="mono"><b>${a.pass}/${a.total}</b>${a.warn ? ` · <span class="down">${a.warn}!</span>` : ""}</span></div>`).join("")}</div>`;
    const stale = SRC.filter(([k]) => D.sources[k] && D.sources[k].stale).map(([k, n]) => `${n}: ${esc(D.sources[k].stale)}`);
    if (stale.length) h += `<div class="note"><b>Nguồn chưa đủ.</b> ${stale.join(" · ")}. Tiêu chí của các nguồn này ghi "thiếu dữ liệu" và không tính điểm.</div>`;
    $("#alerts").innerHTML = h;
  }

  function renderLookup() {
    const syms = Object.keys(D.board).sort();
    $("#gridNote").textContent = `Vàng = đạt từ ${HI} tiêu chí`;
    $("#grid39").innerHTML = syms.map((s) => {
      const b = D.board[s];
      return `<button type="button" data-sym="${esc(s)}" class="${b.pass >= HI ? "hi" : ""}">${esc(s)}<small>${b.pass}/${b.total}</small></button>`;
    }).join("");
    const rec = store.get("km-recent", []).filter((s) => D.board[s]);
    $("#recent").innerHTML = rec.map((s) => `<button type="button" data-sym="${esc(s)}">${esc(s)}</button>`).join("");
  }

  function renderHistory() {
    const days = [{ date: D.trade_date, alerts: D.alerts.map((a) => ({ ...a, ...D.board[a.sym] })) }].concat(D.history || []);
    $("#hist").innerHTML = days.map((d) => bos(`Ngày ${dm(d.date)}`, d.alerts.length ? `${d.alerts.length} mã báo mua` : "không có mã") +
      d.alerts.map((a) => `<div class="hrow"><span class="sym">${esc(a.sym)}</span><span class="px mono">báo ${(a.at || "").slice(11, 16)} · giá ${vn(a.price)}</span><span class="mono"><b>${a.pass}/${a.total}</b>${a.warn ? ` · <span class="down">${a.warn}!</span>` : ""}</span></div>`).join("")).join("") +
      `<p class="disc">Điểm mỗi ngày là điểm máy chấm đúng lúc đó, lưu trong <span class="mono">data/daily/&lt;ngày&gt;.json</span>. Sau 2–3 tháng dùng số này để đo xem điểm cao có thật sự tốt hơn không.</p>`;
  }

  function renderSettings() {
    const L = [
      ["A", "Tin UBCKNN: cổ tức / tăng vốn", "UBCKNN đã nhận hồ sơ phát hành cổ phiếu trả cổ tức hoặc tăng vốn từ vốn chủ sở hữu trong 30 ngày. Tin lấy từ tab UBCKNN của KingStock, có từ 11/09/2026."],
      ["B", "Cụm nến mua", "1 trong 9 mẫu nến mua của candle-radar trong 3 phiên gần nhất."],
      ["B", "Supertrend xanh", "Supertrend (10, 3), ATR kiểu Wilder."],
      ["B", "Giá trên EMA10", "Giá đóng cửa so với EMA 10 phiên."],
      ["C", "Giá trên POC 10 phiên", "POC (mức giá khớp nhiều nhất) của hồ sơ khối lượng 10 phiên."],
      ["C", "Giá trên POC 20 phiên", "Như trên, hồ sơ 20 phiên. Mỗi POC là một tiêu chí riêng."],
      ["C", "Cá mập mua > bán", "Lệnh gộp từ 500 triệu đồng trở lên, so chiều mua với chiều bán chủ động trong phiên."],
      ["C", "Mua đẩy giá lên", "Dòng chủ động (mua − bán)/(mua + bán) từ +5 % và giá phiên tăng trên 0,3 % (luật của price-path)."],
      ["C", "Giá tăng > 2 %", "Giá đóng cửa tăng trên 2 % so với tham chiếu."],
      ["C", "Giá & CVD cùng lên", "Cả giá và dòng tiền cộng dồn đều tăng so với 5 phiên trước."],
      ["D", "SC / Spring #3 / Test", "Có ít nhất một sự kiện trong 20 phiên gần nhất."],
      ["E", "Delta dương, mua > bán chủ động", "Hai yêu cầu này là một phép so sánh nên gộp một dòng."],
      ["E", "CVD dương", "CVD cộng dồn nhiều phiên của order-flow."],
      ["E", "Giá trên VWAP", "VWAP khớp liên tục, không tính ATO/ATC."],
      ["E", "CVD & giá cùng lên", "Cùng tăng so với 5 phiên trước (cần ít nhất 3 phiên dữ liệu)."],
      ["E", "Cá mập mua > bán ≥ 3/5 phiên", "Trong 5 phiên gần nhất, ít nhất 3 phiên có lệnh cá mập (từ 500 triệu đồng) mua chủ động nhiều hơn bán chủ động. Số lấy từ ô Delta cá mập của order-flow."],
      ["E", "Giá trên giá vốn cá mập", "Giá đóng cửa cao hơn giá mua bình quân của cá mập (lệnh từ 500 triệu đồng, cộng dồn tối đa 20 phiên). Đây là đường vàng đứt “Giá vốn CM” trên footprint của order-flow."],
    ];
    $("#crit").innerHTML = L.map(([g, t, d]) => `<span class="L" style="background:${G[g][2]}">${g}</span><span><b>${t}</b><br>${d}</span>`).join("");
    $("#meta").innerHTML = `Dữ liệu phiên ${dm(D.trade_date)} · chấm lúc ${(D.generated_at || "").slice(11, 16)} · ${Object.keys(D.board).length} mã<br>` +
      SRC.map(([k, n]) => { const s = D.sources[k] || {}; return `${n}: ${s.ok ? "OK " + dm(s.date) : "LỖI"}${s.stale || s.error ? " — " + esc(s.stale || s.error) : ""}`; }).join("<br>");
  }

  // ---------------------------------------------------------------- chi tiết mã
  function rowHtml(x) {
    const links = (x.links || []).filter((l) => /^https?:\/\//.test(l.u || ""));
    return `<div class="it ${x.s}"><span class="st ${x.s}">${GLYPH[x.s]}</span><span class="tt">${esc(x.t)}</span><span class="dd">${esc(x.d)}</span>` +
      (links.length ? `<span class="lk">${links.map((l) => `<a href="${esc(l.u)}" target="_blank" rel="noopener">${esc(l.t)} <small>${esc(l.src || "")}</small></a>`).join("")}</span>` : "") + `</div>`;
  }
  function openSheet(sym) {
    const b = D.board[sym];
    if (!b) return;
    const a = D.alerts.find((x) => x.sym === sym);
    $("#sheetIn").innerHTML = `
      <div class="sbar"><button class="back" type="button" id="back">← Quay lại</button><span class="kicker">${a ? `KingStock báo ${dm(a.date)}` : "Tra tay"} · phiên ${dm(D.trade_date)}</span></div>
      <div class="hero">
        <div><div class="sym">${esc(sym)}</div><div class="px mono" style="font-size:16px;margin-top:4px">${vn(b.price)} ${chg(b)}</div></div>
        ${scoreBox(b, "tiêu chí đạt")}
        <div class="co">${esc(b.name)}</div>
        <div class="flags">${a ? `<span class="k">▲ MUA ${(a.at || "").slice(11, 16)} · %K ${vn(a.k, 1)}</span>` : ""}${b.warn ? `<span class="w">${b.warn} cảnh báo đỏ</span>` : ""}${b.na ? `<span class="n">${b.na} thiếu dữ liệu</span>` : ""}</div>
      </div>
      ${b.chart ? `<div class="chart"><canvas id="cv" aria-label="Biểu đồ 46 phiên"></canvas>
        <div class="legend"><span><i style="background:#7DBA2F"></i>EMA10</span><span><i style="background:#2F9D4E"></i>Supertrend xanh</span><span><i style="background:#D6312B"></i>Supertrend đỏ</span><span><i style="background:repeating-linear-gradient(90deg,#1B1530 0 4px,transparent 4px 7px)"></i>POC 10</span><span><i style="background:repeating-linear-gradient(90deg,#6A2FBF 0 2px,transparent 2px 5px)"></i>POC 20</span></div></div>` : ""}
      ${Object.entries(b.groups).map(([k, v]) => {
        const s = v.filter((x) => x.s === "ok" || x.s === "no"), ok = s.filter((x) => x.s === "ok").length;
        return `<section class="grp"><div class="gh"><span class="ico" style="background:${G[k][2]}"><svg><use href="#g-${k}"/></svg></span>
          <h3>${G[k][0]}<small>${G[k][1]}</small></h3><span class="gs ${ok ? "" : "z"}">${s.length ? `${ok}/${s.length}` : "–"}</span></div>` + v.map(rowHtml).join("") + `</section>`;
      }).join("")}
      <p class="disc">Bảng soát, không phải khuyến nghị mua. Giá tính theo nghìn đồng, đã điều chỉnh.</p>`;
    $("#sheet").classList.add("on");
    $("#sheet").scrollTop = 0;
    $("#back").onclick = closeSheet;
    if (b.chart) requestAnimationFrame(() => draw(b.chart));
    if (!a) { const rec = [sym].concat(store.get("km-recent", []).filter((s) => s !== sym)).slice(0, 8); store.set("km-recent", rec); renderLookup(); }
    if (location.hash !== "#m-" + sym) history.pushState(null, "", "#m-" + sym);
  }
  function closeSheet() {
    $("#sheet").classList.remove("on");
    if (location.hash.startsWith("#m-")) history.pushState(null, "", location.pathname + location.search);
  }
  addEventListener("keydown", (e) => { if (e.key === "Escape") closeSheet(); });
  addEventListener("popstate", () => { if (!location.hash.startsWith("#m-")) $("#sheet").classList.remove("on"); });

  function draw(ch) {
    const cv = $("#cv"), dpr = devicePixelRatio || 1, W = cv.clientWidth, H = cv.clientHeight;
    cv.width = W * dpr; cv.height = H * dpr;
    const x = cv.getContext("2d"); x.scale(dpr, dpr);
    const B = ch.b, n = B.length, padL = 6, padR = 46, padT = 26, padB = 20;
    let lo = Infinity, hi = -Infinity;
    B.forEach((r) => { lo = Math.min(lo, r[3]); hi = Math.max(hi, r[2]); });
    ch.ema.forEach((v) => { if (v != null) { lo = Math.min(lo, v); hi = Math.max(hi, v); } });
    ch.st.forEach((v) => { if (v) { lo = Math.min(lo, v[0]); hi = Math.max(hi, v[0]); } });
    const pocs = Object.entries(ch.poc || {}).filter(([, v]) => v != null);   // [["10", giá], ["20", giá]]
    pocs.forEach(([, v]) => { lo = Math.min(lo, v); hi = Math.max(hi, v); });
    const pad = (hi - lo) * 0.06; lo -= pad; hi += pad;
    const step = (W - padL - padR) / n, X = (i) => padL + step * (i + 0.5), Y = (v) => padT + (hi - v) / (hi - lo) * (H - padT - padB);
    // vị trí nhãn POC ở trục giá; hai nhãn sát nhau thì đẩy nhãn thứ hai ra 17 px
    const labY = [];
    pocs.forEach(([, v]) => { const y = Y(v), p = labY[labY.length - 1]; labY.push(p != null && Math.abs(y - p) < 17 ? p + (y >= p ? 17 : -17) : y); });
    x.font = "500 10px 'IBM Plex Mono',monospace"; x.textBaseline = "middle";
    for (let k = 0; k <= 3; k++) {
      const v = lo + (hi - lo) * k / 3, y = Y(v);
      x.strokeStyle = "#EFEAF7"; x.lineWidth = 1; x.beginPath(); x.moveTo(padL, y); x.lineTo(W - padR, y); x.stroke();
      if (labY.every((ly) => Math.abs(y - ly) > 13)) { x.fillStyle = "#6E6886"; x.fillText(vn(v), W - padR + 5, y); }   // chừa chỗ nhãn POC
    }
    // POC 10 & 20 phiên: nét đứt như vạch BoS, nhãn ở trục giá (vị trí tính sẵn trong labY)
    pocs.forEach(([n, v], j) => {
      const y = Y(v), col = n === "10" ? "#1B1530" : "#6A2FBF";
      x.setLineDash(n === "10" ? [5, 4] : [2, 3]); x.strokeStyle = col; x.lineWidth = 1.4;
      x.beginPath(); x.moveTo(padL, y); x.lineTo(W - padR, y); x.stroke(); x.setLineDash([]);
      const ly = labY[j];
      x.fillStyle = col; x.beginPath(); x.roundRect(W - padR + 1, ly - 8, padR - 2, 16, 3); x.fill();
      x.font = "800 9px Montserrat,sans-serif"; x.fillStyle = "#fff"; x.fillText("POC" + n, W - padR + 4, ly + 0.5);
    });
    x.lineWidth = 1.6; x.globalAlpha = 0.75;
    for (let i = 1; i < n; i++) {
      const a = ch.st[i - 1], b = ch.st[i];
      if (!a || !b || a[1] !== b[1]) continue;
      x.strokeStyle = b[1] ? "#2F9D4E" : "#D6312B"; x.beginPath(); x.moveTo(X(i - 1), Y(a[0])); x.lineTo(X(i), Y(b[0])); x.stroke();
    }
    x.globalAlpha = 1;
    const bw = Math.max(2, step * 0.62);
    B.forEach((r, i) => {
      const c = r[4] >= r[1] ? "#2F9D4E" : "#D6312B";
      x.strokeStyle = c; x.lineWidth = 1; x.beginPath(); x.moveTo(X(i), Y(r[2])); x.lineTo(X(i), Y(r[3])); x.stroke();
      const y1 = Y(Math.max(r[1], r[4])), y2 = Y(Math.min(r[1], r[4]));
      x.fillStyle = c; x.fillRect(X(i) - bw / 2, y1, bw, Math.max(1.2, y2 - y1));
    });
    x.strokeStyle = "#7DBA2F"; x.lineWidth = 2.2; x.lineJoin = "round"; x.beginPath();
    let on = false;
    ch.ema.forEach((v, i) => { if (v == null) return; if (on) x.lineTo(X(i), Y(v)); else x.moveTo(X(i), Y(v)); on = true; });
    x.stroke();
    const idx = Object.fromEntries(B.map((r, i) => [r[0], i]));
    ch.marks.forEach(([d, e], j) => {   // mốc Wyckoff: hộp xanh đêm + mũi tên nét đứt, như "1st ENTRY"
      const i = idx[d]; if (i == null) return;
      const bx = X(i), by = Y(B[i][3]) + 4, lab = EVN[e] || e, col = "#0F3B34";
      x.font = "800 10.5px Montserrat,sans-serif";
      const tw = x.measureText(lab).width + 12, top = H - padB - 20 - (j % 2) * 20, left = Math.min(Math.max(bx - tw / 2, padL), W - padR - tw);
      x.setLineDash([3, 3]); x.strokeStyle = col; x.lineWidth = 1.2; x.beginPath(); x.moveTo(bx, by); x.lineTo(bx, top); x.stroke(); x.setLineDash([]);
      x.fillStyle = col; x.beginPath(); x.roundRect(left, top, tw, 17, 4); x.fill();
      x.fillStyle = "#fff"; x.textBaseline = "middle"; x.fillText(lab, left + 6, top + 9);
    });
    x.font = "500 10px 'IBM Plex Mono',monospace"; x.fillStyle = "#6E6886"; x.textBaseline = "alphabetic";
    x.fillText(dm(B[0][0]), padL, H - 4);
    const t = dm(B[n - 1][0]); x.fillText(t, W - padR - x.measureText(t).width, H - 4);
    x.font = "800 11px Montserrat,sans-serif"; x.fillStyle = "#3B1A78"; x.fillText(`${n} PHIÊN · NẾN NGÀY`, padL, 14);
  }

  // ---------------------------------------------------------------- điều hướng
  function tab(name) {
    document.querySelectorAll("nav button").forEach((o) => o.setAttribute("aria-selected", o.dataset.tab === name));
    document.querySelectorAll(".panel").forEach((p) => p.classList.toggle("on", p.id === "p-" + name));
    $("#sheet").classList.remove("on");
    $("#main").scrollTop = 0;
  }
  document.querySelectorAll("nav button").forEach((bt) => bt.addEventListener("click", () => tab(bt.dataset.tab)));
  document.addEventListener("click", (e) => { const c = e.target.closest("[data-sym]"); if (c && D) openSheet(c.dataset.sym); });
  $("#f").addEventListener("submit", (e) => {
    e.preventDefault();
    const s = $("#q").value.trim().toUpperCase(), m = $("#msg");
    if (!s || !D) return;
    if (!D.board[s]) { m.hidden = false; m.textContent = `${s} không thuộc danh mục KingStock (${Object.keys(D.board).length} mã).`; return; }
    m.hidden = true; $("#q").value = ""; openSheet(s);
  });

  // ---------------------------------------------------------------- push (chép wyckoff-radar, chỉ nhánh không Worker)
  const b64ToU8 = (s) => { const p = "=".repeat((4 - s.length % 4) % 4); const b = atob((s + p).replace(/-/g, "+").replace(/_/g, "/")); return Uint8Array.from(b, (c) => c.charCodeAt(0)); };
  const SW = "sw.js?v=2";   // đổi số khi cần máy cũ đăng ký lại service worker
  let toastTimer = null;
  function toast(t, b) { $("#toastTitle").textContent = t; $("#toastBody").textContent = b || ""; $("#toast").classList.add("on"); clearTimeout(toastTimer); toastTimer = setTimeout(() => $("#toast").classList.remove("on"), 3500); }
  async function pushStatus() {
    const st = $("#pushState");
    if (!("serviceWorker" in navigator) || !("PushManager" in window)) { st.textContent = "Trình duyệt này không hỗ trợ thông báo đẩy. Trên iPhone: thêm vào Màn hình chính rồi mở từ đó."; $("#pushBtn").disabled = true; return; }
    if (!CFG.VAPID_PUBLIC) { st.textContent = "Chưa có khoá VAPID trong config.js — bật được sau khi dựng xong trên GitHub."; $("#pushBtn").disabled = true; return; }
    const reg = await navigator.serviceWorker.ready;
    const sub = await reg.pushManager.getSubscription();
    if (sub) { st.textContent = "Máy này đã tạo địa chỉ nhận. Kiểm tra đoạn mã bên dưới đã được dán vào GitHub."; $("#pushBtn").textContent = "Đăng ký lại"; showSubCode(sub); }
    else st.textContent = "Máy này chưa đăng ký nhận thông báo.";
  }
  function showSubCode(sub) {
    const code = JSON.stringify([sub.toJSON()]);
    $("#subCodeWrap").innerHTML = `<div class="subcode state"><b>Đoạn mã đăng ký của máy này.</b> Dán vào GitHub → Settings → Secrets and variables → Actions → <span class="mono">PUSH_SUBS_FALLBACK</span>. Nhiều máy thì nối các đoạn trong cùng một mảng JSON. Làm một lần mỗi máy.
      <textarea id="subTxt" readonly></textarea><button type="button" class="btn" id="copySub" style="margin-top:6px">Sao chép</button></div>`;
    $("#subTxt").value = code;
    $("#copySub").addEventListener("click", async () => {
      try { await navigator.clipboard.writeText(code); toast("Đã sao chép", "Dán vào GitHub Secret PUSH_SUBS_FALLBACK."); }
      catch (_) { $("#subTxt").select(); toast("Đã chọn sẵn đoạn mã", "Bấm giữ để sao chép."); }
    });
  }
  const swReady = () => Promise.race([navigator.serviceWorker.ready, new Promise((_, rej) => setTimeout(() => rej(new Error("Phần chạy nền chưa sẵn sàng — đóng hẳn app, mở lại rồi bấm lần nữa")), 8000))]);
  $("#pushBtn").addEventListener("click", async () => {
    const st = $("#pushState"), btn = $("#pushBtn");
    btn.disabled = true;
    try {
      if (Notification.permission === "denied") { st.textContent = "Điện thoại đang CHẶN thông báo của trang này. Mở Cài đặt trình duyệt → Cài đặt trang web → Thông báo → bật, rồi bấm lại."; return; }
      const perm = await Notification.requestPermission();
      if (perm !== "granted") { st.textContent = "Anh chưa cho phép. Bấm lại và chọn Cho phép."; return; }
      if (!navigator.serviceWorker.controller) { try { await navigator.serviceWorker.register(SW); } catch (_) { /* thử tiếp */ } }
      const reg = await swReady();
      let sub = await reg.pushManager.getSubscription();
      if (!sub) sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: b64ToU8(CFG.VAPID_PUBLIC) });
      toast("Đã tạo địa chỉ nhận", "Sao chép đoạn mã bên dưới và dán vào GitHub — một lần cho máy này.");
      await pushStatus();
    } catch (err) {
      st.textContent = "Không đăng ký được: " + (err && err.message ? err.message : err) + " — chụp màn hình dòng này gửi lại.";
    } finally { btn.disabled = false; }
  });

  // ---------------------------------------------------------------- cài app (27/09/2026)
  // Chrome/Android bắn beforeinstallprompt khi trang đủ điều kiện cài → giữ lại, hiện nút, bấm thì mở hộp cài thật.
  // Máy từng mở trang lúc Pages còn 404 thì menu Chrome chỉ còn "Thêm lối tắt"; nút này tránh phải mò menu.
  let deferred = null;
  const installed = () => matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;
  function installUi() {
    const st = $("#installState");
    if (installed()) { $("#installTop").hidden = true; $("#installBtn").hidden = true; st.textContent = "Đã cài: anh đang mở Kiểm Mua như một app."; return; }
    $("#installTop").hidden = !deferred; $("#installBtn").hidden = !deferred;
    const ios = /iphone|ipad|ipod/i.test(navigator.userAgent);
    st.innerHTML = deferred ? "Bấm nút bên dưới, rồi chọn <b>Cài đặt</b>."
      : ios ? "Trên iPhone: mở bằng Safari → nút <b>Chia sẻ</b> → <b>Thêm vào MH chính</b>."
      : "Chưa thấy nút cài? Mở bằng <b>Chrome</b>, tải lại trang một lần, đợi vài giây. Hoặc bấm <b>⋮</b> → <b>Cài đặt ứng dụng</b> (hoặc <b>Thêm vào màn hình chính</b>). Đã lỡ tạo lối tắt thì xoá lối tắt đó trước.";
  }
  addEventListener("beforeinstallprompt", (e) => { e.preventDefault(); deferred = e; installUi(); });
  addEventListener("appinstalled", () => { deferred = null; installUi(); toast("Đã cài Kiểm Mua", "Mở từ icon kính lúp trên màn hình chính."); });
  async function doInstall() {
    if (!deferred) return installUi();
    deferred.prompt();
    const r = await deferred.userChoice.catch(() => null);
    deferred = null;
    if (r && r.outcome !== "accepted") toast("Chưa cài", "Bấm lại nút Cài app khi anh muốn.");
    installUi();
  }
  $("#installTop").addEventListener("click", doInstall);
  $("#installBtn").addEventListener("click", doInstall);
  installUi();

  // ---------------------------------------------------------------- tải dữ liệu
  if ("serviceWorker" in navigator) navigator.serviceWorker.register(SW).catch(() => {});
  fetch("data/latest.json?t=" + Date.now()).then((r) => { if (!r.ok) throw new Error("Chưa có dữ liệu (data/latest.json " + r.status + ")"); return r.json(); })
    .then((d) => {
      D = d;
      renderToday(); renderLookup(); renderHistory(); renderSettings();
      const m = location.hash.match(/^#m-([A-Z0-9]{3,4})$/);
      if (m) openSheet(m[1]);
    })
    .catch((err) => { $("#alerts").innerHTML = `<div class="err">${esc(err.message)}</div>`; })
    .finally(() => { pushStatus().catch(() => {}); });
})();
