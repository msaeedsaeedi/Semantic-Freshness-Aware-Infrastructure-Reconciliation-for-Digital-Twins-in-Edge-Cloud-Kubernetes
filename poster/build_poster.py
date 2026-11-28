#!/usr/bin/env python3
"""Build Final_Poster.pdf (A0 portrait) from the result files in results/.

Every number, table and figure on the poster is computed here from results/*.csv (and the
constants/trace generator in src/phase1_experiment.py). Claims in the text are asserted against
the data, so the script fails instead of printing something the CSV files do not support.

Needs: numpy, pandas, matplotlib, segno (pip install segno) and Google Chrome / Chromium.
Run from the repository root, after run_all.sh:   python poster/build_poster.py
"""
import os, sys, math, shutil, subprocess, tempfile
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import segno

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
import phase1_experiment as P          # constants + trace generator (single source of truth)

REPO_URL = "https://github.com/AKA-5/Semantic-Freshness-Aware-Infrastructure-Reconciliation-for-Digital-Twins-in-Edge-Cloud-Kubernetes"
OUT_PDF = os.path.join(ROOT, "Final_Poster.pdf")
TRACE = dict(workload="default", seed=4, service=3, t_end=500)   # illustrative window of a real simulated trace

# ------------------------------------------------------------------ palette
NAVY, TEAL, ORANGE, SLATE, INK, MUTED = "#0B2A4A", "#0E9F8E", "#E8743B", "#6B7A90", "#14202E", "#51606F"
WLC = {"drift-heavy": "#4C6EF5", "default": "#9C36B5", "spiky": "#D9A400"}
WL = ["drift-heavy", "default", "spiky"]
PER, EVT, MAT = "Persistence (proposed)", "Event raw", "Periodic matched"

# ------------------------------------------------------------------ data
R = lambda f: pd.read_csv(os.path.join(ROOT, "results", f))
raw, st, ed, es, sens, win = R("final_raw.csv"), R("final_stats.csv"), R("edgesimpy_results.csv"), R("edgesimpy_stats.csv"), R("sensitivity.csv"), R("window_sweep.csv")
mT = pd.read_csv(os.path.join(ROOT, "results", "matched_T.csv"), index_col=0).iloc[:, 0]
r0 = lambda x: int(math.floor(x + 0.5))
rng = lambda v: f"{min(v)}–{max(v)}" if min(v) != max(v) else f"{min(v)}"
mean = lambda w, p, c: raw[(raw.workload == w) & (raw.policy == p)][c].mean()
std = lambda w, p, c: raw[(raw.workload == w) & (raw.policy == p)][c].std()
S_ = lambda w, vs, m, d: st[(st.workload == w) & (st.vs == vs) & (st.metric == m)].iloc[0][d]
E_ = lambda w, vs, m, d: es[(es.workload == w) & (es.vs == vs) & (es.metric == m)].iloc[0][d]
checks = []
def check(label, cond):
    checks.append((label, bool(cond)))
    if not cond: raise SystemExit(f"CLAIM NOT SUPPORTED BY DATA: {label}")

# headline numbers --------------------------------------------------------
gap_red = [r0(100 * (1 - mean(w, PER, "sustained_gap") / mean(w, MAT, "sustained_gap"))) for w in WL]
dly_red = [r0(100 * (1 - mean(w, PER, "delay") / mean(w, MAT, "delay"))) for w in WL]
rec_red = [r0(100 * (1 - mean(w, PER, "recs") / mean(w, EVT, "recs"))) for w in WL]
mg = ed.groupby(["workload", "policy"]).migrations.mean()
mig_red = [r0(100 * (1 - mg[(w, "persistence")] / mg[(w, "event")])) for w in WL]
slower = [r0(S_(w, EVT, "delay", "mean_diff")) for w in WL]
check("gap and delay vs matched periodic significant on all workloads",
      all(S_(w, MAT, m, "significant") and S_(w, MAT, m, "mean_diff") < 0 for w in WL for m in ("sustained_gap", "delay")))
