#!/usr/bin/env python3
"""Local static security scanner (rule-based SAST starter).

Usage:
  python scan.py --path /path/to/code --out report.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Pattern, Tuple


DEFAULT_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".mjs",
    ".cjs",
    ".java",
    ".go",
    ".rb",
    ".php",
    ".cs",
    ".html",
    ".htm",
    ".xml",
    ".yaml",
    ".yml",
    ".json",
    ".env",
    ".ini",
    ".cfg",
    ".sh",
    ".ps1",
}

DEFAULT_EXCLUDED_DIRS = {
    ".git",
    "node_modules",
    "dist",
    "build",
    ".next",
    "venv",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "coverage",
    ".idea",
    ".vscode",
}

SEVERITY_SCORE = {
    "Low": 1,
    "Medium": 3,
    "High": 6,
}

SEMGREP_DEFAULT_CONFIGS = [
    "auto",
]
OPENROUTER_CREDITS_URL = "https://openrouter.ai/api/v1/credits"

POLICY_MODE_FILES = {
    "demo": "Security_Gate_Demo_Mode.md",
    "strict": "Security_Gate_Strict_Production_Mode.md",
}

RISK_ORDER = {
    "Low": 1,
    "Medium": 2,
    "High": 3,
}


@dataclass(frozen=True)
class Rule:
    rule_id: str
    category: str
    severity: str
    description: str
    patterns: List[Pattern[str]]


@dataclass
class Finding:
    rule_id: str
    category: str
    severity: str
    file: str
    line: int
    evidence: str
    description: str
    source_engine: str = "local-regex"
    external_rule_id: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        out = {
            "rule_id": self.rule_id,
            "category": self.category,
            "severity": self.severity,
            "file": self.file,
            "line": self.line,
            "evidence": self.evidence,
            "description": self.description,
            "source_engine": self.source_engine,
        }
        if self.external_rule_id:
            out["external_rule_id"] = self.external_rule_id
        return out


def build_rules() -> List[Rule]:
    """Define extensible regex-based scanning rules."""
    return [
        Rule(
            rule_id="SEC001",
            category="Secrets",
            severity="High",
            description="Hard-coded API key or token-like secret.",
            patterns=[
                re.compile(r"(?i)(api[_-]?key|secret|access[_-]?token|private[_-]?key)\s*[:=]\s*['\"][A-Za-z0-9_\-\.\=]{12,}['\"]"),
                re.compile(r"AKIA[0-9A-Z]{16}"),
                re.compile(r"(?i)ghp_[A-Za-z0-9]{36}"),
                re.compile(r"(?i)AIza[0-9A-Za-z\-_]{35}"),
            ],
        ),
        Rule(
            rule_id="SEC002",
            category="Unsafe Code Execution",
            severity="High",
            description="Potential arbitrary code execution sink.",
            patterns=[
                re.compile(r"\beval\s*\("),
                re.compile(r"\bexec\s*\("),
                re.compile(r"\bos\.system\s*\("),
                re.compile(r"\bsubprocess\.(Popen|call|run|check_output|check_call)\s*\("),
                re.compile(r"\bRuntime\.getRuntime\(\)\.exec\s*\("),
                re.compile(r"\bchild_process\.(exec|execSync|spawn|spawnSync)\s*\("),
            ],
        ),
        Rule(
            rule_id="SEC003",
            category="External Network Call",
            severity="Medium",
            description="Outbound network request detected (review trust boundaries).",
            patterns=[
                re.compile(r"\brequests\.(get|post|put|delete|patch|request)\s*\("),
                re.compile(r"\bhttpx\.(get|post|put|delete|patch|request)\s*\("),
                re.compile(r"\burllib\.request\."),
                re.compile(r"\bfetch\s*\("),
                re.compile(r"\baxios\.(get|post|put|delete|patch|request)\s*\("),
                re.compile(r"\bXMLHttpRequest\b"),
                re.compile(r"\bnew\s+WebSocket\s*\("),
            ],
        ),
        Rule(
            rule_id="SEC004",
            category="Potential Data Exposure",
            severity="Medium",
            description="Sensitive data may be logged or exposed.",
            patterns=[
                re.compile(r"(?i)(print|console\.log|logger\.(info|debug|warning|error))\s*\(.*(password|token|secret|authorization|api[_-]?key)"),
                re.compile(r"(?i)DEBUG\\s*=\\s*True"),
                re.compile(r"(?i)app\.run\(.*debug\s*=\s*True"),
                re.compile(r"(?i)CORS\(.*origins\s*=\s*['\"]\*['\"]"),
            ],
        ),
        Rule(
            rule_id="SEC005",
            category="SQL Injection Risk",
            severity="High",
            description="String-formatted SQL query detected.",
            patterns=[
                re.compile(r"(?i)(SELECT|INSERT|UPDATE|DELETE).*(%s|\+\s*\w+|\{\w+\})"),
                re.compile(r"(?i)cursor\.execute\s*\(\s*f['\"].*(SELECT|INSERT|UPDATE|DELETE)"),
                re.compile(r"(?i)executeQuery\s*\(\s*['\"].*(SELECT|INSERT|UPDATE|DELETE).*\+"),
            ],
        ),
        Rule(
            rule_id="SEC006",
            category="Insecure Deserialization",
            severity="High",
            description="Potentially unsafe deserialization usage.",
            patterns=[
                re.compile(r"\bpickle\.loads\s*\("),
                re.compile(r"\byaml\.load\s*\([^,)]*\)"),
                re.compile(r"\bObjectInputStream\b"),
                re.compile(r"\bunserialize\s*\("),
            ],
        ),
    ]


def compile_rules_from_json(config: Dict[str, object]) -> List[Rule]:
    rules_data = config.get("rules")
    if not isinstance(rules_data, list):
        raise ValueError("rules.json must contain a top-level 'rules' list.")

    compiled_rules: List[Rule] = []
    for idx, item in enumerate(rules_data):
        if not isinstance(item, dict):
            raise ValueError(f"Rule at index {idx} must be an object.")

        rule_id = item.get("rule_id")
        category = item.get("category")
        severity = item.get("severity")
        description = item.get("description")
        patterns_raw = item.get("patterns")

        if not all(isinstance(v, str) for v in [rule_id, category, severity, description]):
            raise ValueError(
                f"Rule at index {idx} is missing required string fields: "
                "rule_id, category, severity, description."
            )
        if severity not in SEVERITY_SCORE:
            raise ValueError(
                f"Rule '{rule_id}' has invalid severity '{severity}'. "
                f"Expected one of: {', '.join(SEVERITY_SCORE.keys())}."
            )
        if not isinstance(patterns_raw, list) or not patterns_raw:
            raise ValueError(f"Rule '{rule_id}' must include a non-empty patterns list.")

        patterns: List[Pattern[str]] = []
        for p_idx, pattern_str in enumerate(patterns_raw):
            if not isinstance(pattern_str, str):
                raise ValueError(
                    f"Rule '{rule_id}' pattern at index {p_idx} must be a string."
                )
            try:
                patterns.append(re.compile(pattern_str))
            except re.error as exc:
                raise ValueError(
                    f"Rule '{rule_id}' has invalid regex at index {p_idx}: {exc}"
                ) from exc

        compiled_rules.append(
            Rule(
                rule_id=rule_id,
                category=category,
                severity=severity,
                description=description,
                patterns=patterns,
            )
        )

    if not compiled_rules:
        raise ValueError("rules.json has no valid rules.")
    return compiled_rules


def load_rules(rules_path: Optional[Path]) -> Tuple[List[Rule], str]:
    script_dir = Path(__file__).resolve().parent
    default_config_path = script_dir / "rules.json"

    if rules_path is not None:
        target = rules_path
    elif default_config_path.exists():
        target = default_config_path
    else:
        return build_rules(), "built-in"

    if not target.exists() or not target.is_file():
        raise ValueError(f"Rules file not found: {target}")

    try:
        config = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Rules file is not valid JSON: {target} ({exc})") from exc
    except OSError as exc:
        raise ValueError(f"Unable to read rules file: {target} ({exc})") from exc

    rules = compile_rules_from_json(config)
    return rules, str(target)


def is_binary_file(path: Path) -> bool:
    try:
        with path.open("rb") as f:
            chunk = f.read(4096)
        return b"\0" in chunk
    except OSError:
        return True


def log(message: str, verbose: bool) -> None:
    if verbose:
        print(f"[scan] {message}", file=sys.stderr)


def normalize_severity(raw: Optional[str], default: str = "Medium") -> str:
    if not raw:
        return default

    value = raw.strip().lower()
    if value in {"error", "critical", "high"}:
        return "High"
    if value in {"warning", "warn", "medium", "moderate"}:
        return "Medium"
    if value in {"info", "low"}:
        return "Low"
    return default


def to_relative_path(path_value: Optional[str], base_path: Path) -> str:
    if not path_value:
        return "unknown"
    raw_path = Path(path_value)
    if not raw_path.is_absolute():
        return str(raw_path)
    try:
        return str(raw_path.resolve().relative_to(base_path))
    except ValueError:
        return str(raw_path)


def run_semgrep_scan(
    scan_path: Path,
    semgrep_bin: str,
    semgrep_configs: List[str],
    verbose: bool,
) -> Tuple[List[Finding], Dict[str, object]]:
    status: Dict[str, object] = {
        "enabled": True,
        "binary": semgrep_bin,
        "status": "ok",
        "configs": semgrep_configs,
    }

    if shutil.which(semgrep_bin) is None:
        status["status"] = "error"
        status["error"] = f"Semgrep binary not found: {semgrep_bin}"
        return [], status

    config_args: List[str] = []
    for conf in semgrep_configs:
        config_args.extend(["--config", conf])

    commands = [
        [
            semgrep_bin,
            "scan",
            "--json",
            "--quiet",
            "--no-git-ignore",
            *config_args,
            str(scan_path),
        ],
        [
            semgrep_bin,
            "--json",
            "--quiet",
            "--no-git-ignore",
            *config_args,
            str(scan_path),
        ],
    ]

    findings: List[Finding] = []
    last_error = "Semgrep execution failed."

    for command in commands:
        log(f"Running semgrep command: {' '.join(command)}", verbose)
        result = subprocess.run(command, capture_output=True, text=True)

        # Semgrep typically returns 0 (no findings) or 1 (findings).
        if result.returncode not in (0, 1):
            last_error = result.stderr.strip() or result.stdout.strip() or last_error
            continue

        try:
            payload = json.loads(result.stdout or "{}")
        except json.JSONDecodeError:
            last_error = (
                "Semgrep output was not valid JSON. "
                + (result.stderr.strip() or "No stderr provided.")
            )
            continue

        for item in payload.get("results", []):
            if not isinstance(item, dict):
                continue
            extra = item.get("extra") if isinstance(item.get("extra"), dict) else {}
            start = item.get("start") if isinstance(item.get("start"), dict) else {}

            check_id = str(item.get("check_id") or "SEMGREP")
            line = int(start.get("line") or 1)
            message = str(extra.get("message") or "Semgrep finding")
            evidence_raw = extra.get("lines")
            evidence = (
                normalize_evidence(str(evidence_raw).splitlines()[0])
                if evidence_raw
                else normalize_evidence(message)
            )

            findings.append(
                Finding(
                    rule_id=f"SEMGREP:{check_id}",
                    external_rule_id=check_id,
                    category="Semgrep",
                    severity=normalize_severity(
                        str(extra.get("severity") or ""),
                        default="Medium",
                    ),
                    file=to_relative_path(item.get("path"), scan_path),
                    line=line,
                    evidence=evidence,
                    description=message,
                    source_engine="semgrep",
                )
            )

        status["findings"] = len(findings)
        status["return_code"] = result.returncode
        return dedupe_findings(findings), status

    status["status"] = "error"
    status["error"] = last_error
    status["findings"] = 0
    return [], status


def run_gitleaks_scan(
    scan_path: Path,
    gitleaks_bin: str,
    gitleaks_config: Optional[Path],
    verbose: bool,
) -> Tuple[List[Finding], Dict[str, object]]:
    status: Dict[str, object] = {
        "enabled": True,
        "binary": gitleaks_bin,
        "status": "ok",
    }
    if gitleaks_config is not None:
        status["config"] = str(gitleaks_config)

    if shutil.which(gitleaks_bin) is None:
        status["status"] = "error"
        status["error"] = f"Gitleaks binary not found: {gitleaks_bin}"
        return [], status

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        report_path = Path(tmp.name)

    command = [
        gitleaks_bin,
        "dir",
        str(scan_path),
        "--report-format",
        "json",
        "--report-path",
        str(report_path),
    ]
    if gitleaks_config is not None:
        command.extend(["--config", str(gitleaks_config)])

    log(f"Running gitleaks command: {' '.join(command)}", verbose)
    result = subprocess.run(command, capture_output=True, text=True)

    # Gitleaks typically returns 0 (no findings) or 1 (findings).
    if result.returncode not in (0, 1):
        status["status"] = "error"
        status["error"] = (
            result.stderr.strip() or result.stdout.strip() or "Gitleaks execution failed."
        )
        status["findings"] = 0
        try:
            report_path.unlink(missing_ok=True)
        except OSError:
            pass
        return [], status

    try:
        raw_report = report_path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        status["status"] = "error"
        status["error"] = f"Unable to read gitleaks report: {exc}"
        status["findings"] = 0
        return [], status
    finally:
        try:
            report_path.unlink(missing_ok=True)
        except OSError:
            pass

    if not raw_report:
        status["findings"] = 0
        status["return_code"] = result.returncode
        return [], status

    try:
        payload = json.loads(raw_report)
    except json.JSONDecodeError as exc:
        status["status"] = "error"
        status["error"] = f"Gitleaks report is not valid JSON: {exc}"
        status["findings"] = 0
        return [], status

    findings: List[Finding] = []
    if isinstance(payload, list):
        for item in payload:
            if not isinstance(item, dict):
                continue

            rule_id = str(item.get("RuleID") or "GITLEAKS")
            line = int(item.get("StartLine") or 1)
            description = str(
                item.get("Description") or "Potential secret detected by gitleaks."
            )
            evidence = str(item.get("Match") or item.get("Secret") or description)

            findings.append(
                Finding(
                    rule_id=f"GITLEAKS:{rule_id}",
                    external_rule_id=rule_id,
                    category="Secrets",
                    severity=normalize_severity(
                        str(item.get("Severity") or ""), default="High"
                    ),
                    file=to_relative_path(item.get("File"), scan_path),
                    line=line,
                    evidence=normalize_evidence(evidence),
                    description=description,
                    source_engine="gitleaks",
                )
            )

    status["findings"] = len(findings)
    status["return_code"] = result.returncode
    return dedupe_findings(findings), status


def collect_files(
    root: Path,
    extensions: Iterable[str],
    excluded_dirs: Iterable[str],
    max_file_size_bytes: int,
) -> List[Path]:
    exts = {ext if ext.startswith(".") else f".{ext}" for ext in extensions}
    excluded = set(excluded_dirs)

    files: List[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in excluded]

        current_dir = Path(dirpath)
        for filename in filenames:
            file_path = current_dir / filename
            suffix = file_path.suffix.lower()

            # .env variants are common secret locations.
            is_env_variant = filename.startswith(".env")
            if suffix not in exts and not is_env_variant:
                continue
            try:
                if file_path.stat().st_size > max_file_size_bytes:
                    continue
            except OSError:
                continue
            if is_binary_file(file_path):
                continue
            files.append(file_path)
    return files


def normalize_evidence(line: str, max_len: int = 180) -> str:
    stripped = line.strip().replace("\t", " ")
    if len(stripped) <= max_len:
        return stripped
    return stripped[: max_len - 3] + "..."


def scan_file(file_path: Path, rules: List[Rule], base_path: Path) -> List[Finding]:
    findings: List[Finding] = []
    try:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return findings

    relative_file = str(file_path.relative_to(base_path))
    lines = text.splitlines()

    for idx, line in enumerate(lines, start=1):
        for rule in rules:
            for pattern in rule.patterns:
                if pattern.search(line):
                    findings.append(
                        Finding(
                            rule_id=rule.rule_id,
                            category=rule.category,
                            severity=rule.severity,
                            file=relative_file,
                            line=idx,
                            evidence=normalize_evidence(line),
                            description=rule.description,
                        )
                    )
                    break
    return dedupe_findings(findings)


def dedupe_findings(findings: List[Finding]) -> List[Finding]:
    seen = set()
    unique: List[Finding] = []
    for item in findings:
        key = (item.source_engine, item.rule_id, item.file, item.line, item.evidence)
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def derive_risk_level(findings: List[Finding]) -> str:
    if not findings:
        return "Low"

    score = sum(SEVERITY_SCORE.get(f.severity, 0) for f in findings)
    has_high = any(f.severity == "High" for f in findings)

    if has_high and score >= 12:
        return "High"
    if has_high or score >= 6:
        return "Medium"
    return "Low"


def derive_recommendation(risk_level: str) -> str:
    if risk_level == "High":
        return "Deployment Blocked"
    if risk_level == "Medium":
        return "Manual Review Required"
    return "Auto-Deploy"


def build_ai_summary(findings: List[Finding], risk_level: str) -> Dict[str, object]:
    if not findings:
        return {
            "ai_risk_level": "Low",
            "ai_summary": "No rule-based findings detected. Validate with deeper context-aware analysis before production.",
            "ai_additional_findings": [],
            "ai_input_hint": "Pass full findings and target threat model to LLM for context-based review.",
        }

    categories = Counter(f.category for f in findings)
    top_categories = ", ".join(
        f"{name} ({count})" for name, count in categories.most_common(3)
    )

    return {
        "ai_risk_level": risk_level,
        "ai_summary": (
            f"Rule scan detected {len(findings)} finding(s). "
            f"Top categories: {top_categories}. "
            "Review data flow and exploitability to reduce false positives."
        ),
        "ai_additional_findings": [],
        "ai_input_hint": "Use findings grouped by file and category to request exploitability and remediation prioritization.",
    }


def normalize_risk_level(raw: Optional[str], default: str = "Low") -> str:
    if not raw:
        return default
    value = raw.strip().lower()
    if value == "high":
        return "High"
    if value == "medium":
        return "Medium"
    if value == "low":
        return "Low"
    return default


def derive_policy_recommendation(mode: str, risk_level: str) -> str:
    if mode == "strict":
        if risk_level == "High":
            return "Deployment Blocked"
        if risk_level == "Medium":
            return "Manual Review Required"
        return "Auto-Deploy Allowed"

    if risk_level == "High":
        return "Deployment Blocked"
    if risk_level == "Medium":
        return "Auto-Deploy Allowed (With Warning)"
    return "Auto-Deploy Allowed"


def to_compat_recommendation(mode_recommendation: str) -> str:
    if mode_recommendation == "Deployment Blocked":
        return "Deployment Blocked"
    if mode_recommendation == "Manual Review Required":
        return "Manual Review Required"
    return "Auto-Deploy"


AI_REDACTION_PLACEHOLDER = "***REDACTED***"

REDACT_PATTERNS: List[Tuple[Pattern[str], Any]] = [
    (
        re.compile(
            r"""(?i)\b(api[_-]?key|access[_-]?token|auth[_-]?token|secret|password|passwd|private[_-]?key|client[_-]?secret|authorization)\b(\s*[:=]\s*)(["'])([^"']{4,})(\3)"""
        ),
        lambda m: f"{m.group(1)}{m.group(2)}{m.group(3)}{AI_REDACTION_PLACEHOLDER}{m.group(5)}",
    ),
    (
        re.compile(
            r"""(?i)\b(api[_-]?key|access[_-]?token|auth[_-]?token|secret|password|passwd|private[_-]?key|client[_-]?secret|authorization)\b(\s*[:=]\s*)([A-Za-z0-9_\-./+=]{6,})"""
        ),
        lambda m: f"{m.group(1)}{m.group(2)}{AI_REDACTION_PLACEHOLDER}",
    ),
    (
        re.compile(r"(?i)\bBearer\s+[A-Za-z0-9\-._~+/]+=*"),
        lambda m: "Bearer " + AI_REDACTION_PLACEHOLDER,
    ),
    (re.compile(r"AKIA[0-9A-Z]{16}"), lambda m: AI_REDACTION_PLACEHOLDER),
    (re.compile(r"(?i)ghp_[A-Za-z0-9]{36}"), lambda m: AI_REDACTION_PLACEHOLDER),
    (re.compile(r"(?i)AIza[0-9A-Za-z\-_]{35}"), lambda m: AI_REDACTION_PLACEHOLDER),
]


