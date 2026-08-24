"""
Regenerates model/renewal_model.json from output/renewal_features_anonymized.csv.

Run this after re-running notebook/renewal_prediction.ipynb (which produces the CSV this
script reads). Exports the trained Gradient Boosting model as a portable JSON format
(preprocessing stats + tree structure) so it can be scored in plain JavaScript in the
widget with no server or Python runtime needed, see widget/renewal_widget_template.html.

Run from the repo root: python scripts/export_model.py
"""
import json
import math
import os
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

final = pd.read_csv(os.path.join(ROOT, "output", "renewal_features_anonymized.csv"))
final["Lease Start"] = pd.to_datetime(final["Lease Start"])
model_df = final[final["Status"].isin(["Renewed", "Did Not Renew"])].copy()
model_df["target"] = (model_df["Status"] == "Renewed").astype(int)
model_df["lease_start_month"] = model_df["Lease Start"].dt.month
model_df["unit_floor"] = (model_df["Unit Name"].astype(int) // 100).astype(int)
model_df["Is_Month_To_Month"] = model_df["Is_Month_To_Month"].astype(int)
for c in ["ever_conditions_applied", "ever_overridden"]:
    model_df[c] = model_df[c].fillna(False).astype(int)
model_df.loc[model_df["Rent"] == 0, "Rent"] = np.nan

numeric_features = ["Term_Days", "Rent", "sqft", "current_past_due", "current_late_count",
                     "screening_count", "avg_satisfaction", "resolved_rate", "timely_rate",
                     "survey_count", "work_order_count", "avg_work_order_amount", "lease_start_month"]
binary_features = ["Is_Month_To_Month", "ever_conditions_applied", "ever_overridden"]
categorical_features = ["unit_floor"]
features = numeric_features + binary_features + categorical_features
X = model_df[features]
y = model_df["target"]

preprocess = ColumnTransformer([
    ("num", Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), numeric_features),
    ("bin", SimpleImputer(strategy="constant", fill_value=0), binary_features),
    ("cat", SimpleImputer(strategy="most_frequent"), categorical_features),
])
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)

# Hyperparameters chosen in the notebook (section 5c) via a small grid search that
# minimizes the train/test ROC AUC gap, see the notebook for the full comparison.
gb = Pipeline([("prep", preprocess), ("clf", GradientBoostingClassifier(
    n_estimators=100, max_depth=2, min_samples_leaf=20, subsample=0.7, learning_rate=0.03, random_state=42,
))])
gb.fit(X_train, y_train)
print("Test ROC AUC:", round(roc_auc_score(y_test, gb.predict_proba(X_test)[:, 1]), 3))

num_imputer = preprocess.named_transformers_["num"].named_steps["impute"]
scaler = preprocess.named_transformers_["num"].named_steps["scale"]
cat_imputer = preprocess.named_transformers_["cat"]
num_medians = dict(zip(numeric_features, num_imputer.statistics_.tolist()))
num_means = dict(zip(numeric_features, scaler.mean_.tolist()))
num_scales = dict(zip(numeric_features, scaler.scale_.tolist()))
cat_mode = dict(zip(categorical_features, cat_imputer.statistics_.tolist()))
clf = gb.named_steps["clf"]
learning_rate = clf.learning_rate

# GradientBoostingClassifier's raw score = a constant bias (from its internal "init"
# estimator) + learning_rate * sum(tree predictions). Recover the bias numerically so the
# JSON export doesn't need to replicate sklearn's internal init-estimator logic.
Xt = preprocess.transform(X)
raw_scores = clf.decision_function(Xt)
tree_sum = np.zeros(len(X))
for est_row in clf.estimators_:
    tree_sum += est_row[0].predict(Xt)
bias = float((raw_scores - learning_rate * tree_sum).mean())


def export_tree(tree):
    t = tree.tree_
    nodes = []
    for i in range(t.node_count):
        if t.children_left[i] == -1:
            nodes.append({"leaf": True, "value": float(t.value[i][0][0])})
        else:
            nodes.append({"leaf": False, "feature": int(t.feature[i]), "threshold": float(t.threshold[i]),
                           "left": int(t.children_left[i]), "right": int(t.children_right[i])})
    return nodes


trees = [export_tree(est_row[0]) for est_row in clf.estimators_]

export = {
    "feature_order": features,
    "numeric_features": numeric_features, "binary_features": binary_features,
    "categorical_features": categorical_features,
    "num_medians": num_medians, "num_means": num_means, "num_scales": num_scales, "cat_mode": cat_mode,
    "learning_rate": learning_rate, "bias": bias, "trees": trees,
}
out_path = os.path.join(ROOT, "model", "renewal_model.json")
with open(out_path, "w") as f:
    json.dump(export, f)
print(f"Wrote {out_path} ({len(trees)} trees)")


# --- Sanity check: a pure-Python/JS-equivalent re-implementation must match sklearn exactly ---
def sigmoid(x):
    return 1 / (1 + math.exp(-x))


def predict_row(row, m):
    vec = []
    for f in m["numeric_features"]:
        v = row.get(f)
        if v is None or (isinstance(v, float) and math.isnan(v)):
            v = m["num_medians"][f]
        vec.append((v - m["num_means"][f]) / m["num_scales"][f])
    for f in m["binary_features"]:
        v = row.get(f, 0)
        vec.append(0 if v is None else v)
    for f in m["categorical_features"]:
        v = row.get(f)
        if v is None:
            v = m["cat_mode"][f]
        vec.append(v)
    raw = m["bias"]
    for tree in m["trees"]:
        node = tree[0]
        while not node["leaf"]:
            node = tree[node["left"]] if vec[node["feature"]] <= node["threshold"] else tree[node["right"]]
        raw += m["learning_rate"] * node["value"]
    return sigmoid(raw)


mismatches = 0
for i in range(len(X_test)):
    row = X_test.iloc[i].to_dict()
    if abs(predict_row(row, export) - gb.predict_proba(X_test.iloc[[i]])[0, 1]) > 1e-6:
        mismatches += 1
print(f"JS-equivalence check: {mismatches} mismatches out of {len(X_test)} test rows")
