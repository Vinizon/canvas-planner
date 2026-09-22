#!/usr/bin/env python3
"""Gera a página HTML autocontida do cronograma a partir do JSON produzido por plan.py --json.

Uso:
    python3 plan.py --json data.json
    python3 generate_page.py data.json index.html
"""
import base64
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS_DIR = os.path.join(HERE, "assets", "fonts")

DIAS_SEMANA_PT = {
    0: "Segunda-feira", 1: "Terça-feira", 2: "Quarta-feira",
    3: "Quinta-feira", 4: "Sexta-feira", 5: "Sábado", 6: "Domingo",
}
DIAS_SEMANA_ABREV = {
    0: "SEG", 1: "TER", 2: "QUA", 3: "QUI", 4: "SEX", 5: "SÁB", 6: "DOM",
}

CATEGORY_HINTS = [
    ("aula", "aula"),
    ("trabalho", "trabalho"),
    ("almoço", "pausa"),
    ("jantar", "pausa"),
    ("café", "pausa"),
    ("acordar", "pausa"),
    ("atividade física", "exercicio"),
    ("leitura", "leitura"),
    ("estudo", "estudo"),
    ("livre", "livre"),
    ("dormir", "sono"),
]


def font_b64(filename):
    with open(os.path.join(FONTS_DIR, filename), "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


def fmt_minutes(m):
    m = int(round(m))
    h, mm = divmod(m, 60)
    if h and mm:
        return f"{h}h{mm:02d}"
    if h:
        return f"{h}h"
    return f"{mm}min"


def parse_date(s):
    return datetime.date.fromisoformat(s)


def parse_dt(s):
    return datetime.datetime.fromisoformat(s)


def fmt_date_long(d):
    return f"{DIAS_SEMANA_PT[d.weekday()]}, {d.strftime('%d/%m')}"


def esc(s):
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def build_css():
    fraunces = font_b64("fraunces600.woff2")
    plex400 = font_b64("plex400.woff2")
    plex600 = font_b64("plex600.woff2")

    return f"""
@font-face {{
  font-family: 'Fraunces';
  font-style: normal;
  font-weight: 600;
  font-display: swap;
  src: url(data:font/woff2;base64,{fraunces}) format('woff2');
}}
@font-face {{
  font-family: 'IBM Plex Sans';
  font-style: normal;
  font-weight: 400;
  font-display: swap;
  src: url(data:font/woff2;base64,{plex400}) format('woff2');
}}
@font-face {{
  font-family: 'IBM Plex Sans';
  font-style: normal;
  font-weight: 600;
  font-display: swap;
  src: url(data:font/woff2;base64,{plex600}) format('woff2');
}}

:root {{
  --bg: #F1F3F6;
  --surface: #FFFFFF;
  --surface-alt: #E7EBF0;
  --ink: #1A2333;
  --ink-muted: #5C6B7F;
  --ink-faint: #8996A7;
  --line: #D7DEE6;
  --accent: #2456A6;
  --accent-ink: #17356F;
  --accent-soft: #E1EAF8;
  --good: #2F7D5C;
  --good-soft: #E3F1EA;
  --warn: #966018;
  --warn-soft: #FBEEDA;
  --critical: #B23A3A;
  --critical-soft: #FBE7E5;
  --cat-aula: #6E7F98;
  --cat-trabalho: #8A94A3;
  --cat-pausa: #A69A8C;
  --cat-exercicio: #6E9C7C;
  --cat-leitura: #93809E;
  --cat-livre: #9AA3AF;
  --cat-sono: #AAB2BD;
  --shadow: 0 1px 2px rgba(20, 30, 50, 0.04), 0 8px 24px -12px rgba(20, 30, 50, 0.15);
  --radius: 14px;
}}

@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    --bg: #0F141C;
    --surface: #171E29;
    --surface-alt: #1E2733;
    --ink: #E7ECF3;
    --ink-muted: #9AA8BB;
    --ink-faint: #6C7A8D;
    --line: #2A3444;
    --accent: #7CA6E8;
    --accent-ink: #D6E4FA;
    --accent-soft: #21324D;
    --good: #66BE93;
    --good-soft: #1B3227;
    --warn: #E0A94A;
    --warn-soft: #3A2E16;
    --critical: #E48B85;
    --critical-soft: #3A2222;
    --cat-aula: #8493AC;
    --cat-trabalho: #8A94A3;
    --cat-pausa: #B0A392;
    --cat-exercicio: #7FBE94;
    --cat-leitura: #B39CC0;
    --cat-livre: #8B94A0;
    --cat-sono: #6C7684;
    --shadow: 0 1px 2px rgba(0,0,0,0.3), 0 8px 24px -12px rgba(0,0,0,0.5);
  }}
}}
:root[data-theme="dark"] {{
  --bg: #0F141C;
  --surface: #171E29;
  --surface-alt: #1E2733;
  --ink: #E7ECF3;
  --ink-muted: #9AA8BB;
  --ink-faint: #6C7A8D;
  --line: #2A3444;
  --accent: #7CA6E8;
  --accent-ink: #D6E4FA;
  --accent-soft: #21324D;
  --good: #66BE93;
  --good-soft: #1B3227;
  --warn: #E0A94A;
  --warn-soft: #3A2E16;
  --critical: #E48B85;
  --critical-soft: #3A2222;
  --cat-aula: #8493AC;
  --cat-trabalho: #8A94A3;
  --cat-pausa: #B0A392;
  --cat-exercicio: #7FBE94;
  --cat-leitura: #B39CC0;
  --cat-livre: #8B94A0;
  --cat-sono: #6C7684;
  --shadow: 0 1px 2px rgba(0,0,0,0.3), 0 8px 24px -12px rgba(0,0,0,0.5);
}}

* {{ box-sizing: border-box; }}
html {{ color-scheme: light dark; }}
body {{
  margin: 0;
  background: var(--bg);
  color: var(--ink);
  font-family: 'IBM Plex Sans', system-ui, sans-serif;
  font-size: 16px;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
}}
.wrap {{
  max-width: 840px;
  margin: 0 auto;
  padding: 32px 20px 80px;
  display: flex;
  flex-direction: column;
  gap: 28px;
}}

header.page {{
  display: flex;
  flex-direction: column;
  gap: 4px;
}}
.eyebrow {{
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--accent);
}}
h1.title {{
  font-family: 'Fraunces', Georgia, serif;
  font-weight: 600;
  font-size: clamp(1.7rem, 4vw, 2.3rem);
  margin: 0;
  text-wrap: balance;
  color: var(--ink);
}}
.updated {{
  font-size: 0.82rem;
  color: var(--ink-faint);
}}

.stat-row {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}}
.stat-tile {{
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  box-shadow: var(--shadow);
}}
.stat-tile .label {{
  font-size: 0.74rem;
  color: var(--ink-faint);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-weight: 600;
}}
.stat-tile .value {{
  font-family: 'Fraunces', Georgia, serif;
  font-size: 1.5rem;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}}
.stat-tile .sub {{
  font-size: 0.8rem;
  color: var(--ink-muted);
}}
.stat-tile.pill-good .value {{ color: var(--good); }}
.stat-tile.pill-warn .value {{ color: var(--warn); }}
.stat-tile.pill-critical .value {{ color: var(--critical); }}

.card {{
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 22px;
}}
.card h2 {{
  font-family: 'Fraunces', Georgia, serif;
  font-size: 1.25rem;
  font-weight: 600;
  margin: 0 0 4px;
}}
.card .card-sub {{
  font-size: 0.85rem;
  color: var(--ink-muted);
  margin: 0 0 16px;
}}

.capacity-bar {{
  height: 8px;
  border-radius: 99px;
  background: var(--surface-alt);
  overflow: hidden;
  margin: 12px 0 4px;
}}
.capacity-bar > div {{
  height: 100%;
  border-radius: 99px;
  background: var(--accent);
  transition: width 0.4s ease;
}}
.capacity-bar.over > div {{ background: var(--critical); }}
.capacity-label {{
  font-size: 0.78rem;
  color: var(--ink-faint);
  font-variant-numeric: tabular-nums;
}}

.badge {{
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 0.72rem;
  font-weight: 600;
  padding: 3px 9px;
  border-radius: 99px;
  letter-spacing: 0.02em;
}}
.badge.ok {{ background: var(--good-soft); color: var(--good); }}
.badge.warn {{ background: var(--warn-soft); color: var(--warn); }}
.badge.critical {{ background: var(--critical-soft); color: var(--critical); }}
.badge.accent {{ background: var(--accent-soft); color: var(--accent-ink); }}

.task-row {{
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 11px 0;
  border-top: 1px solid var(--line);
}}
.task-row:first-of-type {{ border-top: none; }}
.task-row .minutes {{
  flex: 0 0 auto;
  min-width: 58px;
  font-variant-numeric: tabular-nums;
  font-weight: 600;
  color: var(--accent-ink);
  background: var(--accent-soft);
  border-radius: 8px;
  padding: 3px 8px;
  font-size: 0.85rem;
  text-align: center;
}}
.task-row .info {{ flex: 1; min-width: 0; }}
.task-row .info .name {{ font-weight: 600; font-size: 0.95rem; }}
.task-row .info .meta {{
  font-size: 0.8rem;
  color: var(--ink-muted);
  margin-top: 2px;
}}
.task-row .shortfall {{
  font-size: 0.78rem;
  color: var(--critical);
  margin-top: 4px;
}}
.task-row .desc {{
  font-size: 0.83rem;
  color: var(--ink-muted);
  margin-top: 5px;
  line-height: 1.45;
}}
.task-row .links {{
  margin-top: 6px;
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}}
.task-row .links a {{
  font-size: 0.8rem;
  color: var(--accent);
  font-weight: 600;
  text-decoration: none;
}}
.task-row .links a:hover {{ text-decoration: underline; }}
.task-row .submission-tag {{
  font-size: 0.74rem;
  color: var(--ink-faint);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}}
.task-row.empty {{
  color: var(--ink-muted);
  font-size: 0.9rem;
  padding: 4px 0;
}}
.task-row .task-check {{
  flex: 0 0 auto;
  width: 19px;
  height: 19px;
  margin-top: 2px;
  accent-color: var(--accent);
  cursor: pointer;
}}
.task-row.done .info .name {{
  text-decoration: line-through;
  color: var(--ink-faint);
}}
.task-row.done {{ opacity: 0.6; }}
.task-row.done .minutes {{
  background: var(--surface-alt);
  color: var(--ink-faint);
}}

.timeline {{
  display: flex;
  flex-direction: column;
  margin-top: 4px;
}}
.timeline .row {{
  display: grid;
  grid-template-columns: 74px 14px 1fr;
  gap: 0 12px;
  align-items: stretch;
  min-height: 34px;
}}
.timeline .time {{
  font-size: 0.76rem;
  color: var(--ink-faint);
  font-variant-numeric: tabular-nums;
  padding-top: 8px;
  text-align: right;
}}
.timeline .rail {{
  position: relative;
  display: flex;
  justify-content: center;
}}
.timeline .rail::before {{
  content: "";
  position: absolute;
  top: 0;
  bottom: 0;
  width: 2px;
  background: var(--line);
}}
.timeline .dot {{
  width: 9px;
  height: 9px;
  border-radius: 50%;
  margin-top: 9px;
  z-index: 1;
  background: var(--cat-color, var(--ink-faint));
}}
.timeline .content {{
  padding: 6px 0 14px;
  font-size: 0.88rem;
  color: var(--ink-muted);
}}
.timeline .row.focus .content {{
  background: var(--accent-soft);
  color: var(--accent-ink);
  font-weight: 600;
  border-radius: 8px;
  padding: 8px 10px;
  margin: 2px 0 12px;
}}
.timeline .row.focus .time {{ color: var(--accent-ink); font-weight: 600; }}

table.pacing {{
  border-collapse: collapse;
  width: 100%;
  font-size: 0.88rem;
}}
table.pacing th {{
  text-align: left;
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--ink-faint);
  font-weight: 600;
  padding: 0 10px 8px 0;
  border-bottom: 1px solid var(--line);
}}
table.pacing td {{
  padding: 10px 10px 10px 0;
  border-bottom: 1px solid var(--line);
  vertical-align: top;
}}
table.pacing tr:last-child td {{ border-bottom: none; }}
table.pacing .pace {{ font-variant-numeric: tabular-nums; font-weight: 600; }}
table.pacing a.link {{ color: var(--accent); text-decoration: none; font-weight: 600; font-size: 0.82rem; white-space: nowrap; }}
table.pacing a.link:hover {{ text-decoration: underline; }}
.table-scroll {{ overflow-x: auto; }}

.day-list {{
  display: flex;
  flex-direction: column;
  gap: 8px;
}}
details.day-row {{
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--surface-alt);
  overflow: hidden;
}}
details.day-row > summary,
details.file-row > summary {{
  list-style: none;
  cursor: pointer;
  padding: 12px 16px;
  display: flex;
  align-items: baseline;
  gap: 12px;
}}
details.day-row > summary::-webkit-details-marker,
details.file-row > summary::-webkit-details-marker {{ display: none; }}
details.day-row .dow {{
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.05em;
  color: var(--ink-faint);
  flex: 0 0 auto;
}}
details.day-row .date,
details.file-row .course {{
  font-family: 'Fraunces', Georgia, serif;
  font-weight: 600;
  font-size: 1.05rem;
  flex: 0 0 auto;
}}
details.day-row .total,
details.file-row .count {{
  font-size: 0.82rem;
  color: var(--ink-muted);
  font-variant-numeric: tabular-nums;
  flex: 1;
  text-align: right;
}}
details.day-row .detail,
details.file-row .detail {{
  padding: 4px 16px 14px;
  display: flex;
  flex-direction: column;
  border-top: 1px solid var(--line);
  background: var(--surface);
}}
details.day-row[open] > summary,
details.file-row[open] > summary {{ background: var(--surface); border-bottom: 1px solid var(--line); }}

@media (max-width: 480px) {{
  details.day-row > summary {{ flex-wrap: wrap; }}
  details.day-row .total {{ flex-basis: 100%; text-align: left; }}
}}

.later-list {{
  display: flex;
  flex-direction: column;
  gap: 2px;
}}
.later-item {{
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 0;
  border-top: 1px solid var(--line);
  font-size: 0.86rem;
  color: var(--ink-muted);
}}
.later-item:first-child {{ border-top: none; }}
.later-item .date {{ flex: 0 0 auto; font-variant-numeric: tabular-nums; color: var(--ink-faint); }}
.later-item .name {{ flex: 1; color: var(--ink); }}

.simple-row {{
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 14px;
  padding: 10px 0;
  border-top: 1px solid var(--line);
  font-size: 0.88rem;
}}
.simple-row:first-child {{ border-top: none; }}
.simple-row .left {{ display: flex; flex-direction: column; gap: 2px; min-width: 0; flex: 1; }}
.simple-row .left .title {{ color: var(--ink); font-weight: 600; display: flex; align-items: center; gap: 7px; }}
.simple-row .left .meta {{ color: var(--ink-faint); font-size: 0.78rem; }}
.simple-row .right {{
  flex: 0 0 auto;
  text-align: right;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
}}
.simple-row .right .score {{
  font-family: 'Fraunces', Georgia, serif;
  font-weight: 600;
  font-size: 1.05rem;
  color: var(--accent-ink);
  font-variant-numeric: tabular-nums;
}}
.simple-row .right .score.empty {{ font-family: 'IBM Plex Sans', sans-serif; font-weight: 400; font-size: 0.82rem; color: var(--ink-faint); }}
.simple-row a.link {{ color: var(--accent); text-decoration: none; font-weight: 600; font-size: 0.82rem; white-space: nowrap; }}
.simple-row a.link:hover {{ text-decoration: underline; }}
.unread-dot {{
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--accent);
  flex: 0 0 auto;
  display: inline-block;
}}
.file-list {{
  display: flex;
  flex-direction: column;
  gap: 8px;
}}
details.file-row .detail .simple-row {{ font-size: 0.85rem; padding: 8px 0; }}
details.file-row .detail .simple-row .meta {{ font-size: 0.74rem; }}

footer.page {{
  font-size: 0.78rem;
  color: var(--ink-faint);
  text-align: center;
  padding-top: 8px;
}}

@media (prefers-reduced-motion: reduce) {{
  * {{ transition: none !important; animation: none !important; }}
}}

@media (max-width: 480px) {{
  .timeline .row {{ grid-template-columns: 58px 14px 1fr; }}
}}
"""


def category_for(label):
    low = label.lower()
    for hint, cat in CATEGORY_HINTS:
        if hint in low:
            return cat
    return "livre"


def render_timeline(blocks):
    rows = []
    for b in blocks:
        cat = category_for(b["label"])
        is_focus = cat == "estudo"
        row_class = "row focus" if is_focus else "row"
        rows.append(
            f'<div class="{row_class}">'
            f'<div class="time">{esc(b["start"])}</div>'
            f'<div class="rail"><div class="dot" style="--cat-color: var(--cat-{cat})"></div></div>'
            f'<div class="content">{esc(b["label"])}'
            + (f' <span class="badge accent">{fmt_minutes(b["minutes"])}</span>' if b.get("minutes") else "")
            + "</div></div>"
        )
    return f'<div class="timeline">{"".join(rows)}</div>'


def render_task_row(t, minutes_label, shortfall_html=""):
    due_dt = parse_dt(t["due_at"])
    desc_html = f'<div class="desc">{esc(t["description_text"])}</div>' if t.get("description_text") else ""
    links = []
    if t.get("submission_label"):
        links.append(f'<span class="submission-tag">{esc(t["submission_label"])}</span>')
    if t.get("html_url"):
        links.append(f'<a href="{esc(t["html_url"])}" target="_blank" rel="noopener">Abrir no Canvas →</a>')
    links_html = f'<div class="links">{"".join(links)}</div>' if links else ""
    task_id = esc(t.get("id", ""))
    checkbox_html = (
        f'<input type="checkbox" class="task-check" data-task-id="{task_id}" '
        f'aria-label="Marcar {esc(t["title"])} como feito">'
        if task_id else ""
    )
    return (
        f'<div class="task-row">'
        f"{checkbox_html}"
        f'<div class="minutes">{minutes_label}</div>'
        f'<div class="info">'
        f'<div class="name">{esc(t["title"])}</div>'
        f'<div class="meta">{esc(t["course_name"])} · entrega {due_dt.strftime("%d/%m %H:%M")}</div>'
        f"{desc_html}{links_html}{shortfall_html}"
        "</div></div>"
    )


def render_today_card(day, config):
    date = parse_date(day["date"])
    weekday_name = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"][date.weekday()]
    day_type = config["week"][weekday_name]["type"]
    blocks = config["day_templates"][day_type]["blocks"]

    cap = day["mandatory_capacity"]
    used = sum(a["minutes"] for a in day["allocations"])
    pct = min(100, round(100 * used / cap)) if cap else 0
    over = day["overloaded"]

    rows = []
    if not day["allocations"]:
        rows.append('<div class="task-row empty">Nenhuma entrega pendente exige tempo hoje — aproveite pra adiantar leitura ou revisar algo por conta própria.</div>')
    else:
        for a in day["allocations"]:
            t = a["task"]
            shortfall_html = ""
            if a["shortfall"] > 0:
                shortfall_html = f'<div class="shortfall">faltou encaixar {fmt_minutes(a["shortfall"])} hoje — vai precisar compensar em outro dia</div>'
            rows.append(render_task_row(t, fmt_minutes(a["minutes"]), shortfall_html))

    bar_class = "capacity-bar over" if over else "capacity-bar"
    status_badge = '<span class="badge critical">sobrecarregado</span>' if over else '<span class="badge ok">no ritmo</span>'

    return f"""
<section class="card">
  <h2>Hoje — {esc(fmt_date_long(date))}</h2>
  <p class="card-sub">{esc(day["label"])} {status_badge}</p>
  <div class="{bar_class}"><div style="width:{pct}%"></div></div>
  <p class="capacity-label">{fmt_minutes(used)} planejados de {fmt_minutes(cap)} disponíveis para estudo</p>
  <div style="margin-top:18px">
    {"".join(rows)}
  </div>
  <div style="margin-top:22px">
    {render_timeline(blocks)}
  </div>
</section>
"""


def render_pacing_card(pacing):
    if not pacing:
        return """
<section class="card">
  <h2>Ritmo por atividade</h2>
  <p class="card-sub">Nenhuma entrega pendente nos próximos 21 dias. 🎉</p>
</section>
"""
    rows = []
    for p in pacing:
        t = p["task"]
        due_dt = parse_dt(t["due_at"])
        badge = f'<span class="badge critical">{p["days_left"]}d</span>' if p["urgent"] else f'<span class="badge accent">{p["days_left"]}d</span>'
        link_cell = f'<a class="link" href="{esc(t["html_url"])}" target="_blank" rel="noopener">Abrir →</a>' if t.get("html_url") else ""
        rows.append(
            "<tr>"
            f"<td><strong>{esc(t['title'])}</strong><br><span style='color:var(--ink-faint);font-size:0.82rem'>{esc(t['course_name'])}</span></td>"
            f"<td>{esc(t['category'])}</td>"
            f"<td>{due_dt.strftime('%d/%m %H:%M')}</td>"
            f"<td>{badge}</td>"
            f"<td class='pace'>{fmt_minutes(p['daily_pace_minutes'])}/dia</td>"
            f"<td>{link_cell}</td>"
            "</tr>"
        )
    return f"""
<section class="card">
  <h2>Ritmo por atividade</h2>
  <p class="card-sub">Recalculado hoje — minutos por dia para terminar com 1 dia de folga antes do prazo.</p>
  <div class="table-scroll">
  <table class="pacing">
    <thead><tr><th>Atividade</th><th>Categoria</th><th>Entrega</th><th>Dias</th><th>Ritmo</th><th></th></tr></thead>
    <tbody>{"".join(rows)}</tbody>
  </table>
  </div>
</section>
"""


def render_week_card(daily_plan):
    days = daily_plan[1:]
    if not days:
        return ""
    rows = []
    for day in days:
        date = parse_date(day["date"])
        used = sum(a["minutes"] for a in day["allocations"])
        total_label = f"{fmt_minutes(used)} de estudo" if used else "livre de faculdade"
        over_badge = ' <span class="badge critical">alerta</span>' if day["overloaded"] else ""
        if day["allocations"]:
            detail_rows = "".join(
                render_task_row(a["task"], fmt_minutes(a["minutes"]))
                for a in day["allocations"]
            )
        else:
            detail_rows = '<div class="task-row empty">Sem entregas alocadas.</div>'
        rows.append(f"""
<details class="day-row">
  <summary>
    <span class="dow">{DIAS_SEMANA_ABREV[date.weekday()]}</span>
    <span class="date">{date.strftime('%d/%m')}</span>
    <span class="total">{total_label}{over_badge}</span>
  </summary>
  <div class="detail">{detail_rows}</div>
</details>
""")
    return f"""
<section class="card">
  <h2>Próximos dias</h2>
  <p class="card-sub">Toque num dia pra ver o detalhe.</p>
  <div class="day-list">{"".join(rows)}</div>
</section>
"""


def render_announcements_card(announcements):
    if not announcements:
        return ""
    rows = []
    for a in announcements:
        posted = parse_dt(a["posted_at"])
        dot = '<span class="unread-dot"></span>' if a["unread"] else ""
        link = f'<a class="link" href="{esc(a["html_url"])}" target="_blank" rel="noopener">Abrir →</a>' if a.get("html_url") else ""
        rows.append(f"""
<div class="simple-row">
  <div class="left">
    <div class="title">{dot}{esc(a["title"])}</div>
    <div class="meta">{esc(a["course_name"])} · {posted.strftime('%d/%m %H:%M')}</div>
  </div>
  <div class="right">{link}</div>
</div>
""")
    return f"""
<section class="card">
  <h2>Avisos recentes</h2>
  <p class="card-sub">Comunicados e avisos postados nos últimos dias.</p>
  {"".join(rows)}
</section>
"""


def render_files_card(recent_files):
    if not recent_files:
        return ""
    groups = []
    for c in recent_files:
        rows = []
        for f in c["files"]:
            updated = parse_dt(f["updated_at"])
            rows.append(f"""
<div class="simple-row">
  <div class="left">
    <div class="title">{esc(f["name"])}</div>
    <div class="meta">atualizado {updated.strftime('%d/%m')} · {f["size_kb"]} KB</div>
  </div>
  <div class="right"><a class="link" href="{esc(f["url"])}" target="_blank" rel="noopener">Abrir →</a></div>
</div>
""")
        n = len(c["files"])
        plural = "arquivo" if n == 1 else "arquivos"
        groups.append(f"""
<details class="file-row">
  <summary>
    <span class="course">{esc(c["course_name"])}</span>
    <span class="count">{n} {plural}</span>
  </summary>
  <div class="detail">{"".join(rows)}</div>
</details>
""")
    return f"""
<section class="card">
  <h2>Materiais recentes</h2>
  <p class="card-sub">Arquivos atualizados nas últimas duas semanas — sem resumo automático. Toque numa matéria pra ver.</p>
  <div class="file-list">{"".join(groups)}</div>
</section>
"""


def render_grades_card(grades):
    if not grades or all(g["score"] is None for g in grades):
        return ""
    rows = []
    for g in grades:
        if g["score"] is None:
            score_html = '<span class="score empty">sem nota ainda</span>'
        else:
            score_html = f'<span class="score">{g["score"]:.0f}%</span>'
        rows.append(f"""
<div class="simple-row">
  <div class="left"><div class="title">{esc(g["course_name"])}</div></div>
  <div class="right">{score_html}</div>
</div>
""")
    return f"""
<section class="card">
  <h2>Notas</h2>
  <p class="card-sub">Conforme lançado no Canvas — nota atual (só considera o que já foi corrigido).</p>
  {"".join(rows)}
</section>
"""


def render_later_card(later_tasks):
    if not later_tasks:
        return ""
    items = []
    for t in later_tasks:
        due_dt = parse_dt(t["due_at"])
        items.append(
            f'<div class="later-item"><span class="date">{due_dt.strftime("%d/%m")}</span>'
            f'<span class="name">{esc(t["title"])} · {esc(t["course_name"])}</span></div>'
        )
    return f"""
<section class="card">
  <h2>Mais pra frente</h2>
  <p class="card-sub">Fora da janela de 3 semanas — entram no ritmo diário automaticamente quando chegar a hora.</p>
  <div class="later-list">{"".join(items)}</div>
</section>
"""


def render_stats(data, config):
    today_plan = data["daily_plan"][0]
    used = sum(a["minutes"] for a in today_plan["allocations"])
    cap = today_plan["mandatory_capacity"]
    tile_class = "pill-critical" if today_plan["overloaded"] else "pill-good"

    urgent = next((p for p in data["pacing"] if p["urgent"]), None)
    if urgent is None and data["pacing"]:
        urgent = min(data["pacing"], key=lambda p: p["days_left"])
    if urgent:
        urgent_value = f'{urgent["days_left"]}d'
        urgent_sub = esc(urgent["task"]["title"][:40])
        urgent_class = "pill-critical" if urgent["urgent"] else ""
    else:
        urgent_value = "—"
        urgent_sub = "nada urgente"
        urgent_class = "pill-good"

    window_count = len(data["pacing"])

    return f"""
<div class="stat-row">
  <div class="stat-tile {tile_class}">
    <span class="label">Bloco de hoje</span>
    <span class="value">{fmt_minutes(used)} / {fmt_minutes(cap)}</span>
    <span class="sub">{"sobrecarregado" if today_plan["overloaded"] else "dentro do plano"}</span>
  </div>
  <div class="stat-tile {urgent_class}">
    <span class="label">Prazo mais apertado</span>
    <span class="value">{urgent_value}</span>
    <span class="sub">{urgent_sub}</span>
  </div>
  <div class="stat-tile">
    <span class="label">Entregas ativas</span>
    <span class="value">{window_count}</span>
    <span class="sub">nas próximas 3 semanas</span>
  </div>
</div>
"""


def render_page(data, config):
    today = parse_date(data["today"])
    now_str = datetime.datetime.now().strftime("%d/%m %H:%M")
    css = build_css()

    body = "\n".join([
        render_announcements_card(data.get("announcements", [])),
        render_stats(data, config),
        render_today_card(data["daily_plan"][0], config),
        render_pacing_card(data["pacing"]),
        render_files_card(data.get("recent_files", [])),
        render_week_card(data["daily_plan"]),
        render_grades_card(data.get("grades", [])),
        render_later_card(data["later_tasks"]),
    ])

    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Cronograma PUC</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>{css}</style>
</head>
<body>
<div class="wrap">
  <header class="page">
    <span class="eyebrow">PUC Minas · Ciência de Dados e IA</span>
    <h1 class="title">{esc(fmt_date_long(today))}</h1>
    <span class="updated">Atualizado em {now_str} · dados do Canvas</span>
  </header>
  {body}
  <footer class="page">Gerado automaticamente a partir do Canvas (pucminas.instructure.com). Ritmo recalculado a cada atualização.</footer>
</div>
<script>
(function () {{
  var KEY = "canvas-planner-done-v1";
  function loadDone() {{
    try {{ return new Set(JSON.parse(localStorage.getItem(KEY) || "[]")); }}
    catch (e) {{ return new Set(); }}
  }}
  function saveDone(set) {{
    try {{ localStorage.setItem(KEY, JSON.stringify(Array.from(set))); }}
    catch (e) {{ /* storage unavailable (private mode, quota, sandboxed preview) — keep working in-memory */ }}
  }}
  var done = loadDone();
  function applyState(cb) {{
    var row = cb.closest(".task-row");
    if (row) row.classList.toggle("done", cb.checked);
  }}
  var boxes = document.querySelectorAll(".task-check");
  boxes.forEach(function (cb) {{
    var id = cb.dataset.taskId;
    if (done.has(id)) cb.checked = true;
    applyState(cb);
    cb.addEventListener("change", function () {{
      if (cb.checked) done.add(id); else done.delete(id);
      document.querySelectorAll('.task-check[data-task-id="' + CSS.escape(id) + '"]').forEach(function (other) {{
        other.checked = cb.checked;
        applyState(other);
      }});
      saveDone(done);
    }});
  }});
}})();
</script>
</body>
</html>
"""


def main():
    if len(sys.argv) < 3:
        sys.exit("uso: generate_page.py <data.json> <saida.html> [config.json]")
    data_path, out_path = sys.argv[1], sys.argv[2]
    config_path = sys.argv[3] if len(sys.argv) > 3 else os.path.join(HERE, "config.json")

    with open(data_path, encoding="utf-8") as f:
        data = json.load(f)
    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)

    html = render_page(data, config)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"gerado: {out_path} ({len(html)} bytes)")


if __name__ == "__main__":
    main()
