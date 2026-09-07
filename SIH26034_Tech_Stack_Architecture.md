# Tech Stack & Architecture: Legal Metrology Compliance System (SIH26034)

## 1. Tech Stack

* **Frontend:** Vite + React (Tailwind CSS, Shadcn UI, Lucide Icons)
  * Fast HMR, responsive mobile camera integration for field scanning, pre-styled accessible UI components.
* **Backend:** FastAPI (Python 3.11)
  * Monolithic API running business logic, OCR execution, rule evaluation, and PDF generation without IPC overhead.
* **Database & Storage:** Supabase (PostgreSQL + Storage Buckets)
  * Relational tables for audit logs/scans + object storage for packaging images and generated reports.
* **Authentication:** Supabase Auth (JWT + Row Level Security)
  * Role-Based Access Control (`inspector` vs. `officer`) built directly into database queries.
* **AI / Vision Pipeline:** EasyOCR + OpenCV + Gemini 1.5 Flash API
  * **EasyOCR & OpenCV:** Extracts text spatial coordinates ($x, y, w, h$) and computes text height vs. package dimensions for font size validation.
  * **Gemini Flash:** Converts raw OCR text into a validated JSON schema (MRP, Net Qty, Mfg Date, Address, Consumer Care).
* **Report Generation:** ReportLab & `python-docx`
  * Asynchronously compiles digital inspection summaries in PDF and editable DOCX formats.

---

## 2. Complete Project Directory Structure

```text
sih26034-compliance-system/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── auth.py             # User session & role validation endpoints
│   │   │   ├── scan.py             # Packaging upload & processing router
│   │   │   ├── reports.py          # PDF / DOCX export endpoints
│   │   │   └── dashboard.py        # Analytics queries & historic search endpoints
│   │   ├── core/
│   │   │   ├── config.py           # App settings & secret keys management
│   │   │   └── supabase.py         # Supabase client instantiation
│   │   ├── services/
│   │   │   ├── ocr_engine.py       # EasyOCR & OpenCV font height calculations
│   │   │   ├── llm_parser.py       # Gemini Flash structured JSON extraction
│   │   │   ├── rule_checker.py     # Legal Metrology (Packaged Commodities) Rules, 2011 engine
│   │   │   └── pdf_generator.py    # ReportLab PDF creation service
│   │   └── main.py                 # FastAPI application setup & CORS configuration
│   ├── Dockerfile                  # Container definition with OpenCV runtime libs
│   └── requirements.txt            # Backend Python dependencies
├── frontend/
│   ├── src/
│   │   ├── assets/                 # Logos, static icons, and fallback images
│   │   ├── components/
│   │   │   ├── CameraScanner.jsx   # Field inspector camera capture stream
│   │   │   ├── BoundingOverlay.jsx # Interactive image preview with bounding boxes
│   │   │   ├── ComplianceBadge.jsx # Visual status indicators (Pass/Fail)
│   │   │   ├── StatCard.jsx        # Summary KPI cards for dashboards
│   │   │   └── ReportTable.jsx     # Searchable inspection datatable
│   │   ├── pages/
│   │   │   ├── Login.jsx           # Role-based authentication landing page
│   │   │   ├── ScanProduct.jsx     # Inspection submission interface
│   │   │   ├── ReportView.jsx      # Inspection result detail & PDF export view
│   │   │   └── Dashboard.jsx       # Enforcement officer monitoring dashboard
│   │   ├── lib/
│   │   │   └── supabaseClient.js   # Client-side Supabase configuration
│   │   ├── App.jsx                 # Client-side routing definition
│   │   └── main.jsx                # React app mounting point
│   ├── package.json                # Node dependencies
│   ├── tailwind.config.js          # Styling configurations
│   └── vite.config.js              # Vite build setup
└── README.md                       # Installation and execution instructions