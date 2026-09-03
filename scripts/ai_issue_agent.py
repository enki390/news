import os
import sys
import json
import re
import time
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from typing import List, Dict, Tuple, Optional

from google import genai
from google.genai import types

BASE_DIR = Path(__file__).resolve().parent.parent
REPO = os.environ.get("GITHUB_REPOSITORY", "enki390/news")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
EVENT_PATH = os.environ.get("GITHUB_EVENT_PATH", "")

# ---------------------------------------------------------
# GitHub API Helpers
# ---------------------------------------------------------

def github_api_request(endpoint: str, method: str = "GET", data: Optional[dict] = None) -> dict:
    url = f"https://api.github.com/repos/{REPO}/{endpoint.lstrip('/')}"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "AI-Issue-Agent"
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"

    body_bytes = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body_bytes, headers=headers, method=method)
    if data:
        req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req) as resp:
            resp_data = resp.read().decode("utf-8")
            return json.loads(resp_data) if resp_data else {}
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        print(f"GitHub API error ({url}) [{e.code}]: {err_msg}")
        return {"error": err_msg, "status_code": e.code}
    except Exception as e:
        print(f"Network error calling GitHub API ({url}): {e}")
        return {"error": str(e)}

def fetch_issue_comments(issue_number: int) -> List[dict]:
    res = github_api_request(f"issues/{issue_number}/comments?per_page=100")
    return res if isinstance(res, list) else []

def post_issue_comment(issue_number: int, comment_body: str) -> dict:
    return github_api_request(f"issues/{issue_number}/comments", method="POST", data={"body": comment_body})

def update_issue(issue_number: int, state: Optional[str] = None, labels: Optional[List[str]] = None) -> dict:
    payload = {}
    if state:
        payload["state"] = state
    if labels:
        payload["labels"] = labels
    return github_api_request(f"issues/{issue_number}", method="PATCH", data=payload)

# ---------------------------------------------------------
# Gemini API Helpers
# ---------------------------------------------------------

PREFERRED_MODELS = [
    "gemini-3.6-flash",
    "gemini-flash-latest",
    "gemini-3.5-flash",
    "gemini-flash-lite-latest",
    "gemini-3.7-flash",
    "gemini-3.1-pro-preview",
    "gemini-pro-latest"
]

EXCLUDED_KEYWORDS = [
    "tts", "image", "audio", "transcribe", "clip",
    "banana", "computer-use", "robotics", "deep-research",
    "lyria", "gemma", "high-res", "customtools"
]

DEPRECATED_MODELS = {
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-2.0-flash",
    "gemini-2.0-flash-exp",
    "gemini-1.5-flash",
    "gemini-1.5-flash-latest",
    "gemini-1.5-pro",
    "gemini-pro"
}

_CACHED_AGENT_MODELS: Optional[List[str]] = None


def is_valid_text_model(model_name: str) -> bool:
    """Filter out audio/image/TTS/unsupported models."""
    lowered = model_name.lower()
    if lowered in DEPRECATED_MODELS:
        return False
    if any(kw in lowered for kw in EXCLUDED_KEYWORDS):
        return False
    return "flash" in lowered or "pro" in lowered


def get_available_agent_models(client: genai.Client) -> List[str]:
    """Discover available text generation models with caching across calls."""
    global _CACHED_AGENT_MODELS
    if _CACHED_AGENT_MODELS is not None:
        return _CACHED_AGENT_MODELS

    discovered = []
    try:
        for m in client.models.list():
            m_name = getattr(m, 'name', '')
            if m_name:
                clean_name = m_name.replace("models/", "")
                methods = getattr(m, 'supported_generation_methods', []) or getattr(m, 'supported_actions', []) or []
                if not methods or "generateContent" in str(methods):
                    if is_valid_text_model(clean_name):
                        discovered.append(clean_name)
        if discovered:
            ordered = [m for m in PREFERRED_MODELS if m in discovered] + [m for m in discovered if m not in PREFERRED_MODELS]
            _CACHED_AGENT_MODELS = ordered
            return _CACHED_AGENT_MODELS
    except Exception as e:
        print(f"Model discovery note (falling back to PREFERRED_MODELS): {e}")

    _CACHED_AGENT_MODELS = list(PREFERRED_MODELS)
    return _CACHED_AGENT_MODELS


