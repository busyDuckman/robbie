"""
Resolves the config files in each given folder into the flat settings services see.

Config files have a `default:` section and an optional `local:` section. For each file
two resolved copies are written:
  <out>/default/<folder>/<name>.yaml   the default section only (deployed to the Pi)
  <out>/local/<folder>/<name>.yaml     local merged over default (mounted by just up)
Nested mappings merge key by key; anything else (values, lists) is replaced.

Files are overwritten in place and the folders are never recreated, because running
containers bind mount them and would otherwise keep seeing the old copy.

    python3 scripts/resolve_config.py .config config/robbie_agent config/robbie_services
"""
import argparse
import pathlib
import sys

import yaml

SECTIONS = {"default", "local"}


def merge(base, override):
    if isinstance(base, dict) and isinstance(override, dict):
        merged = dict(base)
        for key, value in override.items():
            merged[key] = merge(base[key], value) if key in base else value
        return merged
    return override


def resolve(config, local):
    unknown = set(config) - SECTIONS
    if unknown:
        raise ValueError(f"unknown top level sections: {', '.join(sorted(unknown))}")
    if "default" not in config:
        raise ValueError("no default section")
    resolved = config["default"] or {}
    if local and config.get("local"):
        resolved = merge(resolved, config["local"])
    return resolved


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("out", help="folder to write default/ and local/ into")
    parser.add_argument("sources", nargs="+", help="folders of config files with default and local sections")
    args = parser.parse_args()

    out = pathlib.Path(args.out)
    for source in map(pathlib.Path, args.sources):
        names = {path.name for path in source.glob("*.yaml")}
        for variant in ("default", "local"):
            for stale in (out / variant / source.name).glob("*.yaml"):
                if stale.name not in names:
                    stale.unlink()

        for path in sorted(source.glob("*.yaml")):
            config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            for variant in ("default", "local"):
                try:
                    resolved = resolve(config, local=(variant == "local"))
                except ValueError as e:
                    sys.exit(f"{path}: {e}")
                target = out / variant / source.name / path.name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(yaml.safe_dump(resolved, sort_keys=False), encoding="utf-8")


if __name__ == "__main__":
    main()
