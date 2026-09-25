# PsychAssist User Guide

Version 5.2

Clinical decision support for mental health assessment, notes, treatment
tracking, and follow-up.

Not a diagnosis. Not a substitute for clinical judgement.

---

## Table of contents

1. What this app is
2. Getting started
3. The sidebar
4. Daily workflow (the core loop)
5. Registering patients with unique labels
6. Clinical Assessment
7. Standardised scales (PHQ-9, GAD-7, ADHD)
8. More Scales (16 scales)
9. Counselling & Notes (with handwriting)
10. Treatment Tracker
11. Report and PDF export
12. Trends
13. ICD-11 / DSM-5 lookup
14. Drug Interactions
15. Chat assistant
16. History, Patient Database, Follow-up
17. Epidemiology and Outcomes
18. Audit Log
19. Backup & Restore
20. Export Data
21. Security and passwords
22. Supabase and data persistence
23. Data safety reminders
24. Troubleshooting
25. Clinical caveats
26. Weekly checklist

---

## 1. What this app is

A single-user, password-protected Streamlit app for mental health
practice. It lets you:

- Register patients (with automatic unique labels for same-name cases)
- Run a structured psychiatric assessment and generate a clinical report
- Score standard scales (PHQ-9, GAD-7, ADHD, and 16 more)
- Save counselling notes with free-text and handwriting
- Track medications and follow-ups
- View patient trends, service outcomes, and an audit log
- Back up and restore your data

All data is stored in Supabase (cloud Postgres). Nothing leaves the app
except what you explicitly download.

---

## 2. Getting started

### Sign in
1. Open your app URL in any browser.
2. Enter your password.
3. You stay signed in for 30 minutes of inactivity.

### First-time setup
1. Open **Register Patient** (first item in the sidebar).
2. Register a test patient.
3. Run one full workflow end-to-end (Section 4) to confirm everything
   works.
4. Open **Backup & Restore** and download the Excel backup.

---

## 3. The sidebar

Always visible on the left (hidden automatically in full-screen canvas
mode).

| Element | What it does |
|---|---|
| Sign out | Ends your session |
| Current patient dropdown | Selects the active patient for every page |
| "Duplicates appear as..." | Reminder of the label format |
| Overdue follow-ups (red) | Count of follow-ups past their date |
| Open high-risk (yellow) | Count of HIGH or CRITICAL risk assessments |
| Dark mode toggle | Switches theme |
| Navigation radio | Menu of all 21 pages |

**Golden rule:** always pick the patient from the sidebar **before**
opening any form. Every page reads from `st.session_state.patient_name`.

---

## 4. Daily workflow (the core loop)

    Register -> Assess -> Report -> Prescribe -> Follow-up -> Trends -> Backup

### Step 1 - Register
- Register Patient -> type name, age, sex.
- If the name already exists, a code is appended (see Section 5).

### Step 2 - Assess
- Assessment page.
- Fill duration, onset, MSE, symptoms, risk.
- Click **Generate Report**.

### Step 3 - Report
- Report page.
- Download as .txt or .pdf.
- Past reports are listed below.

### Step 4 - Prescribe
- Treatment Tracker -> add medication, dose, frequency.
- Start, update, or stop from the same page.

### Step 5 - Check interactions
- Drug Interactions -> type patient name -> see flags.

### Step 6 - Follow-up
- Follow-up -> schedule (default: 14 days ahead).
- On return, complete the record with adherence and global impression.

### Step 7 - Trend
- Trends -> pick patient -> PHQ-9 and GAD-7 charts over time.

### Step 8 - Backup
- Backup & Restore -> download Excel.
- Store the file in Google Drive or email it to yourself.

---

## 5. Registering patients with unique labels

Bangladesh has many patients with identical names. This app handles
them automatically.

### How it works
- First occurrence of a name: saved as-is.
  Example: `Rahim Khan`
- Second and later: a code is appended.
  Example: `Rahim Khan (62M - P0001)`

The format is: `Name (AgeSex - Pxxxx)`.

### Steps
1. Open **Register Patient**.
2. Type the name, age, sex.
3. The app shows a live "Suggested patient label".
4. You can edit the final label if you want.
5. Click **Register patient**.

