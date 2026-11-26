#!/usr/bin/env python3
"""Static DOC-04 guard: a role task that touches a secret must have no_log (and diff: false for template/copy).

Walks roles/*/tasks/*.yml, descends into block/rescue/always carrying the inherited no_log, and looks for
sensitive names in every key of a task except its name. The list below is the single place to extend.
"""
import json
import pathlib
import re
import sys

import yaml

SENSITIVE = [
    r"\bxvpn_panel_secrets\b",
    r"\bxvpn_panel_secrets_stored\b",
    r"\bxvpn_panel_secrets_generated\b",
    r"\bxvpn_panel_secrets_merged\b",
    r"\bxvpn_panel_secrets_overrides\b",
    r"\bxvpn_panel_secrets_slurp\b",
    r"\bxvpn_panel_api_token\b",
    r"\bxvpn_panel_admin_jwt\b",
    r"\bxvpn_panel_sp_token\b",
    r"_password\b",
    r"\bapp_secret\b",
    r"\bgate_path\b",
    r"\bgate_cookie_value\b",
    r"\baccessToken\b",
    r"\bREMNAWAVE_API_TOKEN\b",
]
PATTERN = re.compile("|".join(SENSITIVE))
BLOCK_KEYS = ("block", "rescue", "always")
# A template/copy task whose src or dest is an env file or lives under secrets/ renders secrets even when the
# task itself names no sensitive variable (the values come from the template), so it is checked by path.
SECRET_FILE = re.compile(r"(\.env(\.j2)?|/secrets/.*)$")


def no_log_set(value):
    """no_log counts as set when it is true or a templated string (e.g. an edge-route sensitivity switch)."""
    if value is True:
        return True
    if isinstance(value, str):
        return "{{" in value or value.strip().lower() in ("true", "yes")
    return False


def diff_off(value):
    return value is False or (isinstance(value, str) and value.strip().lower() in ("false", "no"))


def walk(tasks, inherited, path, problems):
    for task in tasks or []:
        if not isinstance(task, dict):
            continue
        own = task.get("no_log", inherited)
        nested = [k for k in BLOCK_KEYS if k in task]
        for key in nested:
            walk(task[key], own if no_log_set(own) else inherited, path, problems)
        if nested:
            # the block keyword itself carries no module; sensitive names in its own keys (when, vars) still count
            keys = {k: v for k, v in task.items() if k not in ("name", *BLOCK_KEYS)}
        else:
            keys = {k: v for k, v in task.items() if k != "name"}
        text = json.dumps(keys, default=str)
        module = next((k for k in task if k.split(".")[-1] in ("template", "copy")), None)
        args = task.get(module) if module else None
        by_path = isinstance(args, dict) and any(
            isinstance(args.get(k), str) and SECRET_FILE.search(args[k].strip()) for k in ("src", "dest")
        )
        if not PATTERN.search(text) and not by_path:
            continue
        name = task.get("name", "<unnamed>")
        if not no_log_set(own):
            problems.append(f"{path}: task '{name}' touches a secret without no_log/diff: false")
            continue
        if module and not diff_off(task.get("diff")):
            problems.append(f"{path}: task '{name}' touches a secret without no_log/diff: false")


def self_test():
    """Decoy tasks the guard must flag; a guard that stops catching them fails the check instead of passing quietly."""
    decoys = [
        {"name": "decoy env", "ansible.builtin.template": {"src": "node.env.j2", "dest": "{{ home }}/node.env"}},
        {"name": "decoy secrets dir", "ansible.builtin.copy": {"content": "x", "dest": "{{ home }}/secrets/t"}},
        {"name": "decoy token", "ansible.builtin.set_fact": {"x": "{{ xvpn_panel_sp_token }}"}},
    ]
    for task in decoys:
        problems = []
        walk([task], None, "self-test", problems)
        if not problems:
            print(f"check_no_log self-test: decoy '{task['name']}' was not flagged", file=sys.stderr)
            return False
    return True


def main():
    if not self_test():
        return 1
    root = pathlib.Path(__file__).resolve().parent.parent
    problems = []
    for f in sorted(root.glob("roles/*/tasks/*.yml")):
        data = yaml.safe_load(f.read_text())
        walk(data if isinstance(data, list) else [], None, str(f.relative_to(root)), problems)
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    print("check_no_log: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
