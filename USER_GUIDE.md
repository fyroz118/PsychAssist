# PsychAssist User Guide

Clinical decision support for mental health assessment, notes, and follow-up.
Not a diagnosis. Not a substitute for clinical judgement.

Version 5.1

---

## 1. Getting started

### Sign in
1. Open the app URL in any browser.
2. Enter your password.
3. You stay signed in for 30 minutes of inactivity.

### First-time setup (one-off)
1. Sidebar -> Register Patient -> register yourself as a test patient.
2. Run one full workflow end-to-end (see Section 3) to confirm everything works.
3. Go to Backup & Restore -> download the Excel backup.

---

## 2. The sidebar (always visible)

| Element | Purpose |
|---|---|
| Sign out | Ends your session |
| Current patient dropdown | Selects the active patient for every page |
| Overdue follow-ups badge | Red warning if any follow-up is past its date |
| Open high-risk badge | Yellow warning if any patient has HIGH or CRITICAL risk |
| Dark mode toggle | Switch theme |
| Navigation | Menu of all pages |

**Rule:** Always pick the patient from the sidebar first. Do not type the
name manually into forms unless you are registering a new patient.

---

## 3. Daily workflow (the core loop)

    Register Patient -> Assessment -> Report -> Treatment -> Follow-up -> Trends -> Backup

### Step 1 - Register the patient
- Open Register Patient.
- Type full name, age, sex.
- If the name already exists, the app auto-appends a code like
  `(45M - P0001)` so the two patients never collide.
- Click Register patient.
- The patient now appears in the sidebar dropdown.

### Step 2 - Run the clinical assessment
- Open Assessment.
- Patient name auto-fills from the sidebar.
- Set Duration, Onset, Pattern (top row).
- Set MSE fields: Speech, Affect, Thought, Insight, Judgment.
- Tick Substance Use, Neuro Findings, Impairment (as relevant).
- Tick all symptoms from the symptom categories.
- Tick any risk items (suicidal plan, command hallucinations, violence,
  access to means).
- Click Generate Report.

The app produces:
- A syndrome label (Depressive / Manic / Psychotic / Delirium)
- A severity grade
- Formal criteria match (MDD, Bipolar I, Schizophrenia, Delirium)
- Organic-suspicion score
- Risk level and recommendation
- MSE summary

### Step 3 - View the report
- Open Report.
- The current report is shown.
- Download as .txt or PDF.
- Past reports are listed below.

### Step 4 - Prescribe / start medication
- Open Treatment Tracker.
- Fill in medication, class, dose, frequency, start date.
- Click Start medication.
- Active meds appear below; update adherence or stop from the same page.

### Step 5 - Run a drug interaction check
- Open Drug Interactions.
- Type the patient name.
- The app flags any interactions among their active medications.

### Step 6 - Schedule a follow-up
- Open Follow-up.
- Enter patient, date (default: 14 days from today), notes.
- Click Schedule.

### Step 7 - Record the follow-up
- When the patient returns, open Follow-up.
- Pick the pending appointment.
- Fill in: symptoms improved, adherence, side effects, global impression.
- Click Mark complete.

### Step 8 - Review the trend
- Open Trends.
- Enter patient name.
- See risk timeline, PHQ-9 chart, GAD-7 chart over time.

### Step 9 - Back up
- Open Backup & Restore.
- Download the .xlsx or the SQLite file.
- Save to Google Drive or phone storage.

---

## 4. Standardised scales

### PHQ-9 (depression)
- Open PHQ-9, pick patient.
- Answer 9 questions, 0-3 each.
- Auto-graded: 0-4 none, 5-9 mild, 10-14 moderate, 15-19 mod-severe, 20+ severe.
- Click Save PHQ-9.

### GAD-7 (anxiety)
- Open GAD-7, pick patient.
- Answer 7 questions, 0-3 each.
- Auto-graded: 0-4 minimal, 5-9 mild, 10-14 moderate, 15+ severe.
- Click Save GAD-7.

### ADHD
- Open ADHD, pick patient.
- Choose instrument: Adult (ASRS), Adult (CAARS), or Child (ADHD-RS).
- Answer all items.
- Score is compared to the scale threshold.
- Click Save ADHD.

### More Scales
Includes:
- C-SSRS (suicide screen)
- AUDIT-C (alcohol)
- DAST-10 (drug use)
- MDQ (bipolar screen)
- PCL-5 (PTSD)
- YMRS (mania severity)
- MMSE (cognition)

Select the scale, enter patient, answer questions, click Save scale.

---

## 5. Counselling & Notes

Free-text notes plus a handwriting canvas.

