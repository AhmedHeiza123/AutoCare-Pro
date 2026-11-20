"""Publishes the inventory UI (readable sources in ../inventory-src) into ../dist without Node.

    python build_inventory_ui.py            # copies the sources, adds a cache-busting version to every import, writes dist/inventory.html

The sources are plain ES modules; nothing is minified or transpiled, so what is served is exactly what is in inventory-src.
Re-run it after editing a source file. It never touches the compiled application bundles (it only adds files)."""
import hashlib
import re
import sys
from pathlib import Path

FRONTEND = Path(__file__).resolve().parents[1]
SRC, DIST = FRONTEND / "inventory-src", FRONTEND / "dist"
OUT = DIST / "assets" / "inventory"
MODULES = ["core.js", "screens-catalog.js", "screens-purchasing.js", "screens-stock.js", "main.js", "integration.js"]


def main() -> int:
    missing = [m for m in (*MODULES, "inventory.css") if not (SRC / m).is_file()]
    if missing:
        print("missing source files:", missing)
        return 1
    digest = hashlib.sha256()
    for name in sorted((*MODULES, "inventory.css")):
        digest.update((SRC / name).read_bytes())
    version = digest.hexdigest()[:10]
    OUT.mkdir(parents=True, exist_ok=True)
    for name in MODULES:
        text = (SRC / name).read_text(encoding="utf-8")
        text = re.sub(r"""(from\s+['"])(\./[\w-]+\.js)(['"])""", lambda m: f"{m.group(1)}{m.group(2)}?v={version}{m.group(3)}", text)
        (OUT / name).write_text(text, encoding="utf-8", newline="\n")
    (OUT / "inventory.css").write_text((SRC / "inventory.css").read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
    (OUT / "integration.css").write_text((SRC / "integration.css").read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
    index = (DIST / "index.html").read_text(encoding="utf-8")
    base_css = re.search(r'href="(/assets/index-[\w-]+\.css)"', index)
    html = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>AutoCare Pro - Inventory</title>
    {f'<link rel="stylesheet" href="{base_css.group(1)}">' if base_css else ''}
    <link rel="stylesheet" href="/assets/inventory/inventory.css?v={version}">
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/assets/inventory/main.js?v={version}"></script>
  </body>
</html>
"""
    (DIST / "inventory.html").write_text(html, encoding="utf-8", newline="\n")
    # the small integration script is loaded by the main application page (adds the menu link and the part-source buttons)
    marker = "<!-- inventory-integration -->"
    tag = f'{marker}<script type="module" src="/assets/inventory/integration.js?v={version}"></script>'
    if marker in index:
        index = re.sub(re.escape(marker) + r'<script type="module" src="[^"]+"></script>', tag, index)
    else:
        index = index.replace("</head>", f"    {tag}\n  </head>")
    (DIST / "index.html").write_text(index, encoding="utf-8", newline="\n")
    print(f"published inventory UI version {version}: {len(MODULES)} modules + css + inventory.html; index.html loads integration.js")
    return 0


if __name__ == "__main__":
    sys.exit(main())


