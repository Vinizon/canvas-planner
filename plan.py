#!/usr/bin/env python3
"""Gera o cronograma diário/semanal de estudos a partir do Canvas.

Uso:
    python3 plan.py                 # plano de hoje + ritmo por atividade + próximos 7 dias
    python3 plan.py --days 14       # muda o horizonte da visão de "próximos dias"
    python3 plan.py --save out.md   # também salva o relatório em um arquivo
"""
import argparse
import datetime
import json
import os
import sys

from canvas_api import CanvasClient, load_env
from scheduler import (
    TZ,
    build_schedule,
    collect_announcements,
    collect_grades,
    collect_pending_assignments,
    collect_recent_files,
    enrich_with_details,
    pacing_summary,
)

DIAS_SEMANA_PT = {
    0: "Segunda-feira", 1: "Terça-feira", 2: "Quarta-feira",
    3: "Quinta-feira", 4: "Sexta-feira", 5: "Sábado", 6: "Domingo",
}


def fmt_minutes(m):
    h, mm = divmod(int(m), 60)
    if h and mm:
        return f"{h}h{mm:02d}"
    if h:
        return f"{h}h"
    return f"{mm}min"


def fmt_date(d):
    return f"{DIAS_SEMANA_PT[d.weekday()]}, {d.strftime('%d/%m')}"


def load_config(path="config.json"):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def render_today(day_entry, tasks_by_id):
    lines = [f"## Hoje — {fmt_date(day_entry['date'])} ({day_entry['label']})", ""]
    if not day_entry["allocations"]:
        lines.append("Nenhuma entrega pendente exige tempo hoje. Aproveite para adiantar leitura ou revisão livre.")
    else:
        cap = day_entry["mandatory_capacity"]
        used = sum(a["minutes"] for a in day_entry["allocations"])
        lines.append(f"Bloco de estudo de hoje: **{fmt_minutes(cap)}** disponíveis, **{fmt_minutes(used)}** planejados.")
        if day_entry["used_optional"]:
            lines.append(f"(inclui {fmt_minutes(day_entry['used_optional'])} do bônus opcional de fim de semana)")
        lines.append("")
        for a in day_entry["allocations"]:
            t = a["task"]
            marker = "⚠️ " if a["shortfall"] > 0 else "- "
            lines.append(
                f"{marker}**{fmt_minutes(a['minutes'])}** — {t['title']} ({t['course_name']}) "
                f"— entrega {t['due_at'].strftime('%d/%m %H:%M')}"
            )
            if a["shortfall"] > 0:
                lines.append(
                    f"  faltou encaixar {fmt_minutes(a['shortfall'])} hoje — dia sobrecarregado, "
                    f"vai ter que compensar em outro dia ou usar tempo do fim de semana."
                )
    if day_entry["overloaded"]:
        lines.append("")
        lines.append("**Atenção:** o dia de hoje tem mais trabalho do que cabe no bloco de estudo planejado. Considere usar o horário opcional do fim de semana ou revisar prazos.")
    return "\n".join(lines)


def render_pacing(pacing):
    if not pacing:
        return "## Ritmo por atividade\n\nNenhuma entrega pendente encontrada nos próximos dias. 🎉"
    lines = ["## Ritmo por atividade (recalculado hoje)", ""]
    lines.append("| Atividade | Curso | Categoria | Entrega | Dias restantes | Ritmo sugerido |")
    lines.append("|---|---|---|---|---|---|")
    for p in pacing:
        t = p["task"]
        urgent = " 🔥" if p["urgent"] else ""
        lines.append(
            f"| {t['title']} | {t['course_name']} | {t['category']} | "
            f"{t['due_at'].strftime('%d/%m %H:%M')} | {p['days_left']}{urgent} | "
            f"{fmt_minutes(p['daily_pace_minutes'])}/dia |"
        )
    lines.append("")
    lines.append("_🔥 = prazo apertado (menos de 1 dia de folga). Ritmo = minutos/dia para terminar com 1 dia de margem antes da entrega, começando hoje._")
    return "\n".join(lines)


def render_later(later_tasks):
    if not later_tasks:
        return ""
    lines = ["## Mais pra frente (ainda fora do ritmo diário)", ""]
    lines.append("Essas entregas estão longe o suficiente que não valem minutos fatiados todo dia. Elas entram no ritmo diário automaticamente quando faltar menos de 3 semanas.")
    lines.append("")
    for t in later_tasks:
        lines.append(f"- {t['due_at'].strftime('%d/%m')} — {t['title']} ({t['course_name']}) — {t['category']}, ~{fmt_minutes(t['estimated_minutes'])} estimados")
    return "\n".join(lines)


def render_week(daily_plan):
    lines = ["## Próximos dias", ""]
    for day in daily_plan[1:]:
        used = sum(a["minutes"] for a in day["allocations"])
        if used == 0:
            lines.append(f"**{fmt_date(day['date'])}** ({day['label']}) — livre de faculdade")
            continue
        overload = " ⚠️ sobrecarregado" if day["overloaded"] else ""
        lines.append(f"**{fmt_date(day['date'])}** ({day['label']}) — {fmt_minutes(used)} de estudo{overload}")
        for a in day["allocations"]:
            lines.append(f"  - {fmt_minutes(a['minutes'])} — {a['task']['title']} ({a['task']['course_name']})")
    return "\n".join(lines)


