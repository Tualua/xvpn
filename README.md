# xvpn.remnawave

Ansible collection for deploying Remnawave Panel and Remnawave Node on Rocky/Alma Linux 10
(SELinux enforcing, rootless Podman with Quadlet). Nodes use VLESS Reality in self-steal mode
behind a plausible decoy site, and a dedicated client group can reach the node's internal LAN.

## Usage

```bash
ansible-galaxy collection install -r requirements.yml
ansible-playbook -i inventory xvpn.remnawave.foundation
```

## Development

```bash
bash scripts/check.sh        # ansible-lint, yamllint (mandatory in CI), syntax-check, collection build
molecule test -s container   # container-tier Molecule scenario
```