### Text notes
- Patient name, age, sex, date.
- Counselling symptoms / issues (large box).
- Important notes / follow-up reminders (large box).

### Handwriting canvas
- Pen colour: 8 presets or Custom picker.
- Pen width: 1-20.
- Tool: Pen or Eraser (with size slider).
- Full-screen mode: hides sidebar, expands canvas to 1600x900.

### Buttons
| Button | What it does |
|---|---|
| Save handwriting | Captures the canvas as PNG (must draw something first) |
| Undo last | Removes the last snapshot (see Push snapshot) |
| Push snapshot | Adds current drawing to the undo history |
| Clear | Wipes the canvas completely |
| Fullscreen | Toggles full-screen mode |
| Download handwriting (SVG) | Vector export of strokes |

### Voice dictation
- Click Start dictation in the embedded panel.
- Speak; the transcript appears below.
- Copy the transcript into a text box, then save.

### Re-edit a previous note
- Scroll to "Load a previous note to re-edit".
- Pick a note from the dropdown.
- Click Load as background.
- The old drawing appears under the canvas for annotation.

### Save
- Click Save All Notes to persist.

---

## 6. Lookups

### ICD Lookup
Type a diagnosis (MDD, Bipolar I, Schizophrenia, Delirium, GAD, ADHD,
PTSD, OCD, Panic Disorder, Substance Use Disorder). Shows ICD-11 code,
DSM-5 code, criteria summary, common differentials.

### Drug Interactions
- Reference table at the top.
- Below: type a patient name and the app checks their active meds
  against the table.
- Non-exhaustive; always confirm with a full interaction database.

---

## 7. Records and administration

### History
- Search by name or syndrome.
- 25 rows per page, next/previous pagination.

### Patient Database
- Search by name.
- Pick a patient -> see their assessments and treatment history.

### Epidemiology
- Slider for look-back window (7 to 3650 days).
- Bar charts: by syndrome, severity, risk, sex.

### Outcomes
- Charts of symptoms improved, adherence, global impression.
- Metric: percentage of follow-ups that improved.

### Audit Log
- Every write is logged with timestamp, user, table, row ID.
- Use for compliance and traceability.

---

## 8. Data management

### Backup & Restore
- Download backup (.xlsx): multi-sheet Excel of every table.
- Download SQLite DB: raw file.
- Upload a previous .db file to restore (SQLite mode only).

### Export Data
- One-click .xlsx with all 10 tables.
- Individual CSVs per table.

**Recommended cadence:**
- Back up after every session.
- Download the Excel backup at least weekly.
- Store backups in Google Drive, not only on the phone.

### Supabase (free tier) reminders
- 500 MB database, 5 GB egress per month.
- Projects pause after 7 days with no activity.
- Open the app at least once a week to prevent pausing.
- Free tier has no automatic backups - your manual Excel download is
  the backup.

---

## 9. Security

- The app is password-gated.
- Every action is logged with the current user.
- Handwritten notes are stored in Supabase. Encryption is available
  but off by default.
- If you enable encryption, save the Fernet key in a password manager.
  Losing the key makes encrypted notes permanently unreadable.

---

## 10. Troubleshooting

| Symptom | Fix |
|---|---|
| Forgot password | Streamlit Cloud -> Settings -> Secrets -> change `[auth] password` -> Save |
| App shows old code | Streamlit Cloud -> ⋮ -> Reboot |
| Data missing after redeploy | Check the `[database]` secret still points at Supabase |
| Supabase paused | Open the Supabase dashboard, click Restore |
| Report won't generate | Ensure Patient Name is filled |
| Handwriting not saving | Draw something first; the empty canvas is rejected |
| Charts empty on Trends | Save a PHQ-9 or GAD-7 for that patient first |
| Session timed out | Sign in again; 30-minute idle limit |

---

## 11. Clinical caveats

- This tool is decision support only. It is not a diagnosis.
- Scores and syndromes reflect the inputs you provide.
- Always correlate with clinical judgement, collateral history, and
  investigations.
- The drug interaction table is curated and non-exhaustive.
- Do not use this tool as the sole basis for any clinical decision.

---

## 12. Weekly checklist

- [ ] Open the app (keeps Supabase from pausing)
- [ ] Back up to Excel (Backup & Restore page)
- [ ] Review overdue follow-ups badge
- [ ] Review open high-risk badge
- [ ] Check Audit Log for any anomalies
- [ ] Confirm all charts on Trends and Outcomes still load

---

## 13. Getting help

If something breaks:
1. Note the page name and what you clicked.
2. Note the exact error message (if any).
3. Check Troubleshooting (Section 10).
4. If unresolved, capture a screenshot and describe the steps taken.

---

End of guide.