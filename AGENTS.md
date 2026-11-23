# Public shell contributor guide

- `distros/` contains image recipes. `guest/` contains public guest integration and `schema/` defines public image metadata.
- `components/` records build inputs. `vendor/` contains vendored source materials. `scripts/` and `.github/` contain build and release tooling, with checks in `tests/`.
- Follow the [local build instructions](docs/local-build.md). Run `python3 -m unittest discover -s tests` and `python3 scripts/check-provenance.py`. Match surrounding formatting and check changed shell scripts with `bash -n`.
- Keep public changes focused. Use English for repository prose and commit messages, preserve license notices, and report the checks run.
- The core Host/Guest transport and rendering components are supplied as precompiled closed-source binaries. Public shell changes must preserve and use their public contract interfaces.
