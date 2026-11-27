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

# DOC-04 / D-20: pinned gitleaks scans every tracked file (notice + skip locally, hard fail in CI).
GITLEAKS_VERSION=8.30.1
RUN_GITLEAKS=1
if ! command -v gitleaks >/dev/null 2>&1; then
  if [ -n "${CI:-}" ]; then
    echo "gitleaks is required in CI but is not on PATH" >&2
    exit 1
  fi
  echo "notice: gitleaks not on PATH (local run); CI enforces it"
  RUN_GITLEAKS=0
else
  GITLEAKS_FOUND="$(gitleaks version 2>/dev/null || true)"
  if [ "$GITLEAKS_FOUND" != "$GITLEAKS_VERSION" ]; then
    if [ -n "${CI:-}" ]; then
      echo "gitleaks $GITLEAKS_VERSION is required in CI, found '$GITLEAKS_FOUND'" >&2
      exit 1
    fi
    echo "notice: gitleaks '$GITLEAKS_FOUND' is not the pinned $GITLEAKS_VERSION (local run); CI enforces the pin"
  fi
fi
if [ "$RUN_GITLEAKS" -eq 1 ]; then
  for tool in git tar openssl python3; do
    command -v "$tool" >/dev/null 2>&1 || { echo "$tool is required but is not on PATH" >&2; exit 1; }
  done
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
# set_fact templates its arguments once, so until/retries around it never re-evaluate a random draw.
"$ANSIBLE_PYTHON" scripts/check_until_set_fact.py

# DOC-04 / D-20: no real secret in the repository. Self-test first (proves the scan still catches planted
# secrets), then the scan of the working-tree content of every tracked file (.planning/ included).
# check.sh is itself scanned: secret-named keys are assembled from fragments, random values at runtime.
# Random values avoid the words of the upstream global allowlist regex (true|false|null) and its two
# stopwords, so a generated value can never be suppressed by accident.
GEN_PY='
import base64, json, os, secrets, string, subprocess, sys
case, root = sys.argv[1], sys.argv[2]
P = "xvpn" + "_panel_"
BAD = ("false", "null", "true", "changeme", "abcdefghijklmnopqrstuvwxyz")
MARK = "  # xvpn-test-fixture: " + "non-secret"
def clean(v):
    return not any(b in v.lower() for b in BAD)
def alnum(n):
    while True:
        v = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(n))
        if any(c.islower() for c in v) and any(c.isupper() for c in v) and any(c.isdigit() for c in v) and clean(v):
            return v
def lower(n):
    while True:
        v = "".join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(n))
        if any(c.isalpha() for c in v) and any(c.isdigit() for c in v) and clean(v):
            return v
def b64(nbytes, need):
    while True:
        v = base64.b64encode(os.urandom(nbytes)).decode()
        if clean(v) and need(v) and any(c.isupper() for c in v) and any(c.isdigit() for c in v):
            return v
def put(rel, text):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as fh:
        fh.write(text)
ALL = "inventory/group_vars/all.yml"
if case == "planted-secret":
    put(ALL, P + "app_" + "secret: " + alnum(40) + "\n")
elif case == "leading-slash-secret-file":
    put(ALL, P + "app_secret" + "_file: /" + b64(30, lambda v: "/" in v and "+" not in v and "=" not in v) + "\n")
elif case == "leading-slash-secret-dir":
    put(ALL, P + "app_secret" + "_dir: /" + b64(32, lambda v: "+" in v and "/" in v) + "\n")
elif case == "leading-slash-token-path":
    put(ALL, P + "api_token" + "_path: /" + b64(30, lambda v: "/" in v and "+" not in v and "=" not in v) + "\n")
elif case == "leading-slash-gate-path":
    put(ALL, P + "gate_" + "path: \"/" + alnum(32) + "\"\n")
elif case == "fhs-path-plain-secret":
    put(ALL, P + "app_" + "secret: /var/lib/xvpn/" + lower(24) + "\n")
elif case == "fhs-path-gate-path":
    put(ALL, P + "gate_" + "path: /home/" + lower(32) + "\n")
elif case == "fhs-root-base64-secret-dir":
    put(ALL, P + "app_secret" + "_dir: /var/" + b64(30, lambda v: any(c.isupper() for c in v) and any(c.islower() for c in v) and any(c.isdigit() for c in v) and "+" not in v and "=" not in v) + "\n")
elif case == "url-embedded-secret":
    put(ALL, P + "gate_" + "path: https://panel.invalid/" + alnum(32) + "\n")
