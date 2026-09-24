# PsychAssist Web

Clinical decision-support tool for structured psychiatric assessment.

**This is NOT a medical device and does NOT provide diagnoses.**  
All outputs must be verified by a qualified clinician.

## Features
- Full clinical assessment with syndrome scoring
- Formal diagnostic criteria checks (MDD, Mania, Schizophrenia, Delirium)
- Organic psychosis screen & mixed features
- Risk stratification with emergency alerts
- PHQ-9 and GAD-7 scoring
- Treatment tracker
- Simple clinical chatbot
- Local history & report download

## Run locally
```bash
pip install -r requirements.txt
streamlit run PsychAssist_streamlit.py



Updates:

```markdown

## Changelog — Recent Updates

### v5.0 — Full Feature Bundle

Large update bundling 30+ new features. The app runs out-of-the-box with
SQLite and no authentication; optional features activate automatically when
the corresponding secrets are added.

**New pages**
- Treatment Tracker — start / update / stop medications per patient,
  adherence and side-effect log, full history.
- More Scales — C-SSRS, AUDIT-C, DAST-10, MDQ, PCL-5, YMRS, MMSE
  (short, single-page versions with interpretation).
- ICD-11 / DSM-5-TR Lookup — code, criteria summary and common
  differentials for 10 major diagnoses.
- Drug Interactions — curated reference table plus a per-patient check
  against currently active medications.
- Trends — risk timeline and PHQ-9 / GAD-7 line charts per patient.
- Outcomes — service-level dashboard (symptoms improved, adherence,
  global impression, percentage improved).
- Audit Log — every database write is logged with user and timestamp.
- Backup & Restore — download an Excel backup of all tables, download
  the raw SQLite file, or upload a previous DB to restore.

**Enhanced existing pages**
- Assessment — unchanged clinically; every write now records the current
  user and an audit entry.
- Counselling & Notes — multi-colour pen (8 presets + custom colour
  picker), eraser tool with adjustable size, full-screen drawing mode,
  undo / snapshot history, SVG download, "load previous note as
  background" for re-editing, and inline voice dictation (browser Web
  Speech API).
- Report — added one-click PDF export (fpdf2); past reports remain
  browseable.
- History — free-text search and 25-row pagination.
- Patient Database — search by name, per-patient assessments and
  treatment list.
- Epidemiology — date-range window filter.

**New cross-cutting features**
- Sidebar global patient selector with auto-fill across all forms.
- Sidebar badges: overdue follow-ups and open high-risk count.
- Dark-mode toggle.
- Session timeout (30 minutes idle) when auth is enabled.
- Soft delete on every table (`deleted_at` column); all queries filter it.
- Excel multi-sheet export of all tables.
- Print CSS for clean Ctrl+P output.

**Optional features (activate via `.streamlit/secrets.toml`)**
- Authentication gate — password or per-user credentials.
- Fernet encryption of handwritten notes at rest.
- PostgreSQL / Supabase backend (SQLite used if absent).

**Project hygiene**
- `requirements.txt` extended with `fpdf2`, `openpyxl`,
  `cryptography`, `psycopg2-binary`.
- `.streamlit/secrets.toml.example` template.
- `Dockerfile` and `docker-compose.yml`.
- `tests/test_scoring.py` — pytest suite for scoring functions.
- `.github/workflows/ci.yml` — syntax check and tests on every push.
- `.pre-commit-config.yaml` — black + ruff.
- `SETUP.md` — how to turn on auth, encryption, Postgres, CI, pre-commit.

---

### v4.4 — Full-screen button fix

- Fixed `StreamlitWidgetAlreadyInstantiatedError` when toggling
  full-screen. The state change moved into an `on_click` callback so it
  runs before Streamlit re-creates the widget.

---

### v4.3 — Enhanced handwriting canvas

- Multi-colour pen: 8 preset colours plus a custom colour picker.
- Eraser tool with adjustable size.
- Full-screen drawing mode (hides sidebar and header, expands canvas to
  1600×900).
- True clear-canvas (implemented via widget-key bump).
- Empty-canvas detection before saving — no more false "saved" messages.

---

### v4.2 — IndentationError fix and cleanup

- Removed the top module docstring and converted all multi-line SQL to
  single-line concatenated strings to eliminate paste-induced
  `IndentationError`.
- Replaced non-ASCII box characters in the report text with plain ASCII.

---

### v4.1 — `st.canvas` fix

- Streamlit has no built-in canvas widget. `st.canvas(...)` raised
  `AttributeError`. Replaced with
  [`streamlit-drawable-canvas`](https://github.com/andfanilo/streamlit-drawable-canvas).
- Handwritten notes are now stored as base64 PNG data URLs in SQLite.
- Fixed swapped column indices when displaying saved counselling notes.
- Fixed `NameError: name 'conn' is not defined` on the Assessment and
  ADHD pages.
- Fixed ADHD `INSERT` column names.
- Fixed placeholder count in the Assessment `INSERT` (31 columns,
  previously 30 placeholders).

---

### Dependency additions

The following packages were added to `requirements.txt` across these
updates:

```

streamlit>=1.32
streamlit-drawable-canvas>=0.9.3
pillow>=10.0.0
pandas>=2.0.0
numpy>=1.24
fpdf2>=2.7.0
openpyxl>=3.1.0
cryptography>=42.0.0
psycopg2-binary>=2.9.9

```

---

### Known limitations

- Data stored in SQLite inside the Streamlit container is lost on every
  redeploy or reboot. For persistent storage, configure the
  `[database] url` secret (Postgres / Supabase).
- The app is publicly reachable unless the `[auth]` secret is set.
- The drug interaction table is curated and non-exhaustive; it does not
  replace a full interaction database.
- Undo on the handwriting canvas is snapshot-based, not per-stroke.

---

### Disclaimer

This tool is clinical decision support only. It is not a diagnosis and
does not replace clinical judgement. Do not use it as the sole basis for
any clinical decision.

```