def get_gemini_client() -> genai.Client:
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable is missing.")
    return genai.Client(api_key=GEMINI_API_KEY)


def call_gemini(prompt: str, json_mode: bool = False) -> str:
    client = get_gemini_client()
    models_to_try = get_available_agent_models(client)

    for model_name in models_to_try:
        for attempt in range(1, 3):
            try:
                config = types.GenerateContentConfig()
                if json_mode:
                    config.response_mime_type = "application/json"

                resp = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=config
                )
                if resp and resp.text:
                    return resp.text
            except Exception as e:
                print(f"Gemini call ({model_name}) attempt {attempt} failed: {e}")
                time.sleep(1)

    raise RuntimeError("All Gemini API model attempts failed.")

def extract_json(text: str) -> dict:
    text = text.strip()
    match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if match:
        text = match.group(1).strip()
    try:
        return json.loads(text)
    except Exception:
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            return json.loads(text[start:end+1])
        raise

# ---------------------------------------------------------
# Repository Context Collector
# ---------------------------------------------------------

def get_codebase_context() -> str:
    summary = ["### [Repository Structure]"]
    key_files = ["AGENTS.md", "index.html", "index.css", "app.js", "requirements.txt", "scripts/collector.py"]
    
    file_list = []
    for root, dirs, files in os.walk(BASE_DIR):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('__pycache__', 'node_modules', 'venv')]
        for f in files:
            if not f.startswith('.'):
                rel_path = os.path.relpath(os.path.join(root, f), BASE_DIR)
                file_list.append(rel_path)
    summary.append("Files in repository:\n" + "\n".join(f"- {f}" for f in sorted(file_list)[:60]))

    summary.append("\n### [Key File Contents]")
    for kf in key_files:
        p = BASE_DIR / kf
        if p.exists() and p.is_file():
            try:
                content = p.read_text(encoding="utf-8")
                if len(content) > 3000:
                    content = content[:3000] + "\n... [truncated]"
                summary.append(f"\n#### File: `{kf}`\n```\n{content}\n```")
            except Exception:
                pass

    return "\n".join(summary)

# ---------------------------------------------------------
# Action 1: Create Initial Plan (Issue Opened)
# ---------------------------------------------------------

def handle_issue_opened(issue_number: int, issue_title: str, issue_body: str):
    print(f"Generating initial plan for Issue #{issue_number}: {issue_title}")
    codebase_ctx = get_codebase_context()

    prompt = f"""당신은 NewPaper 프로젝트의 수석 소프트웨어 엔지니어 및 아키텍트입니다.
사용자가 GitHub Issue를 등록했습니다. 아래의 이슈 정보와 코드베이스 컨텍스트를 분석하여,
체계적인 개발 설계 및 단계별 작업 계획서를 한국어로 작성해주세요.

[GitHub Issue 정보]
- 이슈 번호: #{issue_number}
- 이슈 제목: {issue_title}
- 이슈 내용:
{issue_body or "(내용 없음)"}

[프로젝트 코드베이스 컨텍스트]
{codebase_ctx}

[중요 제약사항]
- GitHub Actions 기본 보안 정책상 봇(GITHUB_TOKEN)은 `.github/workflows/` 내 파일 수정/푸시가 거부됩니다.
- 만약 워크플로우 설정 수정이 필요하다면 계획서에 설정 가이드를 작성하되, 자동 코드 수정 대상 파일 목록에는 워크플로우 파일을 직접 포함하지 않고 관리자가 직접 수정하도록 안내하세요.

[작성 지침]
아래 포맷에 맞추어 명확하고 상세한 Markdown 형식의 계획서를 작성해주세요:
1. 🎯 요구사항 분석 및 목표
2. 🏗️ 아키텍처 및 설계 방향
3. 📝 단계별 세부 작업 계획 (수정/생성할 대상 파일 및 구체적 변경 내용 명시)
4. 🧪 검증 및 테스트 방안 (문법 검사, 동작 확인 등)
5. 💡 다음 단계 안내:
   - 본 계획대로 작업을 진행하시려면 댓글로 `**/승인**` 또는 `**/재시도**` 를 입력해 주세요.
   - 수정이나 추가 요청이 있으시면 댓글로 `**/수정 [지시사항]**` 을 입력해 주세요.
"""

    plan_markdown = call_gemini(prompt, json_mode=False)
    comment_body = f"## 🤖 [Gemini 3.7 Flash] 작업 설계 및 계획서\n\n{plan_markdown}"
    post_issue_comment(issue_number, comment_body)
    print(f"Posted initial plan comment to Issue #{issue_number}")

