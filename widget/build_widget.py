"""
Injects model/renewal_model.json into renewal_widget_template.html to produce
renewal_widget.html, a single self-contained file with no build step needed to use it
(just open it in a browser). Run this after scripts/export_model.py if you've retrained.

Run from the repo root: python widget/build_widget.py
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

template_path = os.path.join(ROOT, "widget", "renewal_widget_template.html")
model_path = os.path.join(ROOT, "model", "renewal_model.json")
out_path = os.path.join(ROOT, "widget", "renewal_widget.html")

template = open(template_path, encoding="utf-8").read()
model_json = open(model_path, encoding="utf-8").read()
out = template.replace("%%MODEL_JSON%%", model_json)

open(out_path, "w", encoding="utf-8").write(out)
print(f"Wrote {out_path} ({len(out) / 1024:.1f} KB)")
