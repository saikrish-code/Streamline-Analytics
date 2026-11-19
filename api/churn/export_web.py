"""Export the current churn pipeline's fitted parameters to JSON for in-process scoring
in the Next.js dashboard (dashboard/lib/churn-model.json).

Run: python -m api.churn.export_web
"""

from __future__ import annotations

import json
from pathlib import Path

from api.churn.registry import load_current_model

OUT = Path(__file__).resolve().parents[2] / "dashboard" / "lib" / "churn-model.json"


def main() -> None:
    bundle = load_current_model()
    steps = bundle.model.named_steps
    imputer, scaler = steps["imputer"], steps["scaler"]
    clf = bundle.model.steps[-1][1]
    positive = list(clf.classes_).index(1)
    sign = 1.0 if positive == 1 else -1.0
    indicator = imputer.indicator_
    params = {
        "model_version": bundle.metadata["model_version"],
        "decision_threshold": float(bundle.metadata.get("decision_threshold", 0.5)),
        "features": list(bundle.metadata["feature_columns"]),
        "medians": [float(v) for v in imputer.statistics_],
        "indicator_features": [int(i) for i in indicator.features_] if indicator is not None else [],
        "scaler_mean": [float(v) for v in scaler.mean_],
        "scaler_scale": [float(v) for v in scaler.scale_],
        "coef": [sign * float(v) for v in clf.coef_[0]],
        "intercept": sign * float(clf.intercept_[0]),
    }
    OUT.write_text(json.dumps(params, indent=2), encoding="utf-8")
    print(f"wrote {OUT} ({len(params['coef'])} coefficients)")


if __name__ == "__main__":
    main()
