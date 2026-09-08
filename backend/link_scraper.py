"""Module to scrape and download product images and metadata from product links."""

import json
import logging
import re
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from PIL import Image
import io

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/133.0.0.0 Safari/537.36"
)

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-IN,en-US;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Sec-Ch-Ua": '"Chromium";v="133", "Not(A:Brand";v="99", "Google Chrome";v="133"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
}


def _is_image_url(url: str) -> bool:
    """Check if URL points directly to an image extension."""
    path = urlparse(url).path.lower()
    return any(path.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"])


def _normalize_amazon_hires(img_url: str) -> str:
    """Strip Amazon thumbnail sizing suffix to obtain original full-resolution image."""
    if "media-amazon.com/images/I/" in img_url:
        # e.g. https://m.media-amazon.com/images/I/51qtycRz0-L._SY300_SX300_QL70_FMwebp_.jpg -> .../51qtycRz0-L.jpg
        return re.sub(r"\._[^/]+?\.(jpg|jpeg|png|webp)", r".\1", img_url, flags=re.I)
    return img_url


def _clean_url(url: str, base_url: str) -> str:
    """Join relative URLs and strip whitespace."""
    url = url.strip()
    if url.startswith("//"):
        url = "https:" + url
    return urljoin(base_url, url)


def _is_blacklisted_image_url(url: str) -> bool:
    """Filter out user reviews, avatars, tracking pixels, and ads."""
    u = url.lower()
    blacklist = [
        "aicid=community-reviews",
        "community-reviews",
        "review-image",
        "amazon-avatars",
        "aplus-media",
        "s/aplus",
        "play-button",
        "ad-feedback",
        "_p13n",
        "sims-desktop",
        "loading-4x-gray",
        "sprite",
        "pixel",
        "icon",
        "logo",
        "spinner",
        "badge",
        "rating",
        "star",
        ".svg",
        "fls-eu",
        "aax-eu-zaz",
        "impb",
    ]
    return any(b in u for b in blacklist)


def extract_image_urls_from_html(html: str, base_url: str) -> tuple[list[str], dict]:
    """Extract candidate product image URLs and page metadata from HTML content."""
    soup = BeautifulSoup(html, "html.parser")
    candidates = []
    metadata = {}

    # Meta Title & Description
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        metadata["title"] = og_title["content"].strip()
    elif soup.title and soup.title.string:
        metadata["title"] = soup.title.string.strip()

    title_elem = soup.find(id=re.compile(r"(productTitle|product-title|item-title)", re.I)) or soup.find("h1")
    if title_elem and not metadata.get("title"):
        metadata["title"] = title_elem.get_text(strip=True)

    og_desc = soup.find("meta", property="og:description") or soup.find("meta", attrs={"name": "description"})
    if og_desc and og_desc.get("content"):
        metadata["description"] = og_desc["content"].strip()

    # 1. Amazon Official Product Gallery (Extract colorImages from script JSON)
    official_gallery = []
    for pattern in [
        r"'colorImages':\s*\{\s*'initial':\s*(?:A\.\$\.parseJSON\()?['\"](\[.+?\])['\"]",
        r'data\["colorImages"\]\s*=\s*\{\s*"initial":\s*(?:A\.\$\.parseJSON\()?[\'"](\[.+?\])[\'"]',
        r'\"colorImages\"\s*:\s*\{\s*\"initial\"\s*:\s*(\[.+?\])\s*\}',
    ]:
        m = re.search(pattern, html)
        if m:
            try:
                raw_json = m.group(1).encode("utf-8").decode("unicode-escape")
                gallery_data = json.loads(raw_json)
                for item in gallery_data:
                    url = item.get("hiRes") or item.get("large")
                    if url:
                        cleaned = _normalize_amazon_hires(_clean_url(url, base_url))
                        if not _is_blacklisted_image_url(cleaned):
                            official_gallery.append(cleaned)
                if official_gallery:
                    break
            except Exception:
                pass

    if official_gallery:
        # If Amazon's official product gallery was found, use ONLY these brand-uploaded images
        candidates.extend(official_gallery)

    # 2. JSON-LD structured data (Schema.org)
    for script in soup.find_all("script", type=re.compile(r"application/ld\+json", re.I)):
        try:
            data = json.loads(script.string or "")
            items = data if isinstance(data, list) else [data]
            for item in items:
                if not isinstance(item, dict):
                    continue
                item_type = str(item.get("@type", "")).lower()
                if "product" in item_type or "itempage" in item_type or "offers" in item:
                    if "name" in item and not metadata.get("title"):
                        metadata["title"] = str(item["name"]).strip()
                    if "description" in item and not metadata.get("description"):
                        metadata["description"] = str(item["description"]).strip()
                    if "brand" in item and not metadata.get("brand"):
                        brand = item["brand"]
                        metadata["brand"] = brand.get("name", "") if isinstance(brand, dict) else str(brand)
                    if "offers" in item and not metadata.get("price"):
                        offers = item["offers"]
                        if isinstance(offers, dict) and "price" in offers:
                            metadata["price"] = str(offers["price"])
                    
                    if not candidates:
                        img = item.get("image")
                        if isinstance(img, str):
                            candidates.append(_clean_url(img, base_url))
                        elif isinstance(img, list):
                            for i in img:
                                if isinstance(i, str):
                                    candidates.append(_clean_url(i, base_url))
                                elif isinstance(i, dict) and "url" in i:
                                    candidates.append(_clean_url(i["url"], base_url))
        except Exception:
            pass

    # 3. Product Price Extraction from HTML elements (Amazon, Flipkart, etc.)
    if not metadata.get("price"):
        # Amazon a-offscreen / corePrice / a-price-whole
        price_elem = soup.find(class_=re.compile(r"a-price-whole|a-offscreen", re.I)) or soup.find(id=re.compile(r"corePrice|priceblock_ourprice|priceblock_dealprice", re.I))
        if price_elem:
            ptxt = price_elem.get_text(strip=True)
            p_match = re.search(r"(\d+(?:[.,]\d{1,2})?)", ptxt.replace(",", ""))
            if p_match:
                metadata["price"] = p_match.group(1).rstrip(".")

        # Flipkart / Blinkit / Meesho price classes
        if not metadata.get("price"):
            fk_price = soup.find(class_=re.compile(r"(_30jeq3|Nx9bqj|selling-price)", re.I))
            if fk_price:
                ptxt = fk_price.get_text(strip=True)
                p_match = re.search(r"(\d+(?:[.,]\d{1,2})?)", ptxt.replace(",", ""))
                if p_match:
                    metadata["price"] = p_match.group(1).rstrip(".")

        # Meta tags product:price:amount
        if not metadata.get("price"):
            meta_price = soup.find("meta", property=re.compile(r"product:price:amount|price", re.I)) or soup.find("meta", attrs={"name": re.compile(r"price", re.I)})
            if meta_price and meta_price.get("content"):
                p_match = re.search(r"(\d+(?:[.,]\d{1,2})?)", meta_price["content"])
                if p_match:
                    metadata["price"] = p_match.group(1).rstrip(".")

    # 4. If no official gallery found, fall back to landing images and page tags
    if not candidates:
        landing_img = soup.find("img", id=re.compile(r"(landingImage|imgBlkFront)", re.I))
        if landing_img:
            if landing_img.get("data-old-hires"):
                candidates.append(_normalize_amazon_hires(_clean_url(landing_img["data-old-hires"], base_url)))
            if landing_img.get("data-a-dynamic-image"):
                try:
                    dyn_map = json.loads(landing_img["data-a-dynamic-image"])
                    for u in sorted(dyn_map.keys(), key=lambda k: dyn_map[k][0] * dyn_map[k][1] if isinstance(dyn_map[k], list) and len(dyn_map[k]) >= 2 else 0, reverse=True):
                        candidates.append(_normalize_amazon_hires(_clean_url(u, base_url)))
                except Exception:
                    pass
            if landing_img.get("src"):
                candidates.append(_normalize_amazon_hires(_clean_url(landing_img["src"], base_url)))

        og_image = soup.find("meta", property=re.compile(r"^og:image(:secure_url)?$", re.I))
        if og_image and og_image.get("content"):
            candidates.append(_clean_url(og_image["content"], base_url))

        twitter_image = soup.find("meta", attrs={"name": re.compile(r"^twitter:image(:src)?$", re.I)})
        if twitter_image and twitter_image.get("content"):
            candidates.append(_clean_url(twitter_image["content"], base_url))

        for img in soup.find_all("img"):
            for attr in ["data-old-hires", "data-zoom-image", "data-large-img", "data-highres", "data-src", "src"]:
                val = img.get(attr)
                if not val:
                    continue
                cleaned = _normalize_amazon_hires(_clean_url(val, base_url))
                lower = cleaned.lower()
                if lower.startswith("data:image"):
                    continue
                if _is_blacklisted_image_url(lower):
                    continue
                candidates.append(cleaned)

    # Remove duplicates while preserving order
    seen = set()
    unique_candidates = []
    for c in candidates:
        if c and c not in seen and c.startswith("http") and not _is_blacklisted_image_url(c):
            seen.add(c)
            unique_candidates.append(c)

    return unique_candidates, metadata


def score_label_image(image_bytes: bytes) -> int:
    """Score image by text/label density, nutrition table rows, and barcodes. Higher score = physical back label."""
    try:
        import cv2
        import numpy as np
        img_arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(img_arr, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return 0
        h, w = img.shape
        if h < 100 or w < 100:
            return 0

        # 1. Background vs foreground (e-commerce white/light background packshot)
        prod_mask = (img < 240).astype(np.uint8) * 255
        pts = cv2.findNonZero(prod_mask)
        if pts is not None and len(pts) > 20:
            px, py, pw, ph = cv2.boundingRect(pts)
        else:
            return 0

        # Lifestyle photo penalty: if image has zero white padding and covers 98%+ of canvas,
        # it is typically an advertisement/lifestyle graphic, not a physical product packshot
        is_lifestyle_infographic = (pw >= w * 0.98 and ph >= h * 0.98)

        crop = img[py:py+ph, px:px+pw]

        # 2. Horizontal gradient / text edges (Sobel-Y)
        sobel_y = cv2.convertScaleAbs(cv2.Sobel(crop, cv2.CV_32F, 0, 1, ksize=3))
        _, text_edges = cv2.threshold(sobel_y, 35, 255, cv2.THRESH_BINARY)

        # 3. Nutrition table row detection (stacked horizontal divider lines)
        k_table = cv2.getStructuringElement(cv2.MORPH_RECT, (35, 1))
        table_lines = cv2.morphologyEx(text_edges, cv2.MORPH_OPEN, k_table)
        cnts_tbl, _ = cv2.findContours(table_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        lines_y = []
        for c in cnts_tbl:
            bx, by, bw, bh = cv2.boundingRect(c)
            if bw > 35:
                lines_y.append(by)
        lines_y.sort()

        # Stacked parallel rows (hallmark of mandatory statutory nutrition information tables)
        stacked_table_rows = 0
        for i in range(len(lines_y) - 1):
            diff = lines_y[i+1] - lines_y[i]
            if 8 <= diff <= 55:
                stacked_table_rows += 1

        # 4. Fine print text line strips (ingredients, manufacturer declaration)
        k_line = cv2.getStructuringElement(cv2.MORPH_RECT, (20, 2))
        text_strips = cv2.morphologyEx(text_edges, cv2.MORPH_CLOSE, k_line)
        cnts_strips, _ = cv2.findContours(text_strips, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        valid_strips = sum(1 for c in cnts_strips if 15 < cv2.boundingRect(c)[2] < pw * 0.92 and 3 < cv2.boundingRect(c)[3] < 45)

        # 5. Barcode detection (vertical stripe concentration in a compact subregion)
        sobel_x = cv2.convertScaleAbs(cv2.Sobel(crop, cv2.CV_32F, 1, 0, ksize=3))
        _, bar_edges = cv2.threshold(sobel_x, 50, 255, cv2.THRESH_BINARY)
        k_bar = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 20))
        bar_strips = cv2.morphologyEx(bar_edges, cv2.MORPH_CLOSE, k_bar)
        cnts_bar, _ = cv2.findContours(bar_strips, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        barcode_score = 0
        for c in cnts_bar:
            bx, by, bw, bh = cv2.boundingRect(c)
            if 15 < bw < pw * 0.4 and 25 < bh < ph * 0.4:
                barcode_score = 150
                break

        fine_print_density = np.sum(text_edges > 0) / max(pw * ph, 1)

        score = (
            (stacked_table_rows * 40)
            + (len(lines_y) * 10)
            + (min(valid_strips, 80) * 8)
            + barcode_score
            + int(fine_print_density * 800)
        )
        if is_lifestyle_infographic:
            score -= 300
        return max(score, 0)
    except Exception:
        return 0


async def fetch_product_image_and_metadata(url: str) -> tuple[bytes, str, dict]:
    """Fetch product image bytes, file extension, and metadata. Evaluates all candidate gallery images to find the food label."""
    import asyncio
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        raise ValueError("Invalid URL: must start with http:// or https://")

    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=20.0) as client:
        # Direct image URL
        if _is_image_url(url):
            resp = await client.get(url)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "").lower()
            ext = "jpg"
            if "png" in content_type:
                ext = "png"
            elif "webp" in content_type:
                ext = "webp"
            elif "." in urlparse(url).path:
                ext = urlparse(url).path.rsplit(".", 1)[-1].lower()
            return resp.content, ext, {}

        # Fetch product web page
        resp = await client.get(url)
        resp.raise_for_status()

        content_type = resp.headers.get("content-type", "").lower()
        if "image/" in content_type:
            ext = "png" if "png" in content_type else ("webp" if "webp" in content_type else "jpg")
            return resp.content, ext, {}

        html = resp.text
        candidates, metadata = extract_image_urls_from_html(html, str(resp.url))

        if not candidates:
            raise ValueError(
                "Could not detect any product image on the webpage. "
                "Please upload the image directly or provide a direct image link."
            )

        # Download up to 16 candidate images concurrently
        sample_urls = candidates[:16]

        async def _download_one(target_url: str):
            try:
                img_resp = await client.get(target_url, timeout=12.0)
                if img_resp.status_code == 200 and len(img_resp.content) > 2000:
                    img = Image.open(io.BytesIO(img_resp.content))
                    w, h = img.size
                    if w >= 150 and h >= 150:
                        fmt = (img.format or "JPEG").lower()
                        ext = "png" if fmt == "png" else ("webp" if fmt == "webp" else "jpg")
                        score = score_label_image(img_resp.content)
                        url_lower = target_url.lower()
                        # Keyword bonus for back/panel/facts/nutrition/ingredients
                        if any(kw in url_lower for kw in ["back", "nutrition", "facts", "label", "detail", "ingred", "pt03", "pt04", "pt06"]):
                            score += 25
                        return {
                            "content": img_resp.content,
                            "ext": ext,
                            "score": score,
                            "url": target_url,
                        }
            except Exception as e:
                logger.warning("Failed candidate image %s: %s", target_url, e)
            return None

        results = await asyncio.gather(*[_download_one(u) for u in sample_urls])
        valid_candidates = [r for r in results if r is not None]

        if not valid_candidates:
            raise ValueError(
                "Found image links on page but could not download a high-resolution product image. "
                "Please upload the label photo directly."
            )

        # Sort by label score descending — the image with highest food label/text density is selected
        valid_candidates.sort(key=lambda c: c["score"], reverse=True)
        best = valid_candidates[0]
        logger.info(
            "Selected food label image from %d candidates (winner score=%d, url=%s)",
            len(valid_candidates),
            best["score"],
            best["url"],
        )
        return best["content"], best["ext"], metadata


# Alias
extract_image_and_metadata_from_url = fetch_product_image_and_metadata
