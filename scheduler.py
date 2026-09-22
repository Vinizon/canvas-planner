"""Motor de cronograma: estima esforço, aplica ritmo diário e monta a agenda."""
import datetime
import html as html_module
import math
import os
import re
import unicodedata
from zoneinfo import ZoneInfo

from canvas_api import download_file

TZ = ZoneInfo("America/Sao_Paulo")
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def parse_utc(iso_str):
    dt = datetime.datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    return dt.astimezone(TZ)


def estimate_effort(title, effort_rules):
    t = (title or "").lower()
    for rule in effort_rules["keywords"]:
        if any(kw in t for kw in rule["match"]):
            return rule["minutes"], rule["category"]
    return effort_rules["default_minutes"], effort_rules["default_category"]


def short_course_name(course):
    code = (course or {}).get("course_code") or ""
    cleaned = re.sub(r"^\(\d+\)\s*", "", code).strip()
    return cleaned or (course or {}).get("name") or "Curso desconhecido"


SUBMISSION_TYPE_LABELS = {
    "online_upload": "envio de arquivo",
    "online_text_entry": "texto online",
    "online_quiz": "quiz",
    "discussion_topic": "fórum de discussão",
    "online_url": "envio de link",
    "media_recording": "gravação de áudio/vídeo",
    "on_paper": "entrega em papel",
    "external_tool": "ferramenta externa",
    "none": "sem entrega (informativo)",
}


def strip_html(raw, max_chars=320):
    if not raw:
        return ""
    text = re.sub(r"<[^>]+>", " ", raw)
    text = html_module.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_chars:
        text = text[:max_chars].rsplit(" ", 1)[0] + "…"
    return text


def enrich_with_details(tasks, client):
    """Busca descrição completa, tipo de entrega e link direto no Canvas
    para cada tarefa (só chamado para as tarefas dentro da janela ativa)."""
    for t in tasks:
        detail = None
        try:
            detail = client.get_assignment(t["course_id"], t["id"])
        except RuntimeError:
            try:
                detail = client.get_quiz(t["course_id"], t["id"])
            except RuntimeError:
                detail = None

        if detail:
            t["description_text"] = strip_html(detail.get("description"), 320)
            t["html_url"] = detail.get("html_url") or t.get("html_url")
            sub_types = detail.get("submission_types") or []
            t["submission_label"] = ", ".join(
                SUBMISSION_TYPE_LABELS.get(s, s) for s in sub_types
            )
        else:
            t["description_text"] = ""
            t["submission_label"] = ""
    return tasks


def collect_announcements(planner_items, courses_by_id, config, now, base_url, days_back=5):
    excluded_ids = set(config["planning"]["excluded_course_ids"])
    excluded_kw = [k.lower() for k in config["planning"]["excluded_course_name_keywords"]]
    cutoff = now - datetime.timedelta(days=days_back)

    items = []
    for item in planner_items:
        if item.get("plannable_type") != "announcement":
            continue
        posted_raw = item.get("plannable_date")
        if not posted_raw:
            continue
        posted_at = parse_utc(posted_raw)
        if posted_at < cutoff:
            continue

        course_id = item.get("course_id")
        if course_id in excluded_ids:
            continue
        course = courses_by_id.get(course_id)
        course_name = short_course_name(course)
        if any(kw in course_name.lower() for kw in excluded_kw):
            continue

        plannable = item.get("plannable") or {}
        html_url = item.get("html_url") or plannable.get("html_url")
        if html_url and html_url.startswith("/"):
            html_url = base_url.rstrip("/") + html_url

        items.append(
            {
                "title": plannable.get("title") or "(sem título)",
                "course_name": course_name,
                "posted_at": posted_at,
                "unread": plannable.get("read_state") == "unread",
                "html_url": html_url,
            }
        )
    items.sort(key=lambda a: a["posted_at"], reverse=True)
    return items


def collect_grades(courses, config):
    excluded_ids = set(config["planning"]["excluded_course_ids"])
    excluded_kw = [k.lower() for k in config["planning"]["excluded_course_name_keywords"]]

    grades = []
    for c in courses:
        if c["id"] in excluded_ids:
            continue
        course_name = short_course_name(c)
        if any(kw in course_name.lower() for kw in excluded_kw):
            continue
        score = None
        for e in c.get("enrollments") or []:
            if e.get("type") == "student":
                score = e.get("computed_current_score")
                break
        grades.append({"course_name": course_name, "score": score})

    grades.sort(key=lambda g: (g["score"] is None, g["score"] if g["score"] is not None else 0))
    return grades


def safe_filename(name):
    normalized = unicodedata.normalize("NFC", name or "")
    cleaned = re.sub(r'[^\w\-. À-ÿ]', "_", normalized).strip()
    return cleaned or "arquivo"


