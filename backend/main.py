"""FastAPI main app — /scan, /finalize, /scans endpoints."""

import asyncio
import json
import logging
import os
import shutil
import sys
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

# Ensure project root is in sys.path so backend package imports resolve from any cwd
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

try:
    from backend.image_quality import check_image_quality
    from backend.groq_client import extract_fields
    from backend.ocr_client import ocr_extract
    from backend.merger import merge_results
    from backend.rules_engine import build_compliance_report, check_rules
    from backend.report_gen import generate_docx, generate_pdf
    from backend.link_scraper import fetch_product_image_and_metadata, fetch_all_product_candidate_images
    from backend import supabase_client
except ModuleNotFoundError:
    from image_quality import check_image_quality
    from groq_client import extract_fields
    from ocr_client import ocr_extract
    from merger import merge_results
    from rules_engine import build_compliance_report, check_rules
    from report_gen import generate_docx, generate_pdf
    from link_scraper import fetch_product_image_and_metadata, fetch_all_product_candidate_images
    import supabase_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="LMPC Compliance Scanner", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directories
BASE_DIR = Path(__file__).resolve().parent.parent
RULES_PATH = str(BASE_DIR / "rules" / "lmpc_2011_rules.json")
UPLOADS_DIR = BASE_DIR / "uploads"
REPORTS_DIR = BASE_DIR / "reports"
UPLOADS_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)

# Serve generated reports as static files
app.mount("/reports", StaticFiles(directory=str(REPORTS_DIR)), name="reports")
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")
# Serve frontend
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "frontend")), name="frontend")


@app.get("/")
async def root():
    return FileResponse(str(BASE_DIR / "frontend" / "upload.html"))