check("persistence reconciliations vs matched periodic not significant (Phase 1)", not any(S_(w, MAT, "recs", "significant") for w in WL))
check("persistence slower than event-driven on all workloads", all(S_(w, EVT, "delay", "mean_diff") > 0 and S_(w, EVT, "delay", "significant") for w in WL))
gap_vs_evt = {w: (S_(w, EVT, "sustained_gap", "mean_diff"), bool(S_(w, EVT, "sustained_gap", "significant"))) for w in WL}
check("event-driven has smaller gap on drift-heavy and default, tie on spiky",
      gap_vs_evt["drift-heavy"][1] and gap_vs_evt["drift-heavy"][0] > 0 and gap_vs_evt["default"][1] and gap_vs_evt["default"][0] > 0 and not gap_vs_evt["spiky"][1])
# ablation
for w in WL:
    g = win[win.workload == w].groupby("window")[["sustained_gap", "delay"]].mean()
    check(f"window=1 best gap and delay ({w})", g.sustained_gap.idxmin() == 1 and g.delay.idxmin() == 1)
    check(f"persistence+MA worse than persistence ({w})", mean(w, "Persistence + MA (w=3)", "sustained_gap") > mean(w, PER, "sustained_gap") and mean(w, "Persistence + MA (w=3)", "delay") > mean(w, PER, "delay"))
# sensitivity
check("persistence beats matched periodic in all settings", (sens.gap_gain_pct > 0).all())
n_set = len(sens); sg_lo, sg_hi = r0(sens.gap_gain_pct.min()), r0(sens.gap_gain_pct.max())
c2_sp = sens[(sens.workload == "spiky") & (sens.c == 2)].gap_gain_pct
sp_len = P.WORKLOADS["spiky"][3]; min_ep = (2 - 1) * P.TELE + 1
check("c=2 on spiky is the weak case: episodes of min_ep ticks pass, spikes last longer", c2_sp.max() < 10 and sp_len >= min_ep)
check("c>=3 gains all >= 10%", sens[sens.c >= 3].gap_gain_pct.min() >= 9.5)
# Phase 2
check("Phase 2 migrations vs matched periodic never significant", not any(E_(w, "periodic_matched", "migrations", "significant") for w in WL))
check("Phase 2 gap lower than matched periodic, significant, all workloads", all(E_(w, "periodic_matched", "sustained_gap", "significant") and E_(w, "periodic_matched", "sustained_gap", "mean_diff") < 0 for w in WL))
gap2 = [abs(E_(w, "periodic_matched", "sustained_gap", "mean_diff")) for w in WL]
imb_p = [E_(w, "periodic_matched", "load_imbalance", "mean_diff") for w in WL]
imb_sig = sum(bool(E_(w, "periodic_matched", "load_imbalance", "significant")) for w in WL)
check("Phase 2 imbalance better than matched periodic on every workload", all(x < 0 for x in imb_p))
check("Phase 2 event-driven imbalance lower on spiky (significant)", E_("spiky", "event", "load_imbalance", "significant") and E_("spiky", "event", "load_imbalance", "mean_diff") > 0)
recs2 = [E_(w, "periodic_matched", "recs", "mean_diff") for w in WL]
check("Phase 2 persistence used more reconciliations than matched periodic", all(x > 0 for x in recs2))
aoi = (P.TELE - 1) / 2

# ------------------------------------------------------------------ figures
try:
    font_manager.findfont("Inter", fallback_to_default=False); FONT = "Inter"
except Exception:
    FONT = "DejaVu Sans"
plt.rcParams.update({"font.family": FONT, "svg.fonttype": "path", "font.size": 22, "axes.titlesize": 26, "axes.titleweight": "bold",
    "axes.labelsize": 22, "xtick.labelsize": 20, "ytick.labelsize": 20, "legend.fontsize": 21, "axes.spines.top": False,
    "axes.spines.right": False, "axes.edgecolor": "#8795A4", "axes.labelcolor": INK, "text.color": INK, "xtick.color": INK,
    "ytick.color": INK, "axes.grid": True, "grid.color": "#8795A4", "grid.alpha": .25, "axes.axisbelow": True})
px = lambda w, h: (w / 96, h / 96)
TMP = tempfile.mkdtemp(prefix="poster_")

def save(fig, name):
    fig.savefig(os.path.join(TMP, name), format="svg", bbox_inches=None); plt.close(fig)

# Fig 1: cost vs tracking, periodic frontier recomputed with the repo's own run()
def periodic_frontier(wl):
    data = [P.make_trace(s, *P.WORKLOADS[wl]) for s in range(P.N_SEEDS)]
    out = []
    for k in (10, 15, 20, 30, 40, 50, 75, 100):
        rs = [P.run(*d, "periodic", interval=k) for d in data]
        out.append((k, np.mean([r["recs"] for r in rs]), np.mean([r["sustained_gap"] for r in rs])))
    return out