def redact_evidence_for_ai(evidence: str, finding: Dict[str, Any]) -> Tuple[str, int]:
    redacted = evidence
    replacements = 0

    for pattern, repl in REDACT_PATTERNS:
        redacted, count = pattern.subn(repl, redacted)
        replacements += count

    # If this finding is secret-like but regexes did not catch a value,
    # mask the right-hand side as a conservative fallback.
    if replacements == 0 and _is_secret_finding(finding):
        fallback = re.compile(r"""(?i)(\b(?:api[_-]?key|secret|token|password|authorization)\b\s*[:=]\s*)(.+)$""")
        redacted, count = fallback.subn(r"\1" + AI_REDACTION_PLACEHOLDER, redacted)
        replacements += count

    return redacted, replacements


def redact_text_for_ai(text: str, finding: Dict[str, Any]) -> Tuple[str, int]:
    redacted = text
    replacements = 0
    for pattern, repl in REDACT_PATTERNS:
        redacted, count = pattern.subn(repl, redacted)
        replacements += count

    if replacements == 0 and _is_secret_finding(finding):
        fallback = re.compile(
            r"""(?i)(\b(?:api[_-]?key|secret|token|password|authorization)\b\s*[:=]\s*)(.+)$"""
        )
        redacted, count = fallback.subn(r"\1" + AI_REDACTION_PLACEHOLDER, redacted)
        replacements += count

    return redacted, replacements