@app.post("/scan")
async def scan(
    image: UploadFile | None = File(None),
    product_link: str = Form(""),
):
    """Step 1 of pipeline: extract fields, run rules, return editable results (NOT finalized)."""
    product_link = product_link.strip() if product_link else ""

    if (not image or not image.filename) and not product_link:
        raise HTTPException(400, "Please provide an image or product link.")

    scan_id = str(uuid.uuid4())[:12]
    page_metadata = {}

    if image and image.filename:
        ext = image.filename.rsplit(".", 1)[-1].lower() if "." in image.filename else "jpg"
        save_path = str(UPLOADS_DIR / f"{scan_id}.{ext}")
        with open(save_path, "wb") as f:
            shutil.copyfileobj(image.file, f)

        if product_link:
            try:
                _, _, page_metadata = await fetch_product_image_and_metadata(product_link)
            except Exception as e:
                logger.warning("Could not fetch page metadata from product link: %s", e)
    else:
        # Only product link provided: fetch all candidate gallery images and evaluate all
        try:
            candidates, page_metadata = await fetch_all_product_candidate_images(product_link, max_candidates=5)
        except Exception:
            # Fallback to single image fetch if fetch_all fails or is mocked
            try:
                img_bytes, ext, page_metadata = await fetch_product_image_and_metadata(product_link)
                candidates = [{"content": img_bytes, "ext": ext, "score": 0, "url": product_link}]
            except ValueError as e:
                raise HTTPException(422, str(e))
            except Exception as e:
                logger.error({"error": str(e)}, "Error downloading product image from link")
                raise HTTPException(502, f"Failed to download product image from link: {e}")

        if not candidates:
            raise HTTPException(422, "No downloadable product images found at link.")

        # Save all candidate images temporarily
        candidate_files = []
        for idx, cand in enumerate(candidates):
            c_ext = cand.get("ext", "jpg")
            c_path = str(UPLOADS_DIR / f"{scan_id}_cand_{idx}.{c_ext}")
            with open(c_path, "wb") as f:
                f.write(cand["content"])
            candidate_files.append({"path": c_path, "ext": c_ext, "cand": cand})

        # Run vision evaluation on all photos concurrently
        groq_tasks = [extract_fields(cf["path"]) for cf in candidate_files]
        groq_results = await asyncio.gather(*groq_tasks, return_exceptions=True)

        evaluated_candidates = []
        for idx, cf in enumerate(candidate_files):
            g_res = groq_results[idx]
            if isinstance(g_res, Exception) or not isinstance(g_res, dict):
                logger.warning("Vision extraction failed for candidate photo %d: %s", idx, g_res)
                continue

            # Merge with page metadata for pricing/brand if missing
            cand_merged = dict(g_res)
            if page_metadata:
                if not cand_merged.get("mrp") and page_metadata.get("price"):
                    cand_merged["mrp"] = f"Rs. {page_metadata['price']}"
                if not cand_merged.get("manufacturer_name") and page_metadata.get("brand"):
                    cand_merged["manufacturer_name"] = page_metadata["brand"]

            cand_rules = check_rules(cand_merged, RULES_PATH)
            cand_comp = build_compliance_report(cand_rules)
            cand_score = cand_comp.get("score", 0)

            # Count non-null printed statutory fields
            extracted_count = sum(1 for k, v in g_res.items() if v and not k.startswith("_"))

            evaluated_candidates.append({
                "cf": cf,
                "groq_result": g_res,
                "score": cand_score,
                "extracted_count": extracted_count,
            })

        if not evaluated_candidates:
            # Fallback to the first candidate if all vision calls failed
            winner_cf = candidate_files[0]
            winner_groq = {}
        else:
            # Sort by compliance score descending, then by extracted count descending
            evaluated_candidates.sort(key=lambda x: (x["score"], x["extracted_count"]), reverse=True)
            winner = evaluated_candidates[0]
            winner_cf = winner["cf"]
            winner_groq = winner["groq_result"]
            logger.info(
                "Audited %d product photos from link. Winning photo selected: score=%d (url=%s)",
                len(evaluated_candidates),
                winner["score"],
                winner_cf["cand"].get("url", "unknown"),
            )

        # Move the winning photo to the final scan_id path — ONLY the winning image is displayed
        ext = winner_cf["ext"]
        save_path = str(UPLOADS_DIR / f"{scan_id}.{ext}")
        shutil.copyfile(winner_cf["path"], save_path)

        # Clean up temporary candidate files
        for cf in candidate_files:
            try:
                if os.path.exists(cf["path"]) and cf["path"] != save_path:
                    os.remove(cf["path"])
            except Exception:
                pass

        # Run OCR on the winning photo
        try:
            ocr_result = await ocr_extract(save_path)
        except Exception as e:
            logger.warning("OCR failed on winning photo: %s", e)
            ocr_result = {}

        # Merge winner's Groq result + OCR
        merged = merge_results(winner_groq, ocr_result)

        # Enrich missing fields from scraped webpage metadata if available
        if page_metadata:
            mrp_entry = merged.get("mrp", {})
            if isinstance(mrp_entry, dict) and not mrp_entry.get("value") and page_metadata.get("price"):
                merged["mrp"] = {"value": f"Rs. {page_metadata['price']}", "source": "page_metadata", "needs_review": True}
            mfg_entry = merged.get("manufacturer_name", {})
            if isinstance(mfg_entry, dict) and not mfg_entry.get("value") and page_metadata.get("brand"):
                merged["manufacturer_name"] = {"value": page_metadata["brand"], "source": "page_metadata", "needs_review": True}

        # Run rules on winning image
        rule_results = check_rules(merged, RULES_PATH)
        compliance = build_compliance_report(rule_results)
        image_url = f"/uploads/{scan_id}.{ext}"

    if image and image.filename:
        # Quality check for uploaded file
        is_ok, reason = check_image_quality(save_path)
        if not is_ok:
            if os.path.exists(save_path):
                os.remove(save_path)
            raise HTTPException(422, reason)

        # Parallel: Groq vision + Tesseract OCR
        groq_task = extract_fields(save_path)
        ocr_task = ocr_extract(save_path)
        groq_result, ocr_result = await asyncio.gather(groq_task, ocr_task)

        # Merge
        merged = merge_results(groq_result, ocr_result)

        # Enrich missing fields from scraped webpage metadata if available
        if page_metadata:
            mrp_entry = merged.get("mrp", {})
            if isinstance(mrp_entry, dict) and not mrp_entry.get("value") and page_metadata.get("price"):
                merged["mrp"] = {"value": f"Rs. {page_metadata['price']}", "source": "page_metadata", "needs_review": True}
            mfg_entry = merged.get("manufacturer_name", {})
            if isinstance(mfg_entry, dict) and not mfg_entry.get("value") and page_metadata.get("brand"):
                merged["manufacturer_name"] = {"value": page_metadata["brand"], "source": "page_metadata", "needs_review": True}

        # Run rules
        rule_results = check_rules(merged, RULES_PATH)
        compliance = build_compliance_report(rule_results)
        image_url = f"/uploads/{scan_id}.{ext}"

    response = {
        "scan_id": scan_id,
        "image_url": image_url,
        "product_name": page_metadata.get("title", ""),
        "page_metadata": page_metadata,
        "extracted_fields": {
            k: v for k, v in merged.items() if not k.startswith("_")
        },
        "low_confidence": merged.get("_low_confidence", False),
        "estimated_font_height_mm": merged.get("_estimated_font_height_mm"),
        "violations": compliance["missing_fields"] + compliance["non_compliant_fields"],
        "passed_rules": compliance["passed_rules"],
        "skipped_rules": compliance["skipped_rules"],
        "score": compliance["score"],
        "pass_fail": compliance["pass_fail"],
        "total_rules_checked": compliance["total_rules"],
        "product_link": product_link,
        "finalized": False,
    }

    return JSONResponse(response)


