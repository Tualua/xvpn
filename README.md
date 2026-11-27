# xvpn.remnawave

Ansible collection for deploying Remnawave Panel and Remnawave Node on Rocky/Alma Linux 10
(SELinux enforcing, rootless Podman with Quadlet). Nodes use VLESS Reality in self-steal mode
behind a plausible decoy site, and a dedicated client group can reach the node's internal LAN.

## Usage

```bash
ansible-galaxy collection install -r requirements.yml
ansible-playbook -i inventory xvpn.remnawave.foundation
```

### Preflight checks

Preflight is a read-only first play: on failure it reports every problem in one message and changes nothing on the host.

| Variable | Default | Meaning |
|----------|---------|---------|
| `xvpn_preflight_domains` | `[]` | Domains whose A record must point to this host. The A-record check runs only when the list is non-empty. With the default `xvpn_preflight_dns_check: true` and no domains, preflight prints the warning `A-record check skipped: xvpn_preflight_domains is empty` and continues. |
| `xvpn_preflight_dns_check` | `true` | `false` disables every DNS check. |
| `xvpn_public_interface` | default-route interface | Interface whose IPv4 addresses (primary and secondary) are the expected public IPs. |
| `xvpn_public_ip` | empty | Expected public IPv4 given directly; takes precedence over the interface. |
| `xvpn_preflight_ports` | `[80, 443]` | TCP ports that must be free or held by an accepted service user. |
| `xvpn_preflight_service_users` | `[rw-edge, rw-panel, rw-node]` | Users whose listeners are accepted, so a re-run on a converged host passes. The effective set also includes every `xvpn_podman_rootless_users` name from the inventory. |
| `xvpn_preflight_podman_min_version` | `5.4` | Installed (or newest available) Podman must be at least this version. |

Enable the A-record check by naming the domains, or skip DNS entirely:

```bash
ansible-playbook -i inventory xvpn.remnawave.foundation -e '{"xvpn_preflight_domains": ["node1.example.com"]}'
ansible-playbook -i inventory xvpn.remnawave.foundation -e xvpn_preflight_dns_check=false
```

The read-only checks can also run alone, with the same `-e` options:

```bash
ansible-playbook -i inventory xvpn.remnawave.preflight
```

Notes:

- DNS and proxy setup is the operator's responsibility; no CDN or proxy detection is done. A wrong A record fails preflight unless you set `xvpn_preflight_dns_check: false`. AAAA mismatches only produce a warning.
- The A-record check uses the target host's own resolver (NSS), not a specific DNS server.
- Internationalised domains must be given in punycode (`xn--...`) form.
- `rw-panel` and `rw-node` in the `xvpn_preflight_service_users` default are forward-declared for later phases and harmless before those users exist.
- Play 1 of `xvpn.remnawave.foundation` carries the tag `preflight`: `--tags preflight` runs only the read-only checks, `--skip-tags preflight` skips them (not recommended).

## Panel host

One command deploys the Panel host: Traefik with Let's Encrypt, the Remnawave backend with PostgreSQL and Valkey, the first administrator, an automation API token and the subscription page.

```bash
ansible-galaxy collection install -r requirements.yml
ansible-playbook -i inventory xvpn.remnawave.panel
```

`xvpn.remnawave.site` runs the same Panel play (node plays are added later). A re-run changes nothing and never touches the stored secrets.

Inventory (YAML), one host in the group `remnawave_panel`:

```yaml
all:
  children:
    remnawave_panel:
      hosts:
        panel1:
          ansible_host: 203.0.113.10
      vars:
        xvpn_panel_domain: panel.example.com
        xvpn_subscription_domain: sub.example.com
        xvpn_edge_acme_email: admin@example.com
        xvpn_panel_admin_password: <from vault>   # optional, generated on first run when empty
```

Both FQDNs are required and must differ; their A records must point to the host before the run, because Let's Encrypt validates them over HTTP-01 on port 80.

| Variable | Default | Meaning |
|----------|---------|---------|
| `xvpn_panel_domain` | none (required) | Public FQDN of the Panel. Placeholder names such as `example.com` are rejected. |
| `xvpn_subscription_domain` | none (required while the page is enabled) | Public FQDN of the subscription page. |
| `xvpn_panel_subscription_enabled` | `true` | Deploy the subscription page. `false` stops and removes it. |
| `xvpn_edge_acme_ca` | `production` | `production`, `staging` (untrusted certificates, for testing) or `custom`. |
| `xvpn_edge_acme_ca_server` | empty | ACME directory URL, required with `custom`. |
| `xvpn_edge_acme_email` | empty | Contact address for Let's Encrypt. |
| `xvpn_panel_admin_username` | `rwoperator` | Login of the first administrator. |
| `xvpn_panel_admin_password`, `xvpn_panel_app_secret`, `xvpn_panel_postgres_password`, `xvpn_panel_metrics_password` | empty (generated) | Optional vault inputs, shown as `<from vault>`. Placeholders and weak values are rejected. |
| `xvpn_panel_gate_path`, `xvpn_panel_gate_cookie_name`, `xvpn_panel_gate_cookie_value` | empty (generated) | Optional vault inputs of the entry gate. |
| `xvpn_panel_gate_cookie_max_age` | `2592000` | Lifetime of the gate cookie in seconds. |
| `xvpn_panel_gate_cookie_samesite` | `Strict` | `Strict` or `Lax`, see Admin entry. |
| `xvpn_panel_api_token_days` | `3650` | Lifetime of the automation API token in days. |
| `xvpn_panel_bootstrap_retries` | `60` | Attempts, 5 seconds apart, to wait for the backend during the bootstrap. |
| `xvpn_panel_failure_log_dir` | `/var/log/xvpn` | Root-only directory (0700) for `panel-start-failure.log`, written when the stack start fails and removed after the next successful start. Must be a dedicated absolute directory below `/var/log`, `/opt` or `/srv` (for example `/var/log/xvpn`), with no `.`, `..` or empty components and no trailing slash, and with components that use only letters, digits, `_`, `-` and `.` and do not start with `.`; it must not be the service user's home or one of its parents. An existing directory is accepted only when it is already a real directory owned by root:root with mode 0700, so no existing system or service directory is taken over. |
| `xvpn_edge_decoy_src` | empty | Directory on the controller with your own decoy site; empty uses a neutral built-in page. |
| `xvpn_panel_backend_image`, `xvpn_panel_postgres_image`, `xvpn_panel_valkey_image`, `xvpn_panel_subscription_image`, `xvpn_edge_traefik_image`, `xvpn_edge_decoy_image` | pinned exact tags | Container images; bump them by changing the variable. |

