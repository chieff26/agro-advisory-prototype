import argparse
import json
import os
from datetime import datetime

DEFAULT_RULES = "rules.json"
OUTDIR = "outputs"
HISTORY_PATH = os.path.join(OUTDIR, "history.json")


def load_rules(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def ensure_outdir():
    os.makedirs(OUTDIR, exist_ok=True)


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def parse_float(name: str, val: str) -> float:
    try:
        return float(val)
    except ValueError:
        raise ValueError(f"{name} must be a number.")


def parse_int(name: str, val: str) -> int:
    try:
        return int(val)
    except ValueError:
        raise ValueError(f"{name} must be an integer.")


def recommend(crop: str, soil_ph: float, n: float, p: float, k: float, rainfall_mm: int, rules: dict) -> dict:
    crop_key = crop.strip().lower()
    crops = rules["crops"]
    if crop_key not in crops:
        raise ValueError(f"Unknown crop '{crop}'. Try one of: {', '.join(sorted(crops.keys()))}")

    c = crops[crop_key]
    ideal_low, ideal_high = c["ideal_ph"]
    baseN, baseP, baseK = c["base_npk"]
    t = rules["thresholds"]

    messages = []
    tips = list(c.get("notes", []))

    # pH guidance
    if soil_ph < ideal_low:
        messages.append(f"Soil pH ({soil_ph:.1f}) is LOW for {crop_key}. Consider liming (after soil test).")
    elif soil_ph > ideal_high:
        messages.append(f"Soil pH ({soil_ph:.1f}) is HIGH for {crop_key}. Consider organic matter / sulfur guidance (after soil test).")
    else:
        messages.append(f"Soil pH ({soil_ph:.1f}) is within ideal range for {crop_key}.")

    # Rainfall guidance
    if rainfall_mm < t["low_rainfall_mm"]:
        tips.append("Rainfall is low: plan irrigation, mulching, or drought-tolerant practices.")
    elif rainfall_mm > t["high_rainfall_mm"]:
        tips.append("High rainfall: ensure drainage and monitor fungal disease risk.")
    else:
        tips.append("Rainfall seems moderate: keep basic moisture monitoring.")

    # Nutrient adjustment (simple rule-based scaling)
    # If soil level is low -> increase recommendation; if high -> keep base.
    def adjust(base, soil_value, low_thr):
        if soil_value < low_thr:
            # up to +30% boost based on how low it is
            severity = clamp((low_thr - soil_value) / max(low_thr, 1e-6), 0.0, 1.0)
            return int(round(base * (1.0 + 0.30 * severity)))
        return int(round(base))

    recN = adjust(baseN, n, t["low_n"])
    recP = adjust(baseP, p, t["low_p"])
    recK = adjust(baseK, k, t["low_k"])

    # Extra warnings
    if n < t["low_n"]:
        messages.append("Nitrogen looks low → expect weaker growth if not corrected.")
    if p < t["low_p"]:
        messages.append("Phosphorus looks low → root development may be limited.")
    if k < t["low_k"]:
        messages.append("Potassium looks low → stress tolerance and quality may drop.")

    # Output
    result = {
        "crop": crop_key,
        "inputs": {
            "soil_ph": round(soil_ph, 2),
            "soil_n": round(n, 2),
            "soil_p": round(p, 2),
            "soil_k": round(k, 2),
            "rainfall_mm": rainfall_mm
        },
        "recommendation": {
            "npk_estimate": [recN, recP, recK],
            "explain": "Rule-based estimate using base crop needs + simple thresholds. Verify with local soil test."
        },
        "messages": messages,
        "tips": tips
    }
    return result


def save_history(entry: dict):
    ensure_outdir()
    history = []
    if os.path.exists(HISTORY_PATH):
        try:
            with open(HISTORY_PATH, "r", encoding="utf-8") as f:
                history = json.load(f)
            if not isinstance(history, list):
                history = []
        except Exception:
            history = []

    history.append(entry)
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def save_text_report(result: dict) -> str:
    ensure_outdir()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(OUTDIR, f"recommendation_{result['crop']}_{ts}.txt")

    npk = result["recommendation"]["npk_estimate"]
    lines = []
    lines.append("AGRO ADVISORY PROTOTYPE (Rule-based)")
    lines.append("-" * 45)
    lines.append(f"Crop: {result['crop']}")
    lines.append(f"Inputs: {result['inputs']}")
    lines.append("")
    lines.append(f"Estimated NPK recommendation: N={npk[0]} P={npk[1]} K={npk[2]}")
    lines.append(result["recommendation"]["explain"])
    lines.append("")
    lines.append("Messages:")
    for m in result["messages"]:
        lines.append(f"- {m}")
    lines.append("")
    lines.append("Tips:")
    for t in result["tips"]:
        lines.append(f"- {t}")
    lines.append("")
    lines.append("Disclaimer: Prototype advice only. Confirm with local agronomist/soil test.")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return path


def build_parser():
    p = argparse.ArgumentParser(description="Agro Advisory Prototype (rule-based recommendations).")
    p.add_argument("--rules", default=DEFAULT_RULES, help="Path to rules.json")
    p.add_argument("--crop", required=True, help="Crop name (maize/coffee/sesame)")
    p.add_argument("--ph", required=True, help="Soil pH (e.g., 6.2)")
    p.add_argument("--n", required=True, help="Soil Nitrogen index (example scale)")
    p.add_argument("--p", required=True, help="Soil Phosphorus index (example scale)")
    p.add_argument("--k", required=True, help="Soil Potassium index (example scale)")
    p.add_argument("--rainfall", required=True, help="Expected annual rainfall (mm)")
    return p


def main():
    args = build_parser().parse_args()

    rules = load_rules(args.rules)
    soil_ph = parse_float("ph", args.ph)
    n = parse_float("n", args.n)
    p = parse_float("p", args.p)
    k = parse_float("k", args.k)
    rainfall = parse_int("rainfall", args.rainfall)

    result = recommend(args.crop, soil_ph, n, p, k, rainfall, rules)

    # Print a nice summary
    npk = result["recommendation"]["npk_estimate"]
    print("\n=== AGRO ADVISORY RESULT ===")
    print(f"Crop: {result['crop']}")
    print(f"Inputs: {result['inputs']}")
    print(f"Estimated NPK: N={npk[0]} P={npk[1]} K={npk[2]}")
    print("\nMessages:")
    for m in result["messages"]:
        print("-", m)
    print("\nTips:")
    for t in result["tips"]:
        print("-", t)

    # Save outputs
    stamped = dict(result)
    stamped["timestamp"] = datetime.now().isoformat(timespec="seconds")
    save_history(stamped)
    report_path = save_text_report(result)
    print(f"\n✅ Saved: {report_path}")
    print(f"✅ History: {HISTORY_PATH}")


if __name__ == "__main__":
    main()
