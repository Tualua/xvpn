#!/usr/bin/env bash
# Self-steal regression gate (STEAL-01, STEAL-03, NODE-03): renders the production edge and node templates, runs the
# pinned Traefik and decoy images, Pebble and a pinned native Xray (Reality server plus a real Vision client) and
# executes the case matrix. Output: "selfsteal: OK (<n> cases)" or "FAIL <case id>" lines and exit 1.
# Rootful podman on a CI runner; SELinux is not enforced there, so this proves protocol and routing semantics only.
# Hook: XVPN_SELFSTEAL_BREAK=sni-strict removes sniStrict from the rendered copy to prove the matrix fails.
# Cache: XVPN_SELFSTEAL_CACHE_DIR holds downloads by sha256; a cached file is used only after its sha256 verified.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

for tool in podman curl openssl python3 ansible-playbook sha256sum ss tar; do
  command -v "$tool" >/dev/null 2>&1 || { echo "$tool is required but is not on PATH" >&2; exit 1; }
done

for port in 8080 8443 4443 10808 14000 15000 8053 8055 18080 18090 18091; do
  if [ -n "$(ss -H -ltn "sport = :${port}")" ]; then
    echo "FAIL port-preflight ${port}"
    exit 1
  fi
done

BREAK="${XVPN_SELFSTEAL_BREAK:-}"
case "$BREAK" in
  "" | sni-strict) ;;
  *) echo "unknown XVPN_SELFSTEAL_BREAK value" >&2; exit 1 ;;
esac

WORK="$(mktemp -d)"
TRAEFIK_C="xvpn-selfsteal-traefik"
DECOY_C="xvpn-selfsteal-decoy"
PIDS=()
cleanup() {
  podman rm -f "$TRAEFIK_C" "$DECOY_C" >/dev/null 2>&1 || true
  local pid
  for pid in "${PIDS[@]:-}"; do
    [ -n "$pid" ] && kill "$pid" >/dev/null 2>&1 || true
  done
  rm -rf "$WORK"
}
trap cleanup EXIT

DOMAIN=node.test
TRAEFIK_IMAGE="$(sed -n 's/^xvpn_edge_traefik_image:[[:space:]]*//p' roles/edge/defaults/main.yml)"
[ -n "$TRAEFIK_IMAGE" ] || { echo "FAIL traefik-image-pin"; exit 1; }
DECOY_IMAGE="$(sed -n 's/^xvpn_edge_decoy_image:[[:space:]]*//p' roles/edge/defaults/main.yml)"
[ -n "$DECOY_IMAGE" ] || { echo "FAIL decoy-image-pin"; exit 1; }

