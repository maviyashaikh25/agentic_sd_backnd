from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


BASE_DIR = Path("projects_generated")


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return cleaned or "generation"


def _extract_content_block(code: Optional[str]) -> str:
    if not code:
        return ""

    fenced_match = re.search(r"```(?:[a-zA-Z0-9_+-]+)?\n(.*?)\n```", code, re.DOTALL)
    if fenced_match:
        return fenced_match.group(1).strip()

    return code.strip()


def save_generation_artifacts(
    user_request: str,
    plan: str,
    backend_code: Optional[str],
    frontend_code: Optional[str],
    qa_feedback: str,
    approved: bool,
    final_code: Optional[str] = None,
) -> list[str]:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    workspace_name = f"chat-{timestamp}-{_slugify(user_request)[:40]}"
    workspace_dir = BASE_DIR / workspace_name
    workspace_dir.mkdir(parents=True, exist_ok=True)

    files_written: list[str] = []

    artifacts = {
        "plan.md": plan,
        "qa_feedback.md": qa_feedback,
        "summary.json": json.dumps(
            {
                "user_request": user_request,
                "approved": approved,
                "timestamp": timestamp,
                "workspace": workspace_name,
            },
            indent=2,
        ),
    }

    if final_code:
        cleaned_content = _extract_content_block(final_code)
        file_name = "final_code.txt"
        first_line = cleaned_content.split('\n')[0].strip() if cleaned_content else ""
        if first_line.startswith("#") or first_line.startswith("//") or first_line.startswith("/*"):
            match = re.search(r"([\w\-]+\.\w+)", first_line)
            if match:
                file_name = match.group(1)
                cleaned_content = "\n".join(cleaned_content.split('\n')[1:]).strip()
        
        if file_name == "final_code.txt":
            if "import React" in cleaned_content or "const " in cleaned_content or "export default" in cleaned_content:
                file_name = "final_code.jsx"
            elif "def " in cleaned_content or "import " in cleaned_content:
                file_name = "final_code.py"
        
        artifacts[file_name] = cleaned_content
    else:
        if backend_code:
            artifacts["backend.generated.py"] = _extract_content_block(backend_code)

        if frontend_code:
            artifacts["frontend.generated.jsx"] = _extract_content_block(frontend_code)

    for relative_name, content in artifacts.items():
        file_path = workspace_dir / relative_name
        file_path.write_text(content, encoding="utf-8")
        files_written.append(str(file_path))

    return files_written