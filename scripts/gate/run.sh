#!/usr/bin/env bash
# Gate regression (PANEL-06, QA-05): renders the production edge/panel templates, runs the pinned Traefik image against
# Pebble and loopback stub backends, and executes the verify_gate.yml case ids over HTTPS/HTTP.
# Output: "gate-matrix: OK" or "FAIL <case id>" lines and exit 1. Rootful podman on a CI runner; SELinux is not
# enforced there, so this proves routing semantics only (the VM tier is the SELinux proof).
# Hook: XVPN_GATE_BREAK=auth-regex breaks the auth exclusion regex in the rendered copy to prove the matrix fails.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

for tool in podman curl openssl python3 ansible-playbook sha256sum ss tar; do
  command -v "$tool" >/dev/null 2>&1 || { echo "$tool is required but is not on PATH" >&2; exit 1; }
done

# Port pre-flight: clearer than a bind error deep in the run.
for port in 3000 18080 8080 8443 8053 8055 14000 15000; do
  if [ -n "$(ss -H -ltn "sport = :${port}")" ]; then
    echo "FAIL port-preflight ${port}"
    exit 1
  fi
done

BREAK="${XVPN_GATE_BREAK:-}"
case "$BREAK" in
  "" | auth-regex) ;;
  *) echo "unknown XVPN_GATE_BREAK value" >&2; exit 1 ;;
esac

WORK="$(mktemp -d)"
CONTAINER="xvpn-gate-traefik"
PIDS=()
cleanup() {
  podman rm -f "$CONTAINER" >/dev/null 2>&1 || true
  local pid
  for pid in "${PIDS[@]:-}"; do
    [ -n "$pid" ] && kill "$pid" >/dev/null 2>&1 || true
  done
  rm -rf "$WORK"
}
trap cleanup EXIT

# Fixed non-secret test fixtures are read from the renderer, never re-typed here.
fixture() { sed -n "s/^ *$1: *\([^ ]*\)  # xvpn-test-fixture: non-secret\$/\1/p" scripts/gate/render.yml; }
GATE_PATH="$(fixture gate_path)"
COOKIE_NAME="$(fixture gate_cookie_name)"
COOKIE_VALUE="$(fixture gate_cookie_value)"
[ -n "$GATE_PATH" ] && [ -n "$COOKIE_NAME" ] && [ -n "$COOKIE_VALUE" ] || { echo "FAIL fixture-read"; exit 1; }
COOKIE="${COOKIE_NAME}=${COOKIE_VALUE}"
DOMAIN=panel.test
TRAEFIK_IMAGE="$(sed -n 's/^xvpn_edge_traefik_image:[[:space:]]*//p' roles/edge/defaults/main.yml)"
[ -n "$TRAEFIK_IMAGE" ] || { echo "FAIL traefik-image-pin"; exit 1; }

# Pebble and challtestsrv: pinned, sha256-verified (02-RESEARCH.md "Installation").
PEBBLE_URL=https://github.com/letsencrypt/pebble/releases/download/v2.10.3
CERT_URL=https://raw.githubusercontent.com/letsencrypt/pebble/v2.10.3/test/certs
mkdir -p "$WORK/dl" "$WORK/pebble/certs/localhost" "$WORK/acme" "$WORK/ca"
fetch() { curl -fsSL --retry 3 -o "$2" "$1"; }
fetch "$PEBBLE_URL/pebble-linux-amd64.tar.gz" "$WORK/dl/pebble.tar.gz"
fetch "$PEBBLE_URL/pebble-challtestsrv-linux-amd64.tar.gz" "$WORK/dl/challtestsrv.tar.gz"
fetch "$CERT_URL/pebble.minica.pem" "$WORK/pebble/certs/pebble.minica.pem"
fetch "$CERT_URL/localhost/cert.pem" "$WORK/pebble/certs/localhost/cert.pem"
fetch "$CERT_URL/localhost/key.pem" "$WORK/pebble/certs/localhost/key.pem"
(
  cd "$WORK"
  sha256sum -c - <<'SUMS'
7e33cf3e426b67e9e647c44e8cc91683caa8ab331f7a99e5e27fcee291c4c7e2  dl/pebble.tar.gz
00b2c5ef525cd8ad56cda898a7cac6169a10b0fd3f2a7456fe0cec92e7b36cb6  dl/challtestsrv.tar.gz
0c502e52627ff7de972c7e9e065640103b4589b4e2d23d3fcf21bef1e3c8c67c  pebble/certs/pebble.minica.pem
c87fb918d9bac8db11aa54493b5f0cf6e0725a3fe73f617d1c64737e1ab4caf9  pebble/certs/localhost/cert.pem
0977979255b0e0721c17335c056b627f66a43cf56e5a52f3cda81fb111ecf00e  pebble/certs/localhost/key.pem
SUMS
  tar -xzf dl/pebble.tar.gz -C dl
  tar -xzf dl/challtestsrv.tar.gz -C dl
)
cp "$WORK/pebble/certs/pebble.minica.pem" "$WORK/ca/ca.pem"
cat >"$WORK/pebble/config.json" <<JSON
{"pebble": {"listenAddress": "127.0.0.1:14000", "managementListenAddress": "127.0.0.1:15000",
  "certificate": "$WORK/pebble/certs/localhost/cert.pem", "privateKey": "$WORK/pebble/certs/localhost/key.pem",
  "httpPort": 8080, "tlsPort": 5001, "ocspResponderURL": "", "externalAccountBindingRequired": false}}