# 1. Pinned downloads: sha256 verified, also for a cached file.
CACHE="${XVPN_SELFSTEAL_CACHE_DIR:-}"
PEBBLE_URL=https://github.com/letsencrypt/pebble/releases/download/v2.10.3
CERT_URL=https://raw.githubusercontent.com/letsencrypt/pebble/v2.10.3/test/certs
XRAY_URL=https://github.com/XTLS/Xray-core/releases/download/v26.11.9/Xray-linux-64.zip
mkdir -p "$WORK/dl" "$WORK/pebble/certs/localhost" "$WORK/acme" "$WORK/ca" "$WORK/xray"
fetch_pinned() { # <url> <dest> <sha256>
  local url="$1" dest="$2" sha="$3"
  if [ -n "$CACHE" ] && [ -f "$CACHE/$sha" ] && echo "$sha  $CACHE/$sha" | sha256sum -c --quiet - >/dev/null 2>&1; then
    cp "$CACHE/$sha" "$dest"
    return 0
  fi
  curl -fsSL --retry 5 --retry-all-errors --retry-delay 2 -o "$dest" "$url"
  echo "$sha  $dest" | sha256sum -c --quiet - || { echo "FAIL download-sha256 $url"; exit 1; }
  if [ -n "$CACHE" ]; then
    mkdir -p "$CACHE"
    cp "$dest" "$CACHE/$sha"
  fi
}
fetch_pinned "$PEBBLE_URL/pebble-linux-amd64.tar.gz" "$WORK/dl/pebble.tar.gz" 7e33cf3e426b67e9e647c44e8cc91683caa8ab331f7a99e5e27fcee291c4c7e2
fetch_pinned "$PEBBLE_URL/pebble-challtestsrv-linux-amd64.tar.gz" "$WORK/dl/challtestsrv.tar.gz" 00b2c5ef525cd8ad56cda898a7cac6169a10b0fd3f2a7456fe0cec92e7b36cb6
fetch_pinned "$CERT_URL/pebble.minica.pem" "$WORK/pebble/certs/pebble.minica.pem" 0c502e52627ff7de972c7e9e065640103b4589b4e2d23d3fcf21bef1e3c8c67c
fetch_pinned "$CERT_URL/localhost/cert.pem" "$WORK/pebble/certs/localhost/cert.pem" c87fb918d9bac8db11aa54493b5f0cf6e0725a3fe73f617d1c64737e1ab4caf9
fetch_pinned "$CERT_URL/localhost/key.pem" "$WORK/pebble/certs/localhost/key.pem" 0977979255b0e0721c17335c056b627f66a43cf56e5a52f3cda81fb111ecf00e
fetch_pinned "$XRAY_URL" "$WORK/dl/xray.zip" b651f7e1d9966ee2c1b1ee1bf8b52c72771824d3065dce96bbc8bcc19ed95f82
tar -xzf "$WORK/dl/pebble.tar.gz" -C "$WORK/dl"
tar -xzf "$WORK/dl/challtestsrv.tar.gz" -C "$WORK/dl"
python3 -I -m zipfile -e "$WORK/dl/xray.zip" "$WORK/xray"
XRAY="$WORK/xray/xray"
chmod +x "$WORK/dl/pebble-linux-amd64/linux/amd64/pebble" \
  "$WORK/dl/pebble-challtestsrv-linux-amd64/linux/amd64/pebble-challtestsrv" "$XRAY"
cp "$WORK/pebble/certs/pebble.minica.pem" "$WORK/ca/ca.pem"

# 2. Pebble and challtestsrv.
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
for _ in $(seq 1 60); do
  curl -fsS --cacert "$WORK/pebble/certs/pebble.minica.pem" https://127.0.0.1:15000/roots/0 -o "$WORK/issuer-root.pem" 2>/dev/null && break
  sleep 1
done
if [ ! -s "$WORK/issuer-root.pem" ]; then
  for f in pebble.log challtestsrv.log; do echo "--- $f"; tail -n 20 "$WORK/$f" || true; done
  echo "FAIL pebble-root"
  exit 1
fi

# 3. Render the production templates.
ansible-playbook -i localhost, scripts/selfsteal/render.yml -e "xvpn_selfsteal_work=$WORK/r" >"$WORK/render.log" 2>&1 \
  || { cat "$WORK/render.log"; echo "FAIL render"; exit 1; }
R="$WORK/r"
if [ "$BREAK" = "sni-strict" ]; then
  echo "notice: XVPN_SELFSTEAL_BREAK=sni-strict active, expect FAIL foreign-sni"
  grep -q 'sniStrict: true' "$R/dynamic/00-edge.yml" || { echo "sniStrict not found in the rendered copy"; exit 1; }
  sed -i '/sniStrict: true/d' "$R/dynamic/00-edge.yml"
fi

# 4. Decoy and Traefik.
podman run -d --name "$DECOY_C" -p 127.0.0.1:18080:8080 --log-driver k8s-file \
  -v "$R/decoy/site:/usr/share/nginx/html:ro" -v "$R/decoy/conf.d:/etc/nginx/conf.d:ro" \
  "$DECOY_IMAGE" >/dev/null
