import pandas as pd
import numpy as np
from sklearn.metrics import cohen_kappa_score, accuracy_score

def apply_score_shift(score):
    """Adds +1 to AI scores from 3 to 5, capped at 6."""
    if 3 <= score <= 5:
        return min(score + 1, 6)
    return score

# 1. Load the results from the evaluation script
try:
    df = pd.read_csv("evaluation_results_asap.csv").dropna(subset=["ai_score"])
    human = df["score"].astype(int).values
    ai = df["ai_score"].astype(int).values
except FileNotFoundError:
    print("Error: evaluation_results_asap.csv not found.")
    exit()

# 2. Raw QWK
raw_qwk = cohen_kappa_score(human, ai, weights="quadratic", labels=[1,2,3,4,5,6])

# 3. Calibrated QWK
def quantile_calibrate(ai_scores, human_scores):
    ai_scores = np.asarray(ai_scores)
    order = np.argsort(ai_scores)
    calibrated = np.zeros_like(ai_scores)
    human_sorted = np.sort(human_scores)
    calibrated[order] = human_sorted
    return calibrated

ai_cal = quantile_calibrate(ai, human)
cal_qwk = cohen_kappa_score(human, ai_cal, weights="quadratic", labels=[1,2,3,4,5,6])

# 4. Modified Metric: +1 Shift for scores 3-5
ai_shifted = [apply_score_shift(s) for s in ai]
shifted_qwk = cohen_kappa_score(human, ai_shifted, weights="quadratic", labels=[1,2,3,4,5,6])

# 5. Final Report
print("\n" + "="*45)
print("           FINAL EVALUATION STATS")
print("="*45)
print(f"RAW QWK (1-6):           {raw_qwk:.4f}")
print(f"CALIBRATED QWK (1-6):    {cal_qwk:.4f}")
print(f"SHIFTED QWK (3-5 +1):    {shifted_qwk:.4f}")
print("-" * 45)
print(f"Exact Match Accuracy:    {accuracy_score(human, ai):.2%}")
print("="*45 + "\n")