JSON

"$WORK/dl/pebble-challtestsrv-linux-amd64/linux/amd64/pebble-challtestsrv" -http01 "" -https01 "" -tlsalpn01 "" -doh "" \
  -dnsserver 127.0.0.1:8053 -management 127.0.0.1:8055 -defaultIPv4 127.0.0.1 -defaultIPv6 "" >"$WORK/challtestsrv.log" 2>&1 &
PIDS+=("$!")
PEBBLE_VA_NOSLEEP=1 PEBBLE_WFE_NONCEREJECT=0 "$WORK/dl/pebble-linux-amd64/linux/amd64/pebble" \
  -config "$WORK/pebble/config.json" -dnsserver 127.0.0.1:8053 >"$WORK/pebble.log" 2>&1 &
PIDS+=("$!")

# Loopback stubs: the backend answers every path with its own marker, the decoy with the production decoy page.
cat >"$WORK/stub.py" <<'PY'
import http.server, sys

port, mode, decoy = int(sys.argv[1]), sys.argv[2], sys.argv[3]


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if mode == "decoy":
            body = open(decoy, "rb").read()
        else:
            body = ("xvpn-gate-backend " + self.path).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
PY
DECOY_FILE="$ROOT/roles/edge/files/decoy/index.html"
python3 "$WORK/stub.py" 3000 backend "$DECOY_FILE" &
PIDS+=("$!")
python3 "$WORK/stub.py" 18080 decoy "$DECOY_FILE" &
PIDS+=("$!")

ansible-playbook -i localhost, scripts/gate/render.yml -e "xvpn_gate_work=$WORK" >"$WORK/render.log" 2>&1 \
  || { cat "$WORK/render.log"; echo "FAIL render"; exit 1; }

if [ "$BREAK" = "auth-regex" ]; then
  echo "notice: XVPN_GATE_BREAK=auth-regex active, expect FAIL"
  python3 - "$WORK/dynamic/panel.yml" <<'PY'
import sys

path = sys.argv[1]
text = open(path).read()
old = "(?i)^/+api/+auth(/|$)"
if old not in text:
    sys.exit("auth exclusion regex not found in the rendered copy")
open(path, "w").write(text.replace(old, "^/api/auth(/|$)"))
PY
fi

# Pebble answers its management API once it is up.
for _ in $(seq 1 60); do
  curl -fsS --cacert "$WORK/pebble/certs/pebble.minica.pem" https://127.0.0.1:15000/roots/0 -o "$WORK/root.pem" 2>/dev/null && break
  sleep 1
done
if [ ! -s "$WORK/root.pem" ]; then
  tail -20 "$WORK/pebble.log" "$WORK/challtestsrv.log" || true
  curl -sS --cacert "$WORK/pebble/certs/pebble.minica.pem" https://127.0.0.1:15000/roots/0 2>&1 | tail -3 || true
  echo "FAIL pebble-root"
  exit 1
fi

podman run -d --name "$CONTAINER" --network host --log-driver k8s-file \
  -v "$WORK/static:/etc/traefik/static:ro" -v "$WORK/dynamic:/etc/traefik/dynamic:ro" \
  -v "$WORK/acme:/acme" -v "$WORK/ca:/etc/traefik/ca:ro" \
  -e LEGO_CA_CERTIFICATES=/etc/traefik/ca/ca.pem \
  "$TRAEFIK_IMAGE" --configFile=/etc/traefik/static/traefik.yml >/dev/null

