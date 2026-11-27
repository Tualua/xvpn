#!/usr/bin/env python3
"""Static guard: no role task may combine set_fact with until/retries.

set_fact templates its arguments once per item, so every retry re-checks the same value: an until loop around
a random draw never draws again and fails deterministically once the first draw misses (debug session
flaky-panel-secrets-ci). Draw inside one template instead (rejection sampling in a Jinja loop).
"""
import pathlib
import sys

import yaml

BLOCK_KEYS = ("block", "rescue", "always")
SET_FACT = ("set_fact", "ansible.builtin.set_fact", "ansible.legacy.set_fact")


def walk(tasks, path, errors):
    for task in tasks or []:
        if not isinstance(task, dict):
            continue
        if any(k in task for k in BLOCK_KEYS):
            for key in BLOCK_KEYS:
                walk(task.get(key), path, errors)
            continue
        if any(k in task for k in SET_FACT) and "until" in task:
            errors.append(f"{path}: task '{task.get('name', '<unnamed>')}' uses until with set_fact")


def main():
    root = pathlib.Path(__file__).resolve().parent.parent
    errors = []
    for path in sorted(root.glob("roles/*/tasks/*.yml")):
        walk(yaml.safe_load(path.read_text()), path.relative_to(root), errors)
    for line in errors:
        print(line, file=sys.stderr)
    if errors:
        return 1
    print("check_until_set_fact: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