### Using it everywhere
- Sidebar dropdown lists every patient by label.
- Forms auto-fill the label.
- Reports, notes, treatments, and follow-ups all use the same label.

### Searching
- On History and Patient Database pages, typing `Rahim` matches all
  Rahims. You pick the right one by age, sex, and code.

---

## 6. Clinical Assessment

Produces a syndrome label, severity grade, formal criteria match,
organic-suspicion score, and risk stratification.

### Inputs
1. **Patient Name** - auto-filled from the sidebar.
2. **Age, Sex** - for the label.
3. **Duration** - Hours / Days / Weeks / Months / Years.
4. **Onset** - Sudden / Gradual.
5. **Pattern** - Not specified / Episodic / Chronic / Fluctuating.
6. **MSE fields**:
   - Speech: Normal / Pressured / Slow / Disorganized
   - Affect: Normal / Flat / Depressed / Labile
   - Thought: Normal / Tangential / Disorganized / Flight of ideas
   - Insight: Good / Partial / Poor
   - Judgment: Good / Fair / Poor / Impaired
7. **Substance Use** (multi-select) - Alcohol, Cannabis, Stimulants,
   Opioids, Withdrawal.
8. **Neuro Findings** (multi-select) - Head injury, Fluctuating
   cognition, Focal deficit, Seizure disorder.
9. **Impairment** (multi-select) - Occupational, Social, Self-care.
10. **Symptom categories** - tick every symptom that applies, grouped
    by Mood / Mania / Psychotic / Anxiety / OCD / Trauma / Cognitive /
    Neurological / Behavioral.
11. **Risk items**:
    - Active suicidal plan
    - Command hallucinations
    - Violent behavior
    - Access to means

### Click Generate Report

### Output
- **Syndrome**: Depressive / Manic / Psychotic / Delirium / Unknown
- **Severity**: Mild / Moderate / Severe / Very Severe
- **Formal criteria**: MDD, Bipolar I, Schizophrenia, Delirium
  (fully met or partial)
- **Organic suspicion**: LOW / MODERATE / HIGH / VERY HIGH
- **Risk**: LOW / MODERATE / HIGH / CRITICAL (with recommendation)
- **MSE paragraph**: formatted summary

### Risk scoring reference

| Points | Category |
|---|---|
| 3 | Suicidal thoughts present |
| 6 | Active suicidal plan |
| 6 | Command hallucinations |
| 5 | Violent behavior |
| 4 | Access to means |

- 0-4: LOW RISK, routine monitoring
- 5-9: MODERATE RISK, enhanced monitoring
- 10-14: HIGH RISK, urgent psychiatric consultation
- 15+: CRITICAL RISK, immediate hospitalization

---

## 7. Standardised scales (PHQ-9, GAD-7, ADHD)

### PHQ-9 (depression)
- Open PHQ-9.
- Enter patient name (auto-filled from sidebar).
- Answer 9 sliders, each 0-3.
- Auto-graded total and severity:
  - 0-4 None-Minimal
  - 5-9 Mild
  - 10-14 Moderate
  - 15-19 Moderately Severe
  - 20-27 Severe
- Click **Save PHQ-9**.

### GAD-7 (anxiety)
- Open GAD-7.
- Answer 7 sliders, each 0-3.
- Auto-graded:
  - 0-4 Minimal
  - 5-9 Mild
  - 10-14 Moderate
  - 15-21 Severe
- Click **Save GAD-7**.

### ADHD
- Open ADHD.
- Choose instrument:
  - Adult (ASRS): 6 items, 0-4, threshold 18
  - Adult (CAARS): 10 items, 0-4, threshold 30
  - Child (ADHD-RS): 10 items, 0-3, threshold 24
- Answer sliders.
- Severity: None / Mild / Moderate / Severe.
- Click **Save ADHD**.

All three save to their own tables and appear in Trends and Patient
Database.

---

## 8. More Scales (16 scales)

Open **More Scales**, pick a scale, enter the patient, answer, save.

### List

