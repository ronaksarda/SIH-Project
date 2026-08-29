# PS-SIH26034 — Project Workflow (Simple Words)

This is the exact step-by-step of how the app works, from the moment a user uploads a photo to the moment an officer sees it in the dashboard.

---

## STEP 1: User Opens the Upload Page

**What happens here:** The user (an officer or inspector) opens the app and sees the Upload Page.

**How it's done:** This page is built by Frontend Person #1 using plain HTML, CSS, and JavaScript. It has:
- A button to upload an image
- A text box to paste a product link
- A "Scan" button

---

## STEP 2: User Uploads a Photo or Pastes a Link

**What happens here:** The user picks a photo of a product label (or pastes a product link) and clicks "Scan."

**How it's done:** JavaScript on the Upload Page takes that image (or link) and sends it to the backend. It sends it to a specific address the backend is listening on — an API endpoint like `/scan`, built using Python + FastAPI.

---

## STEP 3: Backend Receives the Image

**What happens here:** The backend (built by you) picks up the image that was sent from the Upload Page.

**How it's done:** In FastAPI, you write a function like `def scan_image()` and connect it to the `/scan` URL. Whatever the frontend sends to `/scan` lands inside this function.

---

## STEP 4: Image Goes to the Grok API (Vision AI)

**What happens here:** The backend sends the image to the Grok API so it can read the label.

**How it's done:** The backend sends the image plus a text instruction (something like "read this label and give me back these specific fields") to the Grok API. Grok sends back the label's information in a clean, organized format instead of messy raw text.

---

## STEP 5: Image Also Goes to the OCR Tool (Double-Check)

**What happens here:** The same image is sent to a separate OCR tool as a second check, because Grok alone can misread small text sometimes.

**How it's done:** The backend sends the image to Tesseract (runs on your own machine/server) or OCR.space API (cloud-based). This tool pulls out raw text and tells you roughly how big the text is on the image — this is what's used for the font-size checking part.

---

## STEP 6: Backend Combines Both Answers

**What happens here:** The backend now has two answers about the same label — one from Grok, one from OCR — and puts them together to double-check accuracy.

**How it's done:** Plain Python code compares both answers and builds one combined, more reliable result.

---

## STEP 7: Backend Checks the Combined Result Against the Rules

**What happens here:** The backend checks what's on the label against the real government rules to see what's missing or wrong.

**How it's done:** The rules themselves are NOT decided by AI. They are fixed government rules from the Legal Metrology (Packaged Commodities) Rules, 2011 — collected by the PPT Person from the official government website, with the exact rule number written next to each one. You take that list and put it into a rules file (like a spreadsheet or text file). Your code then checks the combined Grok+OCR result against that file, one rule at a time, using simple if/else logic (e.g., "if maker's name is missing, flag it").

---

## STEP 8: Backend Decides What's Missing/Wrong and Builds a Score

**What happens here:** Based on the rule check in Step 7, the backend puts together a final list: what's missing, what's wrong, and a compliance score for the label.

**How it's done:** This is done entirely with your own Python logic — no external tool needed here, since it's just organizing the results of the rule check from Step 7.

---

## STEP 9: Backend Saves the Scan to the Database

**What happens here:** Every scan that happens gets saved, so it can be looked up later in the dashboard/history page.

**How it's done:** The backend uses Supabase (a free hosted database + login system + file storage). The backend connects to Supabase using a link and a key, and saves the scan record — product name, date, pass/fail, score, and the image/report files.

---

## STEP 10: Backend Generates the Report File

**What happens here:** A downloadable report is created showing the results of the scan.

**How it's done:** Once the backend knows what's wrong with the label (from Step 8), it feeds that information into ReportLab (for PDF) and/or python-docx (for Word), which auto-generate a formatted report file — no manual formatting needed.

---

## STEP 11: Results Are Sent Back to the Results Page

**What happens here:** The user now sees the outcome of their scan.

**How it's done:** The backend sends the final result back to the Results Page (built by Frontend Person #1). This page shows: the photo, a list of what's missing/wrong, and a "Download Report" button. This page was built using sample/fake data first, then connected to this real backend data.

---

## STEP 12: User Downloads the Report

**What happens here:** The user clicks "Download Report" and gets the PDF/Word file generated in Step 10.

**How it's done:** The Download Report button on the Results Page links directly to the report file the backend created and saved.

---

## STEP 13: Officer Logs In

**What happens here:** An officer who wants to see past scans logs into the app.

**How it's done:** Frontend Person #2 builds a Login Page with just email + password fields and a login button (plain HTML/CSS/JS). What happens when they click login is handled by you, using Supabase's built-in login system.

---

## STEP 14: Officer Views the Dashboard/History Page

**What happens here:** After logging in, the officer sees a list of all past scans.

**How it's done:** Frontend Person #2 builds the Dashboard Page (plain HTML/CSS/JS) showing a table/list of past scans: product name, date, pass/fail, score — plus a search box to filter by product name. This page was first built using sample/fake data, then connected to the real scan records saved in Supabase (from Step 9).

---

## Summary — Full Flow in One Line Each

1. User opens Upload Page
2. User uploads photo/link and clicks Scan
3. Backend (FastAPI `/scan`) receives the image
4. Image sent to Grok API to read the label
5. Same image sent to OCR tool as a second check
6. Backend combines Grok + OCR results
7. Backend checks combined result against the rules file (from LMPC 2011)
8. Backend builds final list of what's missing/wrong + compliance score
9. Backend saves the scan to Supabase database
10. Backend generates the report (ReportLab / python-docx)
11. Result sent back to Results Page (photo + issues list + download button)
12. User downloads the report
13. Officer logs in via Login Page (Supabase auth)
14. Officer views past scans on Dashboard Page (pulled from Supabase)
