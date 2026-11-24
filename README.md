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

## Development

```bash
bash scripts/check.sh        # ansible-lint, yamllint (mandatory in CI), syntax-check, collection build
molecule test -s container   # container-tier Molecule scenario
```