# ---------------------------------------------------------
# Action 2: Revise Plan (User commented /수정)
# ---------------------------------------------------------

def handle_plan_revision(issue_number: int, issue_title: str, issue_body: str, revision_instruction: str, comments: List[dict]):
    print(f"Revising plan for Issue #{issue_number} with instruction: {revision_instruction}")
    codebase_ctx = get_codebase_context()

    history = []
    for c in comments:
        user = c.get("user", {}).get("login", "user")
        body = c.get("body", "")
        if body:
            history.append(f"[{user}]:\n{body}")

    comments_str = "\n\n---\n\n".join(history[-6:])

    prompt = f"""당신은 NewPaper 프로젝트의 수석 소프트웨어 엔지니어 및 아키텍트입니다.
사용자가 기존 작업 계획에 대해 피드백 및 수정 지시사항(`/수정`)을 전달했습니다.
기존 이슈 내용, 대화 히스토리, 그리고 사용자의 최신 수정 지시사항을 반영하여 업데이트된 개발 설계 및 작업 계획서를 다시 작성해주세요.

[GitHub Issue 정보]
- 이슈 번호: #{issue_number}
- 이슈 제목: {issue_title}
- 이슈 원문:
{issue_body}

[이전 대화 및 계획 히스토리]
{comments_str}

[사용자의 최신 수정 지시사항]
{revision_instruction}

[프로젝트 코드베이스 컨텍스트]
{codebase_ctx}

[중요 제약사항]
- GitHub Actions 기본 보안 정책상 봇(GITHUB_TOKEN)은 `.github/workflows/` 내 파일 수정/푸시가 거부됩니다.
- 만약 워크플로우 설정 수정이 필요하다면 계획서에 설정 가이드를 작성하되, 자동 코드 수정 대상 파일 목록에는 워크플로우 파일을 직접 포함하지 않고 관리자가 직접 수정하도록 안내하세요.

[작성 지침]
1. 사용자의 피드백을 정확히 반영하여 기존 계획을 보완 및 수정하세요.
2. Markdown 형식으로 다음 항목을 포함하세요:
   - 🔄 변경된 요구사항 요약
   - 🏗️ 수정된 아키텍처 및 설계
   - 📝 세부 작업 계획 (대상 파일 및 수정 내역)
   - 🧪 검증 방안
3. 코멘트 하단에 항상 다음 안내를 포함하세요:
   - 본 계획대로 진행을 원하시면 `**/승인**` 또는 `**/재시도**` 를 입력해주세요.
   - 추가 수정이 필요하시면 `**/수정 [지시사항]**` 을 입력해주세요.
"""

    revised_plan = call_gemini(prompt, json_mode=False)
    comment_body = f"## 🔄 [Gemini 3.7 Flash] 수정된 작업 설계 및 계획서\n\n{revised_plan}"
    post_issue_comment(issue_number, comment_body)
    print(f"Posted revised plan comment to Issue #{issue_number}")

