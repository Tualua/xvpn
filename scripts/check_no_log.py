#!/usr/bin/env python3
"""Static DOC-04 guard: a role task that touches a secret must have no_log (and diff: false for file-writing modules).

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
# The role variables that hold the path of a secret file (the stored secrets and the API token).
SECRET_FILE_VAR = re.compile(r"\b(?:xvpn_\w*secrets_file|xvpn_\w*api_token_file)\b")
# Modules that write content into a file. ansible.builtin.file is left out: it only sets mode/owner/state and
# carries no content, so it cannot leak a secret into the output.
WRITER_MODULES = ("template", "copy", "lineinfile", "blockinfile", "ini_file", "replace", "assemble", "get_url")
# Modules that read a file into the task result: the content then needs no_log when the file is a secret one
# (diff does not apply to them).
READER_MODULES = ("slurp", "fetch")
PATH_KEYS = ("src", "dest", "path")
FREE_FORM = re.compile(r"\b(?:src|dest|path)=(.+?)(?=\s+\w+=|$)")


def targets_secret_file(args):
    """True when a writer module's src/dest/path (dict form or free-form `k=v` string) is a secret file."""
    if isinstance(args, dict):
        values = [args[k] for k in PATH_KEYS if isinstance(args.get(k), str)]
    elif isinstance(args, str):
        values = FREE_FORM.findall(args)
    else:
        return False
    return any(SECRET_FILE.search(v.strip().strip("'\"")) or SECRET_FILE_VAR.search(v) for v in values)


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
        module = next((k for k in task if k.split(".")[-1] in WRITER_MODULES + READER_MODULES), None)
        args = task.get(module) if module else None
        by_path = targets_secret_file(args)
        if not PATTERN.search(text) and not by_path:
            continue
        name = task.get("name", "<unnamed>")
        if not no_log_set(own):
            problems.append(f"{path}: task '{name}' touches a secret without no_log/diff: false")
            continue
        if module and module.split(".")[-1] in WRITER_MODULES and not diff_off(task.get("diff")):
            problems.append(f"{path}: task '{name}' touches a secret without no_log/diff: false")


def self_test():
    """Decoy tasks the guard must flag; a guard that stops catching them fails the check instead of passing quietly."""
    decoys = [
        {"name": "decoy env", "ansible.builtin.template": {"src": "node.env.j2", "dest": "{{ home }}/node.env"}},
        {"name": "decoy secrets dir", "ansible.builtin.copy": {"content": "x", "dest": "{{ home }}/secrets/t"}},
        {"name": "decoy free-form template", "ansible.builtin.template": "src=node.env.j2 dest={{ home }}/node.env"},
        {"name": "decoy lineinfile", "ansible.builtin.lineinfile": {"path": "{{ home }}/secrets/t", "line": "x"}},
        {"name": "decoy blockinfile free-form", "ansible.builtin.blockinfile": "path={{ home }}/a.env block=x"},
        {"name": "decoy ini_file", "community.general.ini_file": {"path": "{{ home }}/a.env", "option": "k"}},
        {"name": "decoy slurp", "ansible.builtin.slurp": {"src": "{{ xvpn_panel_secrets_file }}"}},
        {"name": "decoy fetch free-form", "ansible.builtin.fetch": "src={{ xvpn_panel_api_token_file }} dest=/tmp/x"},
        {"name": "decoy replace", "ansible.builtin.replace": {"path": "{{ home }}/a.env", "regexp": "a", "replace": "b"}},
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
