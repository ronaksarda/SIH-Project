# PS-SIH26034 — Exact Tech Stack (Who Uses What)

---

## You — Backend + AI Integration

**What you'll use:** Python + FastAPI

**Why:** FastAPI lets you build API endpoints fast, and it auto-generates a testing page (`/docs`) so you can try your own API without building a frontend first.

**How:** You write functions like `def scan_image()` and attach them to a URL like `/scan`. Frontend people will send data to that URL and get a result back.

---

**What you'll use:** Grok API (vision model)

**Why:** It can look at an image and read text out of it, and you can ask it to give you the answer in a clean, organized format instead of messy raw text.

**How:** You send the image + a text instruction ("read this label and give me back these specific fields") to the Grok API, and it sends back the structured answer.

---

**What you'll use:** An OCR tool — Tesseract (free, runs on your own machine/server) or OCR.space API (free tier, cloud-based)

**Why:** Grok alone can misread small text sometimes. OCR is a second, more reliable pass specifically built to pull out raw text and tell you roughly how big the text is on the image — useful for the font-size checking part.

**How:** You send the same image to this tool separately, get back raw text, and use both this and Grok's answer together to double-check accuracy.

---

**What you'll use:** Plain Python (a rules file + if/else logic) — no separate "tool," just your own code

**Why:** The compliance rules are fixed government rules, not something that needs AI to figure out. Writing simple "if this is missing, flag it" logic is faster, cheaper, and something you can prove is correct — an AI guessing at rules is neither.

**How:** You keep a list of rules in a simple file (like a spreadsheet or a text file), and your code checks the AI's answer against that list one by one.

---

**What you'll use:** ReportLab (for PDF) and python-docx (for Word file)

**Why:** These are Python tools built specifically to auto-generate PDF and Word files from your code — no manual formatting needed.

**How:** Once your code knows what's wrong with a label, you feed that into these tools and they spit out a formatted report file.

---

**What you'll use:** Supabase (a free hosted database + login system + file storage, all in one)

**Why:** Instead of setting up and managing your own database server, Supabase gives you a ready-made database, a ready-made login system, and a place to store uploaded images/PDFs — all for free, with almost no setup.

**How:** You create an account, get a link and a key, and your Python code uses that to save/read data — like saving every scan result so it shows up later in the dashboard.

---

## Frontend Person #1 — Upload + Results Page

**What they'll use:** Plain HTML, CSS, and JavaScript (no framework — just regular web files)

**Why:** It's the simplest way to build a webpage with zero setup — open a file, write code, refresh the browser to see it. No complicated tools to install or learn.

**How:** They build an `upload.html` page with an upload button and a text box, and a `result.html` page that shows the scan result. JavaScript is used just to make the "Scan" button work and to display the result nicely on screen.

**Tell them:** "You're building two normal webpages, like ones you've seen a hundred times — an upload form and a results page. Nothing fancy needed."

---

## Frontend Person #2 — Dashboard + Login Page

**What they'll use:** Same as above — plain HTML, CSS, and JavaScript

**Why:** Keeping both frontend people on the exact same simple tools means their pages will look and feel consistent, and either of them can help the other if stuck.

**How:** They build a `dashboard.html` page with a table/list showing past scans, and a `login.html` page with email/password fields and a login button.

**Tell them:** "Same tools as [Frontend Person #1] — just building a table/list page and a simple login form."

---

## PPT Person — Rules + Presentation

**What they'll use:** The official Legal Metrology (Packaged Commodities) Rules, 2011 PDF (from the government website), and PowerPoint (or Google Slides) using the exact template you were given.

**Why:** No coding tool needed for this role — the "tool" is just the actual government document, and the presentation software everyone already knows.

**How:** They open the government PDF, find the sections about mandatory declarations and font sizes, write those down with the exact rule numbers, and hand that list to you. Then they fill in the 6-slide template with content you give them.

**Tell them:** "You don't need any technical tool — just the government's rules document and PowerPoint. Read the real rules, write down the important ones with their exact numbers, and design the slides."

---

## Tester #1 — Real Photo Testing

**What they'll use:** Their phone camera, and the working app once it's online

**Why:** No special tool needed — the whole point is testing with real, imperfect photos like a real user would take.

**How:** They take photos of real packaged products (different lighting/angles), upload each one into the app, and write down what goes wrong.

**Tell them:** "Just your phone camera and the app once it's live. Take photos, upload them, tell me what breaks."

---

## Tester #2 — Rules and Report Accuracy Checking

**What they'll use:** The same government Rules PDF the PPT person used, and the generated PDF reports from the app

**Why:** No special tool needed — this is a manual double-check job, comparing what the app says against the real document.

**How:** They read the rules list the PPT person made, compare it line-by-line against the actual government PDF, and later open generated reports to check the rule numbers mentioned actually match.

**Tell them:** "Just the government rules document and the reports the app generates. Double-check everything lines up correctly."

---

## Quick Summary Table

| Person | Tools |
|---|---|
| You | Python, FastAPI, Grok API, OCR tool, ReportLab, python-docx, Supabase |
| Frontend #1 | HTML, CSS, JavaScript |
| Frontend #2 | HTML, CSS, JavaScript |
| PPT Person | Government Rules PDF, PowerPoint/Google Slides |
| Tester #1 | Phone camera, the live app |
| Tester #2 | Government Rules PDF, generated reports |
