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
5. For MRP: ONLY report a price if you see "MRP", "M.R.P", "Rs.", "₹", or "INR" followed by a number on the label. If there is no price printed, return null. Do NOT invent prices.
6. For net_quantity: ONLY report if you see a weight/volume/count printed (e.g. "500g", "1L"). Do NOT guess from product type.
7. For dates: ONLY report dates you can read on the label. Do NOT make up dates.
8. For batch_no: ONLY report if you see "Batch", "Lot", "B.No" followed by a code. Do NOT fabricate codes.

Return ONLY valid JSON — no markdown, no explanation, no backticks.

Required JSON schema:
{
  "mrp": "string or null — Maximum Retail Price EXACTLY as printed (e.g. '₹120.00', 'Rs. 45'). null if not visible.",
  "net_quantity": "string or null — net weight/volume/count EXACTLY as printed (e.g. '500g', '1L', '10 pieces'). null if not visible.",
  "unit": "string or null — standard unit from net_quantity (e.g. 'g', 'kg', 'ml', 'L', 'pieces'). null if net_quantity is null.",
  "manufacturer_name": "string or null — manufacturer/packer/importer company name as printed. null if not visible.",
  "manufacturer_address": "string or null — full address as printed. null if not visible.",
  "country_of_origin": "string or null — country of origin ONLY if explicitly printed (e.g. 'India', 'Made in China'). null if not stated.",
  "consumer_care": "string or null — customer care contact as printed (phone/email/address). null if not visible.",
  "manufacture_date": "string or null — manufacture/packing date EXACTLY as printed. null if not visible.",
  "best_before_expiry": "string or null — expiry/best-before EXACTLY as printed. null if not visible.",
  "batch_no": "string or null — batch/lot number EXACTLY as printed. null if not visible.",
  "raw_text_blocks": ["array of key text blocks from the label relating to price, quantity, dates, batch, manufacturer, contact"]
}

Return ONLY the JSON object, nothing else."""


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
                max_tokens=800,
            )

            raw = response.choices[0].message.content.strip()

            parsed = None
            try:
                parsed = json.loads(raw)
            except Exception:
                pass

            if not parsed and "```" in raw:
                parts = raw.split("```")
                for p in parts[1:]:
                    cand = p.strip()
                    if cand.lower().startswith("json"):
                        cand = cand[4:].strip()
                    try:
                        parsed = json.loads(cand)
                        break
                    except Exception:
                        continue

            if not parsed:
                start = raw.find("{")
                end = raw.rfind("}")
                if start != -1 and end > start:
                    try:
                        parsed = json.loads(raw[start:end + 1])
                    except Exception:
                        pass

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

