import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split

RANDOM_SEED = 42

TRAINING_PATH = "data/processed/training_data.csv"
MODEL_PATH = "data/processed/ambrosia_risk_model.joblib"

FEATURES = ["temp_mean", "precip_sum", "humidity_mean"]
TARGET = "presence"


def make_model():
    return RandomForestClassifier(
        n_estimators=300,
        max_depth=8,
        min_samples_leaf=3,
        random_state=RANDOM_SEED,
        class_weight="balanced",
    )


data = pd.read_csv(TRAINING_PATH)
print(f"Рядків у датасеті: {len(data)}\n")

X = data[FEATURES]
y = data[TARGET]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=RANDOM_SEED, stratify=y
)
print(f"Train: {len(X_train)}, test: {len(X_test)}\n")

model = make_model()
model.fit(X_train, y_train)

y_pred = model.predict(X_test)
y_proba = model.predict_proba(X_test)[:, 1]

# «Відсутність» тут лише фонові точки, тому accuracy, precision і recall
# орієнтовні; головна метрика, AUC-ROC.
print("=== Тестова вибірка ===")
print(f"Accuracy:  {accuracy_score(y_test, y_pred):.3f}")
print(f"Precision: {precision_score(y_test, y_pred):.3f}")
print(f"Recall:    {recall_score(y_test, y_pred):.3f}")
print(f"F1-score:  {f1_score(y_test, y_pred):.3f}")
print(f"AUC-ROC:   {roc_auc_score(y_test, y_proba):.3f}\n")

print("Матриця плутанини (рядки: факт, стовпці: прогноз):")
print(confusion_matrix(y_test, y_pred))
print()
print(classification_report(y_test, y_pred, target_names=["absence (0)", "presence (1)"]))

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_SEED)
cv_scores = cross_val_score(model, X, y, cv=cv, scoring="roc_auc")
print("=== Крос-валідація, 5 фолдів, AUC-ROC ===")
print("По фолдах:", np.round(cv_scores, 3))
print(f"Середнє: {cv_scores.mean():.3f} (+/- {cv_scores.std():.3f})\n")

importances = pd.Series(model.feature_importances_, index=FEATURES).sort_values(ascending=False)
print("=== Важливість ознак ===")
print(importances)
print()

final_model = make_model()
final_model.fit(X, y)
joblib.dump(final_model, MODEL_PATH)
print(f"Модель збережено: {MODEL_PATH}")