| Scale | Use | Items |
|---|---|---|
| C-SSRS | Suicide risk screen | 6 |
| AUDIT-C | Alcohol use | 3 |
| DAST-10 | Drug use | 10 |
| MDQ | Bipolar screen | 13 |
| PCL-5 | PTSD | 20 |
| YMRS | Mania severity | 11 |
| MMSE | Cognition | 19 |
| HAM-D | Depression (clinician) | 17 |
| HAM-A | Anxiety (clinician) | 14 |
| WHO-5 | Well-being | 5 |
| ISI | Insomnia | 7 |
| EPDS | Postnatal depression | 10 |
| CGI | Global impression | 2 |
| PHQ-2 | Brief depression screen | 2 |
| GAD-2 | Brief anxiety screen | 2 |
| Y-BOCS | OCD severity | 10 |

### Interpretation examples
- **C-SSRS**: 0 Low, 1-2 Moderate, 3-4 High, 5-6 Very High / immediate risk
- **MDQ**: 7+ Yes answers = positive screen
- **PCL-5**: 33+ = probable PTSD
- **EPDS**: 10+ possible depression, 13+ probable
- **PHQ-2 / GAD-2**: 3+ = positive screen, use full PHQ-9 / GAD-7

Every score is saved with the patient name and timestamp.

---

## 9. Counselling & Notes

Free-text notes plus a full handwriting canvas.

### Fields
- Patient name (auto-filled)
- Age, Sex, Date
- Counselling Symptoms / Issues (large text box)
- Important Notes / Follow-up Reminders (large text box)

### Handwriting canvas

**Toolbar**
- **Pen colour**: 8 presets (Black, Red, Blue, Green, Purple, Orange,
  Brown, Pink) or Custom colour picker
- **Pen width**: 1-20
- **Tool**: Pen or Eraser
  - Eraser size: 5-60
- **Full-screen drawing mode** checkbox: hides sidebar, expands canvas
  to 1600x900

**Buttons**
| Button | Effect |
|---|---|
| Save handwriting | Capture canvas as PNG (must draw something) |
| Undo last | Remove the last snapshot |
| Push snapshot | Add current drawing to undo history |
| Clear | Wipe canvas completely |
| Fullscreen | Toggle full-screen mode |
| Download handwriting (SVG) | Vector export of strokes |

**Re-edit a previous note**
- Scroll to "Load a previous note to re-edit"
- Pick a note from the dropdown
- Click **Load as background**
- The old drawing appears under the canvas for annotation

**Voice dictation**
- Click **Start dictation** in the embedded panel
- Speak; transcript appears below
- Copy into the text boxes

**Save all**
- Click **Save All Notes** to persist.

---

## 10. Treatment Tracker

### Start a medication
1. Open Treatment Tracker.
2. Fill patient, medication, class, dose, frequency, route, start date.
3. Optional: psychotherapy and notes.
4. Click **Start medication**.

### Update adherence and side effects
- Active medications list
- Expand the medication
- Set Adherence (Good / Partial / Poor) and type Side effects
- Click **Update**

### Stop a medication
- Expand the medication
- Type reason to stop
- Click **Stop medication**

### History
- All past and current medications are listed below with start and
  end dates.

---

## 11. Report and PDF export

### Current report
- Open Report
- The report text is shown
- If AI insights are present, they appear below

### Downloads
- **Download .txt** - plain text
- **Download PDF** - formatted PDF (requires fpdf2 installed)

### Past reports
- Listed as expandable rows
- Click to view the full report and AI insights

---

## 12. Trends

Open **Trends**, type the patient's name, see:
- **PHQ-9 over time** - line chart
- **GAD-7 over time** - line chart

Charts populate as you save more scale results.

---

## 13. ICD-11 / DSM-5 lookup

Open **ICD Lookup**, pick a diagnosis:
- Major Depressive Disorder
- Bipolar I Disorder - Manic Episode
- Schizophrenia Spectrum Disorder
- Delirium
- Generalized Anxiety Disorder
- ADHD
- PTSD
- OCD
- Panic Disorder
- Substance Use Disorder

Shows:
- ICD-11 code
- DSM-5-TR code
- Criteria summary
- Common differentials

---

## 14. Drug Interactions

### Reference table
All curated interaction pairs are listed with severity.

### Check a patient
- Enter patient name
- The app looks at all Active medications
- Flags any pair that matches the table

**Severity levels**: Severe (red), Moderate (orange), Minor (grey).

⚠ Non-exhaustive. Always confirm with a full interaction database.

