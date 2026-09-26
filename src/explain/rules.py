"""
src/explain/rules.py
======================
Task 05 — Rule-based plain-language driver summaries

Maps raw feature values to plain-language explanation phrases.
Used as Level 1 explainability and as input to the RAG layer.
"""

from typing import List, Dict


# Thresholds are rough empirical bounds for the Maharashtra region
RULES = [
    # (feature_name, condition_fn, phrase)
    ("lead_day",         lambda v: v >= 7,    "Long lead time (Day {:.0f}) — forecast skill degrades significantly beyond 5 days"),
    ("forecast_spread",  lambda v: v > 15.0,  "High ensemble spread ({:.1f} mm) — members strongly disagree on rainfall amount"),
    ("forecast_spread",  lambda v: v <= 2.0,  "Low ensemble spread ({:.1f} mm) — members agree but may miss mesoscale events"),
    ("forecast_range",   lambda v: v > 30.0,  "Very wide ensemble range ({:.1f} mm) — large uncertainty in rainfall total"),
    ("spatial_gradient", lambda v: v > 10.0,  "High spatial variability ({:.1f} mm std) — frontal or convective boundary nearby"),
    ("hist_bias",        lambda v: v > 15.0,  "Historically large errors for this region/lead/season (avg {:.1f} mm)"),
    ("forecast_mean",    lambda v: v > 50.0,  "High rainfall forecast ({:.1f} mm) — heavy-rain events are harder to predict accurately"),
    ("forecast_mean",    lambda v: v < 1.0,   "Near-zero rainfall forecast ({:.1f} mm) — dry-day errors depend on local drizzle/convection"),
    ("forecast_anomaly", lambda v: v > 20.0,  "Forecast is well above normal ({:.1f} mm anomaly) — unusual rainfall harder to verify"),
    ("forecast_anomaly", lambda v: v < -15.0, "Forecast is well below normal ({:.1f} mm anomaly) — potential missed rainfall event"),
]


def get_rule_summary(feature_dict: Dict[str, float], max_rules: int = 3) -> List[str]:
    """
    Return up to max_rules plain-language phrases describing why this forecast
    may be unreliable, based on feature values.

    Args:
        feature_dict: {feature_name: value} for one prediction
        max_rules: maximum number of phrases to return

    Returns:
        List of human-readable explanation strings
    """
    triggered = []
    for (feat, cond_fn, phrase) in RULES:
        val = feature_dict.get(feat)
        if val is None:
            continue
        try:
            if cond_fn(val):
                triggered.append(phrase.format(val))
        except Exception:
            continue

    if not triggered:
        triggered = ["No strong individual risk signals detected; overall risk is driven by combined feature patterns."]

    return triggered[:max_rules]


def confidence_band(cal_prob: float) -> str:
    """Map calibrated bust probability to a human-readable confidence label."""
    if cal_prob < 0.20:
        return "High"
    elif cal_prob < 0.45:
        return "Moderate"
    else:
        return "Low"


if __name__ == "__main__":
    # Quick test
    sample = {
        "lead_day": 7,
        "forecast_spread": 20.5,
        "forecast_range": 45.0,
        "spatial_gradient": 12.3,
        "hist_bias": 18.0,
        "forecast_mean": 55.0,
        "forecast_anomaly": 25.0,
    }
    phrases = get_rule_summary(sample)
    print("Rule-based explanation:")
    for p in phrases:
        print(f"  • {p}")
    print(f"Confidence band (for prob=0.62): {confidence_band(0.62)}")
