#!/usr/bin/env bash
# Single local/CI quality gate: lint, yamllint, argument_specs, syntax-check, build.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Tool gate first.
for tool in ansible-lint ansible-galaxy ansible-playbook; do
  command -v "$tool" >/dev/null 2>&1 || { echo "$tool is required but is not on PATH" >&2; exit 1; }
done
RUN_YAMLLINT=1
if ! command -v yamllint >/dev/null 2>&1; then
  if [ -n "${CI:-}" ]; then
    echo "yamllint is required in CI but is not on PATH" >&2
    exit 1
  fi
  echo "notice: yamllint not on PATH (local run); CI enforces it"
  RUN_YAMLLINT=0
fi

mkdir -p "$ROOT/.ansible/collections/ansible_collections/xvpn"
ln -sfn "$ROOT" "$ROOT/.ansible/collections/ansible_collections/xvpn/remnawave"
ansible-galaxy collection install -r requirements.yml -p "$ROOT/.ansible/collections"
export ANSIBLE_COLLECTIONS_PATH="$ROOT/.ansible/collections"

for d in roles/*/; do
  [ -d "$d" ] || continue
  name="$(basename "$d")"
  if [ ! -f "$d/meta/argument_specs.yml" ]; then
    echo "missing meta/argument_specs.yml in roles/$name" >&2
    exit 1
  fi
done

ansible-lint

if [ "$RUN_YAMLLINT" -eq 1 ]; then
  yamllint -s .
fi

shopt -s nullglob
playbooks=(playbooks/*.yml)
ext_playbooks=(extensions/molecule/*/{converge,prepare,verify,side_effect,create,destroy}.yml)
scenarios=(extensions/molecule/*/molecule.yml)
shopt -u nullglob

if [ "${#scenarios[@]}" -gt 0 ] && [ "${#ext_playbooks[@]}" -eq 0 ]; then
  echo "no extensions/molecule playbook was syntax-checked" >&2
  exit 1
fi
for f in "${playbooks[@]}" "${ext_playbooks[@]}"; do
  echo "syntax-check: $f"
  ansible-playbook --syntax-check -i localhost, "$f"
done

ansible-galaxy collection build --force --output-path "$(mktemp -d)"

echo "check.sh: OK"
