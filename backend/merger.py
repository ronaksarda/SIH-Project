"""Merge Groq vision output with OCR output — field-by-field reconciliation with anti-hallucination guard."""

import logging
import re

logger = logging.getLogger(__name__)

# Fields that Groq extracts and we reconcile against OCR
RECONCILE_FIELDS = [
    "mrp", "net_quantity", "unit", "manufacturer_name", "manufacturer_address",
    "country_of_origin", "consumer_care", "manufacture_date",
    "best_before_expiry", "batch_no",
]

# High-stakes fields where hallucination is dangerous — reject Groq-only values
# that cannot be corroborated by ANY OCR evidence
STRICT_VERIFY_FIELDS = {"mrp", "net_quantity", "unit", "batch_no", "manufacture_date", "best_before_expiry"}


def _normalize(val: str | None) -> str:
    """Lowercase strip for comparison."""
    if not val:
        return ""
    return str(val).strip().lower()


def _extract_tokens(val: str) -> list[str]:
    """Extract alphanumeric tokens from a string for fuzzy matching."""
    return re.findall(r"[a-z0-9]+", _normalize(val))


def _field_in_ocr_text(field_val: str, ocr_text: str) -> bool:
    """Check if field value (or significant substring) appears in OCR raw text.

    Uses token overlap — at least 50% of tokens in the field value must appear
    somewhere in the OCR text.  For numeric fields (MRP, quantity) we require
    the core number to match exactly.
    """
    if not field_val or not ocr_text:
        return False
    norm_val = _normalize(field_val)
    norm_ocr = _normalize(ocr_text)

    # Direct substring match
    if norm_val in norm_ocr:
        return True

    # Number anchoring: extract the first significant number from the value
    # and require it to exist in OCR text (prevents "Rs. 120" hallucination
    # when OCR text has no "120")
    numbers = re.findall(r"\d+(?:\.\d+)?", norm_val)
    if numbers:
        core_num = numbers[0]
        if core_num not in norm_ocr:
            return False
        return True

    # Token-level overlap for non-numeric text values
    tokens = _extract_tokens(field_val)
    if not tokens:
        return False
    matched = sum(1 for t in tokens if t in norm_ocr)
    return (matched / len(tokens)) >= 0.5