def build_finding_context_snippet(
    scan_path: Path,
    finding: Dict[str, Any],
    context_lines: int,
) -> Optional[str]:
    file_value = finding.get("file")
    line_value = finding.get("line")
    if not isinstance(file_value, str) or not file_value:
        return None

    try:
        target_line = int(line_value)
    except (TypeError, ValueError):
        return None
    if target_line <= 0:
        return None

    target_path = (scan_path / file_value).resolve()
    try:
        if not str(target_path).startswith(str(scan_path.resolve())):
            return None
    except OSError:
        return None

    try:
        raw = target_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None

    lines = raw.splitlines()
    if not lines:
        return None

    start = max(1, target_line - context_lines)
    end = min(len(lines), target_line + context_lines)

    snippet_lines: List[str] = []
    for idx in range(start, end + 1):
        marker = ">>" if idx == target_line else "  "
        snippet_lines.append(f"{marker} {idx:>4}: {lines[idx - 1]}")
    return "\n".join(snippet_lines)


def pick_top_findings(
    findings: List[Dict[str, Any]],
    limit: int = 12,
    redact_input: bool = False,
    scan_path: Optional[Path] = None,
    context_lines: int = 8,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    severity_rank = {"High": 0, "Medium": 1, "Low": 2}

    sorted_findings = sorted(
        findings,
        key=lambda item: (
            severity_rank.get(str(item.get("severity", "Medium")), 3),
            str(item.get("file", "")),
            int(item.get("line", 0) or 0),
        ),
    )
    top = sorted_findings[:limit]
    key_findings: List[Dict[str, Any]] = []
    redaction_summary: Dict[str, Any] = {
        "enabled": redact_input,
        "findings_considered": len(top),
        "findings_redacted": 0,
        "replacement_count": 0,
        "context_lines": context_lines,
        "context_attached": 0,
    }
    for idx, finding in enumerate(top, start=1):
        evidence = str(finding.get("evidence", ""))
        context_snippet: Optional[str] = None
        if scan_path is not None:
            context_snippet = build_finding_context_snippet(
                scan_path=scan_path,
                finding=finding,
                context_lines=context_lines,
            )
            if context_snippet:
                redaction_summary["context_attached"] += 1

        if redact_input:
            evidence, replacements = redact_evidence_for_ai(evidence, finding)
            redaction_summary["replacement_count"] += replacements
            if replacements > 0:
                redaction_summary["findings_redacted"] += 1
            if context_snippet:
                context_snippet, context_replacements = redact_text_for_ai(
                    context_snippet,
                    finding,
                )
                redaction_summary["replacement_count"] += context_replacements
                if context_replacements > 0:
                    redaction_summary["findings_redacted"] += 1

        item: Dict[str, Any] = {
            "id": f"KF-{idx:03d}",
            "tool": finding.get("source_engine", "local-regex"),
            "source_engine": finding.get("source_engine", "local-regex"),
            "category": finding.get("category", "Unknown"),
            "severity": normalize_severity(str(finding.get("severity", "Medium"))),
            "file": finding.get("file", "unknown"),
            "line": finding.get("line"),
            "evidence": evidence,
            "explanation": finding.get("description", ""),
            "confidence": 0.75,
            "tags": [],
        }
        if context_snippet:
            item["context_snippet"] = context_snippet
        key_findings.append(item)
    return key_findings, redaction_summary


def summarize_tool_findings(findings: List[Dict[str, Any]]) -> Dict[str, int]:
    by_engine = Counter(str(item.get("source_engine", "local-regex")) for item in findings)
    by_severity = Counter(normalize_severity(str(item.get("severity", "Medium"))) for item in findings)
    return {
        "local_regex_findings": by_engine.get("local-regex", 0),
        "semgrep_findings": by_engine.get("semgrep", 0),
        "gitleaks_findings": by_engine.get("gitleaks", 0),
        "high_severity": by_severity.get("High", 0),
        "medium_severity": by_severity.get("Medium", 0),
        "low_severity": by_severity.get("Low", 0),
    }


def _is_secret_finding(finding: Dict[str, Any]) -> bool:
    text = " ".join(
        [
            str(finding.get("rule_id", "")),
            str(finding.get("category", "")),
            str(finding.get("description", "")),
            str(finding.get("evidence", "")),
        ]
    ).lower()
    if str(finding.get("source_engine", "")).lower() == "gitleaks":
        return True
    secret_tokens = [
        "secret",
        "credential",
        "token",
        "api_key",
        "access_key",
        "private key",
    ]
    return any(token in text for token in secret_tokens)


def _is_dangerous_exec_finding(finding: Dict[str, Any]) -> bool:
    text = " ".join(
        [
            str(finding.get("rule_id", "")),
            str(finding.get("category", "")),
            str(finding.get("description", "")),
            str(finding.get("evidence", "")),
        ]
    ).lower()
    dangerous_tokens = [
        "eval(",
        "exec(",
        "os.system",
        "subprocess",
        "child_process.exec",
        "runtime.getruntime().exec",
        "shell",
        "command injection",
        "dangerous execution",
    ]
    return any(token in text for token in dangerous_tokens)


def _extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    stripped = text.strip()
    if not stripped:
        return None
    try:
        parsed = json.loads(stripped)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    start = stripped.find("{")
    if start == -1:
        return None

    in_string = False
    escaped = False
    depth = 0
    end = -1
    for idx, ch in enumerate(stripped[start:], start=start):
        if escaped:
            escaped = False
            continue
        if ch == "\\":
            escaped = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = idx + 1
                break

    if end == -1:
        return None

    candidate = stripped[start:end]
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_optional_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def load_policy_instruction(mode: str, override_file: Optional[Path]) -> Tuple[str, str]:
    if override_file is not None:
        target = override_file
    else:
        script_dir = Path(__file__).resolve().parent
        policy_file = POLICY_MODE_FILES.get(mode, POLICY_MODE_FILES["demo"])
        target = script_dir / "instructions" / policy_file

    if not target.exists() or not target.is_file():
        raise ValueError(f"Policy instruction file not found: {target}")
    try:
        return target.read_text(encoding="utf-8"), str(target)
    except OSError as exc:
        raise ValueError(f"Unable to read policy instruction file: {target} ({exc})") from exc


def build_openrouter_headers(api_key: str) -> Dict[str, str]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    referer = os.getenv("OPENROUTER_SITE_URL")
    title = os.getenv("OPENROUTER_APP_NAME")
    if referer:
        headers["HTTP-Referer"] = referer
    if title:
        headers["X-Title"] = title
    return headers


def call_openrouter_chat_completion(
    base_url: str,
    api_key: str,
    model: str,
    messages: List[Dict[str, str]],
    timeout_sec: int,
) -> Dict[str, Any]:
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.1,
    }

    headers = build_openrouter_headers(api_key)

    req = urllib.request.Request(
        url=base_url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
        raw = resp.read().decode("utf-8")
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("OpenRouter response is not a JSON object.")
    return parsed


def extract_openrouter_usage(payload: Dict[str, Any]) -> Dict[str, Any]:
    usage = payload.get("usage")
    if not isinstance(usage, dict):
        return {
            "cost": None,
            "prompt_tokens": None,
            "completion_tokens": None,
            "total_tokens": None,
        }

    return {
        "cost": _to_optional_float(usage.get("cost")),
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),
    }


