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

# QA-05: no Molecule scenario that runs the edge may use the production ACME CA.
check_acme_ca() {
  local converge dir text ok=1
  shopt -s nullglob
  # Molecule converge files and the non-Molecule renderers of the edge templates (scripts/gate/*.yml).
  for converge in extensions/molecule/*/converge.yml scripts/gate/*.yml; do
    grep -Eq 'playbooks/(panel|site)\.yml|xvpn\.remnawave\.edge|traefik\.yml\.j2' "$converge" || continue
    dir="$(dirname "$converge")"
    # the converge file plus the scenario vars files, comment lines removed; a scenario without vars/ reads converge alone
    text="$(cat "$converge" "$dir"/vars/*.yml 2>/dev/null | grep -Ev '^[[:space:]]*#' || true)"
    if ! grep -Eq '^[[:space:]]*xvpn_edge_acme_ca:[[:space:]]*(staging|custom)[[:space:]]*$' <<<"$text" \
      || grep -Eq '^[[:space:]]*xvpn_edge_acme_ca:[[:space:]]*production' <<<"$text"; then
      echo "QA-05: $converge does not pin xvpn_edge_acme_ca to staging or custom" >&2
      ok=0
    fi
    if grep -E '^[[:space:]]*xvpn_edge_acme_ca_server:' <<<"$text" | grep 'api\.letsencrypt\.org' | grep -qv 'acme-staging'; then
      echo "QA-05: $converge points xvpn_edge_acme_ca_server at the production Let's Encrypt directory" >&2
      ok=0
    fi
  done
  shopt -u nullglob
  [ "$ok" -eq 1 ] || exit 1
  echo "check_acme_ca: OK"
}
check_acme_ca

# DOC-04: every role task that touches a secret has no_log (and diff: false for template/copy).
# Run with the interpreter of ansible-playbook: it ships PyYAML, which a bare python3 may lack locally.
ANSIBLE_PYTHON="$(head -1 "$(command -v ansible-playbook)" | sed -n 's/^#![[:space:]]*//p' | awk '{print $1}')"
if [ -z "$ANSIBLE_PYTHON" ] || ! "$ANSIBLE_PYTHON" -c 'import yaml' >/dev/null 2>&1; then
  ANSIBLE_PYTHON=python3
fi
"$ANSIBLE_PYTHON" scripts/check_no_log.py

shopt -s nullglob
playbooks=(playbooks/*.yml)
ext_playbooks=(extensions/molecule/*/{converge,prepare,verify,side_effect,create,destroy}.yml)
scenarios=(extensions/molecule/*/molecule.yml)
shopt -u nullglob

if [ "${#scenarios[@]}" -gt 0 ] && [ "${#ext_playbooks[@]}" -eq 0 ]; then
  echo "no extensions/molecule playbook was syntax-checked" >&2
  exit 1
fi
for f in "${playbooks[@]}" "${ext_playbooks[@]}" scripts/gate/render.yml; do
  echo "syntax-check: $f"
  ansible-playbook --syntax-check -i localhost, "$f"
done

ansible-galaxy collection build --force --output-path "$(mktemp -d)"

echo "check.sh: OK"
