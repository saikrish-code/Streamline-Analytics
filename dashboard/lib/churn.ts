// In-process churn scoring: reproduces the exported scikit-learn pipeline
// (SimpleImputer(median, add_indicator) -> StandardScaler -> LogisticRegression).
// Regenerate churn-model.json with `python -m api.churn.export_web` after retraining.
import model from "./churn-model.json";

export type ChurnFeatures = Record<string, number | null | undefined>;

export const CHURN_MODEL_VERSION: string = model.model_version;

export function scoreChurn(features: ChurnFeatures): number {
  const raw = model.features.map(name => {
    const v = features[name];
    return v == null || Number.isNaN(Number(v)) ? null : Number(v);
  });
  const imputed = raw.map((v, i) => (v == null ? model.medians[i] : v));
  const indicators = model.indicator_features.map(i => (raw[i] == null ? 1 : 0));
  const row = [...imputed, ...indicators];
  let z = model.intercept;
  for (let i = 0; i < row.length; i++) {
    const scale = model.scaler_scale[i] || 1;
    z += model.coef[i] * ((row[i] - model.scaler_mean[i]) / scale);
  }
  return 1 / (1 + Math.exp(-z));
}