HTTPS_RESOLVE="${DOMAIN}:8443:127.0.0.1"
ready=0
for _ in $(seq 1 60); do
  if curl -sS -o /dev/null --cacert "$WORK/root.pem" --resolve "$HTTPS_RESOLVE" "https://${DOMAIN}:8443/" 2>/dev/null; then
    ready=1
    break
  fi
  sleep 2
done
if [ "$ready" -ne 1 ]; then
  podman logs "$CONTAINER" 2>&1 | grep -v -i "$GATE_PATH" | tail -40 || true
  echo "FAIL certificate-issuance"
  exit 1
fi

DECOY_BODY="$(cat "$DECOY_FILE")"
FAILED=()
fail() { echo "FAIL $1"; FAILED+=("$1"); }

# req <id> <path> <expect> [cookie] [user-agent] [bearer]; expect as in verify_gate_requests.yml
req() {
  local id="$1" path="$2" expect="$3" cookie="${4:-}" ua="${5:-}" bearer="${6:-}"
  local args=(-sS --path-as-is --cacert "$WORK/root.pem" --resolve "$HTTPS_RESOLVE" -o "$WORK/body" -w '%{http_code}')
  [ -n "$cookie" ] && args+=(-H "Cookie: $cookie")
  [ -n "$bearer" ] && args+=(-H "Authorization: Bearer $bearer")
  [ -n "$ua" ] && args+=(-A "$ua")
  local code body same=0
  code="$(curl "${args[@]}" "https://${DOMAIN}:8443${path}" 2>/dev/null || echo 0)"
  body="$(cat "$WORK/body" 2>/dev/null || true)"
  [ "$body" = "$DECOY_BODY" ] && same=1
  local backend=0
  [ "$code" != 400 ] && [ "$code" -gt 0 ] && [ "$code" -lt 500 ] && [ "$same" -eq 0 ] && backend=1
  local ok=0
  case "$expect" in
    decoy) [ "$code" = 200 ] && [ "$same" -eq 1 ] && ok=1 ;;
    backend) [ "$backend" -eq 1 ] && ok=1 ;;
    ok200) [ "$code" = 200 ] && [ "$same" -eq 0 ] && ok=1 ;;
    json) [ "$code" = 200 ] && grep -q isLoginAllowed "$WORK/body" && ok=1 ;;
    sub) [ "$backend" -eq 1 ] && [ "$body" != "404 page not found" ] && ok=1 ;;
    bad400) [ "$code" = 400 ] && ok=1 ;;
  esac
  [ "$ok" -eq 1 ] || fail "$id"
}

run_tracer_cases() {
  req root-no-cookie / decoy
  req root-with-cookie / ok200 "$COOKIE"

  # gate-sets-cookie: the exact path answers 302 to / with the cookie attributes of D-04 (Host carries the port).
  local headers
  headers="$(curl --path-as-is -sS -o /dev/null -D - --cacert "$WORK/root.pem" --resolve "$HTTPS_RESOLVE" \
    "https://${DOMAIN}:8443/${GATE_PATH}" 2>/dev/null | tr -d '\r' || true)"
  if ! { head -1 <<<"$headers" | grep -q ' 302' \
    && [ "$(grep -ci "^location: https://${DOMAIN}:8443/\$" <<<"$headers")" -eq 1 ] \
    && [ "$(grep -ci '^set-cookie:' <<<"$headers")" -eq 1 ] \
    && grep -i '^set-cookie:' <<<"$headers" | grep -q "${COOKIE};" \
    && grep -i '^set-cookie:' <<<"$headers" | grep -q 'Max-Age=2592000;' \
    && grep -i '^set-cookie:' <<<"$headers" | grep -q 'Path=/;' \
    && grep -i '^set-cookie:' <<<"$headers" | grep -q 'Secure;' \
    && grep -i '^set-cookie:' <<<"$headers" | grep -q 'HttpOnly;' \
    && grep -i '^set-cookie:' <<<"$headers" | grep -q 'SameSite=Strict'; }; then
    fail gate-sets-cookie
  fi
}

run_tracer_cases

if [ "${#FAILED[@]}" -gt 0 ]; then
  exit 1
fi
echo "gate-matrix: OK"