### Files on the Panel host

| Path | Content |
|------|---------|
| `/var/lib/xvpn/rw-panel/secrets/panel-secrets.yml` | Generated secrets, mode 0600, owner `rw-panel` |
| `/var/lib/xvpn/rw-panel/secrets/api-token` | Automation API token, mode 0600 |
| `/var/lib/xvpn/rw-panel/secrets/admin-url` | Admin entry URL, mode 0600 |
| `/var/lib/xvpn/rw-edge/traefik/` | Traefik state including `acme.json` (certificates), owner `rw-edge` |
| `/var/log/xvpn/panel-start-failure.log` | Journals and container logs of a failed stack start, mode 0600, owner root; may contain environment values, removed after a successful start. |

Back these files up: a lost secrets file together with a surviving database volume stops the run on purpose instead of generating values that no longer match the database.

### Secrets

Secrets are generated once on the host and stored in `panel-secrets.yml`; the run prints no secret value. A vault value overrides generation. v1 has no rotation: a vault value that differs from the one already applied fails the run, except the gate values, which replace the stored ones.

### Admin entry

Read the entry URL on the Panel host:

```bash
sudo cat /var/lib/xvpn/rw-panel/secrets/admin-url
```

Opening it sets the gate cookie; without the cookie the Panel domain shows a neutral decoy site. `/api/*` except `/api/auth/*` stays reachable with an API token, and `/api/sub/*` stays public. With `Strict` the cookie is not sent on links from other sites, so only password login works and a link from another site lands on the decoy; `Lax` relaxes that.

### Subscription page

The page runs on its own domain and authenticates to the Panel with the automation token. Set `xvpn_panel_subscription_enabled: false` to switch it off: the run stops the page and removes its unit, its environment file and its route, and the Panel serves subscriptions from `<panel-domain>/api/sub`. Setting it back to `true` restores the page.

### Ports

Ports 80 and 443 are opened in firewalld. The backend (3000), the subscription page (3010) and the decoy (18080) listen on `127.0.0.1` only.

### Known limitations

- `SameSite=Strict` allows password login only; OAuth2 and Telegram callbacks land on the decoy.
- There is no secret rotation in v1 except the gate secret.
- One full-scope API token (lifetime `xvpn_panel_api_token_days`, default 3650 days) is held by the internet-facing subscription page.
- The Traefik access log never records request paths, so path-based fail2ban jails cannot work on it.
- `FRONT_END_DOMAIN=*` is only the backend's CORS origin with credentials off; the UI is same-origin.
- Real client IPs are logged for direct clients only, not behind a CDN or another proxy.

## Development

```bash
bash scripts/check.sh        # ansible-lint, yamllint (mandatory in CI), syntax-check, collection build
molecule test -s container   # container-tier Molecule scenario
```

## Testing

Tests run in three tiers.

| Tier | Command | Needs | Covers |
|------|---------|-------|--------|
| Static | `bash scripts/check.sh` | nothing but the Python tooling | ansible-lint, yamllint, syntax-check, collection build; no containers |
| Container | `molecule test -s container`, `molecule test -s preflight` | Podman | role logic, templates, Quadlet generator dry run, idempotence |
| VM | `molecule test -s vm` | Linux host with `/dev/kvm`, libvirt, Vagrant and the vagrant-libvirt plugin | real AlmaLinux 10 and Rocky 10 VMs: SELinux enforcing, reboot survival, zero AVC |

Run a single distribution with `molecule test -s vm --platform-name alma10` (or `rocky10`).

CI notes:

- The `molecule-vm` workflow runs on pull requests to `main`, nightly and on demand. It is not a required merge check until it has five consecutive green runs.
- The workflow's `MODE="0666"` udev rule for `/dev/kvm` is for ephemeral GitHub-hosted runners only. Do not copy it to self-hosted runners.
- Rootless services bind port 80, so the `podman_rootless` role sets the host-wide `net.ipv4.ip_unprivileged_port_start=80`; every local user can then bind ports 80 and above.
- Both VM legs run Podman 6.1.x. Podman 5.4-5.8 is allowed by the preflight floor but is untested beyond the version check (risk accepted, VM coverage deferred to Phase 5, QA-06).
- `fedora.linux_system_roles.podman` additionally installs `iptables-nft` on EL10. This is harmless on the nftables-only Podman 6 host but expected in package lists.
- `xvpn_verify_expected_ports` in `extensions/molecule/shared/verify_common.yml` is the cross-phase contract of the exact-set firewall check: every later phase that adds a port must extend it in its scenario vars.
- Phase 1 adds no SELinux boolean, port or module; any future need must be proven by the zero-AVC check first.
- `passt-selinux` is installed only when the enabled repositories offer it (EL10.3 and later).