---

## 15. Chat assistant

A lightweight assistant that returns general mental health references.
Not a clinical tool. Type a question, receive a short answer.

---

## 16. History, Patient Database, Follow-up

### History
- Search by patient name or syndrome
- 25 rows per page
- Pagination via "Page" number

### Patient Database
- Search by name
- Select a patient to see their assessments and treatments

### Follow-up
- **Schedule**: patient, date (default +14 days), notes
- **Complete**: pick pending, mark improved, adherence, side effects,
  global impression
- **All**: full table below

---

## 17. Epidemiology and Outcomes

### Epidemiology
- Look-back window slider (7-3650 days)
- Bar charts: syndrome, severity, risk, sex

### Outcomes
- Symptoms improved, adherence, global impression charts
- Metrics: follow-ups completed, % improved or partially improved

---

## 18. Audit Log

Every write (insert, update, stop) is logged with:
- Timestamp
- User
- Action
- Table name
- Row ID
- Detail

View the last 500 entries on the Audit Log page.

---

## 19. Backup & Restore

### Download
- **Backup (.xlsx)** - all 10 tables in separate sheets
- **SQLite DB** - raw database file (only when running in SQLite mode)

### Restore
- Upload a .db file (SQLite mode only)

**Recommended: download after every session.**

---

## 20. Export Data

### Excel
- One-click .xlsx with all tables as separate sheets

### CSV
- Per-table CSV download

---

## 21. Security and passwords

- The app is password-gated.
- Passwords are stored as Streamlit secrets, not in code.
- Session times out after 30 minutes idle.
- Every write is logged with the current user.

### Change your password
1. Streamlit Cloud → Settings → Secrets
2. Edit `[auth] password = "new-password"`
3. Save (app reboots automatically)

---

## 22. Supabase and data persistence

### Why Supabase
The app defaults to SQLite (data wipes on every redeploy). With
Supabase configured, data persists across redeploys.

### Setup (one-time)
1. Create a free Supabase project
2. Copy the Session pooler connection string
3. Streamlit Cloud → Settings → Secrets → add:

        [database]
        url = "postgresql://postgres.xxx:password@aws-0-region.pooler.supabase.com:5432/postgres"

4. Save; the app creates its tables on first run

### Free tier limits
- 500 MB database
- 5 GB egress per month
- **Projects pause after 7 days with no activity**
- No automatic backups on the free tier

---

## 23. Data safety reminders

1. **Back up after every session** (Backup & Restore -> Excel)
2. **Open the app at least once a week** to keep Supabase active
3. **Save backups to Google Drive**, not just your phone
4. **Do not lose your password** - it's in Streamlit secrets
5. **Do not share the app URL** - it's password-gated but not per-user

---

## 24. Troubleshooting

| Symptom | Fix |
|---|---|
| Forgot password | Streamlit Cloud -> Settings -> Secrets -> edit `[auth]` |
| App shows old code | Streamlit Cloud -> ⋮ -> Reboot |
| Data missing after redeploy | Check `[database]` secret still present |
| Supabase paused | Open Supabase dashboard, click Restore |
| Report won't generate | Ensure patient name is filled |
| Handwriting not saving | Draw something first |
| Charts empty on Trends | Save a scale for that patient first |
| Session timed out | Sign in again |
| "Widget already instantiated" | Reboot the app |
| Number input looks wrong | Use the sidebar selector, not manual typing |

---

## 25. Clinical caveats

- This tool is **decision support only**. It is not a diagnosis.
- Scores reflect your inputs. Correlate with clinical judgement,
  collateral history, and investigations.
- The drug interaction table is curated and non-exhaustive.
- Do not use this tool as the sole basis for any clinical decision.
- The app is designed for single-user personal use. If you add
  colleagues, plan for per-user accounts and per-user data scoping.

---

## 26. Weekly checklist

- [ ] Open the app (prevents Supabase pause)
- [ ] Back up to Excel (Backup & Restore)
- [ ] Review overdue follow-ups badge
- [ ] Review open high-risk badge
- [ ] Check Audit Log for anomalies
- [ ] Confirm Trends and Outcomes charts still load
- [ ] Confirm the password prompt still appears on a fresh browser

---

End of guide.