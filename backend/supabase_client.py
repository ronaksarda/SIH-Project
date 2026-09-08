"""Supabase client for cloud persistence — no local database."""

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent

_client = None


def _get_client():
    """Lazy-init Supabase client."""
    global _client
    if _client is None:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        if not url or not key:
            return None
        cleaned_url = url.rstrip("/").removesuffix("/rest/v1").rstrip("/")
        try:
            from supabase import create_client
            _client = create_client(cleaned_url, key)
        except Exception as e:
            logger.warning("Could not init Supabase client: %s", e)
            return None
    return _client


def save_scan(scan_data: dict) -> str | None:
    """Save scan directly to Supabase."""
    scan_id = scan_data.get("id") or scan_data.get("scan_id") or str(uuid.uuid4())[:12]
    client = _get_client()
    if not client:
        return scan_id

    product_name = scan_data.get("product_name", "Unknown Product")
    status = scan_data.get("pass_fail", "FAIL")
    score = scan_data.get("score", 0)
    image_url = scan_data.get("image_url", "")
    report_url = scan_data.get("report_url") or scan_data.get("pdf_url", "")
    user_email = scan_data.get("user_email", "")

    # Try inspections table
    try:
        insp_row = {
            "product_name": product_name,
            "status": status,
            "image_path": image_url,
        }
        res = client.table("inspections").insert(insp_row).execute()
        if res.data:
            return str(res.data[0].get("id", scan_id))
    except Exception as e:
        logger.warning("Supabase inspections insert: %s", e)

    # Try scans table
    try:
        scan_row = {
            "id": scan_id,
            "product_name": product_name,
            "status": status,
            "score": score,
            "image_url": image_url,
            "report_url": report_url,
            "user_email": user_email,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        res = client.table("scans").insert(scan_row).execute()
        if res.data:
            return str(res.data[0].get("id", scan_id))
    except Exception as e:
        logger.warning("Supabase scans insert: %s", e)

    return scan_id


def upload_file(file_path: str, bucket: str = "reports") -> str | None:
    """Upload file to Supabase storage."""
    client = _get_client()
    if not client or not os.path.exists(file_path):
        return None

    try:
        filename = os.path.basename(file_path)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        storage_path = f"{ts}_{filename}"

        with open(file_path, "rb") as f:
            client.storage.from_(bucket).upload(storage_path, f.read())

        return client.storage.from_(bucket).get_public_url(storage_path)
    except Exception as e:
        logger.warning("Supabase storage upload failed: %s", e)
        return None


def get_scans(limit: int = 100, user_email: str | None = None) -> list:
    """Fetch scans directly from Supabase cloud database."""
    client = _get_client()
    if not client:
        return []

    # 1. Try scans table (has user_email support)
    try:
        q = client.table("scans").select("*").order("created_at", desc=True).limit(limit)
        if user_email:
            q = q.eq("user_email", user_email)
        res = q.execute()
        if res.data:
            return res.data
    except Exception:
        pass

    # 2. Try inspections table
    try:
        res = client.table("inspections").select("*").order("created_at", desc=True).limit(limit).execute()
        scans = []
        for r in res.data or []:
            scans.append({
                "id": str(r.get("id")),
                "product_name": r.get("product_name", "Packaged Commodity"),
                "created_at": r.get("created_at"),
                "pass_fail": r.get("status", "FAIL"),
                "score": 90 if r.get("status") == "PASS" else 40,
                "image_url": r.get("image_path", ""),
                "report_url": f"/reports/{r.get('id')}_report.pdf",
            })
        return scans
    except Exception as e:
        logger.warning("Supabase get_scans error: %s", e)

    return []
