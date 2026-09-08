"""Rules engine — reads lmpc_2011_rules.json and evaluates compliance. Python-only decisions."""

import json
import logging
import re

logger = logging.getLogger(__name__)


def _load_rules(rules_path: str) -> list[dict]:
    """Load rules from JSON file."""
    with open(rules_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("rules", [])


def _get_field_value(merged: dict, field: str):
    """Extract the actual value from a merged field entry (may be dict or raw)."""
    field_data = merged.get(field)
    if isinstance(field_data, dict):
        return field_data.get("value")
    return field_data


def check_rules(merged: dict, rules_path: str) -> list[dict]:
    """Evaluate each rule against merged extraction results.

    Returns list of dicts: {rule_id, rule_number, rule_text, field, status, reason, severity}
    status: 'pass', 'fail', 'skip' (when rule doesn't apply, e.g. country_of_origin for domestic)
    """
    rules = _load_rules(rules_path)
    results = []

    for rule in rules:
        field = rule["applies_to_field"]
        check = rule["check_type"]
        threshold = rule.get("threshold_value")
        severity = rule.get("severity", 5)
        rule_id = rule["rule_id"]
        rule_number = rule["rule_number"]
        rule_text = rule["rule_text"]

        entry = {
            "rule_id": rule_id,
            "rule_number": rule_number,
            "rule_text": rule_text,
            "field": field,
            "severity": severity,
            "status": "pass",
            "reason": "",
        }

        # Get field value from merged result
        value = _get_field_value(merged, field)

        # --- Presence check ---
        if check == "presence":
            # Special case: country_of_origin only required for imports
            if field == "country_of_origin":
                # If no indication of import, skip this rule
                ocr_text = merged.get("_ocr_raw_text", "").lower()
                groq_blocks = " ".join(merged.get("_groq_raw_text_blocks", [])).lower()
                all_text = ocr_text + " " + groq_blocks
                import_keywords = ["imported", "import", "country of origin", "made in"]
                is_import = any(kw in all_text for kw in import_keywords)
                if not is_import and not value:
                    entry["status"] = "skip"
                    entry["reason"] = "No indication of imported product; rule not applicable."
                    results.append(entry)
                    continue

            if not value or not str(value).strip():
                entry["status"] = "fail"
                entry["reason"] = f"Required field '{field}' is missing or empty."
            else:
                entry["reason"] = "Field present."
            results.append(entry)

        # --- Regex format check ---
        elif check == "regex":
            if not value or not str(value).strip():
                entry["status"] = "fail"
                entry["reason"] = f"Field '{field}' is empty; cannot validate format."
            else:
                pattern = threshold
                if re.search(pattern, str(value), re.IGNORECASE):
                    entry["reason"] = "Format valid."
                else:
                    entry["status"] = "fail"
                    entry["reason"] = f"Field '{field}' value '{value}' does not match required format."
            results.append(entry)

        # --- Minimum font size check (Rule 7 / Table I) ---
        elif check == "min_font_size":
            font_mm = merged.get("_estimated_font_height_mm")
            pdp_area = merged.get("pdp_area_cm2")
            rule_min_area = rule.get("pdp_area_min_cm2", 0)
            rule_max_area = rule.get("pdp_area_max_cm2", 999999)

            if pdp_area is not None:
                # User or system provided actual PDP area — only apply matching slab
                if not (rule_min_area <= pdp_area < rule_max_area):
                    entry["status"] = "skip"
                    entry["reason"] = f"Not applicable for PDP area {pdp_area}cm² (slab: {rule_min_area}-{rule_max_area}cm²)."
                    results.append(entry)
                    continue
            else:
                # PDP area unknown: apply ONLY the smallest slab (<50cm²) as a
                # conservative baseline, skip all larger slabs
                if rule_min_area > 0:
                    entry["status"] = "skip"
                    entry["reason"] = f"PDP area not specified; only evaluating base slab (<50cm²). This slab ({rule_min_area}-{rule_max_area}cm²) skipped."
                    results.append(entry)
                    continue

            if font_mm is None:
                entry["status"] = "skip"
                entry["reason"] = "Font size could not be estimated from image."
            else:
                min_mm = float(threshold)
                if font_mm >= min_mm:
                    entry["reason"] = f"Font height {font_mm}mm meets minimum {min_mm}mm for this PDP slab."
                else:
                    entry["status"] = "fail"
                    entry["reason"] = f"Font height {font_mm}mm is BELOW minimum {min_mm}mm required by Rule 7 Table I."
            results.append(entry)

        # --- Min ratio check (font width/height) ---
        elif check == "min_ratio":
            # Requires per-character bounding box analysis that
            # Tesseract's word-level boxes can't reliably provide
            entry["status"] = "skip"
            entry["reason"] = "Font width-to-height ratio check requires per-character analysis; skipped."
            results.append(entry)

        else:
            entry["status"] = "skip"
            entry["reason"] = f"Unknown check type '{check}'."
            results.append(entry)

    return results


def build_compliance_report(rule_results: list[dict]) -> dict:
    """Build compliance summary from rule check results.

    Returns: {
        missing_fields: [...],
        non_compliant_fields: [...],
        skipped_rules: [...],
        passed_rules: [...],
        score: 0-100,
        total_rules: int,
        pass_fail: 'PASS' | 'FAIL'
    }
    """
    missing = []
    non_compliant = []
    skipped = []
    passed = []

    total_severity = 0
    lost_severity = 0

    for r in rule_results:
        sev = r.get("severity", 5)

        if r["status"] == "skip":
            skipped.append(r)
            continue

        total_severity += sev

        if r["status"] == "pass":
            passed.append(r)
        elif r["status"] == "fail":
            lost_severity += sev
            if "missing" in r["reason"].lower() or "empty" in r["reason"].lower():
                missing.append(r)
            else:
                non_compliant.append(r)

    # Weighted score: 100 * (1 - lost/total)
    score = round(100 * (1 - lost_severity / total_severity)) if total_severity > 0 else 0
    score = max(0, min(100, score))

    return {
        "missing_fields": missing,
        "non_compliant_fields": non_compliant,
        "skipped_rules": skipped,
        "passed_rules": passed,
        "score": score,
        "total_rules": len(rule_results),
        "pass_fail": "PASS" if score >= 70 else "FAIL",
    }
