"""Web app klasifikasi Dry Bean (Random Forest) dengan Flask. Siap deploy ke Railway."""
import json
import logging
import math
import os
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from flask import Flask, jsonify, render_template, request

BASE = Path(__file__).resolve().parent
app = Flask(__name__)
log = logging.getLogger("drybean")
logging.basicConfig(level=logging.INFO)

model, meta, LOAD_ERROR = None, None, None
try:
    model = joblib.load(BASE / "model" / "rf_dry_bean.joblib")
    meta = json.loads((BASE / "model" / "metadata.json").read_text(encoding="utf-8"))
    try:
        import sklearn
        trained = meta.get("sklearn_version")
        if trained and trained != sklearn.__version__:
            log.warning("Versi scikit-learn berbeda: model dilatih dengan %s, server memakai %s. "
                        "Samakan di requirements.txt.", trained, sklearn.__version__)
    except Exception:
        pass
except Exception as exc:  # model belum ada / rusak
    LOAD_ERROR = f"{type(exc).__name__}: {exc}"
    log.error("Model gagal dimuat: %s", LOAD_ERROR)

PALETTE = ["#E4572E", "#7A5CFA", "#F2A900", "#0E7C66", "#2E86DE", "#D6336C", "#6C8E23"]
LABELS = {
    "Area": "Luas (Area)", "Perimeter": "Keliling (Perimeter)", "MajorAxisLength": "Sumbu panjang",
    "MinorAxisLength": "Sumbu pendek", "ConvexArea": "Luas cembung", "EquivDiameter": "Diameter setara",
    "AspectRatio": "Rasio aspek", "Eccentricity": "Eksentrisitas", "Extent": "Extent", "Solidity": "Solidity",
    "Roundness": "Kebulatan (Roundness)", "Compactness": "Kekompakan (Compactness)",
    "ShapeFactor1": "Faktor bentuk 1", "ShapeFactor2": "Faktor bentuk 2",
    "ShapeFactor3": "Faktor bentuk 3", "ShapeFactor4": "Faktor bentuk 4",
}
GROUPS = [
    ("Ukuran biji", "Dimensi dalam piksel dari citra biji",
     ["Area", "Perimeter", "MajorAxisLength", "MinorAxisLength", "ConvexArea", "EquivDiameter"]),
    ("Bentuk biji", "Seberapa lonjong, bulat, dan padat bentuknya",
     ["AspectRatio", "Eccentricity", "Extent", "Solidity", "Roundness", "Compactness"]),
    ("Faktor bentuk", "Rasio turunan dari ukuran dan luas",
     ["ShapeFactor1", "ShapeFactor2", "ShapeFactor3", "ShapeFactor4"]),
]


def build_config():
    feats, classes = meta["feature_names"], meta["class_names"]
    fmin, fmax, fmed = meta["feature_min"], meta["feature_max"], meta["feature_median"]
    by_lower = {f.lower(): f for f in feats}
    label_of = {k.lower(): v for k, v in LABELS.items()}

    def pretty(name):
        return label_of.get(name.lower(), name)

    def describe(name):
        lo, hi = float(fmin[name]), float(fmax[name])
        step = (hi - lo) / 1000 or 0.001
        return {"name": name, "label": pretty(name), "min": lo, "max": hi,
                "median": float(fmed[name]), "step": step,
                "decimals": int(max(0, min(6, math.ceil(-math.log10(step)))))}

    known = {f.lower() for _, _, fs in GROUPS for f in fs}
    groups = [{"title": t, "sub": sub, "features": [describe(by_lower[f.lower()]) for f in fs if f.lower() in by_lower]}
              for t, sub, fs in GROUPS]
    extra = [f for f in feats if f.lower() not in known]
    if extra:
        groups.append({"title": "Fitur lain", "sub": "", "features": [describe(f) for f in extra]})
    groups = [g for g in groups if g["features"]]

    fi = sorted(meta["feature_importance"].items(), key=lambda kv: -kv[1])[:10]
    top = fi[0][1] or 1
    show = [by_lower[f] for f in ["area", "aspectratio", "roundness"] if f in by_lower] or feats[:3]
    return {
        "features": [f for g in groups for f in g["features"]],
        "groups": groups,
        "classes": [{"name": c, "label": c.title(), "color": PALETTE[i % len(PALETTE)],
                     "median": meta["class_median"][c]} for i, c in enumerate(classes)],
        "importance": [{"label": pretty(n), "value": v, "pct": v / top * 100} for n, v in fi],
        "profile_cols": [pretty(f) for f in show],
        "profile": [{"label": c.title(), "values": [meta["class_median"][c][f] for f in show]} for c in classes],
        "accuracy": meta["test_accuracy"], "macro_f1": meta["macro_f1"],
        "n_estimators": meta["best_params"]["n_estimators"],
        "max_depth": meta["best_params"]["max_depth"],
    }


@app.get("/")
def index():
    if model is None:
        return render_template("error.html", detail=LOAD_ERROR), 503
    return render_template("index.html", cfg=build_config())


@app.post("/api/predict")
def predict():
    if model is None:
        return jsonify(error="Model belum dimuat."), 503
    payload = request.get_json(silent=True) or {}
    values = payload.get("features")
    if not isinstance(values, dict):
        return jsonify(error="Kirim JSON {\"features\": {...}}."), 400
    row = {}
    for f in meta["feature_names"]:
        try:
            v = float(values[f])
        except (KeyError, TypeError, ValueError):
            return jsonify(error=f"Nilai fitur '{f}' tidak ada atau bukan angka."), 400
        if not math.isfinite(v):
            return jsonify(error=f"Nilai fitur '{f}' tidak valid."), 400
        row[f] = v
    proba = model.predict_proba(pd.DataFrame([row], columns=meta["feature_names"]))[0]
    names = meta["class_names"]
    classes = [names[int(c)] if isinstance(c, (int, np.integer)) else str(c) for c in model.classes_]
    ranked = sorted(zip(classes, proba), key=lambda kv: -kv[1])
    return jsonify(top=ranked[0][0], confidence=float(ranked[0][1]),
                   probabilities=[{"class": c, "p": float(p)} for c, p in ranked])


@app.get("/health")
def health():
    return jsonify(status="ok" if model is not None else "model-missing"), (200 if model is not None else 503)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
