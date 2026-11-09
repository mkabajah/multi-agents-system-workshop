"""
VIEWER · turns one run's events into a self-contained HTML page you open in a browser.

    runs/<pattern>-<time>.html     one file per run (nothing to install, works offline)
    runs/latest.html               the last run, always at the same path

The page is a "swimlane" diagram: one column per agent, time flows down. Each event is a card in the
column of the agent that did it, so you SEE who worked, who delegated to whom, and in what order.
Press ▶ Replay (or the → key) to watch the run step by step, the way you'd explain it in class.
"""
import datetime as dt
import html
import json

from lab.config import ROOT

RUNS = ROOT / "runs"
LANE_COLORS = {"code": "#64748b", "lead": "#8b5cf6", "agent": "#8b5cf6", "router": "#d97706", "sourcer": "#2563eb",
               "screener": "#0891b2", "coordinator": "#dc2626", "writer": "#16a34a", "critic": "#ca8a04"}
KIND_LABEL = {"start": "starts", "think": "model call", "tool": "tool", "result": "result",
              "delegate": "delegates", "answer": "answer", "note": "note"}


def save(rec, pattern_id: str, meta: dict, question: str, answer: str, seconds: float) -> str:
    """Write the HTML page for this run and return its path."""
    RUNS.mkdir(exist_ok=True)
    lanes = rec.agents(with_code=True)       # the first lane is 'code': your Python orchestration
    data = {
        "pattern": f"{pattern_id} · {meta['name']}", "question": question, "answer": answer,
        "lanes": [{"name": a, "color": LANE_COLORS.get(a.split("-")[0], "#64748b")} for a in lanes],
        "events": [{"t": e.t, "lane": lanes.index(e.agent) if e.agent in lanes else 0, "kind": e.kind,
                    "label": KIND_LABEL[e.kind], "text": e.text} for e in rec.events],
        "stats": {"agents": len(rec.agents()), "model calls": rec.model_calls, "tool calls": rec.tool_calls,
                  "seconds": round(seconds, 1), "tokens": rec.tokens or "n/a (fake model)"},
    }
    page = TEMPLATE.replace("__TITLE__", html.escape(data["pattern"])).replace("__DATA__", json.dumps(data).replace("</", "<\\/"))
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    path = RUNS / f"{pattern_id}-{stamp}.html"
    path.write_text(page, encoding="utf-8")
    (RUNS / "latest.html").write_text(page, encoding="utf-8")
    return str(path.relative_to(ROOT))


TEMPLATE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>__TITLE__</title>
<style>
:root{--bg:#f7f7f5;--card:#fff;--ink:#1c1c1c;--mute:#6b6b6b;--line:#e3e3df}
@media (prefers-color-scheme:dark){:root{--bg:#161616;--card:#212121;--ink:#ececec;--mute:#9a9a9a;--line:#333}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 system-ui,-apple-system,Segoe UI,sans-serif}
header{padding:24px 24px 8px;max-width:1500px;margin:auto}h1{margin:0 0 6px;font-size:24px}
.q{color:var(--mute)}.stats{display:flex;gap:10px;flex-wrap:wrap;margin:14px 0}
.stat{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:8px 14px}
.stat b{display:block;font-size:20px}.stat span{color:var(--mute);font-size:12px;text-transform:uppercase;letter-spacing:.04em}
.bar{display:flex;gap:8px;align-items:center;margin:10px 0}button{font:inherit;border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:8px;padding:6px 14px;cursor:pointer}
.wrap{overflow-x:auto;padding:0 24px 24px;max-width:1500px;margin:auto}
.grid{display:grid;gap:0 10px}
.lane{position:sticky;top:0;z-index:2;background:var(--bg);padding:10px 0 8px;font-weight:700;text-align:center;border-bottom:3px solid}
.cell{padding:3px 0;min-width:0;overflow-wrap:anywhere}
.ev{background:var(--card);border:1px solid var(--line);border-left:4px solid;border-radius:8px;padding:6px 10px;font-size:13px;transition:opacity .25s,transform .25s}
.ev .k{font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:var(--mute)}.ev .t{float:right;font-size:11px;color:var(--mute)}
.ev.delegate{background:color-mix(in srgb,var(--c) 12%,var(--card))}.ev.answer{border-width:1px 1px 1px 4px;font-weight:600}
.ev.note{border-style:dashed}.ev.think{opacity:.6;padding:1px 10px}.ev.think .k{display:inline}.hidden{opacity:0;transform:translateY(-4px);pointer-events:none}
.ans{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px;margin:10px 0}
</style></head><body>
<header><h1 id="h"></h1><div class="q" id="q"></div><div class="stats" id="s"></div>
<div class="bar"><button id="replay">▶ Replay</button><button id="next">Next step →</button><button id="all">Show all</button><span class="q" id="pos"></span></div></header>
<div class="wrap"><div class="grid" id="g"></div><h3>Final answer</h3><div class="ans" id="a"></div></div>
<script>
const D=__DATA__, g=document.getElementById('g'), cards=[];
const esc=s=>String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
document.getElementById('h').textContent=D.pattern;document.getElementById('q').textContent='Question: '+D.question;
document.getElementById('a').textContent=D.answer;
document.getElementById('s').innerHTML=Object.entries(D.stats).map(([k,v])=>`<div class="stat"><b>${esc(v)}</b><span>${esc(k)}</span></div>`).join('');
g.style.gridTemplateColumns=`repeat(${D.lanes.length},minmax(0,1fr))`;g.style.minWidth=(D.lanes.length*175)+'px';
D.lanes.forEach(l=>{const d=document.createElement('div');d.className='lane';d.style.borderColor=l.color;d.style.color=l.color;d.textContent=l.name;g.appendChild(d)});
D.events.forEach((e,i)=>{const l=D.lanes[e.lane];
  for(let c=0;c<D.lanes.length;c++){const cell=document.createElement('div');cell.className='cell';cell.style.gridRow=i+2;cell.style.gridColumn=c+1;
    if(c===e.lane){const v=document.createElement('div');v.className='ev '+e.kind;v.style.borderLeftColor=l.color;v.style.setProperty('--c',l.color);
      v.innerHTML=e.kind==='think'?`<span class="t">${e.t}s</span><span class="k">· model call</span>`:`<span class="t">${e.t}s</span><div class="k">${esc(e.label)}</div>${esc(e.text.length>220?e.text.slice(0,217)+'…':e.text)}`;v.title=e.text;cell.appendChild(v);cards.push(v)}
    g.appendChild(cell)}});
let n=cards.length,timer;const pos=document.getElementById('pos');
const show=(k,scroll=true)=>{n=k;cards.forEach((c,i)=>c.classList.toggle('hidden',i>=k));pos.textContent=`step ${k} / ${cards.length}`;if(scroll&&k>0)cards[k-1].scrollIntoView({block:'nearest',behavior:'smooth'})};
const step=()=>{if(n<cards.length)show(n+1);else clearInterval(timer)};
document.getElementById('replay').onclick=()=>{clearInterval(timer);show(0);timer=setInterval(step,700)};
document.getElementById('next').onclick=()=>{clearInterval(timer);if(n>=cards.length)show(0);step()};
document.getElementById('all').onclick=()=>{clearInterval(timer);show(cards.length)};
document.addEventListener('keydown',e=>{if(e.key==='ArrowRight')document.getElementById('next').click()});
show(cards.length,false);   // on load: everything visible, page at the top
</script></body></html>"""