start_traefik() {
  podman rm -f "$TRAEFIK_C" >/dev/null 2>&1 || true
  podman run -d --name "$TRAEFIK_C" --network host --log-driver k8s-file \
    -v "$R/static:/etc/traefik/static:ro" -v "$R/dynamic:/etc/traefik/dynamic:ro" \
    -v "$WORK/acme:/acme" -v "$WORK/ca:/etc/traefik/ca:ro" \
    -e LEGO_CA_CERTIFICATES=/etc/traefik/ca/ca.pem \
    "$TRAEFIK_IMAGE" --configFile=/etc/traefik/static/traefik.yml >/dev/null
}
start_traefik

# 5. Keys and Xray: generated at runtime, never committed.
KEYS="$("$XRAY" x25519)"
PRIV="$(sed -n 's/^[Pp]rivate[ ]*[Kk]ey:[[:space:]]*//p' <<<"$KEYS" | head -n1)"
PUB="$(sed -n 's/^Password[^:]*:[[:space:]]*//p' <<<"$KEYS" | head -n1)"
[ -n "$PUB" ] || PUB="$(sed -n 's/^[Pp]ublic[ ]*[Kk]ey:[[:space:]]*//p' <<<"$KEYS" | head -n1)"
[ -n "$PRIV" ] && [ -n "$PUB" ] || { echo "FAIL keygen"; exit 1; }
UUID="$(python3 -c 'import uuid;print(uuid.uuid4())')"
SID="$(openssl rand -hex 8)"
export PRIV PUB UUID SID WORK

write_server() { # <xver>
  XVER="$1" python3 - <<'PY'
import json, os

cfg = {
    "log": {"loglevel": "warning"},
    "inbounds": [{
        "listen": "127.0.0.1", "port": 4443, "protocol": "vless",
        "settings": {"clients": [{"id": os.environ["UUID"], "flow": "xtls-rprx-vision"}], "decryption": "none"},
        "streamSettings": {"network": "tcp", "security": "reality", "realitySettings": {
            "target": "127.0.0.1:8443", "xver": int(os.environ["XVER"]), "serverNames": ["node.test"],
            "privateKey": os.environ["PRIV"], "shortIds": [os.environ["SID"]]}},
        "sniffing": {"enabled": True, "destOverride": ["http", "tls"]},
    }],
    "outbounds": [
        {"tag": "DIRECT", "protocol": "freedom", "settings": {"finalRules": [
            {"action": "allow", "network": "tcp", "ip": ["127.0.0.1"], "port": "18090"}]}},
        {"tag": "BLOCK", "protocol": "blackhole"},
    ],
}
json.dump(cfg, open(os.environ["WORK"] + "/xs.json", "w"))
PY
}
python3 - <<'PY'
import json, os

