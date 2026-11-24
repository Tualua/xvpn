# API Coverage — Phase 01: Rootless-фундамент и тестовый стенд

No external API integration: rootless Podman/SELinux/firewalld foundation and Molecule bench; roles call no external API.

## Why the detector fired

The signals come from plan prose only: the Galaxy API and the Vagrant Cloud API are read at planning/development time to verify version pins and box checksums (01-02, 01-11), and `gh api` appears in 01-03 as a forbidden pattern in a grep guard. The Remnawave Panel API integration starts in a later phase and gets its own coverage matrix there.
