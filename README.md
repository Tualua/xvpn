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