# ---------------------------------------------------------
# Action 3: Execute Code & Self-Healing Deployment (User commented /승인)
# ---------------------------------------------------------

def validate_code(modified_files: List[str]) -> Tuple[bool, str]:
    """Validate modified files using syntax compilation and basic checks."""
    errors = []
    for rel_path in modified_files:
        full_path = BASE_DIR / rel_path
        if not full_path.exists():
            continue

        if rel_path.endswith(".py"):
            try:
                res = subprocess.run(
                    [sys.executable, "-m", "py_compile", str(full_path)],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if res.returncode != 0:
                    errors.append(f"Python Syntax Error in {rel_path}:\n{res.stderr}")
            except Exception as e:
                errors.append(f"Failed to validate {rel_path}: {e}")

        elif rel_path.endswith(".json"):
            try:
                with open(full_path, "r", encoding="utf-8") as jf:
                    json.load(jf)
            except Exception as e:
                errors.append(f"JSON Parse Error in {rel_path}: {e}")

    # Check collector importability if scripts/ modified
    if any(f.startswith("scripts/") and f.endswith(".py") for f in modified_files):
        try:
            res = subprocess.run(
                [sys.executable, "-c", "import scripts.config; import scripts.sources.base"],
                capture_output=True,
                text=True,
                cwd=str(BASE_DIR),
                timeout=30
            )
            if res.returncode != 0:
                errors.append(f"Module Import Error:\n{res.stderr}")
        except Exception as e:
            errors.append(f"Import check error: {e}")

    if errors:
        return False, "\n\n".join(errors)
    return True, ""

def filter_and_apply_file_changes(files: List[dict]) -> Tuple[List[str], List[dict]]:
    """Filter out .github/workflows files to prevent GitHub push rejection, and apply remaining changes."""
    modified = []
    skipped_workflows = []
    for item in files:
        rel_path = item.get("path", "").strip().lstrip("./").replace("\\", "/")
        content = item.get("content")
        action = item.get("action", "update")
        if not rel_path:
            continue

        # Guard against workflow file updates by Actions bot (avoids push failure)
        if rel_path.startswith(".github/workflows/") or rel_path.startswith(".github/workflows"):
            skipped_workflows.append(item)
            print(f"[Workflow Guard] Skipping automated update for workflow file: {rel_path}")
            continue

        target = BASE_DIR / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)

        if action == "delete":
            if target.exists():
                target.unlink()
                modified.append(rel_path)
        else:
            if content is not None:
                target.write_text(content, encoding="utf-8")
                modified.append(rel_path)
    return modified, skipped_workflows