front = {w: periodic_frontier(w) for w in WL}
for w in WL:   # frontier recomputation must agree with the committed Periodic T=50 rows
    k50 = [x for x in front[w] if x[0] == 50][0]
    check(f"frontier matches committed Periodic T=50 ({w})", abs(k50[1] - mean(w, "Periodic T=50", "recs")) < 1e-9 and abs(k50[2] - mean(w, "Periodic T=50", "sustained_gap")) < 1e-9)
fig, axs = plt.subplots(1, 3, figsize=px(1930, 480))
for ax, w in zip(axs, WL):
    f = front[w]; ax.plot([x[1] for x in f], [x[2] for x in f], "-", color="#B3BDC9", lw=5, zorder=1)
    for p, col, mk, sz in ((MAT, SLATE, "s", 700), (EVT, ORANGE, "^", 800), (PER, TEAL, "o", 1100)):
        ax.scatter(mean(w, p, "recs"), mean(w, p, "sustained_gap"), s=sz, c=col, marker=mk, edgecolor="white", linewidth=3, zorder=3)
    ax.set_title(w); ax.set_xlabel("Reconciliations (1000 ticks, 6 services)")
    ax.margins(x=.08, y=.12)
axs[0].set_ylabel("Sustained gap ↓")
h = [plt.Line2D([], [], color="#B3BDC9", lw=5), plt.Line2D([], [], color=SLATE, marker="s", ls="", ms=16), plt.Line2D([], [], color=ORANGE, marker="^", ls="", ms=18), plt.Line2D([], [], color=TEAL, marker="o", ls="", ms=20)]
fig.legend(h, ["Periodic, sweep of interval T", "Periodic matched to persistence", "Event-driven (raw)", "Persistence (proposed)"], loc="upper center", ncol=4, frameon=False, bbox_to_anchor=(.5, 1.02))
fig.tight_layout(rect=(0, 0, 1, .84)); save(fig, "fig1.svg")

# Fig 2: moving-average window
g = win.groupby(["workload", "window"])[["sustained_gap", "delay"]].mean().reset_index()
fig, axs = plt.subplots(2, 1, figsize=px(900, 640), sharex=True)
for ax, col, lab in zip(axs, ["sustained_gap", "delay"], ["Sustained gap ↓", "Delay (ticks) ↓"]):
    for w in WL:
        d = g[g.workload == w]; ax.plot(d.window, d[col], "-o", color=WLC[w], lw=4.5, ms=13, label=w)
    ax.set_ylabel(lab, fontsize=20); ax.margins(y=.15)
axs[1].set_xlabel("Moving-average window w  (1 = no smoothing)"); axs[1].set_xticks([1, 2, 3, 5, 8])
h, l = axs[0].get_legend_handles_labels(); fig.legend(h, l, loc="upper center", ncol=3, frameon=False, fontsize=19, bbox_to_anchor=(.5, 1.01))
fig.tight_layout(rect=(0, 0, 1, .92)); save(fig, "fig2.svg")

# Fig 3: EdgeSimPy
names = {"event": "Event-driven (raw)", "periodic_matched": "Periodic (matched)", "persistence": "Persistence"}
cols = {"event": ORANGE, "periodic_matched": SLATE, "persistence": TEAL}
fig, axs = plt.subplots(1, 3, figsize=px(1930, 380))
for ax, col, ttl in zip(axs, ["migrations", "sustained_gap", "load_imbalance"], ["Migrations per run", "Sustained gap", "Load imbalance"]):
    for k, p in enumerate(names):
        m = [ed[(ed.workload == w) & (ed.policy == p)][col] for w in WL]
        ax.bar(np.arange(3) + (k - 1) * .27, [x.mean() for x in m], .25, yerr=[x.std() for x in m], capsize=5, color=cols[p], error_kw=dict(lw=2, ecolor="#33414f"))
    ax.set_xticks(range(3)); ax.set_xticklabels(WL, fontsize=19); ax.set_title(ttl); ax.grid(axis="x", visible=False)
fig.legend([plt.Rectangle((0, 0), 1, 1, color=cols[p]) for p in names], list(names.values()), loc="upper center", ncol=3, frameon=False, bbox_to_anchor=(.5, 1.03))
fig.tight_layout(rect=(0, 0, 1, .82)); save(fig, "fig3.svg")