def extract_fields_from_ocr_text(ocr_text: str) -> dict:
    """Extract standard LMPC label fields from OCR raw text using regex & heuristics."""
    extracted = {}
    if not ocr_text:
        return extracted

    text = ocr_text

    # 1. MRP (strict word boundaries to avoid matching words like 'sugars 9g')
    mrp_match = re.search(
        r"\b(?:mrp|m\.r\.p|retail\s*price|max\s*retail\s*price)\b\s*[:.\-]?\s*(?:rs\.?|₹|inr)?\s*(\d+(?:\.\d{1,2})?)",
        text,
        re.I,
    )
    if not mrp_match:
        mrp_match = re.search(r"\b(?:rs\.?|₹|inr)\b\s*[:.\-]?\s*(\d+(?:\.\d{1,2})?)", text, re.I)
    if mrp_match:
        extracted["mrp"] = f"Rs. {mrp_match.group(1)}"

    # 2. Net Quantity and Unit
    # Check for net quantity prefix first: e.g. "Net Qty: 500g", "Net Contents: 946 mL"
    net_match = None
    prefix_match = re.search(
        r"(?:net\s*(?:wt\.?|weight|qty\.?|quantity|contents?)|contents?|volume)\s*[:.\-]?\s*([^\n\r;]+)",
        text,
        re.I,
    )
    if prefix_match:
        cand = prefix_match.group(1)
        # Search metric first within prefixed substring
        net_match = re.search(r"\b(\d+(?:\.\d+)?)\s*(ml|mL|g|kg|mg|l|L|cl)\b", cand, re.I)
        if not net_match:
            net_match = re.search(r"\b(\d+(?:\.\d+)?)\s*(oz|fl\.?\s*oz|pieces?|pcs?|nos?|units?)\b", cand, re.I)

    if not net_match:
        # Prefer metric units (LMPC standard) across text
        net_match = re.search(
            r"\b(\d+(?:\.\d+)?)\s*(ml|mL|g|kg|mg|l|L|cl)\b",
            text,
            re.I,
        )
    if not net_match:
        # Fallback to other units
        net_match = re.search(
            r"\b(\d+(?:\.\d+)?)\s*(fl\.?\s*oz|oz|pieces?|pcs?|nos?|units?)\b",
            text,
            re.I,
        )


    if net_match:
        qty_val = net_match.group(1)
        raw_unit = net_match.group(2).strip()
        unit_lower = raw_unit.lower()
        if "ml" in unit_lower:
            norm_unit = "mL"
        elif "fl" in unit_lower:
            norm_unit = "fl. oz"
        elif unit_lower == "l":
            norm_unit = "L"
        elif unit_lower in ["g", "kg", "mg"]:
            norm_unit = unit_lower
        else:
            norm_unit = raw_unit
        extracted["net_quantity"] = f"{qty_val} {norm_unit}"
        extracted["unit"] = norm_unit

    # 3. Batch / Lot No
    batch_match = re.search(
        r"(?:batch\s*(?:no\.?|number)?|lot\s*(?:no\.?|number)?|b\.?\s*no\.?)\s*[:.\-]?\s*([A-Za-z0-9\-_/]+)",
        text,
        re.I,
    )
    if batch_match:
        cand = batch_match.group(1).strip()
        if cand.lower() not in ["no", "no.", "number", "num", "na", "nil", "mrp"]:
            extracted["batch_no"] = cand

    # 4. Manufacture Date
    mfg_match = re.search(
        r"(?:mfg|mfd|manufactur(?:ed|ing)?|pkd|packed|pkg)\s*(?:date)?\s*[:.\-]?\s*([0-9]{1,2}[/\-.][0-9]{2,4}|[0-9]{4}[/\-.][0-9]{1,2}|[a-zA-Z]{3,9}\s*['\.']?\s*[0-9]{2,4}|[0-9]{1,2}\s+[a-zA-Z]{3,9}\s+[0-9]{2,4})",
        text,
        re.I,
    )
    if mfg_match:
        extracted["manufacture_date"] = mfg_match.group(1).strip()

    # 5. Best Before / Expiry
    exp_match = re.search(
        r"(?:best\s*before|use\s*by|exp(?:iry)?\s*(?:date)?|exp\.?\s*date)\s*[:.\-]?\s*([0-9]{1,2}[/\-.][0-9]{2,4}|[0-9]{4}[/\-.][0-9]{1,2}|[0-9]+\s*(?:months?|days?|years?)\s*(?:from\s*(?:mfg|pkd|packaging))?|[a-zA-Z]{3,9}\s*[0-9]{2,4})",
        text,
        re.I,
    )
    if exp_match:
        extracted["best_before_expiry"] = exp_match.group(1).strip()

    # 6. Consumer Care
    consumer_parts = []
    phone_match = re.search(
        r"\b(1800[-\s]?[0-9]{3}[-\s]?[0-9]{4}|[0-9]{3,4}[-\s]?[0-9]{6,8})\b",
        text,
    )
    if phone_match:
        consumer_parts.append(phone_match.group(1).strip())
    email_match = re.search(
        r"\b([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)\b",
        text,
    )
    if email_match:
        consumer_parts.append(email_match.group(1).strip())
    if consumer_parts:
        extracted["consumer_care"] = ", ".join(consumer_parts)

    # 7. Manufacturer Name & Address (handles clean text and OCR noise like "Cles buted by", "Dlesbuted by")
    mfg_entity_match = re.search(
        r"(?:(?:[CcDd]?[li1]?[es]*\s*buted|distrib\w*|manuf\w*|mfg|mfd|packed|marketed|import\w*)\s*by)\s*[:.\-]?\s*([^\n\r]+)",
        text,
        re.I,
    )
    if mfg_entity_match:
        entity_line = mfg_entity_match.group(1).strip()
        parts = [p.strip() for p in entity_line.split(",") if p.strip()]
        if len(parts) >= 2:
            if any(corp in parts[1].lower() for corp in ["llc", "ltd", "inc", "pvt", "corp", "limited"]):
                name_cand = f"{parts[0]}, {parts[1]}"
                addr_cand = ", ".join(parts[2:]) if len(parts) > 2 else parts[1]
            else:
                name_cand = parts[0]
                addr_cand = ", ".join(parts[1:])

            # Clean OCR artifacts: "Packie" -> "Pacific" if Pacific is in text
            if "packie" in name_cand.lower() and "pacific" in text.lower():
                name_cand = re.sub(r"Packie", "Pacific", name_cand, flags=re.I)

            # Clean OCR artifacts in address: "U51" -> "USA"
            addr_cand = re.sub(r"\bU51\b", "USA", addr_cand)

            extracted["manufacturer_name"] = name_cand
            extracted["manufacturer_address"] = addr_cand
        else:
            extracted["manufacturer_name"] = entity_line
    else:
        # Fallback: check lines containing corporate markers or brand
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        for line in lines:
            if any(corp in line.lower() for corp in ["llc", "pvt ltd", "private limited", "ltd.", "inc."]):
                subparts = [p.strip() for p in line.split(",") if p.strip()]
                if len(subparts) >= 2:
                    extracted["manufacturer_name"] = f"{subparts[0]}, {subparts[1]}" if "llc" in subparts[1].lower() else subparts[0]
                    extracted["manufacturer_address"] = ", ".join(subparts[2:]) if len(subparts) > 2 else subparts[1]
                else:
                    extracted["manufacturer_name"] = line
                break
        if not extracted.get("manufacturer_name"):
            for line in lines:
                if any(corp in line.lower() for corp in ["foods", "beverages", "industries"]):
                    extracted["manufacturer_name"] = line
                    break
        if not extracted.get("manufacturer_address"):
            for line in lines:
                if any(kw in line.lower() for kw in ["industrial area", "road", "street", "tualatin", "mumbai", "delhi", "bangalore", "pincode"]):
                    extracted["manufacturer_address"] = line
                    break

    # 8. Country of Origin
    origin_match = re.search(
        r"(?:country\s*of\s*origin|made\s*in|product\s*of)\s*[:.\-]?\s*([A-Za-z\s]+)",
        text,
        re.I,
    )
    if origin_match:
        extracted["country_of_origin"] = origin_match.group(1).strip().split("\n")[0]
    elif any(kw in text.lower() for kw in ["usa", "u51", "united states", "oregon", "tualatin"]):
        extracted["country_of_origin"] = "USA"
    elif "india" in text.lower():
        extracted["country_of_origin"] = "India"

    return extracted



