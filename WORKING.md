# PS-SIH26034 — Simple Task Split (No Jargon)

You handle the backend and all the API/AI integration — that's the hard, technical part, and it's on you. Everyone else is a beginner, so their jobs are kept simple and hands-on: mostly building screens, checking outputs, and putting the presentation together. Below is exactly what each person does, in plain words.

---

## You — Backend + AI Integration
You're doing everything that involves code talking to APIs and making decisions:
- Taking the uploaded image, sending it to the AI/OCR to read the label.
- Writing the logic that checks the label against the rules and decides what's missing or wrong.
- Making the PDF report at the end.
- Setting up the database that stores every scan.
- Login/signup system (basic — user logs in, that's it).

Nobody else touches this. This is the "brain" of the project.

---

## Frontend Person #1 — The Upload Screen
Their whole job: build the page where someone uploads a photo or pastes a product link, and the page that shows the result after scanning.

**What they actually do:**
- Make a page with a button to upload an image, and a text box to paste a product link.
- Make a "Scan" button.
- Make a results page that shows: the photo, a list of what's missing/wrong, and a "Download Report" button.
- Make it look clean — colors, spacing, fonts, buttons that look nice when clicked.

**What they don't touch:**
- They don't write any code that talks to the AI or database. You give them fake sample data (a made-up list of "these things are missing") and they just build the screen to display it nicely. Once your backend is ready, connecting the screen to real data is a small, quick step — not their job to figure out.

**In one line, tell them:** "Build the upload page and the results page. I'll tell you exactly what data you'll get, you just make it look good and display it."

---

## Frontend Person #2 — The History/Dashboard Screen
Their whole job: build the page that shows all the past scans, so an officer can look back at old reports.

**What they actually do:**
- Make a page with a list/table of past scans (product name, date, pass/fail, score).
- Add a search box to filter by product name.
- Add a simple login page (just email + password fields, a login button — I'll handle what happens when they click it).
- Make it look clean and match Person #1's design so the whole app feels consistent.

**What they don't touch:**
- Same as above — they don't connect to the real database themselves. You give them fake sample rows to build against, and I plug in the real data later.

**In one line, tell them:** "Build the dashboard page showing past scans, and the login page. I'll give you sample data to build with, you just make the screen and make it look good."

---

## PPT Person — Rules + Presentation
Two jobs, both important, neither involves coding:

**Job 1 — Collect the real rules:**
- Go to the government's Legal Metrology website, download the actual Rules document (2011).
- Pick out the important ones: what must be on a label (name of maker, quantity, price, date, contact info) and what font size is required.
- Write these down in a simple list with the exact rule number next to each one — you'll hand this list to me and I'll put it into the system.
- **Important:** copy the rule number exactly as written in the document. Don't guess or reword it.

**Job 2 — Build the presentation:**
- Use the exact PPT template you were given — 6 slides, don't add or remove slides, don't rename the slide titles.
- I'll give you the content for each slide separately — you just need to design it nicely (not paragraphs, use bullet points and a simple diagram/picture where possible).

**In one line, tell them:** "Go get the real rules from the government site and list them out for me with rule numbers. Then build the 6-slide PPT with content I give you — just make it look clean, bullet points only, no big blocks of text."

---

## Tester #1 — Try It With Real Photos
- Take 15-20 real photos of packaged products around your house — different lighting, some blurry, some at an angle, not just perfect clear photos.
- Upload each one to the app once it's working and note down what goes wrong (something not detected, wrong text, app crashes, etc).
- Tell me exactly which photo failed and what happened — send me the photo too.

**In one line, tell them:** "Take a bunch of real product photos, upload them once it's working, and tell me exactly what breaks or looks wrong."

---

## Tester #2 — Double-Check the Rules and Reports
- Take the list of rules the PPT person collected, and independently check each one against the real government document — make sure nothing was copied wrong.
- Once reports start generating, open a few and check: does the report make sense? Is the rule number it mentions actually correct? Does the PDF look properly formatted (nothing cut off, nothing missing)?

**In one line, tell them:** "Double check the rules list against the real government document for mistakes, and once reports start coming out, check that they actually make sense and look right."

---

## Quick Summary Table

| Person | One-line job |
|---|---|
| You | Backend, AI integration, database, report generation — the whole engine |
| Frontend #1 | Upload page + results page, using sample data I give you |
| Frontend #2 | Dashboard/history page + login page, using sample data I give you |
| PPT Person | Collect real rules from govt site + build the 6-slide PPT |
| Tester #1 | Try real photos, report what breaks |
| Tester #2 | Double check rules and reports for accuracy |

Give each person their "one-line job" first, then hand them their fuller list when they're ready to start.