# Fig 4: one real simulated trace (illustrative window) -- validated against the repo's run()
def per_service(true_s, sust_s, kind, t_end):
    last, pend, ev, state = sust_s[0], 0, [], []
    for t in range(t_end):
        if t % P.TELE == 0:
            x = true_s[t]
            if kind == "event":
                if abs(x - last) > P.THR: ev.append(t); last = x
            else:
                pend = pend + 1 if abs(x - last) > P.THR else 0
                if pend >= P.CONF: ev.append(t); last = x; pend = 0
        state.append(last)
    return ev, np.array(state)
sust, true, jumps = P.make_trace(TRACE["seed"], *P.WORKLOADS[TRACE["workload"]])
for kind, name in (("event", "event"), ("persistence", "persistence")):   # same decisions as the repo's run()
    tot = sum(len(per_service(true[:, s], sust[:, s], kind, P.T)[0]) for s in range(P.S))
    check(f"trace logic equals repo run() for {name}", tot == P.run(sust, true, jumps, kind, window=1)["recs"])
s, te = TRACE["service"], TRACE["t_end"]
ev_e, _ = per_service(true[:, s], sust[:, s], "event", te); ev_p, st_p = per_service(true[:, s], sust[:, s], "persistence", te)
jmp = [t for ss, t, _ in jumps if ss == s and t < te]
fig, axs = plt.subplots(3, 1, figsize=px(900, 500), sharex=True, gridspec_kw=dict(height_ratios=[3, 1, 1], hspace=.1))
a = axs[0]; t = np.arange(te)
a.plot(t, true[:te, s], color="#9AA7B5", lw=2.2, label="telemetry")
a.step(t, st_p, where="post", color=TEAL, lw=5, label="persistence state")
for k, j in enumerate(jmp): a.axvline(j, color=NAVY, ls=(0, (4, 4)), lw=2.4, label="real shift" if k == 0 else None)
a.set_ylabel("Demand"); a.legend(loc="lower center", bbox_to_anchor=(.5, 1.0), frameon=False, fontsize=18, ncol=3, handlelength=1.6, columnspacing=1.2)
for ax, ev, col, lab in ((axs[1], ev_e, ORANGE, f"Event-driven: {len(ev_e)} updates"), (axs[2], ev_p, TEAL, f"Persistence: {len(ev_p)} updates")):
    ax.eventplot([ev], colors=col, lineoffsets=-.35, linelengths=.7, linewidths=5); ax.set_yticks([]); ax.grid(False)
    ax.set_ylim(-.8, .9); ax.text(.0, .97, lab, transform=ax.transAxes, ha="left", va="top", fontsize=19, fontweight="bold", color=col)
    ax.spines["left"].set_visible(False)
axs[2].set_xlabel("Tick"); axs[2].set_xlim(0, te)
save(fig, "fig4.svg"); n_ev, n_pe = len(ev_e), len(ev_p)

# ------------------------------------------------------------------ html pieces
def cls(p): return "hl" if p == PER else ""
def mini(w):
    rows = "".join(f'<tr class="{cls(p)}"><td>{n}</td><td>{mean(w,p,"recs"):.0f}</td><td>{mean(w,p,"false_recs"):.1f}</td><td>{mean(w,p,"sustained_gap"):.2f}</td><td>{mean(w,p,"delay"):.0f}</td></tr>'
                   for p, n in ((MAT, "Periodic"), (EVT, "Event-driven"), (PER, "Persistence")))
    return f'<div class="mini"><div class="mh" style="border-color:{WLC[w]}">{w}</div><table class="t"><tr><th></th><th>Recs</th><th>False</th><th>Gap</th><th>Delay</th></tr>{rows}</table></div>'
def sens_table():
    hdr = "".join(f'<th colspan="3" style="border-bottom:6px solid {WLC[w]}">{w}</th>' for w in WL)
    sub = "".join(f"<th>c={c}</th>" for _ in WL for c in (2, 3, 4))
    body = ""
    for th in sorted(sens.theta.unique()):
        cells = ""
        for w in WL:
            for c in (2, 3, 4):
                v = sens[(sens.workload == w) & (sens.theta == th) & (sens.c == c)].gap_gain_pct.iloc[0]
                a = min(v / 50, 1); bg = f"rgba(14,159,142,{.12 + .7 * a:.2f})"
                cells += f'<td style="background:{bg}">{r0(v)}</td>'
        body += f"<tr><th>θ={th}</th>{cells}</tr>"
    return f'<table class="t sens"><tr><th></th>{hdr}</tr><tr><th></th>{sub}</tr>{body}</table>'
