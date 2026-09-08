# LabelSure AI — Legal Metrology (LMPC 2011) Compliance Inspection System

LabelSure AI is an automated compliance verification engine designed for Indian Legal Metrology (Packaged Commodities) Rules, 2011. It audits physical packaged goods and e-commerce listings against statutory labeling standards using a hybrid dual-AI vision pipeline, optical character recognition (OCR), deterministic rule enforcement, and a human-in-the-loop inspector review workflow.

## Key Features

- **Multi-Modal Inspection Input**: Evaluates direct image uploads (camera/disk in JPG, PNG, WebP) and live e-commerce product links (Amazon, Flipkart, Blinkit, Zepto, Swiggy Instamart, BigBasket).
- **Automated Gallery & Back-Label Resolution**: Scrapes multiple candidate photos from e-commerce listings, evaluates label/nutrition text density via computer vision scoring, runs parallel vision LLM audits, and selects the statutory back-of-pack image.
- **Pre-Flight Image Quality Guard**: Validates resolution, aspect ratio, and Laplacian variance blur thresholds before invoking compute-heavy pipelines.
- **Hybrid Anti-Hallucination Pipeline**: Runs Groq Vision LLM (`qwen/qwen3.8-27b`) and local Tesseract OCR (with cloud OCR fallback) concurrently. Cross-validates strict statutory fields (MRP, Unit Sale Price, Net Quantity, Batch Number, Dates) against OCR token evidence to eliminate LLM hallucinations.
- **Deterministic LMPC 2011 Rules Engine**: Evaluates Gazette notification G.S.R. 629(E) statutory standards including manufacturer name/address, metric unit declarations, manufacturing dates, MRP/USP declarations, consumer grievance contacts, country of origin, and minimum font height requirements (mm).
- **Two-Step Human-in-the-Loop Workflow**: Officers inspect extracted bounding boxes, adjust values in an interactive split-screen review workspace, and commit legally verified audits.
- **Automated Notice & Report Generation**: Generates production-grade compliance reports and formal notices in PDF (ReportLab) and DOCX (python-docx).
- **Cloud Persistence & Historical Audits**: Stores scan history, pass/fail metrics, evidence images, and generated audit reports in Supabase (PostgreSQL + Storage).

---

## Tech Stack

- **Backend Framework**: FastAPI 0.115.6 / Uvicorn 0.34.0 (Python 3.10+)
- **AI & Vision Model**: Groq Cloud API (`qwen/qwen3.8-27b` via `groq 0.15.0`)
- **OCR Engine**: Tesseract OCR (via `pytesseract 0.3.13`) with OCR.space HTTP fallback
- **Image Processing**: Pillow 11.1.0, OpenCV-Python (headless), NumPy 2.2.3
- **Web Scraping**: HTTPX 0.28.1, BeautifulSoup4
- **Document Generation**: ReportLab 4.2.5 (PDF), python-docx 1.1.2 (DOCX)
- **Database & Object Storage**: Supabase (`supabase-py 2.11.0`, PostgreSQL, Supabase Storage)
- **Frontend**: Vanilla HTML5, Vanilla JavaScript, Tailwind CSS (CDN), Lucide Icons, Anime.js

---

## Prerequisites