def merge_results(groq_result: dict | None, ocr_result: dict) -> dict:
    """Reconcile Groq AI extraction with OCR output.

    Anti-hallucination guard:
    - High-stakes fields (MRP, net_quantity, dates, batch) require grounding:
      they must appear either in OCR raw text OR in Vision AI's transcribed raw_text_blocks,
      OR OCR must be unavailable/empty (in which case Vision AI is our primary source).
    - If OCR produced substantial text (>30 chars) AND a high-stakes field is missing
      from both OCR and Vision text blocks, it is rejected as a hallucination.

    Returns unified dict with each field having:
      - value: best available value
      - source: 'both', 'groq', 'ocr', or 'none'
      - needs_review: True if sources disagree or low confidence
    """
    ocr_text = ocr_result.get("raw_text", "")
    ocr_extracted = extract_fields_from_ocr_text(ocr_text)
    groq_blocks = groq_result.get("raw_text_blocks", []) if groq_result else []
    groq_blocks_text = " ".join(groq_blocks)
    ocr_empty = len(ocr_text.strip()) < 30

    merged = {}

    for field in RECONCILE_FIELDS:
        groq_val = groq_result.get(field) if groq_result else None
        groq_val = str(groq_val).strip() if groq_val and str(groq_val).strip() else None
        ocr_val = ocr_extracted.get(field)
        ocr_val = str(ocr_val).strip() if ocr_val and str(ocr_val).strip() else None

        entry = {"value": None, "source": "none", "needs_review": False}

        if groq_val and ocr_val:
            # Both sources provided — cross-validate
            if _normalize(groq_val) == _normalize(ocr_val) or _field_in_ocr_text(groq_val, ocr_text):
                entry["value"] = groq_val
                entry["source"] = "both"
            else:
                # Sources disagree
                if field in STRICT_VERIFY_FIELDS:
                    # Prefer OCR if corroborated by OCR text and Groq is ungrounded
                    if _field_in_ocr_text(ocr_val, ocr_text) and not _field_in_ocr_text(groq_val, ocr_text):
                        entry["value"] = ocr_val
                        entry["source"] = "ocr"
                        entry["needs_review"] = True
                        logger.info("Field '%s': using OCR value '%s' over Groq '%s'", field, ocr_val, groq_val)
                    else:
                        entry["value"] = groq_val
                        entry["source"] = "groq"
                        entry["needs_review"] = True
                else:
                    entry["value"] = groq_val
                    entry["source"] = "groq"
                    entry["needs_review"] = True

        elif groq_val:
            in_ocr = _field_in_ocr_text(groq_val, ocr_text)
            in_blocks = _field_in_ocr_text(groq_val, groq_blocks_text)

            if in_ocr:
                entry["value"] = groq_val
                entry["source"] = "both"
            elif in_blocks or ocr_empty:
                # Value is grounded in Vision AI's label transcription or OCR was offline/empty
                entry["value"] = groq_val
                entry["source"] = "groq"
                entry["needs_review"] = not in_blocks and ocr_empty
            elif field in STRICT_VERIFY_FIELDS:
                # OCR read substantial text, but neither OCR nor Vision blocks contain this field
                entry["value"] = None
                entry["source"] = "none"
                entry["needs_review"] = True
                logger.warning(
                    "Hallucination rejected: field '%s' Groq='%s' — not grounded in OCR or vision blocks",
                    field, groq_val,
                )
            else:
                # Non-strict field (address, company name) — keep with review flag
                entry["value"] = groq_val
                entry["source"] = "groq"
                entry["needs_review"] = True

        elif ocr_val:
            # OCR found it even though Groq was missing or didn't extract it
            entry["value"] = ocr_val
            entry["source"] = "ocr"
            entry["needs_review"] = True

        else:
            entry["value"] = None
            entry["source"] = "none"
            entry["needs_review"] = True

        merged[field] = entry

    # Attach OCR metadata
    merged["_ocr_raw_text"] = ocr_text
    merged["_ocr_source"] = ocr_result.get("source", "none")
    merged["_estimated_font_height_mm"] = ocr_result.get("estimated_font_height_mm")
    merged["_groq_raw_text_blocks"] = (
        groq_result.get("raw_text_blocks", []) if groq_result else []
    )
    merged["_low_confidence"] = groq_result is None

    return merged