wl_rows = "".join(f'<tr><td><b>{w}</b></td><td>{P.WORKLOADS[w][0]}</td><td>{P.WORKLOADS[w][1]}</td><td>{P.WORKLOADS[w][2]}</td><td>{P.WORKLOADS[w][3]}</td><td>{mT[w]}</td></tr>' for w in WL)
_q = segno.make(REPO_URL, error="m"); _w, _h = _q.symbol_size(border=1, scale=10)
qr = _q.svg_inline(dark=NAVY, border=1, scale=10).replace("<svg ", f'<svg viewBox="0 0 {_w} {_h}" ', 1)   # viewBox so CSS can scale it
svg = lambda n: f'<img src="{n}" style="width:100%;display:block">'
cmin = (P.CONF - 1) * P.TELE + 1; dlo, dhi = (P.CONF - 1) * P.TELE, P.CONF * P.TELE - 1

HTML = open(os.path.join(os.path.dirname(__file__), "poster_template.html"), encoding="utf-8").read()
subs = {
 "GAP": rng(gap_red), "DLY": rng(dly_red), "REC": rng(rec_red), "MIG": rng(mig_red), "SLOW": rng(slower),
 "THETA": f"{P.THR:g}", "C": P.CONF, "DELTA": P.TELE, "CMIN": cmin, "DLO": dlo, "DHI": dhi, "AOI": f"{aoi:g}", "NEED": f"{P.NEED:g}",
 "TICKS": P.T, "SERV": P.S, "SEEDS": P.N_SEEDS, "P2SEEDS": 10,
 "WLROWS": wl_rows, "MINIS": "".join(mini(w) for w in WL), "SENS": sens_table(),
 "NSET": n_set, "SGLO": sg_lo, "SGHI": sg_hi, "C2LO": r0(c2_sp.min()), "C2HI": r0(c2_sp.max()), "SPLEN": sp_len,
 "GAP2": f"{min(gap2):.1f}–{max(gap2):.1f}", "IMB": f"{min(abs(x) for x in imb_p):.1f}–{max(abs(x) for x in imb_p):.1f}", "IMBSIG": imb_sig,
 "IMBEVT": f"{E_('spiky','event','load_imbalance','mean_diff'):.1f}", "RECS2": f"{min(recs2):.0f}–{max(recs2):.0f}",
 "NEV": n_ev, "NPE": n_pe, "TSEED": TRACE["seed"], "TEND": TRACE["t_end"], "TWL": TRACE["workload"],
 "QR": qr, "URL": REPO_URL.replace("https://", ""),
 "FIG1": svg("fig1.svg"), "FIG2": svg("fig2.svg"), "FIG3": svg("fig3.svg"), "FIG4": svg("fig4.svg"),
}
for k, v in subs.items(): HTML = HTML.replace(f"%%{k}%%", str(v))
assert "%%" not in HTML, "unfilled placeholder in template"
html_path = os.path.join(TMP, "poster.html"); open(html_path, "w", encoding="utf-8").write(HTML)

# ------------------------------------------------------------------ render
chrome = next((c for c in ("google-chrome", "chromium", "chromium-browser", "chrome") if shutil.which(c)), None)
if not chrome: raise SystemExit("Chrome/Chromium not found")
tmp_pdf = os.path.join(TMP, "poster.pdf")
subprocess.run([chrome, "--headless=new", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={tmp_pdf}", "file://" + html_path],
               check=True, capture_output=True, timeout=300)
info = subprocess.run(["pdfinfo", tmp_pdf], capture_output=True, text=True).stdout
pages = int([l for l in info.splitlines() if l.startswith("Pages:")][0].split()[1])
check("poster is exactly one page (no overflow onto a second page)", pages == 1)
shutil.copy(tmp_pdf, OUT_PDF)
if os.environ.get("POSTER_KEEP_TMP"): print("kept:", TMP)
else: shutil.rmtree(TMP)
print(f"{len(checks)} data checks passed; wrote {OUT_PDF}")