def handle_execution_and_deploy(issue_number: int, issue_title: str, issue_body: str, comments: List[dict]):
    print(f"Starting code execution for Issue #{issue_number}")
    post_issue_comment(
        issue_number,
        "🚀 **[/승인 확인됨]**\n\nGemini 3.7 Flash가 승인된 계획에 따라 코드 작업 및 배포 검증을 시작합니다. 잠시만 기다려주세요..."
    )

    codebase_ctx = get_codebase_context()
    history = []
    for c in comments:
        user = c.get("user", {}).get("login", "user")
        body = c.get("body", "")
        if body:
            history.append(f"[{user}]:\n{body}")
    comments_str = "\n\n---\n\n".join(history[-6:])

    max_attempts = 5
    last_error = ""
    work_summary = ""
    commit_msg = f"feat: implement solutions for issue #{issue_number}"
    modified_files = []
    skipped_workflow_files = []

    for attempt in range(1, max_attempts + 1):
        print(f"=== Code Generation / Healing Attempt {attempt}/{max_attempts} ===")

        if attempt == 1:
            prompt = f"""당신은 NewPaper 프로젝트의 최고 개발자입니다.
사용자가 이슈 해결 계획을 최종 승인하였습니다. 계획서와 요구사항에 맞추어 모든 필요한 코드 파일을 생성하거나 수정해주세요.

[이슈 정보]
- #{issue_number}: {issue_title}
- 원문: {issue_body}

[승인된 계획 및 대화 히스토리]
{comments_str}

[프로젝트 코드베이스]
{codebase_ctx}

[중요 제약사항]
- GitHub Actions 보안 정책상 `.github/workflows/` 내 파일은 자동 푸시할 수 없습니다. 워크플로우 수정이 필요한 경우 `files` 목록에는 포함하지 마시고, `work_summary`에 수정 가이드를 작성하세요.

[반드시 준수할 출력 JSON 스키마]
반드시 아래와 같은 JSON 구조 하나만을 출력하세요:
{{
  "commit_message": "feat: 간결하고 명확한 커밋 메시지",
  "work_summary": "수행한 작업에 대한 상세한 Markdown 요약 설명",
  "files": [
    {{
      "path": "수정 또는 생성할 파일의 상대경로 (예: scripts/collector.py, index.html 등)",
      "action": "update",
      "content": "해당 파일의 완전한 전체 소스코드 (축약 금지)"
    }}
  ]
}}
"""
        else:
            prompt = f"""이전 시도에서 생성한 코드를 검증/배포하는 도중 아래와 같은 오류가 발생했습니다.
오류 원인을 정확히 분석하고, 문제를 완벽히 해결한 수정된 파일 목록을 동일한 JSON 형식으로 출력해주세요.

[발생한 오류 로그]
{last_error}

[이전 시도 파일 목록]
{modified_files}

[중요 제약사항]
- `.github/workflows/` 내 파일은 `files` 목록에 포함하지 마세요.

[반드시 준수할 출력 JSON 스키마]
{{
  "commit_message": "fix: 오류 해결 및 안정화 (시도 {attempt})",
  "work_summary": "수정 내역 및 에러 해결 내용 요약",
  "files": [
    {{
      "path": "파일 상대 경로",
      "action": "update",
      "content": "오류가 수정된 완전한 파일 전체 내용"
    }}
  ]
}}
"""

        try:
            resp_text = call_gemini(prompt, json_mode=True)
            result = extract_json(resp_text)
            commit_msg = result.get("commit_message", commit_msg)
            work_summary = result.get("work_summary", work_summary)
            files = result.get("files", [])

            if not files:
                raise ValueError("No files generated by Gemini.")

            modified_files, skipped_workflow_files = filter_and_apply_file_changes(files)
            print(f"Applied changes to: {modified_files}")
            if skipped_workflow_files:
                print(f"Skipped workflow files: {[f.get('path') for f in skipped_workflow_files]}")

            # Validation step
            is_valid, err_msg = validate_code(modified_files)
            if is_valid:
                print("Code validation passed successfully!")
                break
            else:
                print(f"Validation failed (attempt {attempt}): {err_msg}")
                last_error = err_msg

        except Exception as e:
            print(f"Attempt {attempt} exception: {e}")
            last_error = str(e)

        if attempt == max_attempts:
            post_issue_comment(
                issue_number,
                f"❌ **[배포 실패 안내]**\n\n최대 자가 치유 시도({max_attempts}회) 후에도 다음 오류가 해결되지 않았습니다:\n```\n{last_error}\n```\n추가 지시사항이 있으시면 `**/수정 [지시사항]**` 을 입력해 주세요."
            )
            return

    # Git Commit & Push
    try:
        if modified_files:
            subprocess.run(["git", "config", "--global", "user.name", "github-actions[bot]"], check=True)
            subprocess.run(["git", "config", "--global", "user.email", "github-actions[bot]@users.noreply.github.com"], check=True)
            subprocess.run(["git", "add", "."], check=True)
            
            diff_proc = subprocess.run(["git", "diff", "--staged", "--quiet"])
            if diff_proc.returncode != 0:
                full_commit_msg = f"{commit_msg} (fixes #{issue_number})"
                subprocess.run(["git", "commit", "-m", full_commit_msg], check=True)
                
                # Fetch & Rebase to prevent non-fast-forward conflicts with remote
                try:
                    subprocess.run(["git", "fetch", "origin", "main"], check=True, capture_output=True, text=True)
                    subprocess.run(["git", "rebase", "origin/main"], check=True, capture_output=True, text=True)
                except Exception as rb_err:
                    print(f"Rebase attempt note: {rb_err}")

                subprocess.run(["git", "push", "origin", "HEAD:main"], check=True, capture_output=True, text=True)
                print("Successfully committed and pushed to origin main.")
            else:
                print("No git diff detected to commit.")
        else:
            print("No non-workflow files modified to commit.")

        # Post Completion Comment
        file_list_md = "\n".join(f"- `{f}`" for f in modified_files) if modified_files else "- (자동 푸시된 일반 코드 파일 없음)"
        
        workflow_notice_md = ""
        if skipped_workflow_files:
            workflow_notice_md = "\n\n### ⚠️ [워크플로우 파일 수동 반영 안내]\nGitHub Actions 보안 정책(workflows 권한 제한)으로 인해 `.github/workflows/` 내 파일은 Actions 봇이 직접 푸시할 수 없습니다. 아래 변경 내용을 참고하여 저장소에 직접 반영해 주세요:\n"
            for wf in skipped_workflow_files:
                wf_p = wf.get("path")
                wf_c = wf.get("content", "")
                workflow_notice_md += f"\n#### `{wf_p}`\n```yaml\n{wf_c}\n```\n"

        completion_comment = f"""## 🎉 [Gemini 3.7 Flash] 작업 완료 안내

요청하신 이슈 (#{issue_number})에 대한 작업이 완료되었습니다!

### 📋 작업 내용 요약
{work_summary}

### 📂 변경 및 생성된 파일 목록
{file_list_md}{workflow_notice_md}

### 🚀 배포 상태
- **커밋 메시지**: `{commit_msg}`
- **상태**: 정상 처리 완료 ✅ (검증 {attempt}회차 통과)
"""
        post_issue_comment(issue_number, completion_comment)
        print(f"Posted completion comment to Issue #{issue_number}")

    except subprocess.CalledProcessError as e:
        stderr_msg = (e.stderr or e.stdout or str(e)).strip()
        print(f"Subprocess error during git push: {stderr_msg}")
        is_workflow_err = "workflows permission" in stderr_msg or "refusing to allow a GitHub App to create or update workflow" in stderr_msg
        if is_workflow_err:
            error_comment = f"""⚠️ **[Git 푸시 권한 오류 안내 - 워크플로우 파일 수정 제한]**

GitHub 보안 정책상 기본 `GITHUB_TOKEN`은 `.github/workflows/` 내 워크플로우 파일을 푸시할 수 없습니다 (`workflows` 권한 제한).

💡 **해결 방법**:
1. 워크플로우 파일(`.github/workflows/*.yml`) 수정은 저장소 관리자가 직접 커밋해야 합니다.
2. AI 에이전트가 워크플로우 파일을 수정할 수 있게 하려면 `workflow` 스코프가 있는 Personal Access Token(PAT)을 발급하여 `secrets.PAT_WORKFLOW_TOKEN`으로 등록하고 연동해야 합니다.
"""
        else:
            error_comment = f"""⚠️ **[Git 커밋/푸시 오류 발생]**

코드 작업 및 문법 검증은 성공하였으나, 저장소로 푸시(`git push`)하는 중 오류가 발생했습니다:
```
{stderr_msg}
```

💡 **조치 및 재시도 방법 안내**:
1. 저장소 권한(`Settings` → `Actions` → `General` → `Workflow permissions`에서 **Read and write permissions** 허용 여부) 및 브랜치 보호 규칙을 확인해 주세요.
2. 재시도를 원하시면 댓글로 `**/재시도**` 또는 `**/승인**`을 입력해 주시면 다시 실행됩니다.
3. 추가 수정이 필요하시면 `**/수정 [지시사항]**`을 입력해 주세요.
"""
        post_issue_comment(issue_number, error_comment)

    except Exception as e:
        print(f"Error during git push or comment posting: {e}")
        error_comment = f"""⚠️ **[배포 중 예외 발생]**

코드 배포 처리 중 오류가 발생했습니다:
`{e}`

💡 **재시도 안내**: 댓글로 `**/재시도**` 또는 `**/수정 [지시사항]**`을 입력해 주세요.
"""
        post_issue_comment(issue_number, error_comment)