- **Python**: Version 3.10, 3.11, or 3.12
- **Tesseract OCR**:
  - Windows: [UB-Mannheim Tesseract Installer](https://github.com/UB-Mannheim/tesseract/wiki) (installed to `C:\Program Files\Tesseract-OCR\tesseract.exe`)
  - Linux: `sudo apt-get install tesseract-ocr`
  - macOS: `brew install tesseract`
- **Groq API Key**: Free account and key from [console.groq.com](https://console.groq.com)
- **Supabase Project** (Optional for local testing, required for cloud persistence): Project URL & Anon/Service Key from [supabase.com](https://supabase.com)
- **OCR.space API Key** (Optional fallback): Free key from [ocr.space](https://ocr.space)

---

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/ronaksarda/SIH_WINNER.git
cd SIH_WINNER
```

### 2. Set Up Virtual Environment

#### Windows (PowerShell)
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

#### Linux / macOS
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy the sample environment file:

```bash
cp .env.example .env
```

Edit `.env` and set your credentials:

```ini
# Groq API (Required for Vision LLM extraction)
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_MODEL=qwen/qwen3.8-27b

# Supabase (Optional for local mocks; required for dashboard persistence)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key_here

# OCR.space Fallback (Optional; utilized if local Tesseract binary is absent)
OCR_SPACE_KEY=your_ocr_space_key_here

# Server Configuration
HOST=0.0.0.0
PORT=8000
```

### 5. Supabase Database Setup (If using Cloud Persistence)

Execute the following schema in your Supabase SQL Editor:

```sql
CREATE TABLE IF NOT EXISTS inspections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT now(),
    product_name TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PASS', 'FAIL')),
    score INTEGER DEFAULT 0,
    image_path TEXT,
    report_url TEXT,
    user_email TEXT,
    raw_result JSONB
);

-- Storage buckets:
-- Create public buckets named 'reports' and 'scans' via Supabase Storage Dashboard.
```

### 6. Run the Application

From the project root:

```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Or run directly:

```bash
python backend/main.py
```

Open your browser to:
- **Scan Portal**: [http://localhost:8000](http://localhost:8000) (or [http://localhost:8000/static/upload.html](http://localhost:8000/static/upload.html))
- **Officer Dashboard**: [http://localhost:8000/static/dashboard.html](http://localhost:8000/static/dashboard.html)
- **API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Architecture Overview

### Directory Structure

```
SIH_WINNER/
├── backend/
│   ├── __init__.py
│   ├── main.py               # FastAPI application, routing, orchestration
│   ├── groq_client.py        # Groq Vision LLM client with JSON recovery
│   ├── ocr_client.py         # Tesseract OCR & OCR.space fallback + font size estimator
│   ├── merger.py             # Anti-hallucination reconciliation logic
│   ├── rules_engine.py       # Deterministic LMPC 2011 compliance checks & scoring
│   ├── link_scraper.py       # E-commerce link resolution, gallery scraping, label density scoring
│   ├── report_gen.py         # PDF (ReportLab) & DOCX (python-docx) report generators
│   ├── image_quality.py      # Laplacian blur & dimension validation
│   └── supabase_client.py    # Supabase PostgreSQL & Storage persistence
├── frontend/
│   ├── upload.html           # Main inspection portal (Image upload & URL audit)
│   ├── results.html          # Split-screen verification & officer correction workspace
│   ├── dashboard.html        # Analytics, inspection history, and export center
│   ├── login.html            # Inspector / officer authentication screen
│   ├── logo.png              # Portal branding
│   └── samples/              # Sample test packages for demonstration
├── rules/
│   └── lmpc_2011_rules.json  # Codified Legal Metrology (Packaged Commodities) rules
├── reports/                  # Locally generated PDF and DOCX reports (ephemeral)
├── uploads/                  # Ingested and normalized label images (ephemeral)
├── tests/                    # Pytest test suite (unit, integration, smoke)
├── .env.example              # Template environment configuration
├── requirements.txt          # Production dependencies
└── README.md                 # System documentation
```

### End-to-End Processing Pipeline

```
[User Input: Image or E-Commerce URL]
                   │
                   ▼
       [Link Scraper / Fetcher]
   (Extracts gallery images, computes label density,
    runs vision scoring, picks back-of-pack photo)
                   │
                   ▼
       [Image Quality Gate]
  (Resolution check + Laplacian variance blur threshold)
                   │
         ┌─────────┴─────────┐
         ▼                   ▼
[Groq Vision LLM]    [Tesseract / Cloud OCR]
(Zero-shot schema     (Bounding boxes, raw tokens,
 structured output)   DPI-to-mm font height)
         │                   │
         └─────────┬─────────┘
                   ▼
       [Anti-Hallucination Merger]
  (Reconciles fields against OCR token stream;
   drops unverified high-stakes declarations)
                   │
                   ▼
     [LMPC 2011 Deterministic Rules]
  (Regex validation, presence checks, font size slabs)
                   │
                   ▼
       [/scan JSON Response]
                   │
                   ▼
    [Officer Review Workspace]
  (Inspector edits/validates extracted data)
                   │
                   ▼
            [/finalize POST]
                   │
         ┌─────────┴─────────┐
         ▼                   ▼
 [PDF / DOCX Generation] [Supabase Cloud Sync]
  (ReportLab / docx)     (PostgreSQL + Storage)
```

### Statutory Rules Matrix (`rules/lmpc_2011_rules.json`)

| Rule ID | Statutory Reference | Description | Check Type | Target Field | Severity (1-10) |
|---|---|---|---|---|---|
| `R6_1_a_name` | Rule 6(1)(a) | Manufacturer / Packer / Importer Name | Presence | `manufacturer_name` | 9 |
| `R6_1_a_addr` | Rule 6(1)(a) | Complete Physical Address | Presence | `manufacturer_address` | 9 |
| `R6_1_b_qty` | Rule 6(1)(b) | Net Quantity Declaration | Presence | `net_quantity` | 10 |
| `R6_1_b_unit` | Rule 6(1)(b) | Standard Metric Unit (g, kg, ml, L, etc.) | Regex | `unit` | 8 |
| `R6_1_c_date` | Rule 6(1)(c) | Month & Year of Manufacture / Packing | Presence | `manufacture_date` | 8 |
| `R6_1_c_date_fmt` | Rule 6(1)(c) | Date Format Compliance | Regex | `manufacture_date` | 6 |
| `R6_1_d_mrp` | Rule 6(1)(d) | Maximum Retail Price (incl. of all taxes) | Presence | `mrp` | 10 |
| `R6_1_d_mrp_fmt` | Rule 6(1)(d) | MRP Currency Format (₹ / Rs. / INR) | Regex | `mrp` | 7 |
| `R6_1_d_usp` | Rule 6(1)(d) | Unit Sale Price for packages > 1kg / 1L | Regex / Presence | `unit_sale_price` | 7 |
| `R6_1_e_care` | Rule 6(1)(e) | Consumer Care Name, Phone, Email, Address | Presence | `consumer_care` | 8 |
| `R6_1_e_care_contact` | Rule 6(1)(e) | Valid Email / Phone Number in Care Cell | Regex | `consumer_care` | 6 |
| `R6_1_f_origin` | Rule 6(1)(f) | Country of Origin (for imported goods) | Presence | `country_of_origin` | 8 |
| `R6_1_g_batch` | Rule 6(1)(g) | Batch / Lot Identification Code | Presence | `batch_no` | 7 |
| `R7_font_size` | Rule 7 | Minimum Font Height in mm based on net qty | Numeric Threshold | `_estimated_font_height_mm` | 7 |

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `GROQ_API_KEY` | **Yes** | — | API key for Groq Vision inference (`console.groq.com`). |
| `GROQ_MODEL` | No | `qwen/qwen3.8-27b` | Model identifier for vision extraction on Groq. |
| `SUPABASE_URL` | No | — | URL of Supabase project instance (e.g., `https://xyz.supabase.co`). |
| `SUPABASE_KEY` | No | — | Supabase `anon` public key or `service_role` key. |
| `OCR_SPACE_KEY` | No | — | API key for OCR.space fallback when Tesseract is unavailable. |
| `HOST` | No | `0.0.0.0` | Host interface for Uvicorn server binding. |
| `PORT` | No | `8000` | Port for Uvicorn server binding. |

---

## API Reference

### 1. Pre-Scan Inspection (`POST /scan`)
Accepts either an uploaded package image or an e-commerce product link. Extracts all statutory fields, evaluates rules, and returns an unfinalized audit.

- **URL**: `/scan`
- **Method**: `POST`
- **Content-Type**: `multipart/form-data`
- **Parameters**:
  - `image` (*File*, optional): Image binary (JPG, PNG, WebP).
  - `product_link` (*string*, optional): Web URL to product page.

#### Response Example
```json
{
  "scan_id": "8f3b21c4e901",
  "image_url": "/uploads/8f3b21c4e901.jpg",
  "product_name": "Almonds 500g",
  "page_metadata": { "brand": "NutriChoice", "price": "450" },
  "extracted_fields": {
    "mrp": { "value": "Rs. 450.00", "source": "groq+ocr", "needs_review": false },
    "unit_sale_price": { "value": "Rs. 0.90/g", "source": "groq", "needs_review": false },
    "net_quantity": { "value": "500g", "source": "groq+ocr", "needs_review": false },
    "unit": { "value": "g", "source": "groq", "needs_review": false },
    "manufacturer_name": { "value": "Agro Foods Ltd", "source": "groq", "needs_review": false },
    "manufacturer_address": { "value": "Plot 44, MIDC, Pune 411018", "source": "groq", "needs_review": false },
    "manufacture_date": { "value": "11/2024", "source": "groq+ocr", "needs_review": false },
    "best_before_expiry": { "value": "11/2025", "source": "groq", "needs_review": false },
    "batch_no": { "value": "AF2411", "source": "groq+ocr", "needs_review": false },
    "consumer_care": { "value": "care@agrofoods.com 1800-200-1122", "source": "groq", "needs_review": false },
    "country_of_origin": { "value": "India", "source": "groq", "needs_review": false }
  },
  "low_confidence": false,
  "estimated_font_height_mm": 2.4,
  "violations": [],
  "passed_rules": [ ... ],
  "skipped_rules": [ ... ],
  "score": 100,
  "pass_fail": "PASS",
  "total_rules_checked": 14,
  "product_link": "",
  "finalized": false
}
```

### 2. Finalize & Sign-Off (`POST /finalize`)
Accepts corrections submitted by the legal metrology officer, re-evaluates rules against verified values, compiles PDF and DOCX reports, and persists the record to Supabase.

- **URL**: `/finalize`
- **Method**: `POST`
- **Content-Type**: `application/json`

#### Request Payload
```json
{
  "scan_id": "8f3b21c4e901",
  "officer_name": "Inspector R. K. Sharma",
  "officer_email": "r.sharma@metrology.gov.in",
  "product_name": "Almonds 500g",
  "image_url": "/uploads/8f3b21c4e901.jpg",
  "corrected_fields": {
    "mrp": "Rs. 450.00",
    "net_quantity": "500g",
    "unit": "g",
    "manufacturer_name": "Agro Foods Ltd",
    "manufacturer_address": "Plot 44, MIDC, Pune 411018",
    "manufacture_date": "11/2024",
    "batch_no": "AF2411",
    "consumer_care": "care@agrofoods.com 1800-200-1122"
  },
  "estimated_font_height_mm": 2.4
}
```

#### Response Example
```json
{
  "scan_id": "8f3b21c4e901",
  "score": 100,
  "pass_fail": "PASS",
  "violations": [],
  "pdf_url": "/reports/8f3b21c4e901_report.pdf",
  "docx_url": "/reports/8f3b21c4e901_report.docx",
  "supabase_row_id": "8f3b21c4e901",
  "finalized": true
}
```

### 3. Inspection History (`GET /scans`)
Fetches historical scans and audit records from Supabase (or memory fallback).

- **URL**: `/scans`
- **Method**: `GET`
- **Query Parameters**:
  - `user_email` (*string*, optional): Filter inspections by officer email.

### 4. Health Check (`GET /health`)
- **URL**: `/health`
- **Method**: `GET`
- **Response**: `{"status": "ok"}`

---

## Testing

The test suite covers unit tests, anti-hallucination guard validations, scraper logic, OCR merger reconciliation, font size calculation, and full pipeline smoke testing.

### Running Tests

Run all unit and integration tests with verbose reporting:

```bash
pytest tests/ -v
```

Run specific test modules:

```bash
# Test anti-hallucination verification logic
pytest tests/test_hallucination_and_fonts.py -v

# Test e-commerce link scraper and label density scoring
pytest tests/test_link_scraper.py -v

# Test multi-photo gallery evaluation and back-of-pack selection
pytest tests/test_multi_image_scan.py -v

# Test end-to-end synthetic pipeline
pytest tests/test_smoke.py -v
```

---

## Deployment

### Docker Deployment

A production-ready `Dockerfile` can package the application with Tesseract dependencies:

```dockerfile
FROM python:3.12-slim

# Install system dependencies & Tesseract OCR
RUN apt-get update && apt-get install -y --no-install-recommends     tesseract-ocr     tesseract-ocr-eng     libgl1     libglib2.0-0     && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Build and Run Container
```bash
docker build -t labelsure-ai .
docker run -p 8000:8000 --env-file .env labelsure-ai
```

### Cloud / VPS Deployment (Ubuntu / Debian)

1. Provision an Ubuntu 22.04 / 24.04 instance.
2. Install dependencies:
   ```bash
   sudo apt update
   sudo apt install -y python3-venv python3-pip tesseract-ocr nginx
   ```
3. Set up systemd service `/etc/systemd/system/labelsure.service`:
   ```ini
   [Unit]
   Description=LabelSure AI Service
   After=network.target

   [Service]
   User=ubuntu
   WorkingDirectory=/home/ubuntu/SIH_WINNER
   EnvironmentFile=/home/ubuntu/SIH_WINNER/.env
   ExecStart=/home/ubuntu/SIH_WINNER/venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000

   [Install]
   WantedBy=multi-user.target
   ```
4. Start and enable service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now labelsure
   ```

---

## Troubleshooting

### 1. `pytesseract.TesseractNotFoundError`
- **Cause**: Tesseract executable is not installed or not discoverable in system PATH.
- **Fix**:
  - Windows: Install from UB-Mannheim. The application auto-detects `C:\Program Files\Tesseract-OCR\tesseract.exe`. If installed elsewhere, add it to system PATH.
  - Linux: Run `sudo apt-get install tesseract-ocr`.
  - Fallback: Supply `OCR_SPACE_KEY` in `.env` to enable the cloud OCR fallback route.

### 2. `GROQ_API_KEY not set` or `429 Rate Limit`
- **Cause**: Missing key or rate limiting on the Groq Cloud endpoint.
- **Fix**: Verify `.env` contains a valid key. For 429 rate limits, `backend/groq_client.py` includes automatic retry logic with backoff.

### 3. E-Commerce Link Scraping Returns 422 / 502
- **Cause**: The e-commerce site blocked automated requests or anti-bot challenge was triggered.
- **Fix**: E-commerce platforms frequently update bot detection. Use high-resolution direct image uploads for listings behind CAPTCHA walls or Cloudflare challenges.

### 4. Supabase File Upload / Persistence Fails Silently
- **Cause**: Storage buckets do not exist or Supabase credentials lack table insert permissions.
- **Fix**: Ensure buckets named `reports` and `scans` exist in your Supabase project under Storage. If running in offline test mode, the system gracefully falls back to local storage in `./reports` and `./uploads`.

---

## License

Developed for the Smart India Hackathon (SIH). Distributed under the MIT License.