def fetch_openrouter_credits(
    credits_url: str,
    api_key: str,
    timeout_sec: int,
) -> Dict[str, Any]:
    req = urllib.request.Request(
        url=credits_url,
        headers=build_openrouter_headers(api_key),
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
        raw = resp.read().decode("utf-8")
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("Credits API response is not a JSON object.")

    data = parsed.get("data")
    if not isinstance(data, dict):
        raise ValueError("Credits API response missing data object.")

    total_credits = _to_optional_float(data.get("total_credits"))
    total_usage = _to_optional_float(data.get("total_usage"))
    remaining = (
        (total_credits - total_usage)
        if total_credits is not None and total_usage is not None
        else None
    )
    return {
        "total_credits": total_credits,
        "total_usage": total_usage,
        "remaining": remaining,
    }


def parse_openrouter_response(payload: Dict[str, Any]) -> Dict[str, Any]:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("OpenRouter response missing choices.")
    first = choices[0] if isinstance(choices[0], dict) else {}
    message = first.get("message") if isinstance(first.get("message"), dict) else {}
    content = message.get("content")

    text = ""
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        text_parts: List[str] = []
        for item in content:
            if isinstance(item, dict):
                piece = item.get("text")
                if isinstance(piece, str):
                    text_parts.append(piece)
        text = "\n".join(text_parts)

    parsed = _extract_json_object(text)
    if parsed is None:
        raise ValueError("Model output was not valid JSON object.")
    return parsed


def call_ai_gate_with_openrouter(
    report: Dict[str, Any],
    scan_path: Path,
    instruction_text: str,
    mode: str,
    model: str,
    base_url: str,
    api_key: str,
    timeout_sec: int,
    max_findings: int,
    redact_input: bool,
    context_lines: int,
    verbose: bool,
    log_payload: bool,
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    tool_findings = report.get("rule_findings")
    if not isinstance(tool_findings, list):
        tool_findings = []
    finding_sample, redaction_summary = pick_top_findings(
        [f for f in tool_findings if isinstance(f, dict)],
        limit=max_findings,
        redact_input=redact_input,
        scan_path=scan_path,
        context_lines=context_lines,
    )

    input_payload = {
        "mode": mode,
        "scanned_path": str(scan_path),
        "tool_summary": summarize_tool_findings(
            [f for f in tool_findings if isinstance(f, dict)]
        ),
        "findings_sample": finding_sample,
        "input_redaction": redaction_summary,
    }

    system_prompt = (
        "You are an AI security reviewer. "
        "Return only a valid JSON object. "
        "Do not include markdown fences."
    )
    user_prompt = (
        "Apply the following policy instruction and produce JSON with fields:\n"
        "ai_risk_level, ai_summary, ai_additional_findings, "
        "explanation_for_decision, mitigation_suggestions, confidence_and_limitations.\n\n"
        "Policy instruction:\n"
        f"{instruction_text}\n\n"
        "Scan input JSON:\n"
        f"{json.dumps(input_payload, ensure_ascii=False)}"
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    request_payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.1,
    }

    log(
        (
            "AI gate request prepared: "
            f"provider=openrouter model={model} "
            f"findings_sample={len(finding_sample)} "
            f"redaction_enabled={redaction_summary.get('enabled')} "
            f"redacted_findings={redaction_summary.get('findings_redacted')} "
            f"replacements={redaction_summary.get('replacement_count')}"
        ),
        verbose,
    )

    if log_payload:
        print(
            "[ai] Request payload (sent to AI):",
            file=sys.stderr,
        )
        print(
            json.dumps(request_payload, ensure_ascii=False, indent=2),
            file=sys.stderr,
        )

    raw_payload = call_openrouter_chat_completion(
        base_url=base_url,
        api_key=api_key,
        model=model,
        messages=messages,
        timeout_sec=timeout_sec,
    )
    usage = extract_openrouter_usage(raw_payload)
    return parse_openrouter_response(raw_payload), redaction_summary, usage


def build_ai_gate_report(
    report: Dict[str, Any],
    mode: str,
    policy_version: str,
    instruction_file: str,
    model_name: str,
    ai_output: Optional[Dict[str, Any]],
    ai_status: str,
    ai_error: Optional[str],
) -> Dict[str, Any]:
    tool_findings = report.get("rule_findings")
    findings = [f for f in tool_findings if isinstance(f, dict)] if isinstance(tool_findings, list) else []
    key_findings, _ = pick_top_findings(findings, limit=12, redact_input=False)
    tool_summary = summarize_tool_findings(findings)

    has_secret = any(_is_secret_finding(f) for f in findings)
    has_dangerous_exec = any(_is_dangerous_exec_finding(f) for f in findings)
    high_count = sum(1 for f in findings if normalize_severity(str(f.get("severity", "Medium"))) == "High")
    medium_findings = [
        f for f in findings if normalize_severity(str(f.get("severity", "Medium"))) == "Medium"
    ]

    risk_level = "Low"
    decision_path: List[str] = []
    overrides_applied: List[str] = []

    if has_secret:
        risk_level = "High"
        decision_path.append("Detected secrets/credentials -> override to High.")
        overrides_applied.append("SECRETS_ALWAYS_HIGH")
    elif has_dangerous_exec:
        risk_level = "High"
        decision_path.append("Detected dangerous execution pattern -> override to High.")
        overrides_applied.append("DANGEROUS_EXEC_ALWAYS_HIGH")
    elif high_count > 0:
        risk_level = "High"
        decision_path.append("High severity tool finding present -> High risk.")
        overrides_applied.append("HIGH_FINDING_OVERRIDE")
    else:
        if mode == "strict":
            if len(medium_findings) >= 3:
                risk_level = "High"
                decision_path.append(
                    "Strict mode: multiple Medium findings (>=3) escalated to High."
                )
                overrides_applied.append("STRICT_MULTI_MEDIUM_ESCALATION")
            elif len(medium_findings) >= 1:
                risk_level = "Medium"
                decision_path.append("Strict mode: Medium findings require manual review.")
            else:
                risk_level = "Low"
                decision_path.append("No material findings.")
        else:
            if len(medium_findings) >= 1:
                risk_level = "Medium"
                decision_path.append("Demo mode: Medium findings produce warning but allow deploy.")
            else:
                risk_level = "Low"
                decision_path.append("No material findings.")

    ai_risk = None
    ai_additional_findings: List[Dict[str, Any]] = []
    ai_summary = ""
    explanation_for_decision = ""
    mitigation_suggestions: List[str] = []
    confidence_and_limitations: List[str] = [
        "Static analysis only",
        "Rule + AI fusion is heuristic and may miss context",
    ]

    if isinstance(ai_output, dict):
        ai_risk = normalize_risk_level(str(ai_output.get("ai_risk_level", "")), default="Low")
        ai_summary = str(ai_output.get("ai_summary", "")).strip()
        explanation_for_decision = str(ai_output.get("explanation_for_decision", "")).strip()
        raw_mitigations = ai_output.get("mitigation_suggestions")
        if isinstance(raw_mitigations, list):
            mitigation_suggestions = [str(item) for item in raw_mitigations]
        raw_limits = ai_output.get("confidence_and_limitations")
        if isinstance(raw_limits, list):
            confidence_and_limitations = [str(item) for item in raw_limits]

        raw_ai_findings = ai_output.get("ai_additional_findings")
        if isinstance(raw_ai_findings, list):
            for idx, item in enumerate(raw_ai_findings, start=1):
                if not isinstance(item, dict):
                    continue
                ai_finding = {
                    "id": f"AI-{idx:03d}",
                    "tool": "ai",
                    "source_engine": "ai",
                    "category": str(item.get("category", "AI Insight")),
                    "severity": normalize_severity(str(item.get("severity", "Medium"))),
                    "file": str(item.get("file", "unknown")),
                    "line": item.get("line"),
                    "evidence": str(item.get("evidence", "")),
                    "explanation": str(item.get("explanation", "")),
                    "confidence": _safe_float(item.get("confidence"), default=0.6),
                    "tags": item.get("tags", []) if isinstance(item.get("tags"), list) else [],
                }
                ai_additional_findings.append(ai_finding)

    if ai_risk and RISK_ORDER.get(ai_risk, 0) > RISK_ORDER.get(risk_level, 0):
        risk_level = ai_risk
        decision_path.append(f"AI escalated risk to {ai_risk}.")
        overrides_applied.append("AI_ESCALATION")

    if ai_status == "failed" and mode == "strict" and RISK_ORDER[risk_level] < RISK_ORDER["Medium"]:
        risk_level = "Medium"
        decision_path.append("Strict mode: AI unavailable -> escalate to Manual Review Required.")
        overrides_applied.append("STRICT_AI_FAILURE_ESCALATION")

    mode_recommendation = derive_policy_recommendation(mode, risk_level)
    compat_recommendation = to_compat_recommendation(mode_recommendation)

    if ai_additional_findings:
        key_findings.extend(ai_additional_findings[:8])

    if not explanation_for_decision:
        explanation_for_decision = (
            "Risk derived from fused static findings and policy rules."
            if not ai_summary
            else ai_summary
        )

    return {
        "enabled": True,
        "mode": "Demo" if mode == "demo" else "Production",
        "policy_mode": mode,
        "policy_version": policy_version,
        "instruction_file": instruction_file,
        "model": model_name,
        "analysis_status": ai_status,
        "analysis_error": ai_error,
        "tool_summary": tool_summary,
        "key_findings": key_findings,
        "fusion_decision": {
            "risk_level": risk_level,
            "recommendation": mode_recommendation,
            "compat_recommendation": compat_recommendation,
            "decision_path": decision_path,
            "overrides_applied": overrides_applied,
        },
        "explanation_for_decision": explanation_for_decision,
        "mitigation_suggestions": mitigation_suggestions,
        "confidence_and_limitations": confidence_and_limitations,
    }


def scan_directory(
    path: Path,
    rules: List[Rule],
    max_file_size_kb: int = 512,
    enable_semgrep: bool = False,
    enable_gitleaks: bool = False,
    semgrep_bin: str = "semgrep",
    semgrep_configs: Optional[List[str]] = None,
    gitleaks_bin: str = "gitleaks",
    gitleaks_config: Optional[Path] = None,
    verbose: bool = False,
) -> Dict[str, object]:
    files = collect_files(
        root=path,
        extensions=DEFAULT_EXTENSIONS,
        excluded_dirs=DEFAULT_EXCLUDED_DIRS,
        max_file_size_bytes=max_file_size_kb * 1024,
    )
    log(f"Candidate files to scan: {len(files)}", verbose)

    all_findings: List[Finding] = []
    total_files = len(files)
    for index, file_path in enumerate(files, start=1):
        relative_file = str(file_path.relative_to(path))
        log(f"[{index}/{total_files}] Checking {relative_file}", verbose)
        file_findings = scan_file(file_path, rules, base_path=path)
        if file_findings:
            log(
                f"[{index}/{total_files}] Findings in {relative_file}: {len(file_findings)}",
                verbose,
            )
        all_findings.extend(file_findings)

    engines: Dict[str, Dict[str, object]] = {
        "local_regex": {
            "enabled": True,
            "status": "ok",
            "findings": len(all_findings),
            "rules_count": len(rules),
        }
    }

    if enable_semgrep:
        semgrep_configs_final = semgrep_configs or SEMGREP_DEFAULT_CONFIGS
        semgrep_findings, semgrep_status = run_semgrep_scan(
            scan_path=path,
            semgrep_bin=semgrep_bin,
            semgrep_configs=semgrep_configs_final,
            verbose=verbose,
        )
        engines["semgrep"] = semgrep_status
        all_findings.extend(semgrep_findings)
        log(
            f"Semgrep findings: {len(semgrep_findings)} (status={semgrep_status.get('status')})",
            verbose,
        )
    else:
        engines["semgrep"] = {"enabled": False, "status": "skipped", "findings": 0}

    if enable_gitleaks:
        gitleaks_findings, gitleaks_status = run_gitleaks_scan(
            scan_path=path,
            gitleaks_bin=gitleaks_bin,
            gitleaks_config=gitleaks_config,
            verbose=verbose,
        )
        engines["gitleaks"] = gitleaks_status
        all_findings.extend(gitleaks_findings)
        log(
            f"Gitleaks findings: {len(gitleaks_findings)} (status={gitleaks_status.get('status')})",
            verbose,
        )
    else:
        engines["gitleaks"] = {"enabled": False, "status": "skipped", "findings": 0}

    all_findings = dedupe_findings(all_findings)
    log(f"Scan complete. Total findings: {len(all_findings)}", verbose)

    risk_level = derive_risk_level(all_findings)
    recommendation = derive_recommendation(risk_level)

    report = {
        "risk_level": risk_level,
        "recommendation": recommendation,
        "rule_findings": [f.to_dict() for f in all_findings],
        "ai_analysis": build_ai_summary(all_findings, risk_level),
        "limitations": [
            "Static analysis only",
            "No runtime execution",
            "Regex-based pattern matching may produce false positives/negatives",
            "No full taint/data-flow tracking in this version",
        ],
        "metadata": {
            "scanned_path": str(path),
            "files_scanned": len(files),
            "findings_count": len(all_findings),
            "rules_count": len(rules),
            "engines": engines,
        },
    }
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Static security scanner (rule-based)")
    parser.add_argument(
        "--path",
        required=True,
        help="Directory path to scan recursively",
    )
    parser.add_argument(
        "--out",
        required=True,
        help="Output JSON report path",
    )
    parser.add_argument(
        "--max-file-kb",
        type=int,
        default=512,
        help="Max file size in KB to scan (default: 512)",
    )
    parser.add_argument(
        "--rules",
        default=None,
        help=(
            "Optional path to rules.json. "
            "If omitted, scanner uses ./rules.json (next to scan.py) when present, "
            "otherwise built-in rules."
        ),
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-file scan logs to stderr.",
    )
    parser.add_argument(
        "--enable-semgrep",
        action="store_true",
        help="Run Semgrep and merge findings into the report.",
    )
    parser.add_argument(
        "--semgrep-bin",
        default="semgrep",
        help="Semgrep executable name or absolute path (default: semgrep).",
    )
    parser.add_argument(
        "--semgrep-config",
        action="append",
        default=[],
        help=(
            "Semgrep config selector/path. Repeat flag to add more configs. "
            "If omitted, defaults to '--config auto'. "
            "Example: --semgrep-config p/default"
        ),
    )
    parser.add_argument(
        "--enable-gitleaks",
        action="store_true",
        help="Run Gitleaks and merge findings into the report.",
    )
    parser.add_argument(
        "--gitleaks-bin",
        default="gitleaks",
        help="Gitleaks executable name or absolute path (default: gitleaks).",
    )
    parser.add_argument(
        "--gitleaks-config",
        default=None,
        help="Optional path to .gitleaks.toml config.",
    )
    parser.add_argument(
        "--enable-ai-gate",
        action="store_true",
        help="Enable AI policy analysis and fusion decision.",
    )
    parser.add_argument(
        "--policy-mode",
        choices=["demo", "strict"],
        default="demo",
        help="AI gate policy mode (default: demo).",
    )
    parser.add_argument(
        "--ai-provider",
        choices=["openrouter"],
        default="openrouter",
        help="AI provider (default: openrouter).",
    )
    parser.add_argument(
        "--ai-model",
        default="openai/gpt-4o-mini",
        help="Model name for AI gate (default: openai/gpt-4o-mini).",
    )
    parser.add_argument(
        "--ai-base-url",
        default="https://openrouter.ai/api/v1/chat/completions",
        help="Chat completion endpoint for AI provider.",
    )
    parser.add_argument(
        "--ai-credits-url",
        default=OPENROUTER_CREDITS_URL,
        help="Credits endpoint for AI provider balance lookup.",
    )
    parser.add_argument(
        "--ai-api-key-env",
        default="OPENROUTER_API_KEY",
        help="Environment variable name for AI API key (default: OPENROUTER_API_KEY).",
    )
    parser.add_argument(
        "--ai-timeout-sec",
        type=int,
        default=45,
        help="Timeout for AI API request in seconds (default: 45).",
    )
    parser.add_argument(
        "--ai-max-findings",
        type=int,
        default=40,
        help="Maximum number of findings to send to AI (default: 40).",
    )
    parser.add_argument(
        "--ai-context-lines",
        type=int,
        default=8,
        help="Number of source lines before/after each finding to send to AI (default: 8).",
    )
    parser.add_argument(
        "--ai-redact-input",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Redact sensitive values before sending findings to AI. "
            "Use --no-ai-redact-input to disable."
        ),
    )
    parser.add_argument(
        "--ai-log-payload",
        action="store_true",
        help=(
            "Print full AI request payload to stderr before calling provider. "
            "Use with care in shared terminals."
        ),
    )
    parser.add_argument(
        "--ai-policy-file",
        default=None,
        help=(
            "Optional custom policy markdown file. "
            "If omitted, uses built-in file by --policy-mode."
        ),
    )
    return parser.parse_args()


def build_engine_warnings(report: Dict[str, object], args: argparse.Namespace) -> List[str]:
    warnings: List[str] = []
    metadata = report.get("metadata") if isinstance(report.get("metadata"), dict) else {}
    engines = metadata.get("engines") if isinstance(metadata, dict) else {}
    if not isinstance(engines, dict):
        return warnings

    if args.enable_semgrep:
        semgrep_state = engines.get("semgrep")
        if isinstance(semgrep_state, dict) and semgrep_state.get("status") == "error":
            semgrep_error = str(semgrep_state.get("error") or "unknown semgrep error")
            if "not found" in semgrep_error.lower():
                warnings.append(
                    "Semgrep is enabled but not installed/in PATH. "
                    "Install with 'brew install semgrep' or 'python3 -m pip install semgrep', "
                    "then verify with 'semgrep --version'."
                )
            else:
                warnings.append(f"Semgrep is enabled but failed: {semgrep_error}")

    if args.enable_gitleaks:
        gitleaks_state = engines.get("gitleaks")
        if isinstance(gitleaks_state, dict) and gitleaks_state.get("status") == "error":
            gitleaks_error = str(gitleaks_state.get("error") or "unknown gitleaks error")
            if "not found" in gitleaks_error.lower():
                warnings.append(
                    "Gitleaks is enabled but not installed/in PATH. "
                    "Install with 'brew install gitleaks' (or download a release binary), "
                    "then verify with 'gitleaks version'."
                )
            else:
                warnings.append(f"Gitleaks is enabled but failed: {gitleaks_error}")

    return warnings


def build_ai_gate_warnings(ai_gate: Dict[str, Any], enabled: bool) -> List[str]:
    if not enabled:
        return []

    warnings: List[str] = []
    status = str(ai_gate.get("analysis_status", ""))
    if status in {"failed", "degraded"}:
        error_message = str(ai_gate.get("analysis_error") or "unknown AI gate error")
        warnings.append(f"AI gate status={status}: {error_message}")
    return warnings


def main() -> int:
    args = parse_args()
    scan_path = Path(args.path).expanduser().resolve()
    out_path = Path(args.out).expanduser().resolve()
    rules_path = Path(args.rules).expanduser().resolve() if args.rules else None
    ai_policy_file_path = (
        Path(args.ai_policy_file).expanduser().resolve() if args.ai_policy_file else None
    )
    gitleaks_config_path = (
        Path(args.gitleaks_config).expanduser().resolve()
        if args.gitleaks_config
        else None
    )

    if not scan_path.exists() or not scan_path.is_dir():
        print(json.dumps({"error": f"Invalid directory path: {scan_path}"}, indent=2))
        return 2

    try:
        rules, rules_source = load_rules(rules_path)
    except ValueError as exc:
        print(json.dumps({"error": str(exc)}, indent=2), file=sys.stderr)
        return 3

    log(f"Using rules source: {rules_source}", args.verbose)
    report = scan_directory(
        scan_path,
        rules=rules,
        max_file_size_kb=args.max_file_kb,
        enable_semgrep=args.enable_semgrep,
        enable_gitleaks=args.enable_gitleaks,
        semgrep_bin=args.semgrep_bin,
        semgrep_configs=args.semgrep_config,
        gitleaks_bin=args.gitleaks_bin,
        gitleaks_config=gitleaks_config_path,
        verbose=args.verbose,
    )
    report["metadata"]["rules_source"] = rules_source

    warnings = build_engine_warnings(report, args)
    ai_api_called = False
    ai_usage: Optional[Dict[str, Any]] = None
    ai_credits: Optional[Dict[str, Any]] = None
    ai_credits_error: Optional[str] = None

    ai_gate: Dict[str, Any] = {
        "enabled": False,
        "mode": "Demo" if args.policy_mode == "demo" else "Production",
        "policy_mode": args.policy_mode,
        "policy_version": "v0.1",
        "instruction_file": None,
        "model": args.ai_model,
        "analysis_status": "skipped",
        "analysis_error": None,
        "tool_summary": summarize_tool_findings(
            report["rule_findings"] if isinstance(report.get("rule_findings"), list) else []
        ),
        "key_findings": pick_top_findings(
            report["rule_findings"] if isinstance(report.get("rule_findings"), list) else [],
            limit=12,
            redact_input=False,
            scan_path=scan_path,
            context_lines=max(0, args.ai_context_lines),
        )[0],
        "input_redaction": {
            "enabled": False,
            "findings_considered": 0,
            "findings_redacted": 0,
            "replacement_count": 0,
        },
        "fusion_decision": {
            "risk_level": report["risk_level"],
            "recommendation": "Manual Review Required"
            if report["recommendation"] == "Manual Review Required"
            else (
                "Deployment Blocked"
                if report["recommendation"] == "Deployment Blocked"
                else "Auto-Deploy Allowed"
            ),
            "compat_recommendation": report["recommendation"],
            "decision_path": ["AI gate disabled; using rule-engine decision."],
            "overrides_applied": [],
        },
        "explanation_for_decision": "AI gate disabled.",
        "mitigation_suggestions": [],
        "confidence_and_limitations": [
            "Static analysis only",
            "AI gate disabled by default",
        ],
    }

    if args.enable_ai_gate:
        if args.ai_log_payload and not args.ai_redact_input:
            warnings.append(
                "AI payload logging is enabled while input redaction is disabled; "
                "terminal output may include sensitive values."
            )
        ai_status = "ok"
        ai_error: Optional[str] = None
        ai_output: Optional[Dict[str, Any]] = None
        ai_input_redaction: Dict[str, Any] = {
            "enabled": bool(args.ai_redact_input),
            "findings_considered": 0,
            "findings_redacted": 0,
            "replacement_count": 0,
        }
        instruction_text = ""
        instruction_source = ""

        try:
            instruction_text, instruction_source = load_policy_instruction(
                mode=args.policy_mode,
                override_file=ai_policy_file_path,
            )
        except ValueError as exc:
            ai_status = "failed"
            ai_error = str(exc)

        api_key = os.getenv(args.ai_api_key_env, "")
        if ai_status == "ok" and not api_key:
            ai_status = "failed"
            ai_error = (
                f"Missing API key. Set environment variable '{args.ai_api_key_env}'."
            )

        if ai_status == "ok":
            try:
                if args.ai_provider == "openrouter":
                    ai_api_called = True
                    ai_output, ai_input_redaction, ai_usage = call_ai_gate_with_openrouter(
                        report=report,
                        scan_path=scan_path,
                        instruction_text=instruction_text,
                        mode=args.policy_mode,
                        model=args.ai_model,
                        base_url=args.ai_base_url,
                        api_key=api_key,
                        timeout_sec=args.ai_timeout_sec,
                        max_findings=args.ai_max_findings,
                        redact_input=args.ai_redact_input,
                        context_lines=max(0, args.ai_context_lines),
                        verbose=args.verbose,
                        log_payload=args.ai_log_payload,
                    )
                else:
                    ai_status = "failed"
                    ai_error = f"Unsupported ai provider: {args.ai_provider}"
            except urllib.error.HTTPError as exc:
                detail = ""
                try:
                    detail = exc.read().decode("utf-8")
                except Exception:  # noqa: BLE001
                    detail = ""
                ai_status = "failed"
                ai_error = (
                    f"AI API HTTP error {exc.code}: "
                    f"{detail.strip() if detail else exc.reason}"
                )
            except urllib.error.URLError as exc:
                ai_status = "failed"
                ai_error = f"AI API network error: {exc.reason}"
            except (ValueError, json.JSONDecodeError) as exc:
                ai_status = "degraded"
                ai_error = f"AI response parse issue: {exc}"
            except Exception as exc:  # noqa: BLE001
                ai_status = "failed"
                ai_error = f"AI gate unexpected error: {exc}"

        if ai_api_called and api_key and args.ai_provider == "openrouter":
            try:
                ai_credits = fetch_openrouter_credits(
                    credits_url=args.ai_credits_url,
                    api_key=api_key,
                    timeout_sec=args.ai_timeout_sec,
                )
            except urllib.error.HTTPError as exc:
                detail = ""
                try:
                    detail = exc.read().decode("utf-8")
                except Exception:  # noqa: BLE001
                    detail = ""
                ai_credits_error = (
                    f"Credits API HTTP error {exc.code}: "
                    f"{detail.strip() if detail else exc.reason}"
                )
            except urllib.error.URLError as exc:
                ai_credits_error = f"Credits API network error: {exc.reason}"
            except (ValueError, json.JSONDecodeError) as exc:
                ai_credits_error = f"Credits API parse issue: {exc}"
            except Exception as exc:  # noqa: BLE001
                ai_credits_error = f"Credits API unexpected error: {exc}"

        ai_gate = build_ai_gate_report(
            report=report,
            mode=args.policy_mode,
            policy_version="v0.1",
            instruction_file=instruction_source or str(ai_policy_file_path or ""),
            model_name=args.ai_model,
            ai_output=ai_output,
            ai_status=ai_status,
            ai_error=ai_error,
        )
        ai_gate["enabled"] = True
        ai_gate["input_redaction"] = ai_input_redaction
        ai_gate["api_observability"] = {
            "called": ai_api_called,
            "usage": ai_usage,
            "credits": ai_credits,
            "credits_error": ai_credits_error,
        }

        # AI gate drives top-level decision when enabled.
        fusion = ai_gate.get("fusion_decision", {})
        if isinstance(fusion, dict):
            risk_level = fusion.get("risk_level")
            compat_recommendation = fusion.get("compat_recommendation")
            if isinstance(risk_level, str):
                report["risk_level"] = risk_level
            if isinstance(compat_recommendation, str):
                report["recommendation"] = compat_recommendation

        ai_summary = str(ai_output.get("ai_summary", "")).strip() if isinstance(ai_output, dict) else ""
        if ai_summary:
            report["ai_analysis"] = {
                "ai_risk_level": ai_gate["fusion_decision"]["risk_level"],
                "ai_summary": ai_summary,
                "ai_additional_findings": ai_output.get("ai_additional_findings", [])
                if isinstance(ai_output.get("ai_additional_findings"), list)
                else [],
            }

    report["ai_gate"] = ai_gate
    report["metadata"]["ai_api"] = {
        "called": ai_api_called,
        "provider": args.ai_provider if args.enable_ai_gate else None,
        "model": args.ai_model if args.enable_ai_gate else None,
        "usage": ai_usage,
        "credits": ai_credits,
        "credits_error": ai_credits_error,
    }
    warnings.extend(build_ai_gate_warnings(ai_gate, args.enable_ai_gate))

    if warnings:
        report["metadata"]["warnings"] = warnings
        for warning in warnings:
            print(f"[warning] {warning}", file=sys.stderr)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    summary = {
        "status": "ok",
        "report_path": str(out_path),
        "risk_level": report["risk_level"],
        "findings_count": len(report["rule_findings"]),
        "recommendation": report["recommendation"],
    }
    if warnings:
        summary["warnings"] = warnings

    if ai_api_called:
        if ai_usage:
            cost = ai_usage.get("cost")
            prompt_tokens = ai_usage.get("prompt_tokens")
            completion_tokens = ai_usage.get("completion_tokens")
            total_tokens = ai_usage.get("total_tokens")
            print(
                (
                    "[ai] Usage: "
                    f"cost={cost if cost is not None else 'unknown'} "
                    f"prompt_tokens={prompt_tokens if prompt_tokens is not None else 'unknown'} "
                    f"completion_tokens={completion_tokens if completion_tokens is not None else 'unknown'} "
                    f"total_tokens={total_tokens if total_tokens is not None else 'unknown'}"
                ),
                file=sys.stderr,
            )
            if cost is not None:
                summary["ai_cost"] = cost
        else:
            print("[ai] Usage: unavailable", file=sys.stderr)

        if ai_credits:
            remaining = ai_credits.get("remaining")
            total_credits = ai_credits.get("total_credits")
            total_usage = ai_credits.get("total_usage")
            print(
                (
                    "[ai] Credits: "
                    f"remaining={remaining if remaining is not None else 'unknown'} "
                    f"total_credits={total_credits if total_credits is not None else 'unknown'} "
                    f"total_usage={total_usage if total_usage is not None else 'unknown'}"
                ),
                file=sys.stderr,
            )
            if remaining is not None:
                summary["ai_credits_remaining"] = remaining
        elif ai_credits_error:
            print(f"[ai] Credits lookup failed: {ai_credits_error}", file=sys.stderr)

    print(
        json.dumps(summary, indent=2)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