cfg = {
    "log": {"loglevel": "warning"},
    "inbounds": [{"listen": "127.0.0.1", "port": 10808, "protocol": "socks", "settings": {"udp": False}}],
    "outbounds": [{
        "protocol": "vless",
        "settings": {"vnext": [{"address": "127.0.0.1", "port": 4443, "users": [
            {"id": os.environ["UUID"], "encryption": "none", "flow": "xtls-rprx-vision"}]}]},
        "streamSettings": {"network": "tcp", "security": "reality", "realitySettings": {
            "serverName": "node.test", "fingerprint": "chrome", "publicKey": os.environ["PUB"],
            "shortId": os.environ["SID"], "spiderX": "/"}},
    }],
}
json.dump(cfg, open(os.environ["WORK"] + "/xc.json", "w"))
PY
wait_port() { # <port>
  for _ in $(seq 1 30); do
    (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null && return 0
    sleep 1
  done
  return 1
}
XS_PID=""
start_server() {
  [ -z "$XS_PID" ] || { kill "$XS_PID" >/dev/null 2>&1 || true; wait "$XS_PID" 2>/dev/null || true; }
  "$XRAY" run -c "$WORK/xs.json" >>"$WORK/xs.log" 2>&1 &
  XS_PID="$!"
  PIDS+=("$XS_PID")
  wait_port 4443 || { tail -n 20 "$WORK/xs.log"; echo "FAIL xray-server"; exit 1; }
}
write_server 0
start_server
"$XRAY" run -c "$WORK/xc.json" >"$WORK/xc.log" 2>&1 &
PIDS+=("$!")
wait_port 10808 || { tail -n 20 "$WORK/xc.log"; echo "FAIL xray-client"; exit 1; }

# 6. Certificate wait while Xray holds the Reality port (HTTP-01 does not need the TLS port).
cert_probe() {
  echo | openssl s_client -connect 127.0.0.1:8443 -servername "$DOMAIN" -CAfile "$WORK/issuer-root.pem" \
    -verify_return_error -verify_hostname "$DOMAIN" 2>&1 | grep -q 'Verify return code: 0 (ok)'
}
ready=0
for _ in $(seq 1 60); do
  if cert_probe; then ready=1; break; fi
  sleep 2
done
if [ "$ready" -ne 1 ]; then
  podman logs "$TRAEFIK_C" 2>&1 | tail -40 || true
  echo "FAIL cert-issue"
  exit 1
fi

# 7. Loopback sinks.
mkdir -p "$WORK/sink-ok" "$WORK/sink-forbidden"
printf 'xvpn-selfsteal-sink-ok' >"$WORK/sink-ok/marker"
printf 'xvpn-selfsteal-sink-forbidden' >"$WORK/sink-forbidden/marker"
python3 -m http.server 18090 --bind 127.0.0.1 -d "$WORK/sink-ok" >"$WORK/sink-ok.log" 2>&1 &
PIDS+=("$!")
python3 -m http.server 18091 --bind 127.0.0.1 -d "$WORK/sink-forbidden" >"$WORK/sink-forbidden.log" 2>&1 &
PIDS+=("$!")
wait_port 18090 && wait_port 18091 || { echo "FAIL sinks"; exit 1; }

# 8. Cases.
FAILED=()
CASES=0
fail() { echo "FAIL $1"; FAILED+=("$1"); }
sclient() { # <args...>; the handshake output, never hangs
  timeout 20 openssl s_client "$@" </dev/null 2>&1 || true
}
via_client() { # <url>
  curl -sS --max-time 15 --socks5-hostname 127.0.0.1:10808 "$1" 2>&1 || true
}

CASES=$((CASES + 1))
code="$(curl -sS --max-time 20 --resolve "$DOMAIN:4443:127.0.0.1" --cacert "$WORK/issuer-root.pem" -o /dev/null \
  -w '%{http_code} %{http_version}' "https://$DOMAIN:4443/" 2>&1 || true)"
out="$(sclient -connect 127.0.0.1:4443 -servername "$DOMAIN" -alpn h2 -CAfile "$WORK/issuer-root.pem")"
if [ "$code" = "200 2" ] && grep -q 'TLSv1.3' <<<"$out" && grep -q 'ALPN protocol: h2' <<<"$out" \
  && grep -q 'Verify return code: 0 (ok)' <<<"$out"; then
  echo "ok valid-sni"
else
  fail valid-sni
  echo "http: $code"; echo "$out" | tail -n 25
fi

# A handshake that leaks nothing: an alert or no certificate, never the Traefik default certificate or its 404.
no_leak() { # <id> <output>
  if { grep -q 'alert number 112' <<<"$2" || grep -q 'no peer certificate available' <<<"$2"; } \
    && ! grep -q 'TRAEFIK DEFAULT CERT' <<<"$2" && ! grep -q '404 page not found' <<<"$2"; then
    echo "ok $1"
  else
    fail "$1"
    echo "$2" | tail -n 25
  fi
}
e2e_ok() { [ "$(via_client http://127.0.0.1:18090/marker)" = "xvpn-selfsteal-sink-ok" ]; }
# retry the client request until it succeeds (restarts need a moment)
e2e_wait() {
  local _
  for _ in $(seq 1 15); do
    e2e_ok && return 0
    sleep 2
  done
  return 1
}

CASES=$((CASES + 1))
out="$(sclient -connect 127.0.0.1:8443 -servername "$DOMAIN" -CAfile "$WORK/issuer-root.pem" -verify_hostname "$DOMAIN")"
out2="$(sclient -connect 127.0.0.1:8443 -servername evil.invalid)"
if grep -q 'Verify return code: 0 (ok)' <<<"$out" && ! grep -q 'TRAEFIK DEFAULT CERT' <<<"$out2" \
  && { grep -q 'alert number 112' <<<"$out2" || grep -q 'no peer certificate available' <<<"$out2"; }; then
  echo "ok direct-loopback"
else
  fail direct-loopback
  echo "$out" | tail -n 15; echo "$out2" | tail -n 15
fi

CASES=$((CASES + 1))
no_leak foreign-sni "$(sclient -connect 127.0.0.1:4443 -servername evil.invalid)"
CASES=$((CASES + 1))
no_leak no-sni "$(sclient -connect 127.0.0.1:4443 -noservername)"

CASES=$((CASES + 1))
got="$(via_client http://127.0.0.1:18090/marker)"
if [ "$got" = "xvpn-selfsteal-sink-ok" ]; then
  echo "ok client-e2e"
else
  fail client-e2e
  echo "got: $got"; tail -n 20 "$WORK/xs.log" "$WORK/xc.log"
fi

CASES=$((CASES + 1))
got="$(via_client http://127.0.0.1:18091/marker)"
sleep 1
if ! grep -q 'xvpn-selfsteal-sink-forbidden' <<<"$got" && grep -qi 'finalrule' "$WORK/xs.log"; then
  echo "ok client-private-blocked"
else
  fail client-private-blocked
  echo "got: $got"; tail -n 20 "$WORK/xs.log"
fi

CASES=$((CASES + 1))
podman stop -t 2 "$TRAEFIK_C" >/dev/null
down_ok=0
e2e_ok || down_ok=1
start_traefik
ready=0
for _ in $(seq 1 30); do
  if cert_probe; then ready=1; break; fi
  sleep 2
done
if [ "$down_ok" -eq 1 ] && [ "$ready" -eq 1 ] && e2e_wait; then
  echo "ok traefik-down"
else
  fail traefik-down
  echo "failed while down: $down_ok (1 = ok), cert back: $ready"
fi

# xver pairing: only the rendered copy under $WORK changes, never a role template.
CASES=$((CASES + 1))
write_server 1
start_server
if e2e_ok; then
  fail xver1-mismatch
else
  echo "ok xver1-mismatch"
fi

CASES=$((CASES + 1))
python3 - "$R/static/traefik.yml" <<'PY'
import sys

path = sys.argv[1]
text = open(path).read()
old = '    address: "127.0.0.1:8443"\n'
if old not in text:
    sys.exit("websecure address line not found in the rendered copy")
new = old + "    proxyProtocol:\n      trustedIPs:\n        - 127.0.0.1/32\n"
open(path, "w").write(text.replace(old, new, 1))
PY
start_traefik
code="000"
if e2e_wait; then
  code="$(curl -sS --max-time 20 --resolve "$DOMAIN:4443:127.0.0.1" --cacert "$WORK/issuer-root.pem" -o /dev/null \
    -w '%{http_code}' "https://$DOMAIN:4443/" 2>&1 || true)"
fi
if [ "$code" = "200" ]; then
  echo "ok xver1-proxyprotocol"
else
  fail xver1-proxyprotocol
  echo "http: $code"; podman logs "$TRAEFIK_C" 2>&1 | tail -n 15; tail -n 15 "$WORK/xs.log"
fi

if [ "${#FAILED[@]}" -gt 0 ]; then
  echo "selfsteal: ${#FAILED[@]} case(s) failed: ${FAILED[*]}"
  exit 1
fi
echo "selfsteal: OK ($CASES cases)"
