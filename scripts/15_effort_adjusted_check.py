import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold, cross_val_predict

from common import CLIMATE, LAND, make_rf, spatial_blocks

N_BINS = 5

d = pd.read_csv("data/processed/training_data_cell.csv")
d["log_visits"] = np.log1p(d["visits"])
y = d["presence"]
blocks = spatial_blocks(d)


def oof_proba(cols):
    # прогноз для кожного рядка від моделі, яка його регіон не бачила
    return cross_val_predict(make_rf(), d[cols], y, cv=GroupKFold(n_splits=5),
                             groups=blocks, method="predict_proba")[:, 1]


print(f"Рядків: {len(d)}, presence: {int(y.sum())}, фон: {int((1 - y).sum())}")
print("\nСередня кількість візитів у комірці:")
print(d.groupby("presence")["visits"].describe()[["mean", "50%", "max"]].round(1))

print(f"\nAUC лише за кількістю візитів: {roc_auc_score(y, d['log_visits']):.3f}")

p = oof_proba(CLIMATE + LAND)
print(f"AUC моделі (клімат + земля), усі дані: {roc_auc_score(y, p):.3f}")

d["bin"] = pd.qcut(d["log_visits"], q=N_BINS, duplicates="drop")
rows = []
weighted_sum = total_weight = 0.0
for interval, g in d.groupby("bin", observed=True):
    n1 = int(g["presence"].sum())
    n0 = int((1 - g["presence"]).sum())
    auc = np.nan
    if n1 >= 10 and n0 >= 10:
        auc = roc_auc_score(g["presence"], p[g.index])
        weighted_sum += auc * n1 * n0
        total_weight += n1 * n0
    rows.append({"візитів у комірці": str(interval), "presence": n1, "фон": n0, "AUC": round(auc, 3)})

print("\nAUC усередині груп з подібною інтенсивністю спостережень:")
print(pd.DataFrame(rows).to_string(index=False))
if total_weight:
    print(f"\nЗважений AUC усередині груп: {weighted_sum / total_weight:.3f}")

only_visits = roc_auc_score(y, oof_proba(["log_visits"]))
with_features = roc_auc_score(y, oof_proba(["log_visits"] + CLIMATE + LAND))
print(f"\nЛише візити (по регіонах):                {only_visits:.3f}")
print(f"Візити + клімат + земля (по регіонах):    {with_features:.3f}   приріст {with_features - only_visits:+.3f}")