def collect_recent_files(client, courses, config, now, days_back=14, max_per_course=5, materials_dir=None):
    excluded_ids = set(config["planning"]["excluded_course_ids"])
    excluded_kw = [k.lower() for k in config["planning"]["excluded_course_name_keywords"]]
    cutoff = now - datetime.timedelta(days=days_back)

    files_by_course = []
    for c in courses:
        if c["id"] in excluded_ids:
            continue
        course_name = short_course_name(c)
        if any(kw in course_name.lower() for kw in excluded_kw):
            continue
        try:
            raw_files = client.get_course_files(c["id"])
        except RuntimeError:
            continue

        recent = []
        for f in raw_files:
            updated_raw = f.get("updated_at")
            if not updated_raw:
                continue
            updated_at = parse_utc(updated_raw)
            if updated_at < cutoff:
                continue
            recent.append(
                {
                    "name": f.get("display_name") or f.get("filename") or "(sem nome)",
                    "updated_at": updated_at,
                    "url": f.get("url"),
                    "size_bytes": f.get("size") or 0,
                    "size_kb": round((f.get("size") or 0) / 1024),
                }
            )
        recent.sort(key=lambda x: x["updated_at"], reverse=True)
        recent = recent[:max_per_course]

        if materials_dir and recent:
            course_dir = os.path.join(materials_dir, safe_filename(course_name))
            os.makedirs(course_dir, exist_ok=True)
            for entry in recent:
                local_path = os.path.join(course_dir, safe_filename(entry["name"]))
                already_ok = (
                    os.path.exists(local_path)
                    and os.path.getsize(local_path) == entry["size_bytes"]
                )
                if not already_ok and entry["url"]:
                    try:
                        download_file(entry["url"], local_path)
                    except Exception:
                        local_path = None
                entry["local_path"] = local_path if (local_path and os.path.exists(local_path)) else None

        if recent:
            files_by_course.append({"course_name": course_name, "files": recent})

    files_by_course.sort(key=lambda c: c["files"][0]["updated_at"], reverse=True)
    return files_by_course


def day_type_for(date, config):
    weekday_name = WEEKDAYS[date.weekday()]
    return config["week"][weekday_name]["type"]


def day_capacity(date, config):
    dt_key = day_type_for(date, config)
    template = config["day_templates"][dt_key]
    mandatory = sum(
        b.get("minutes", 0) for b in template["blocks"] if b.get("fixed") == "study"
    )
    optional = template.get("optional_study_minutes", 0)
    return mandatory, optional, template["label"]


def collect_pending_assignments(planner_items, courses_by_id, config, now):
    excluded_ids = set(config["planning"]["excluded_course_ids"])
    excluded_kw = [k.lower() for k in config["planning"]["excluded_course_name_keywords"]]

    tasks = []
    for item in planner_items:
        if item.get("plannable_type") not in ("assignment", "quiz"):
            continue
        plannable = item.get("plannable") or {}
        due_raw = item.get("plannable_date")
        if not due_raw:
            continue
        due_at = parse_utc(due_raw)
        if due_at <= now:
            continue

        submission = item.get("submissions")
        if isinstance(submission, dict) and submission.get("submitted"):
            continue

        course_id = item.get("course_id")
        if course_id in excluded_ids:
            continue
        course = courses_by_id.get(course_id)
        course_name = short_course_name(course)
        if any(kw in course_name.lower() for kw in excluded_kw):
            continue

        title = plannable.get("title") or plannable.get("name") or "(sem título)"
        minutes, category = estimate_effort(title, config["effort_rules"])

        tasks.append(
            {
                "id": item.get("plannable_id"),
                "course_id": course_id,
                "title": title,
                "course_name": course_name,
                "due_at": due_at,
                "estimated_minutes": minutes,
                "remaining_minutes": minutes,
                "category": category,
                "html_url": plannable.get("html_url"),
            }
        )
    tasks.sort(key=lambda t: t["due_at"])
    return tasks


def build_schedule(tasks, config, start_date, horizon_days):
    """Simula dia a dia, recalculando o ritmo (minutos/dia) de cada tarefa
    a partir do que falta e de quantos dias restam até o prazo."""
    buffer_days = config["planning"]["safety_buffer_days"]
    remaining = {t["id"]: t["remaining_minutes"] for t in tasks}
    daily_plan = []

    for i in range(horizon_days):
        date = start_date + datetime.timedelta(days=i)
        mandatory_cap, optional_cap, label = day_capacity(date, config)
        capacity_left = mandatory_cap
        used_optional = 0
        allocations = []

        active = [t for t in tasks if remaining[t["id"]] > 0 and t["due_at"].date() >= date]
        active.sort(key=lambda t: t["due_at"])

        for t in active:
            due_date = t["due_at"].date()
            deadline_day = due_date - datetime.timedelta(days=buffer_days)
            days_left = (deadline_day - date).days + 1
            if days_left < 1:
                days_left = 1
            pace = math.ceil(remaining[t["id"]] / days_left)

            alloc = min(pace, remaining[t["id"]], max(capacity_left, 0))
            overflow = pace - alloc
            if overflow > 0 and optional_cap > used_optional:
                extra = min(overflow, optional_cap - used_optional, remaining[t["id"]] - alloc)
                if extra > 0:
                    alloc += extra
                    used_optional += extra

            if alloc > 0:
                remaining[t["id"]] -= alloc
                capacity_left -= min(alloc, capacity_left)
                allocations.append(
                    {
                        "task": t,
                        "minutes": alloc,
                        "target_pace": pace,
                        "shortfall": max(0, pace - alloc),
                        "days_left": days_left,
                    }
                )

        daily_plan.append(
            {
                "date": date,
                "label": label,
                "mandatory_capacity": mandatory_cap,
                "optional_capacity": optional_cap,
                "used_optional": used_optional,
                "allocations": allocations,
                "overloaded": any(a["shortfall"] > 0 for a in allocations),
            }
        )

    return daily_plan


def pacing_summary(tasks, config, today):
    """Ritmo recomendado por atividade, assumindo distribuição igual desde hoje."""
    buffer_days = config["planning"]["safety_buffer_days"]
    summary = []
    for t in tasks:
        due_date = t["due_at"].date()
        deadline_day = due_date - datetime.timedelta(days=buffer_days)
        days_left = (deadline_day - today).days + 1
        if days_left < 1:
            days_left = 1
            urgent = True
        else:
            urgent = False
        pace = math.ceil(t["remaining_minutes"] / days_left)
        summary.append(
            {
                "task": t,
                "days_left": days_left,
                "daily_pace_minutes": pace,
                "urgent": urgent,
            }
        )
    return summary
