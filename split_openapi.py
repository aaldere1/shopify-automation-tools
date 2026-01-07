#!/usr/bin/env python3
"""
Split a large openapi.json into multiple smaller JSON files with $refs.
Usage: python3 split_openapi.py
"""
import os
import shutil
import json

def sanitize(name: str) -> str:
    """Sanitize an OpenAPI key to a safe filename."""
    s = name.strip("/").replace("/", "_")
    s = s.replace("{", "").replace("}", "")
    if not s:
        s = "root"
    return s

def main():
    src = "openapi.json"
    out_dir = "openapi_split"
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    with open(src, "r") as f:
        data = json.load(f)
    os.makedirs(out_dir, exist_ok=True)
    # Split paths
    paths = data.get("paths", {})
    paths_dir = os.path.join(out_dir, "paths")
    os.makedirs(paths_dir, exist_ok=True)
    root_paths = {}
    for path, spec in paths.items():
        filename = sanitize(path) + ".json"
        filepath = os.path.join(paths_dir, filename)
        with open(filepath, "w") as pf:
            json.dump(spec, pf, indent=2)
        root_paths[path] = {"$ref": f"./paths/{filename}"}
    # Split components
    comps = data.get("components", {})
    root_components = {}
    if comps:
        comp_dir = os.path.join(out_dir, "components")
        os.makedirs(comp_dir, exist_ok=True)
        for comp_type, entries in comps.items():
            type_dir = os.path.join(comp_dir, comp_type)
            os.makedirs(type_dir, exist_ok=True)
            root_components[comp_type] = {}
            for name, spec in entries.items():
                filename = name + ".json"
                filepath = os.path.join(type_dir, filename)
                with open(filepath, "w") as cf:
                    json.dump(spec, cf, indent=2)
                root_components[comp_type][name] = {"$ref": f"./components/{comp_type}/{filename}"}
    # Split webhooks
    webhooks = data.get("x-webhooks", {})
    root_webhooks = {}
    if webhooks:
        wh_dir = os.path.join(out_dir, "x-webhooks")
        os.makedirs(wh_dir, exist_ok=True)
        for name, spec in webhooks.items():
            filename = name + ".json"
            filepath = os.path.join(wh_dir, filename)
            with open(filepath, "w") as wf:
                json.dump(spec, wf, indent=2)
            root_webhooks[name] = {"$ref": f"./x-webhooks/{filename}"}
    # Build root document
    root = {}
    for key in ("openapi", "info", "servers", "tags"):
        if key in data:
            root[key] = data[key]
    root["paths"] = root_paths
    if root_components:
        root["components"] = root_components
    if root_webhooks:
        root["x-webhooks"] = root_webhooks
    # Write root openapi.json
    out_root = os.path.join(out_dir, "openapi.json")
    with open(out_root, "w") as rf:
        json.dump(root, rf, indent=2)
    print(f"Split complete: {out_dir}")

if __name__ == "__main__":
    main()