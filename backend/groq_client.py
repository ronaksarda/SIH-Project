"""Groq vision model client — extracts structured label fields from product images."""

import base64
import json
import logging
import os

from dotenv import load_dotenv
from groq import AsyncGroq

load_dotenv()

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """You are an EXTREMELY STRICT label-reading AI for Indian Legal Metrology compliance (LMPC 2011).
You MUST ONLY report text you can LITERALLY SEE printed on this product label image.

CRITICAL RULES — VIOLATION IS UNACCEPTABLE:
1. NEVER GUESS, INFER, ESTIMATE, or FABRICATE any value.
2. If a field is NOT PHYSICALLY PRINTED on the label, you MUST return null for that field.
3. Do NOT use product knowledge or training data to fill in missing information.
4. If text is blurry or partially occluded and you cannot read it with confidence, return null.
5. For MRP: Report the package price ONLY (e.g. '₹99.00', 'Rs. 99.00', '₹45'). Do NOT bundle per-unit rate or per-gram rate into mrp. If there is no price printed, return null.
6. For unit_sale_price: If there is a per-unit/per-gram rate printed (e.g. '₹0.55/g', 'Rs. 1.20/ml', '₹10/100g'), report it separately in unit_sale_price.
7. For net_quantity: Report weight/volume/count as printed (e.g. '180g', '500g', '1L').
8. For dates: When dual dates are printed (e.g. '27.07.26 / 21.08.27'), the first is manufacture_date and the second is best_before_expiry.
9. For batch_no: Report the batch/lot code (e.g. 'HM20826'). Do NOT fabricate.

Return ONLY valid JSON — no markdown, no explanation, no backticks.

Required JSON schema:
{
  "mrp": "string or null — Package Maximum Retail Price ONLY (e.g. '₹99.00', 'Rs. 99.00'). null if not visible.",
  "unit_sale_price": "string or null — Unit sale price if printed (e.g. '₹0.55/g', 'Rs. 0.55/g'). null if not visible.",
  "net_quantity": "string or null — Net weight/volume/count as printed (e.g. '180g', '500g', '1L'). null if not visible.",
  "unit": "string or null — Standard unit from net_quantity (e.g. 'g', 'kg', 'ml', 'L'). null if net_quantity is null.",
  "manufacturer_name": "string or null — Manufacturer/packer/importer company name as printed. null if not visible.",
  "manufacturer_address": "string or null — Complete address as printed. null if not visible.",
  "country_of_origin": "string or null — Country of origin ONLY if explicitly printed (e.g. 'India'). null if not stated.",
  "consumer_care": "string or null — Customer care contact details (phone/email/address/URL). null if not visible.",
  "manufacture_date": "string or null — Manufacture or packaging date as printed. null if not visible.",
  "best_before_expiry": "string or null — Best before or expiry date as printed. null if not visible.",
  "batch_no": "string or null — Batch or lot number as printed. null if not visible.",
  "raw_text_blocks": ["up to 12 key printed statutory lines verbatim from the label (e.g. Net Qty, Mfd by, Ingredients, Nutrition)"]
}

Return ONLY the JSON object, nothing else."""


def _recover_json(raw: str) -> dict | None:
    """Attempt robust parsing or repair of partially truncated JSON from LLM."""
    if not raw:
        return None
    # 1. Direct parse
    try:
        return json.loads(raw)
    except Exception:
        pass

    # 2. Markdown code block
    if "```" in raw:
        for part in raw.split("```")[1:]:
            cand = part.strip()
            if cand.lower().startswith("json"):
                cand = cand[4:].strip()
            try:
                return json.loads(cand)
            except Exception:
                pass

    # 3. Substring between outermost { and }
    start = raw.find("{")
    if start != -1:
        end = raw.rfind("}")
        if end > start:
            try:
                return json.loads(raw[start:end + 1])
            except Exception:
                pass

        # 4. Truncated completion: close open string and append braces
        chunk = raw[start:].strip()
        # If open quote, close it
        in_str = False
        escape = False
        for ch in chunk:
            if ch == "\\" and not escape:
                escape = True
                continue
            if ch == '"' and not escape:
                in_str = not in_str
            escape = False
        if in_str:
            chunk += '"'

        for suffix in ["}", "]}", "\"]}", "}"]:
            try:
                return json.loads(chunk + suffix)
            except Exception:
                pass

        # Truncate at last comma and close object
        last_comma = chunk.rfind(",")
        if last_comma != -1:
            try:
                return json.loads(chunk[:last_comma] + "}")
            except Exception:
                pass

    return None


async def extract_fields(image_path: str) -> dict | None:
    """Send image to Groq vision model, return parsed JSON or None on failure."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        logger.error("GROQ_API_KEY not set")
        return None

    model = os.environ.get("GROQ_MODEL", "qwen/qwen3.8-27b")

    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")

    # Detect mime type from extension
    ext = image_path.rsplit(".", 1)[-1].lower()
    mime_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}
    mime = mime_map.get(ext, "image/jpeg")

    client = AsyncGroq(api_key=api_key)

    for attempt in range(2):  # retry once on malformed response
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": EXTRACTION_PROMPT},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:{mime};base64,{b64}"},
                            },
                        ],
                    }
                ],
                temperature=0.1,
                max_tokens=2048,
            )

            raw = response.choices[0].message.content.strip()
            parsed = _recover_json(raw)

            if parsed and isinstance(parsed, dict):
                logger.info("Groq extraction succeeded (attempt=%d)", attempt + 1)
                return parsed

            logger.warning("Groq returned non-JSON (attempt=%d): %s", attempt + 1, raw[:200])
            if attempt == 0:
                continue
            return None

        except Exception as e:
            logger.error("Groq API call failed (attempt=%d): %s", attempt + 1, e)
            if attempt == 0 and "429" in str(e):
                import asyncio
                await asyncio.sleep(2.0)
                continue
            return None