@app.post("/finalize")
async def finalize(data: dict):
    """Step 2: officer-corrected data → re-run rules → generate reports → persist."""

    scan_id = data.get("scan_id", str(uuid.uuid4())[:12])
    corrected_fields = data.get("corrected_fields", {})
    officer_name = data.get("officer_name", "Inspector")
    product_name = data.get("product_name", "Unknown Product")

    # Rebuild merged result from corrected fields
    merged = {}
    for field, value in corrected_fields.items():
        merged[field] = {"value": value, "source": "officer_corrected", "needs_review": False}

    # Re-attach font size if provided
    merged["_estimated_font_height_mm"] = data.get("estimated_font_height_mm")
    merged["_ocr_raw_text"] = data.get("ocr_raw_text", "")
    merged["_groq_raw_text_blocks"] = data.get("groq_raw_text_blocks", [])
    merged["_low_confidence"] = data.get("low_confidence", False)

    # Re-run rules on corrected data
    rule_results = check_rules(merged, RULES_PATH)
    compliance = build_compliance_report(rule_results)

    # Generate reports
    report_data = {
        "info": {
            "product_name": product_name,
            "scan_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "officer_name": officer_name,
        },
        "score": compliance["score"],
        "pass_fail": compliance["pass_fail"],
        "missing_fields": compliance["missing_fields"],
        "non_compliant_fields": compliance["non_compliant_fields"],
        "passed_rules": compliance["passed_rules"],
    }

    pdf_path = str(REPORTS_DIR / f"{scan_id}_report.pdf")
    docx_path = str(REPORTS_DIR / f"{scan_id}_report.docx")

    generate_pdf(report_data, pdf_path)
    generate_docx(report_data, docx_path)

    pdf_url = f"/reports/{scan_id}_report.pdf"
    docx_url = f"/reports/{scan_id}_report.docx"

    # Try Supabase persistence
    supabase_pdf_url = supabase_client.upload_file(pdf_path)
    supabase_docx_url = supabase_client.upload_file(docx_path)

    image_url = data.get("image_url", "")
    supabase_image_url = None
    if image_url:
        local_image = str(BASE_DIR / image_url.lstrip("/"))
        if os.path.exists(local_image):
            supabase_image_url = supabase_client.upload_file(local_image, bucket="scans")

    user_email = data.get("user_email") or data.get("officer_email") or ""

    scan_row_id = supabase_client.save_scan({
        "id": scan_id,
        "user_email": user_email,
        "product_name": product_name,
        "pass_fail": compliance["pass_fail"],
        "score": compliance["score"],
        "image_url": supabase_image_url or image_url,
        "report_url": supabase_pdf_url or pdf_url,
        "raw_result": {
            "corrected_fields": corrected_fields,
            "rule_results": [
                {"rule_id": r["rule_id"], "status": r["status"], "reason": r["reason"]}
                for r in rule_results
            ],
        },
    })

    return JSONResponse({
        "scan_id": scan_id,
        "score": compliance["score"],
        "pass_fail": compliance["pass_fail"],
        "violations": compliance["missing_fields"] + compliance["non_compliant_fields"],
        "pdf_url": supabase_pdf_url or pdf_url,
        "docx_url": supabase_docx_url or docx_url,
        "supabase_row_id": scan_row_id,
        "finalized": True,
    })


@app.get("/scans")
async def get_scans(user_email: str | None = None):
    """Dashboard: fetch recent scans."""
    scans = supabase_client.get_scans(user_email=user_email)
    return JSONResponse(scans)


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    app_target = "backend.main:app" if Path.cwd() == BASE_DIR else "main:app"
    uvicorn.run(app_target, host="0.0.0.0", port=8000, reload=True)