elif case == "url-userinfo":
    put("inventory/panel.env", "DATABASE_URL=postgresql://postgres:" + alnum(24) + "@remnawave-db:5432/postgres\n")
elif case == "jwt-shape":
    def enc(b):
        return base64.urlsafe_b64encode(b).rstrip(b"=").decode()
    head = enc(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    body = enc(json.dumps({"sub": secrets.token_hex(12), "iat": 1700000000}).encode())
    put("notes.md", "bearer " + head + "." + body + "." + enc(os.urandom(32)) + "\n")
elif case == "pem-private-key":
    path = os.path.join(root, "roles/x/files/key.pem")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    subprocess.run(["openssl", "genpkey", "-algorithm", "ed25519", "-out", path], check=True, stderr=subprocess.DEVNULL)
elif case == "marker-outside-allowlist":
    put(ALL, P + "gate_" + "path: " + alnum(32) + MARK + "\n")
elif case == "inline-allow-ignored":
    put(ALL, P + "app_" + "secret: " + alnum(40) + "  # gitleaks:" + "allow\n")
elif case == "marker-inside-allowlist":
    for rel in ("scripts/gate/render.yml", "extensions/molecule/container/verify.yml"):
        put(rel, "    " + P + "gate_" + "path: " + alnum(32) + MARK + "\n")
elif case == "placeholders":
    put(ALL, P + "app_secret: \"{{ vault_" + P + "app_secret }}\"\n"
        + P + "postgres_" + "password: \"<from vault>\"\n"
        + P + "admin_" + "password: CHANGE_ME\n"
        + P + "api_" + "token: \"\"\n"
        + P + "secrets_" + "file: /var/lib/xvpn/rw-panel/secrets/panel-secrets.yml\n")
    put("inventory/panel.env", "DATABASE_URL=postgresql://postgres:{{ " + P + "postgres_" + "password }}@remnawave-db:5432/postgres\n")
else:
    sys.exit("unknown self-test case " + case)
'
SELFTEST_CASES=(
  planted-secret:3
  leading-slash-secret-file:3
  leading-slash-secret-dir:3
  leading-slash-token-path:3
  leading-slash-gate-path:3
  fhs-path-plain-secret:3
  fhs-path-gate-path:3
  fhs-root-base64-secret-dir:3
  url-embedded-secret:3
  url-userinfo:3
  jwt-shape:3
  pem-private-key:3
  marker-outside-allowlist:3
  inline-allow-ignored:3
  marker-inside-allowlist:0
  placeholders:0
)

check_secrets() {
  local empty rc id want case_dir failed=0 entry
  SECRETS_WORK="$(mktemp -d)"
  trap 'rm -rf "$SECRETS_WORK"' EXIT
  local work="$SECRETS_WORK"
  empty="$work/empty-ignore"
  mkdir -p "$empty"
  local -a gl=(dir --no-banner --ignore-gitleaks-allow --redact --exit-code 3 --log-level error
    --gitleaks-ignore-path "$empty" --config "$ROOT/.gitleaks.toml")

  for entry in "${SELFTEST_CASES[@]}"; do
    id="${entry%%:*}"
    want="${entry##*:}"
    case_dir="$work/selftest/$id"
    mkdir -p "$case_dir"
    python3 -I -c "$GEN_PY" "$id" "$case_dir"
    rc=0
    (cd "$case_dir" && gitleaks "${gl[@]}" . >/dev/null 2>&1) || rc=$?
    if [ "$rc" -ne "$want" ]; then
      echo "FAIL $id (rc=$rc)" >&2
      failed=1
    fi
  done
  [ "$failed" -eq 0 ] || exit 1
  echo "check_secrets self-test: OK"

  mkdir -p "$work/tree"
  git -C "$ROOT" ls-files -z | tar -C "$ROOT" --null --no-recursion --ignore-failed-read -T - -cf - | tar -C "$work/tree" -xf -
  rc=0
  (cd "$work/tree" && gitleaks "${gl[@]}" --verbose .) || rc=$?
  case "$rc" in
    0) echo "check_secrets: OK" ;;
    3) echo "check_secrets: findings above (values redacted)" >&2; exit 1 ;;
    *) echo "check_secrets: gitleaks error rc=$rc" >&2; exit 1 ;;
  esac
}
if [ "$RUN_GITLEAKS" -eq 1 ]; then
  check_secrets
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
for f in "${playbooks[@]}" "${ext_playbooks[@]}" scripts/gate/render.yml; do
  echo "syntax-check: $f"
  ansible-playbook --syntax-check -i localhost, "$f"
done

ansible-galaxy collection build --force --output-path "$(mktemp -d)"

echo "check.sh: OK"
