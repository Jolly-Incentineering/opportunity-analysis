"""
config_install.py — Version-aware install for plugin data files.

Protects user-customized template configs and benchmarks during plugin updates.

Behaviour:
  - Fresh install (dest missing):         copy src → dest, record in manifest
  - Re-run, plugin unchanged:             skip (no-op)
  - Re-run, plugin updated, no user edits: overwrite dest, update manifest
  - Re-run, plugin updated, user edited:  save src as dest.plugin_update.json,
                                          print warning — user merges manually

Usage:
    python config_install.py --src <plugin_file> --dest <workspace_file>
                             --manifest <manifest.json> --plugin-version <version>
"""
import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path


def _md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description="Version-aware config file installer")
    p.add_argument("--src",            required=True, help="Source file (from plugin)")
    p.add_argument("--dest",           required=True, help="Destination file (in workspace)")
    p.add_argument("--manifest",       required=True, help="Path to template_manifest.json")
    p.add_argument("--plugin-version", required=True, help="Current plugin version string")
    args = p.parse_args()

    src     = Path(args.src)
    dest    = Path(args.dest)
    mf_path = Path(args.manifest)

    if not src.exists():
        print(json.dumps({"action": "skipped", "file": src.name, "reason": "src_missing"}))
        return

    manifest = json.loads(mf_path.read_text(encoding="utf-8")) if mf_path.exists() else {}
    dest.parent.mkdir(parents=True, exist_ok=True)

    if not dest.exists():
        # Fresh install
        shutil.copy2(src, dest)
        manifest[src.name] = {
            "plugin_version":  args.plugin_version,
            "installed_hash":  _md5(dest),
        }
        mf_path.parent.mkdir(parents=True, exist_ok=True)
        mf_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(json.dumps({"action": "installed", "file": src.name}))
        return

    prev = manifest.get(src.name, {})

    if prev.get("plugin_version") == args.plugin_version:
        # Plugin hasn't changed this file since last install
        print(json.dumps({"action": "skipped", "file": src.name, "reason": "no_plugin_update"}))
        return

    # Plugin has a newer version — check whether user modified the workspace copy
    workspace_hash = _md5(dest)

    if workspace_hash == prev.get("installed_hash", ""):
        # No user edits — safe to overwrite
        shutil.copy2(src, dest)
        manifest[src.name] = {
            "plugin_version":  args.plugin_version,
            "installed_hash":  _md5(dest),
        }
        mf_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(json.dumps({"action": "updated", "file": src.name}))
    else:
        # User has local edits — save update alongside, don't overwrite
        update_path = dest.with_suffix(".plugin_update.json")
        shutil.copy2(src, update_path)
        print(json.dumps({
            "action":          "conflict",
            "file":            src.name,
            "update_saved_as": str(update_path),
            "message":         (
                f"{src.name} has local edits. "
                f"Plugin update saved as {update_path.name} — "
                "merge manually then delete the .plugin_update.json file."
            ),
        }))


if __name__ == "__main__":
    main()