# ---------------------------------------------------------
# Main Router
# ---------------------------------------------------------

def main():
    if not EVENT_PATH or not os.path.exists(EVENT_PATH):
        print(f"Event path not found: {EVENT_PATH}")
        return

    try:
        with open(EVENT_PATH, "r", encoding="utf-8") as f:
            event = json.load(f)

        issue = event.get("issue", {})
        issue_number = issue.get("number")
        issue_title = issue.get("title", "")
        issue_body = issue.get("body", "")
        comment = event.get("comment", {})

        if not issue_number:
            print("No issue found in event payload.")
            return

        # Check if comment event
        if comment:
            author_type = comment.get("user", {}).get("type", "")
            author_login = comment.get("user", {}).get("login", "")
            if author_type == "Bot" or author_login == "github-actions[bot]":
                print("Ignoring bot comment.")
                return

            comment_body = comment.get("body", "").strip()
            print(f"Processing comment from {author_login}: {comment_body[:80]}...")

            # Check trigger keywords: /승인, /재시도, /다시시도, /재실행
            is_approval_or_retry = any(k in comment_body for k in ["/승인", "/재시도", "/다시시도", "/재실행"])
            if is_approval_or_retry:
                all_comments = fetch_issue_comments(issue_number)
                handle_execution_and_deploy(issue_number, issue_title, issue_body, all_comments)
            elif "/수정" in comment_body:
                idx = comment_body.find("/수정")
                instruction = comment_body[idx + len("/수정"):].strip()
                if instruction.startswith(":") or instruction.startswith("-"):
                    instruction = instruction[1:].strip()
                all_comments = fetch_issue_comments(issue_number)
                handle_plan_revision(issue_number, issue_title, issue_body, instruction, all_comments)
            else:
                print("Comment does not contain /승인, /재시도, or /수정 trigger keywords. Skipping.")
        else:
            # Issue opened event
            action = event.get("action", "")
            if action == "opened":
                handle_issue_opened(issue_number, issue_title, issue_body)
            else:
                print(f"Unhandled issue action: {action}")

    except Exception as fatal_e:
        print(f"Fatal error in main: {fatal_e}")
        try:
            if EVENT_PATH and os.path.exists(EVENT_PATH):
                with open(EVENT_PATH, "r", encoding="utf-8") as f:
                    event = json.load(f)
                issue_num = event.get("issue", {}).get("number")
                if issue_num:
                    post_issue_comment(
                        issue_num,
                        f"❌ **[에이전트 실행 오류 안내]**\n\n작업 처리 중 예기치 않은 오류가 발생했습니다:\n```\n{fatal_e}\n```\n잠시 후 `**/재시도**` 댓글을 입력해 주세요."
                    )
        except Exception as post_err:
            print(f"Failed to post fatal error comment: {post_err}")
        sys.exit(1)

if __name__ == "__main__":
    main()
