import shutil
import subprocess
import json
import logging
import uuid
from pathlib import Path
import yaml
from typing import List, Dict, Any

from app.config import settings

logger = logging.getLogger(__name__)


BASE_DIR = Path(__file__).resolve().parents[2]


# ---------------------------
# Load plugins config
# ---------------------------
def load_plugins_config() -> List[Dict[str, Any]]:
    config_path = BASE_DIR / "backend" / "app" / "plugins.yml"

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    return config.get("plugins", [])


# ---------------------------
# Run all plugins
# ---------------------------
def run_plugins(deploy_dir: str) -> List[Dict[str, Any]]:
    plugins = load_plugins_config()

    if not plugins:
        logger.warning("No plugins configured.")
        return []

    logger.info("Plugins to be executed: %s", [p["name"] for p in plugins])

    results = []

    for plugin in plugins:
        result = _run_single_plugin(plugin, deploy_dir)
        if result is not None:
            results.append(
                {
                    "plugin": plugin["name"],
                    "result": result
                }
            )

    return results


# ---------------------------
# Run one plugin
# ---------------------------
def _run_single_plugin(plugin: Dict[str, Any], deploy_dir: str):
    plugin_name = plugin["name"]
    cmd = plugin["cmd"]
    cwd = BASE_DIR / plugin["cwd"]

    deploy_dir_for_plugin = settings.plugin_working_directory / uuid.uuid4().hex[:16]
    shutil.copytree(Path(deploy_dir), Path(deploy_dir_for_plugin), dirs_exist_ok=True)

    logger.info(f"Starting plugin '{plugin_name}' with deploy_dir '{deploy_dir_for_plugin}'")

    process = subprocess.Popen(
        cmd,
        shell=True,
        cwd=str(cwd),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    # Write input
    process.stdin.write(str(deploy_dir_for_plugin) + "\n")
    process.stdin.flush()
    process.stdin.close()

    plugin_result = None

    # Real-time read stdout
    for line in iter(process.stdout.readline, ""):
        line = line.strip()
        if not line:
            continue

        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            logger.warning("[%s] Non-JSON output ignored: %s", plugin_name, line)
            continue

        msg_type = payload.get("type")

        if msg_type == "log":
            logger.info("[%s] %s", plugin_name, payload.get("msg"))

        elif msg_type == "result":
            plugin_result = payload.get("result")
            logger.info("[%s] Result received.", plugin_name)

        else:
            logger.warning("[%s] Unknown message type: %s", plugin_name, payload)

    process.wait()

    logger.info(
        "Plugin finished: %s (exit_code=%s)",
        plugin_name,
        process.returncode
    )

    shutil.rmtree(deploy_dir_for_plugin)
    return plugin_result
