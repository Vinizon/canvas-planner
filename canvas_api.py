"""Cliente mínimo para a API REST do Canvas (Instructure)."""
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request


def load_env(path=".env"):
    env = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


class CanvasClient:
    def __init__(self, base_url, token):
        self.base_url = base_url.rstrip("/") + "/api/v1"
        self.token = token

    def _request(self, path, params=None):
        url = path if path.startswith("http") else self.base_url + path
        if params:
            url += "?" + urllib.parse.urlencode(params, doseq=True)
        req = urllib.request.Request(
            url, headers={"Authorization": f"Bearer {self.token}"}
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                body = resp.read().decode("utf-8")
                link_header = resp.headers.get("Link", "")
        except urllib.error.HTTPError as e:
            raise RuntimeError(
                f"Canvas API error {e.code} em {url}: {e.read().decode('utf-8', 'ignore')}"
            ) from e
        return json.loads(body) if body else None, link_header

    def _next_link(self, link_header):
        for part in link_header.split(","):
            m = re.search(r'<([^>]+)>;\s*rel="next"', part)
            if m:
                return m.group(1)
        return None

    def get_all(self, path, params=None):
        results = []
        params = dict(params or {})
        params.setdefault("per_page", 100)
        data, link = self._request(path, params)
        results.extend(data or [])
        next_url = self._next_link(link)
        while next_url:
            data, link = self._request(next_url)
            results.extend(data or [])
            next_url = self._next_link(link)
        return results

    def whoami(self):
        data, _ = self._request("/users/self")
        return data

    def active_courses(self):
        return self.get_all(
            "/courses",
            {"enrollment_state": "active", "include[]": "term"},
        )

    def planner_items(self, start_date=None, end_date=None):
        params = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return self.get_all("/planner/items", params)

    def get_assignment(self, course_id, assignment_id):
        data, _ = self._request(f"/courses/{course_id}/assignments/{assignment_id}")
        return data

    def get_quiz(self, course_id, quiz_id):
        data, _ = self._request(f"/courses/{course_id}/quizzes/{quiz_id}")
        return data

    def get_course_files(self, course_id):
        return self.get_all(f"/courses/{course_id}/files", {"sort": "updated_at", "order": "desc"})


def download_file(url, dest_path):
    """Baixa um arquivo do Canvas. As URLs de arquivo do Canvas já vêm com um
    verifier assinado, então não precisam do header de Authorization."""
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = resp.read()
    with open(dest_path, "wb") as f:
        f.write(data)
    return len(data)