def to_jsonable(daily_plan, pacing, later_tasks, today, announcements, grades, recent_files):
    def task_json(t):
        return {
            "id": str(t["id"]),
            "title": t["title"],
            "course_name": t["course_name"],
            "category": t["category"],
            "due_at": t["due_at"].isoformat(),
            "estimated_minutes": t["estimated_minutes"],
            "description_text": t.get("description_text", ""),
            "submission_label": t.get("submission_label", ""),
            "html_url": t.get("html_url"),
        }

    return {
        "today": today.isoformat(),
        "daily_plan": [
            {
                "date": d["date"].isoformat(),
                "label": d["label"],
                "mandatory_capacity": d["mandatory_capacity"],
                "optional_capacity": d["optional_capacity"],
                "used_optional": d["used_optional"],
                "overloaded": d["overloaded"],
                "allocations": [
                    {
                        "task": task_json(a["task"]),
                        "minutes": a["minutes"],
                        "target_pace": a["target_pace"],
                        "shortfall": a["shortfall"],
                        "days_left": a["days_left"],
                    }
                    for a in d["allocations"]
                ],
            }
            for d in daily_plan
        ],
        "pacing": [
            {
                "task": task_json(p["task"]),
                "days_left": p["days_left"],
                "daily_pace_minutes": p["daily_pace_minutes"],
                "urgent": p["urgent"],
            }
            for p in pacing
        ],
        "later_tasks": [task_json(t) for t in later_tasks],
        "announcements": [
            {
                "title": a["title"],
                "course_name": a["course_name"],
                "posted_at": a["posted_at"].isoformat(),
                "unread": a["unread"],
                "html_url": a["html_url"],
            }
            for a in announcements
        ],
        "grades": grades,
        "recent_files": [
            {
                "course_name": c["course_name"],
                "files": [
                    {
                        "name": f["name"],
                        "updated_at": f["updated_at"].isoformat(),
                        "url": f["url"],
                        "size_kb": f["size_kb"],
                        "local_path": f.get("local_path"),
                    }
                    for f in c["files"]
                ],
            }
            for c in recent_files
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=None, help="Horizonte em dias para a visão semanal")
    parser.add_argument("--save", type=str, default=None, help="Também salvar o relatório neste arquivo")
    parser.add_argument("--json", type=str, default=None, help="Salvar os dados estruturados (JSON) neste arquivo")
    parser.add_argument("--config", type=str, default=os.path.join(os.path.dirname(__file__), "config.json"))
    args = parser.parse_args()

    env = load_env(os.path.join(os.path.dirname(__file__), ".env"))
    token = env.get("CANVAS_TOKEN") or os.environ.get("CANVAS_TOKEN")
    base_url = env.get("CANVAS_BASE_URL") or os.environ.get("CANVAS_BASE_URL")
    if not token or not base_url:
        sys.exit("Faltam CANVAS_TOKEN / CANVAS_BASE_URL no .env")

    config = load_config(args.config)
    horizon = args.days or config["planning"]["lookahead_days_for_report"]

    client = CanvasClient(base_url, token)
    now = datetime.datetime.now(TZ)
    today = now.date()

    courses = client.active_courses()
    courses_by_id = {c["id"]: c for c in courses}

    announcement_days_back = config["planning"].get("announcement_days_back", 5)
    planner_items = client.planner_items(
        start_date=(now - datetime.timedelta(days=announcement_days_back)).strftime("%Y-%m-%d"),
        end_date=(now + datetime.timedelta(days=180)).strftime("%Y-%m-%d"),
    )

    all_tasks = collect_pending_assignments(planner_items, courses_by_id, config, now)
    announcements = collect_announcements(
        planner_items, courses_by_id, config, now, base_url, announcement_days_back
    )
    grades = collect_grades(courses, config)
    materials_dir = None if os.environ.get("SKIP_MATERIALS") else os.path.join(os.path.dirname(os.path.abspath(__file__)), "materials")
    recent_files = collect_recent_files(
        client, courses, config, now,
        days_back=config["planning"].get("files_recent_days", 14),
        max_per_course=config["planning"].get("files_per_course", 5),
        materials_dir=materials_dir,
    )

    window_days = config["planning"].get("active_window_days", 21)
    cutoff = today + datetime.timedelta(days=window_days)
    tasks = [t for t in all_tasks if t["due_at"].date() <= cutoff]
    later_tasks = sorted(
        (t for t in all_tasks if t["due_at"].date() > cutoff), key=lambda t: t["due_at"]
    )

    tasks = enrich_with_details(tasks, client)

    max_due = max((t["due_at"].date() for t in tasks), default=today)
    sim_horizon = max(horizon, (max_due - today).days + 2)

    daily_plan = build_schedule(tasks, config, today, sim_horizon)
    pacing = pacing_summary(tasks, config, today)

    sections = [
        f"# Cronograma de estudos — {fmt_date(today)}",
        render_today(daily_plan[0], {t["id"]: t for t in tasks}),
        render_pacing(pacing),
        render_week(daily_plan[: horizon + 1]),
    ]
    later_section = render_later(later_tasks)
    if later_section:
        sections.append(later_section)

    report = "\n\n".join(sections)

    print(report)

    if args.save:
        with open(args.save, "w", encoding="utf-8") as f:
            f.write(report + "\n")
        print(f"\n(salvo em {args.save})", file=sys.stderr)

    if args.json:
        data = to_jsonable(
            daily_plan[: horizon + 1], pacing, later_tasks, today, announcements, grades, recent_files
        )
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"(dados salvos em {args.json})", file=sys.stderr)


if __name__ == "__main__":
    main()
