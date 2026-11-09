"""Load the current trusted churn model artifact and verify its compatibility."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import sklearn
import scipy

from api.churn.features import FEATURE_COLUMNS

DEFAULT_REGISTRY_DIR = Path(__file__).resolve().parents[1] / "model_registry" / "churn"


@dataclass(frozen=True)
class ModelBundle:
    model: Any
    metadata: dict[str, Any]


def load_current_model() -> ModelBundle:
    registry = Path(os.getenv("CHURN_MODEL_REGISTRY", DEFAULT_REGISTRY_DIR))
    pointer = registry / "current.json"
    if not pointer.is_file():
        raise FileNotFoundError(f"No current churn model pointer found at {pointer}")

    version = json.loads(pointer.read_text(encoding="utf-8"))["model_version"]
    model_dir = registry / version
    metadata = json.loads((model_dir / "metadata.json").read_text(encoding="utf-8"))
    expected_sklearn = metadata.get("versions", {}).get("scikit_learn")
    expected_versions = metadata.get("versions", {})
    expected_joblib = expected_versions.get("joblib")
    if expected_sklearn != sklearn.__version__:
        raise RuntimeError(
            "Model/scikit-learn version mismatch: artifact requires "
            f"{expected_sklearn}, service has {sklearn.__version__}. Rebuild the image with the "
            "training environment's package versions."
        )
    if expected_joblib != joblib.__version__:
        raise RuntimeError(
            f"Model/joblib version mismatch: artifact requires {expected_joblib}, "
            f"service has {joblib.__version__}. Rebuild the image with the training environment's package versions."
        )
    for package, actual_version in (("numpy", np.__version__), ("scipy", scipy.__version__)):
        if expected_versions.get(package) != actual_version:
            raise RuntimeError(
                f"Model/{package} version mismatch: artifact requires {expected_versions.get(package)}, "
                f"service has {actual_version}. Rebuild the image with the training environment's package versions."
            )
    if metadata.get("feature_columns") != FEATURE_COLUMNS:
        raise RuntimeError("Model feature schema does not match the API request schema")
    model_path = model_dir / "model.joblib"
    return ModelBundle(model=joblib.load(model_path), metadata=metadata)
