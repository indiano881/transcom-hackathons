import asyncio
import json
import logging
from pathlib import Path

import anthropic

from ..config import settings
from ..models import CheckResult
from ..prompts.security import SECURITY_PROMPT
from ..prompts.cost import COST_PROMPT
from ..prompts.brand import BRAND_PROMPT
from .zip_handler import get_text_files, get_file_metadata

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-5-20250929"


def _format_files_for_prompt(files: list[dict]) -> str:
    parts = []
    for f in files:
        parts.append(f"--- {f['path']} ---\n{f['content']}\n")
    return "\n".join(parts)


async def _call_claude(prompt: str) -> dict:
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    message = await client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    text = message.content[0].text.strip()
    # Extract JSON from response (handle markdown code blocks)
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1])
    return json.loads(text)


def _warn_result(error: str) -> CheckResult:
    return CheckResult(
        status="warn",
        summary=f"Check could not complete: {error}",
        details=["AI analysis unavailable — defaulting to warn"],
    )


async def run_security_check(deploy_dir: Path) -> CheckResult:
    try:
        if not settings.anthropic_api_key:
            logger.warning(f"settings.anthropic_api_key is {settings.anthropic_api_key}, shouldn't call anthropic api.")
            return _warn_result('run security check')
        files = get_text_files(deploy_dir)
        if not files:
            return CheckResult(status="pass", summary="No text files to analyze", details=[])
        prompt = SECURITY_PROMPT + _format_files_for_prompt(files)
        result = await _call_claude(prompt)
        return CheckResult(**result)
    except Exception as e:
        logger.exception("Security check failed")
        return _warn_result(str(e))


async def run_cost_check(deploy_dir: Path) -> CheckResult:
    try:
        if not settings.anthropic_api_key:
            logger.warning(f"settings.anthropic_api_key is {settings.anthropic_api_key}, shouldn't call anthropic api.")
            return _warn_result('run cost check')
        metadata = get_file_metadata(deploy_dir)
        prompt = COST_PROMPT + json.dumps(metadata, indent=2)
        result = await _call_claude(prompt)
        return CheckResult(**result)
    except Exception as e:
        logger.exception("Cost check failed")
        return _warn_result(str(e))


async def run_brand_check(deploy_dir: Path) -> CheckResult:
    try:
        if not settings.anthropic_api_key:
            logger.warning(f"settings.anthropic_api_key is {settings.anthropic_api_key}, shouldn't call anthropic api.")
            return _warn_result('run brand check')
        files = get_text_files(deploy_dir)
        if not files:
            return CheckResult(status="pass", summary="No text files to analyze", details=[])
        prompt = BRAND_PROMPT + _format_files_for_prompt(files)
        result = await _call_claude(prompt)
        return CheckResult(**result)
    except Exception as e:
        logger.exception("Brand check failed")
        return _warn_result(str(e))


async def run_all_checks(deploy_dir: Path) -> dict:
    security, cost, brand = await asyncio.gather(
        run_security_check(deploy_dir),
        run_cost_check(deploy_dir),
        run_brand_check(deploy_dir),
    )
    return {"security": security, "cost": cost, "brand": brand}
