# -*- coding: utf-8 -*-
# PsychAssist Web v5.2 - Clinical Decision Support (Streamlit)
# Decision support only - not a diagnosis.
#
# v5.2
#   * Added 9 more scales to the More Scales page:
#     HAM-D, HAM-A, WHO-5, ISI, EPDS, CGI, PHQ-2, GAD-2, Y-BOCS.
#     Total scales on More Scales page: 16.
#
# v5.1
#   * Unique patient labels for same-name patients
#     ("Rahim Khan (45M - P0001)").
#   * New Register Patient page.
#
# v5.0
#   * Treatment tracker, multi-step undo, PDF export, ICD lookup,
#     drug interactions, trends, outcomes, audit log, backup/restore,
#     Postgres/Supabase support, auth gate, encryption, dark mode,
#     sidebar badges, global patient selector, voice dictation.
#
# v4.x
#   * Handwriting canvas via streamlit-drawable-canvas.
#   * Multi-colour pen, eraser, fullscreen, clear.
#   * Fixed IndentationError from pasted multi-line SQL.

import io
import os
import re
import base64
import hashlib
import random
import sqlite3
import time
from datetime import datetime, date, timedelta

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image
from streamlit_drawable_canvas import st_canvas

try:
    from fpdf import FPDF
    HAS_FPDF = True
except Exception:
    HAS_FPDF = False

try:
    from cryptography.fernet import Fernet
    HAS_FERNET = True
except Exception:
    HAS_FERNET = False

try:
    import openpyxl
    HAS_OPENPYXL = True
except Exception:
    HAS_OPENPYXL = False

DB_PATH = "psychassist_web.db"
SESSION_TIMEOUT_MIN = 30

st.set_page_config(
    page_title="PsychAssist Web",
    page_icon="brain",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _secret(*path, default=None):
    try:
        cur = st.secrets
        for p in path:
            cur = cur[p]
        return cur
    except Exception:
        return default


APP_PASSWORD = _secret("auth", "password", default=None)
USER_NAMES = _secret("auth", "users", default=None)
DB_URL = _secret("database", "url", default=None)
FERNET_KEY = _secret("encryption", "key", default=None)
MULTIUSER = bool(USER_NAMES)
USE_AUTH = bool(APP_PASSWORD or USER_NAMES)
USE_PG = bool(DB_URL)
USE_ENCRYPTION = bool(FERNET_KEY and HAS_FERNET)


def _fernet():
    if not USE_ENCRYPTION:
        return None
    if "fernet" not in st.session_state:
        st.session_state.fernet = Fernet(
            FERNET_KEY.encode() if isinstance(FERNET_KEY, str) else FERNET_KEY
        )
    return st.session_state.fernet


def enc(text):
    if not text or not USE_ENCRYPTION:
        return text or ""
    return "enc::" + _fernet().encrypt(text.encode()).decode()


def dec(text):
    if not text or not isinstance(text, str):
        return text or ""
    if not text.startswith("enc::"):
        return text
    if not USE_ENCRYPTION:
        return text
    try:
        return _fernet().decrypt(text[5:].encode()).decode()
    except Exception:
        return text


def check_auth():
    if not USE_AUTH:
        st.session_state.user = "guest"
        return True
    if st.session_state.get("authed"):
        return True
    st.title("PsychAssist - Sign in")
    st.caption("Decision support only. Not a diagnosis.")
    with st.form("login"):
        user = st.text_input("Username")
        pw = st.text_input("Password", type="password")
        ok = st.form_submit_button("Sign in")
    if ok:
        if USER_NAMES and user in USER_NAMES:
            if pw == USER_NAMES[user]:
                st.session_state.authed = True
                st.session_state.user = user
                st.session_state.last_seen = time.time()
                st.rerun()
            else:
                st.error("Wrong password.")
        elif APP_PASSWORD and pw == APP_PASSWORD:
            st.session_state.authed = True
            st.session_state.user = user or "clinician"
            st.session_state.last_seen = time.time()
            st.rerun()
        else:
            st.error("Invalid credentials.")
    return False


def enforce_timeout():
    now = time.time()
    last = st.session_state.get("last_seen", now)
    if now - last > SESSION_TIMEOUT_MIN * 60:
        st.session_state.authed = False
        st.warning("Session timed out. Please sign in again.")
        st.stop()
    st.session_state.last_seen = now


def _adapt(sql):
    return sql.replace("?", "%s") if USE_PG else sql


def get_conn():
    if USE_PG:
        try:
            import psycopg2
            return psycopg2.connect(DB_URL)
        except Exception:
            pass
    return sqlite3.connect(DB_PATH, check_same_thread=False)


class DBCursor:
    def __init__(self, cur, pg):
        self._c = cur
        self._pg = pg
    def execute(self, sql, params=()):
        self._c.execute(_adapt(sql) if self._pg else sql, params)
        return self
    def fetchall(self):
        return self._c.fetchall()
    def fetchone(self):
        return self._c.fetchone()


class DBConn:
    def __init__(self, raw, pg):
        self._raw = raw
        self._pg = pg
    def cursor(self):
        return DBCursor(self._raw.cursor(), self._pg)
    def execute(self, sql, params=()):
        cur = self._raw.cursor()
        cur.execute(_adapt(sql) if self._pg else sql, params)
        return DBCursor(cur, self._pg)
    def commit(self):
        self._raw.commit()
    def close(self):
        self._raw.close()


def db():
    return DBConn(get_conn(), USE_PG)


def init_db():
    c = db()
    cur = c.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS assessments (id INTEGER PRIMARY KEY AUTOINCREMENT, patient_name TEXT, age TEXT, sex TEXT, symptoms TEXT, syndrome TEXT, severity TEXT, risk_level TEXT, formal_diagnoses TEXT, organic_level TEXT, organic_score INTEGER, functional_impairment TEXT, mse TEXT, duration TEXT, onset TEXT, pattern TEXT, speech TEXT, affect TEXT, thought_process TEXT, insight TEXT, judgment TEXT, substance_use TEXT, neuro_findings TEXT, report_text TEXT, ai_insights TEXT, mdd_criteria TEXT, mania_criteria TEXT, schizophrenia_criteria TEXT, delirium_criteria TEXT, mixed_features INTEGER, symptom_weight REAL, phq9_score INTEGER, gad7_score INTEGER, adhd_score INTEGER, adhd_type TEXT, adhd_severity TEXT, differential TEXT, treatment_recommendations TEXT, created_by TEXT, deleted_at TEXT, timestamp TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS treatments (id INTEGER PRIMARY KEY AUTOINCREMENT, patient_name TEXT, medication_name TEXT, medication_class TEXT, dose TEXT, frequency TEXT, route TEXT, start_date TEXT, end_date TEXT, status TEXT, adherence TEXT, side_effects TEXT, psychotherapy TEXT, reason_start TEXT, reason_stop TEXT, notes TEXT, created_by TEXT, deleted_at TEXT, timestamp TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS phq9_scores (id INTEGER PRIMARY KEY AUTOINCREMENT, patient_name TEXT, total_score INTEGER, severity TEXT, answers TEXT, created_by TEXT, deleted_at TEXT, timestamp TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS gad7_scores (id INTEGER PRIMARY KEY AUTOINCREMENT, patient_name TEXT, total_score INTEGER, severity TEXT, answers TEXT, created_by TEXT, deleted_at TEXT, timestamp TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS adhd_scores (id INTEGER PRIMARY KEY AUTOINCREMENT, patient_name TEXT, total_score INTEGER, severity TEXT, answers TEXT, adhd_type TEXT, created_by TEXT, deleted_at TEXT, timestamp TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS counselling_notes (id INTEGER PRIMARY KEY AUTOINCREMENT, patient_name TEXT, age TEXT, sex TEXT, date TEXT, counselling_symptoms TEXT, important_notes TEXT, handwritten_notes TEXT, handwriting_svg TEXT, created_by TEXT, deleted_at TEXT, timestamp TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS follow_ups (id INTEGER PRIMARY KEY AUTOINCREMENT, patient_name TEXT, assessment_id INTEGER, follow_up_date TEXT, status TEXT, notes TEXT, symptoms_improved TEXT, adherence TEXT, side_effects TEXT, global_impression TEXT, created_by TEXT, deleted_at TEXT, created_at TEXT, completed_at TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS patients (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, age TEXT, sex TEXT, phone TEXT, notes TEXT, created_by TEXT, deleted_at TEXT, first_seen TEXT, last_seen TEXT, created_at TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS audit_log (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, user TEXT, action TEXT, table_name TEXT, row_id INTEGER, detail TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS other_scales (id INTEGER PRIMARY KEY AUTOINCREMENT, patient_name TEXT, scale TEXT, score INTEGER, severity TEXT, answers TEXT, created_by TEXT, deleted_at TEXT, timestamp TEXT)")
    c.commit()
    c.close()


def audit(action, table_name, row_id=None, detail=""):
    try:
        c = db()
        c.execute("INSERT INTO audit_log (ts, user, action, table_name, row_id, detail) VALUES (?,?,?,?,?,?)", (str(datetime.now()), st.session_state.get("user", "?"), action, table_name, row_id, detail[:500]))
        c.commit()
        c.close()
    except Exception:
        pass


init_db()


symptom_categories = {
    "Mood Symptoms": ["Low mood", "Anhedonia", "Fatigue", "Hopelessness", "Excessive guilt", "Suicidal thoughts", "Sleep disturbance", "Irritability"],
    "Mania Symptoms": ["Reduced sleep", "Increased energy", "Grandiosity", "Pressured speech", "Racing thoughts", "Risk-taking behavior", "Distractibility"],
    "Psychotic Symptoms": ["Auditory hallucinations", "Visual hallucinations", "Delusions", "Paranoia", "Thought broadcasting", "Disorganized speech", "Negative symptoms"],
    "Anxiety Symptoms": ["Panic attacks", "Excessive worry", "Palpitations", "Sweating", "Tremor", "Avoidance behavior", "Fear of dying"],
    "OCD Symptoms": ["Obsessions", "Compulsions"],
    "Trauma Symptoms": ["Flashbacks", "Nightmares", "Hypervigilance"],
    "Cognitive Symptoms": ["Memory loss", "Confusion", "Disorientation", "Fluctuating attention", "Personality change", "Poor concentration"],
    "Neurological Symptoms": ["Seizure", "Weakness", "Tremor (neurological)", "Gait disturbance", "Headache", "Loss of consciousness"],
    "Behavioral Symptoms": ["Aggression", "Self-harm", "Catatonia", "Social withdrawal"],
}

ICD_LOOKUP = {
    "Major Depressive Disorder": {"icd11": "6A70", "dsm5": "296.2x / 296.3x", "criteria": "5+ symptoms for 2 weeks including low mood or anhedonia; functional impairment; not due to substance/medical cause.", "differential": "Bipolar depression, persistent depressive disorder, adjustment disorder, hypothyroidism, anemia."},
    "Bipolar I Disorder - Manic Episode": {"icd11": "6A60", "dsm5": "296.4x", "criteria": "Elevated/irritable mood + increased energy for >=1 week (or any duration if hospitalized) with 3+ manic symptoms.", "differential": "Substance-induced mood, schizoaffective, ADHD, hyperthyroidism, steroid-induced mania."},
    "Schizophrenia Spectrum Disorder": {"icd11": "6A20", "dsm5": "295.90", "criteria": ">=2 of: delusions, hallucinations, disorganized speech, disorganized behavior, negative symptoms; >=6 months.", "differential": "Substance-induced psychosis, schizoaffective, bipolar with psychotic features, medical/neuro cause."},
    "Delirium": {"icd11": "6D70", "dsm5": "780.09", "criteria": "Acute onset, fluctuating attention and awareness; secondary to medical/substance cause.", "differential": "Dementia, psychosis, depression, mania."},
    "Generalized Anxiety Disorder": {"icd11": "6B00", "dsm5": "300.02", "criteria": "Excessive worry >=6 months, difficult to control, with 3+ of restlessness, fatigue, concentration, irritability, muscle tension, sleep disturbance.", "differential": "Panic disorder, social anxiety, OCD, GAD secondary to medical (hyperthyroid, caffeine)."},
    "ADHD": {"icd11": "6A05", "dsm5": "314.0x", "criteria": ">=6 inattentive or >=6 hyperactive/impulsive symptoms, onset before 12, in 2+ settings, impairment.", "differential": "Anxiety, depression, learning disorder, trauma, sleep disorder, substance use."},
    "PTSD": {"icd11": "6B40", "dsm5": "309.81", "criteria": "Trauma exposure + intrusion, avoidance, negative cognitions, hyperarousal for >=1 month.", "differential": "Acute stress disorder, adjustment disorder, depression, panic disorder, TBI."},
    "OCD": {"icd11": "6B20", "dsm5": "300.3", "criteria": "Obsessions and/or compulsions that are time-consuming or cause distress/impairment.", "differential": "GAD, specific phobia, tic disorder, OCD personality."},
    "Panic Disorder": {"icd11": "6B01", "dsm5": "300.01", "criteria": "Recurrent unexpected panic attacks + >=1 month of persistent concern or maladaptive behavior.", "differential": "Medical causes (cardiac, thyroid, pheo), substance use, GAD, social anxiety."},
    "Substance Use Disorder": {"icd11": "6C4x", "dsm5": "various", "criteria": ">=2 of 11 criteria within 12 months (control, impairment, risky use, pharmacological criteria).", "differential": "Primary psychiatric disorder with secondary use, medical cause, dual diagnosis."},
}

DRUG_INTERACTIONS = [
    ("SSRI", "MAOI", "Severe", "Serotonin syndrome risk - avoid; 14-day washout."),
    ("SSRI", "Triptan", "Moderate", "Serotonin syndrome risk; monitor."),
    ("SSRI", "NSAID", "Moderate", "Increased GI bleeding; consider PPI."),
    ("SSRI", "Warfarin", "Severe", "Increased bleeding; monitor INR."),
    ("SSRI", "Tramadol", "Moderate", "Seizure + serotonin syndrome risk."),
    ("Lithium", "NSAID", "Severe", "Lithium toxicity - avoid or monitor levels."),
    ("Lithium", "ACE-I/ARB", "Severe", "Lithium toxicity risk; monitor levels."),
    ("Lithium", "Thiazide", "Severe", "Lithium toxicity risk; monitor levels."),
    ("Valproate", "Lamotrigine", "Severe", "Stevens-Johnson risk; halve lamotrigine."),
    ("Valproate", "Carbamazepine", "Moderate", "Reduced valproate levels."),
    ("Clozapine", "Carbamazepine", "Severe", "Agranulocytosis risk; avoid."),
    ("Clozapine", "Caffeine", "Moderate", "Increased clozapine levels."),
    ("Olanzapine", "Benzodiazepine", "Moderate", "Excess sedation; caution."),
    ("Haloperidol", "QT-prolongers", "Severe", "Additive QT prolongation."),
    ("Benzodiazepine", "Opioid", "Severe", "Respiratory depression - avoid."),
    ("Benzodiazepine", "Alcohol", "Severe", "Respiratory depression, overdose."),
    ("TCA", "MAOI", "Severe", "Hypertensive crisis - avoid."),
    ("TCA", "SSRI", "Severe", "Serotonin syndrome; 2-week washout."),
    ("Antipsychotic", "Metformin", "Minor", "Weight gain mitigation."),
    ("Lamotrigine", "OCP", "Moderate", "OCP reduces lamotrigine levels."),
]

medication_database = {
    "Major Depressive Disorder": {
        "first_line": [
            {"name": "Sertraline", "class": "SSRI", "starting_dose": "50mg", "max_dose": "200mg", "side_effects": "Nausea, headache, insomnia, sexual dysfunction", "contraindications": "MAOIs within 14 days"},
            {"name": "Escitalopram", "class": "SSRI", "starting_dose": "10mg", "max_dose": "20mg", "side_effects": "Nausea, fatigue, insomnia", "contraindications": "MAOIs, pimozide"},
            {"name": "Fluoxetine", "class": "SSRI", "starting_dose": "20mg", "max_dose": "80mg", "side_effects": "Nervousness, anxiety, insomnia", "contraindications": "MAOIs, thioridazine"},
        ],
        "second_line": [
            {"name": "Bupropion", "class": "NDRI", "starting_dose": "150mg", "max_dose": "300mg", "side_effects": "Agitation, dry mouth, insomnia", "contraindications": "Seizure disorder, eating disorders"},
        ],
        "augmentation": [
            {"name": "Aripiprazole", "class": "Atypical Antipsychotic", "starting_dose": "2-5mg", "max_dose": "15mg", "side_effects": "Akathisia, weight gain", "contraindications": "Hypersensitivity"},
        ],
    },
    "Bipolar I Disorder - Manic Episode": {
        "first_line": [
            {"name": "Lithium", "class": "Mood Stabilizer", "starting_dose": "300mg", "max_dose": "1800mg", "side_effects": "Tremor, polydipsia, polyuria", "contraindications": "Severe renal disease"},
            {"name": "Valproate", "class": "Anticonvulsant", "starting_dose": "250mg", "max_dose": "60mg/kg", "side_effects": "Sedation, tremor, weight gain", "contraindications": "Hepatic disease, pregnancy"},
        ],
        "second_line": [
            {"name": "Olanzapine", "class": "Atypical Antipsychotic", "starting_dose": "10mg", "max_dose": "20mg", "side_effects": "Weight gain, metabolic syndrome", "contraindications": "Dementia-related psychosis"},
        ],
    },
    "Schizophrenia Spectrum Disorder": {
        "first_line": [
            {"name": "Risperidone", "class": "Atypical Antipsychotic", "starting_dose": "2mg", "max_dose": "8mg", "side_effects": "EPS, weight gain", "contraindications": "Hypersensitivity"},
            {"name": "Aripiprazole", "class": "Atypical Antipsychotic", "starting_dose": "10mg", "max_dose": "30mg", "side_effects": "Akathisia, insomnia", "contraindications": "Hypersensitivity"},
        ],
    },
    "Delirium": {
        "first_line": [
            {"name": "Haloperidol", "class": "Typical Antipsychotic", "starting_dose": "0.5mg", "max_dose": "5mg", "side_effects": "EPS, QT prolongation", "contraindications": "Parkinson's disease"},
        ],
    },
    "Generalized Anxiety Disorder": {
        "first_line": [
            {"name": "Sertraline", "class": "SSRI", "starting_dose": "25mg", "max_dose": "200mg", "side_effects": "Nausea, insomnia", "contraindications": "MAOIs"},
        ],
    },
}

PHQ9_QUESTIONS = [
    "Little interest or pleasure in doing things",
    "Feeling down, depressed, or hopeless",
    "Trouble falling or staying asleep, or sleeping too much",
    "Feeling tired or having little energy",
    "Poor appetite or overeating",
    "Feeling bad about yourself - or that you are a failure",
    "Trouble concentrating on things",
    "Moving or speaking slowly / being fidgety or restless",
    "Thoughts that you would be better off dead or of hurting yourself",
]

GAD7_QUESTIONS = [
    "Feeling nervous, anxious, or on edge",
    "Not being able to stop or control worrying",
    "Worrying too much about different things",
    "Trouble relaxing",
    "Being so restless that it is hard to sit still",
    "Becoming easily annoyed or irritable",
    "Feeling afraid as if something awful might happen",
]

SCALES = {
    "C-SSRS (screen)": {
        "questions": [
            "Wished you were dead or wished you could go to sleep and not wake up?",
            "Actually had thoughts of killing yourself?",
            "Been thinking about how you might do this?",
            "Had any intention of acting on these thoughts?",
            "Started to work out or worked out the details of how to kill yourself?",
            "Done anything, started to do anything, or prepared to do anything to end your life?",
        ],
        "options": ["No (0)", "Yes (1)"],
        "interpret": lambda s: ("Low" if s == 0 else "Moderate" if s <= 2 else "High" if s <= 4 else "Very High / immediate risk"),
    },
    "AUDIT-C (alcohol)": {
        "questions": [
            "How often do you have a drink containing alcohol?",
            "How many standard drinks on a typical drinking day?",
            "How often do you have six or more drinks on one occasion?",
        ],
        "options": ["0", "1", "2", "3", "4"],
        "interpret": lambda s: ("Negative" if s <= 3 else "Positive screen - hazardous drinking"),
    },
    "DAST-10 (drugs)": {
        "questions": [
            "Used drugs other than those required for medical reasons?",
            "Abused prescription drugs?",
            "Always able to stop using drugs when you want? (reverse)",
            "Had blackouts or flashbacks from drug use?",
            "Felt bad or guilty about drug use?",
            "Partner / parents / relatives complained about your drug use?",
            "Neglected family or work obligations because of drugs?",
            "Engaged in illegal activities to obtain drugs?",
            "Experienced withdrawal symptoms when stopping?",
            "Had medical problems from drug use?",
        ],
        "options": ["No (0)", "Yes (1)"],
        "interpret": lambda s: ("Low" if s <= 2 else "Moderate" if s <= 5 else "Substantial" if s <= 8 else "Severe"),
    },
    "MDQ (bipolar screen)": {
        "questions": [
            "Felt so good or hyper that others thought you were not your normal self?",
            "Felt so irritable you shouted at people or started fights?",
            "Felt much more self-confident than usual?",
            "Got much less sleep and did not miss it?",
            "Much more talkative or spoke faster than usual?",
            "Thoughts raced through your head or could not slow them down?",
            "So easily distracted you had trouble concentrating?",
            "Much more energy than usual?",
            "Much more active or did many more things than usual?",
            "Much more social or outgoing than usual?",
            "Much more interested in sex than usual?",
            "Did things unusual for you that others thought excessive or risky?",
            "Spending money got you or your family into trouble?",
        ],
        "options": ["No (0)", "Yes (1)"],
        "interpret": lambda s: ("Negative" if s <= 6 else "Positive screen"),
    },
    "PCL-5 (PTSD)": {
        "questions": [
            "Repeated disturbing memories, thoughts, or images of the stress?",
            "Repeated disturbing dreams of the stress?",
            "Suddenly feeling or acting as if the stress were happening again?",
            "Feeling very upset when reminded of the stress?",
            "Physical reactions when reminded of the stress?",
            "Avoiding memories, thoughts, or feelings related to the stress?",
            "Avoiding external reminders of the stress?",
            "Trouble remembering important parts of the stress?",
            "Negative beliefs about yourself, others, or the world?",
            "Blaming yourself or others for the stress?",
            "Strong negative feelings such as fear, horror, anger, guilt?",
            "Loss of interest in activities you used to enjoy?",
            "Feeling distant or cut off from other people?",
            "Trouble experiencing positive feelings?",
            "Irritable behavior, angry outbursts, or acting aggressively?",
            "Taking too many risks or doing things that could cause harm?",
            "Being superalert or watchful or on guard?",
            "Feeling jumpy or easily startled?",
            "Having difficulty concentrating?",
            "Trouble falling or staying asleep?",
        ],
        "options": ["0 - Not at all", "1 - A little", "2 - Moderately", "3 - Quite a bit", "4 - Extremely"],
        "interpret": lambda s: ("Below threshold" if s < 33 else "Probable PTSD (>32)"),
    },
    "YMRS (mania)": {
        "questions": [
            "Elevated mood (0-4)?",
            "Increased motor activity / energy (0-4)?",
            "Sexual interest (0-4)?",
            "Sleep (0-4)?",
            "Irritability (0-8)?",
            "Speech rate / amount (0-8)?",
            "Language / thought disorder (0-8)?",
            "Content (0-8)?",
            "Disruptive / aggressive behavior (0-8)?",
            "Appearance (0-4)?",
            "Insight (0-4)?",
        ],
        "options": ["0", "1", "2", "3", "4", "5", "6", "7", "8"],
        "interpret": lambda s: ("Normal" if s <= 12 else "Hypomania" if s <= 19 else "Manic" if s <= 29 else "Severe mania"),
    },
    "MMSE (cognition)": {
        "questions": [
            "Orientation - year (0-1)?",
            "Orientation - season (0-1)?",
            "Orientation - date (0-1)?",
            "Orientation - day (0-1)?",
            "Orientation - month (0-1)?",
            "Orientation - country (0-1)?",
            "Orientation - state (0-1)?",
            "Orientation - town/city (0-1)?",
            "Orientation - hospital / place (0-1)?",
            "Orientation - floor (0-1)?",
            "Registration - 3 words (0-3)?",
            "Attention - 5 serial 7s (0-5)?",
            "Recall - 3 words (0-3)?",
            "Language - naming (0-2)?",
            "Language - repetition (0-1)?",
            "Language - 3-stage command (0-3)?",
            "Language - reading (0-1)?",
            "Language - writing (0-1)?",
            "Language - copy design (0-1)?",
        ],
        "options": ["0", "1", "2", "3", "4", "5"],
        "interpret": lambda s: ("Normal (>=24)" if s >= 24 else "Mild (18-23)" if s >= 18 else "Moderate (10-17)" if s >= 10 else "Severe (<10)"),
    },
    "HAM-D (depression)": {
        "questions": [
            "Depressed mood (0-4)?",
            "Feelings of guilt (0-4)?",
            "Suicide (0-4)?",
            "Insomnia - early (0-2)?",
            "Insomnia - middle (0-2)?",
            "Insomnia - late (0-2)?",
            "Work and activities (0-4)?",
            "Retardation (0-4)?",
            "Agitation (0-4)?",
            "Anxiety - psychic (0-4)?",
            "Anxiety - somatic (0-4)?",
            "Somatic symptoms GI (0-2)?",
            "Somatic symptoms general (0-2)?",
            "Genital symptoms (0-2)?",
            "Hypochondriasis (0-4)?",
            "Loss of insight (0-2)?",
            "Loss of weight (0-2)?",
        ],
        "options": ["0", "1", "2", "3", "4"],
        "interpret": lambda s: ("Normal" if s <= 7 else "Mild" if s <= 13 else "Moderate" if s <= 18 else "Severe" if s <= 22 else "Very Severe"),
    },
    "HAM-A (anxiety)": {
        "questions": [
            "Anxious mood (0-4)?",
            "Tension (0-4)?",
            "Fears (0-4)?",
            "Insomnia (0-4)?",
            "Intellectual / concentration (0-4)?",
            "Depressed mood (0-4)?",
            "Somatic - muscular (0-4)?",
            "Somatic - sensory (0-4)?",
            "Cardiovascular (0-4)?",
            "Respiratory (0-4)?",
            "Gastrointestinal (0-4)?",
            "Genitourinary (0-4)?",
            "Autonomic (0-4)?",
            "Behaviour at interview (0-4)?",
        ],
        "options": ["0", "1", "2", "3", "4"],
        "interpret": lambda s: ("Normal" if s <= 7 else "Mild" if s <= 14 else "Moderate" if s <= 21 else "Severe" if s <= 28 else "Very Severe"),
    },
    "WHO-5 (well-being)": {
        "questions": [
            "I have felt cheerful and in good spirits (0-5)?",
            "I have felt calm and relaxed (0-5)?",
            "I have felt active and vigorous (0-5)?",
            "I woke up feeling fresh and rested (0-5)?",
            "My daily life has been filled with things that interest me (0-5)?",
        ],
        "options": ["0", "1", "2", "3", "4", "5"],
        "interpret": lambda s: ("Poor well-being (<50)" if s * 4 < 50 else "Reduced (50-68)" if s * 4 < 69 else "Good (>=69)"),
    },
    "ISI (insomnia)": {
        "questions": [
            "Severity of falling asleep (0-4)?",
            "Severity of staying asleep (0-4)?",
            "Severity of early morning awakening (0-4)?",
            "Satisfaction with current sleep pattern (0-4)?",
            "Interference with daily functioning (0-4)?",
            "Noticeability by others (0-4)?",
            "Worry / distress about sleep (0-4)?",
        ],
        "options": ["0", "1", "2", "3", "4"],
        "interpret": lambda s: ("No clinically significant insomnia" if s <= 7 else "Subthreshold insomnia" if s <= 14 else "Moderate clinical insomnia" if s <= 21 else "Severe clinical insomnia"),
    },
    "EPDS (postnatal)": {
        "questions": [
            "I have been able to laugh and see the funny side of things (0-3)?",
            "I have looked forward with enjoyment to things (0-3)?",
            "I have blamed myself unnecessarily when things went wrong (0-3)?",
            "I have been anxious or worried for no good reason (0-3)?",
            "I have felt scared or panicky for no very good reason (0-3)?",
            "Things have been getting on top of me (0-3)?",
            "I have been so unhappy that I have had difficulty sleeping (0-3)?",
            "I have felt sad or miserable (0-3)?",
            "I have been so unhappy that I have been crying (0-3)?",
            "The thought of harming myself has occurred to me (0-3)?",
        ],
        "options": ["0", "1", "2", "3"],
        "interpret": lambda s: ("Low risk" if s < 10 else "Possible depression (>=10)" if s < 13 else "Probable depression (>=13)"),
    },
    "CGI (global)": {
        "questions": [
            "Severity of illness (1-7, 1=normal, 7=extremely ill)?",
            "Global improvement (1-7, 1=very much better, 7=very much worse)?",
        ],
        "options": ["1", "2", "3", "4", "5", "6", "7"],
        "interpret": lambda s: ("Improving" if s < 6 else "Stable" if s <= 8 else "Worsening"),
    },
    "PHQ-2 (brief depression)": {
        "questions": [
            "Little interest or pleasure in doing things (0-3)?",
            "Feeling down, depressed, or hopeless (0-3)?",
        ],
        "options": ["0", "1", "2", "3"],
        "interpret": lambda s: ("Negative" if s < 3 else "Positive screen - full PHQ-9 recommended"),
    },
    "GAD-2 (brief anxiety)": {
        "questions": [
            "Feeling nervous, anxious, or on edge (0-3)?",
            "Not being able to stop or control worrying (0-3)?",
        ],
        "options": ["0", "1", "2", "3"],
        "interpret": lambda s: ("Negative" if s < 3 else "Positive screen - full GAD-7 recommended"),
    },
    "Y-BOCS (OCD)": {
        "questions": [
            "Time occupied by obsessions (0-4)?",
            "Interference from obsessions (0-4)?",
            "Distress from obsessions (0-4)?",
            "Resistance to obsessions (0-4)?",
            "Control over obsessions (0-4)?",
            "Time occupied by compulsions (0-4)?",
            "Interference from compulsions (0-4)?",
            "Distress from compulsions (0-4)?",
            "Resistance to compulsions (0-4)?",
            "Control over compulsions (0-4)?",
        ],
        "options": ["0", "1", "2", "3", "4"],
        "interpret": lambda s: ("Subclinical" if s <= 7 else "Mild" if s <= 15 else "Moderate" if s <= 23 else "Severe" if s <= 31 else "Extreme"),
    },
}


def has_s(sel, s): return s in sel

def severity_grader(score):
    if score <= 5: return "Mild"
    if score <= 12: return "Moderate"
    if score <= 20: return "Severe"
    return "Very Severe"

def depressive_logic(sel, dur, aff):
    if not (has_s(sel, "Low mood") or has_s(sel, "Anhedonia")): return 0
    s = 12
    for x in ["Fatigue", "Hopelessness", "Excessive guilt", "Suicidal thoughts", "Sleep disturbance", "Poor concentration"]:
        if has_s(sel, x): s += 2
    if sum(1 for x in ["Grandiosity", "Increased energy", "Reduced sleep"] if has_s(sel, x)) >= 2: s -= 8
    if dur in ["Weeks", "Months"]: s += 2
    if aff == "Depressed": s += 3
    return max(s, 0)

def mania_logic(sel, dur, sp, th):
    if not (has_s(sel, "Reduced sleep") and has_s(sel, "Increased energy")): return 0
    s = 12
    for x in ["Grandiosity", "Pressured speech", "Racing thoughts", "Risk-taking behavior", "Distractibility"]:
        if has_s(sel, x): s += 2
    if dur in ["Days", "Weeks"]: s += 2
    if sp == "Pressured": s += 3
    if th == "Flight of ideas": s += 3
    return max(s, 0)

def psychosis_logic(sel, dur, sp, th):
    if not (has_s(sel, "Auditory hallucinations") or has_s(sel, "Visual hallucinations") or has_s(sel, "Delusions")): return 0
    s = 12
    for x in ["Paranoia", "Disorganized speech", "Negative symptoms"]:
        if has_s(sel, x): s += 2
    if dur in ["Months", "Years"]: s += 3
    if sp == "Disorganized": s += 3
    if th == "Disorganized": s += 4
    return max(s, 0)

def delirium_logic(sel, dur, onset, fluc):
    if not (has_s(sel, "Confusion") and has_s(sel, "Disorientation")): return 0
    s = 15
    if has_s(sel, "Fluctuating attention") or has_s(sel, "Visual hallucinations"): s += 3
    if dur in ["Hours", "Days"]: s += 5
    if onset == "Sudden": s += 4
    if fluc: s += 4
    return max(s, 0)

def diagnose_mdd(sel, dur, imp):
    cnt = sum(1 for x in ["Low mood", "Anhedonia", "Fatigue", "Hopelessness", "Excessive guilt", "Suicidal thoughts", "Sleep disturbance", "Poor concentration"] if has_s(sel, x))
    core = has_s(sel, "Low mood") or has_s(sel, "Anhedonia")
    nom = not (has_s(sel, "Grandiosity") or has_s(sel, "Increased energy"))
    if cnt >= 5 and core and nom and dur in ["Weeks", "Months"] and imp != "None reported":
        return {"diagnosis": "Major Depressive Disorder", "status": "CRITERIA FULLY MET", "confidence": "HIGH"}
    if cnt >= 3:
        return {"diagnosis": "Major Depressive Disorder", "status": "PARTIAL CRITERIA", "confidence": "MODERATE"}
    return None

def diagnose_mania(sel, dur):
    cnt = sum(1 for x in ["Reduced sleep", "Increased energy", "Grandiosity", "Pressured speech", "Racing thoughts", "Risk-taking behavior", "Distractibility"] if has_s(sel, x))
    if cnt >= 4 and has_s(sel, "Reduced sleep") and has_s(sel, "Increased energy") and dur in ["Days", "Weeks"]:
        return {"diagnosis": "Bipolar I Disorder - Manic Episode", "status": "CRITERIA FULLY MET", "confidence": "HIGH"}
    return None

def diagnose_schizophrenia(sel, dur):
    core = has_s(sel, "Delusions") or has_s(sel, "Auditory hallucinations")
    cnt = sum(1 for x in ["Auditory hallucinations", "Visual hallucinations", "Delusions", "Paranoia", "Disorganized speech", "Negative symptoms"] if has_s(sel, x))
    if core and cnt >= 2 and dur in ["Months", "Years"]:
        return {"diagnosis": "Schizophrenia Spectrum Disorder", "status": "CRITERIA FULLY MET", "confidence": "HIGH"}
    return None

def diagnose_delirium(sel, dur, fluc):
    if has_s(sel, "Confusion") and has_s(sel, "Disorientation") and (has_s(sel, "Fluctuating attention") or fluc) and dur in ["Hours", "Days"]:
        return {"diagnosis": "Delirium", "status": "CRITERIA FULLY MET", "confidence": "HIGH"}
    return None

def organic_psychosis_detector(sel, onset, fluc, sz, focal, hi):
    sc = 0
    if has_s(sel, "Visual hallucinations"): sc += 3
    if has_s(sel, "Confusion"): sc += 4
    if fluc: sc += 4
    if sz: sc += 4
    if focal: sc += 5
    if onset == "Sudden": sc += 3
    if hi: sc += 4
    if sc >= 15: lvl = "VERY HIGH suspicion of organic psychosis"
    elif sc >= 10: lvl = "HIGH suspicion of organic psychosis"
    elif sc >= 6: lvl = "MODERATE suspicion of organic psychosis"
    else: lvl = "LOW suspicion of organic psychosis"
    return lvl, sc

def risk_assessment(sel, plan, cmd, vio, means):
    sc = 0
    if has_s(sel, "Suicidal thoughts"): sc += 3
    if plan: sc += 6
    if cmd: sc += 6
    if vio: sc += 5
    if means: sc += 4
    if sc >= 15: return "CRITICAL RISK", "IMMEDIATE HOSPITALIZATION REQUIRED", sc
    if sc >= 10: return "HIGH RISK", "URGENT psychiatric consultation required", sc
    if sc >= 5: return "MODERATE RISK", "Enhanced monitoring required", sc
    return "LOW RISK", "Routine monitoring", sc

def mixed_features_detector(sel):
    dep = sum(1 for x in ["Low mood", "Anhedonia", "Hopelessness", "Excessive guilt", "Suicidal thoughts"] if has_s(sel, x))
    man = sum(1 for x in ["Reduced sleep", "Increased energy", "Grandiosity", "Pressured speech", "Racing thoughts"] if has_s(sel, x))
    return dep >= 3 and man >= 3

def generate_mse(sp, aff, th, ins, jud):
    sm = {"Normal": "normal rate and rhythm", "Pressured": "rapid, difficult to interrupt", "Slow": "reduced rate", "Disorganized": "disorganized"}
    am = {"Normal": "full range", "Flat": "severely reduced", "Depressed": "sad, discouraged", "Labile": "rapidly changing"}
    tm = {"Normal": "logical and goal-directed", "Tangential": "off-topic", "Disorganized": "illogical", "Flight of ideas": "rapid shifts"}
    im = {"Good": "excellent awareness", "Partial": "partial recognition", "Poor": "limited awareness"}
    jm = {"Good": "intact", "Fair": "mildly impaired", "Poor": "moderately impaired", "Impaired": "markedly impaired"}
    return ("Speech: " + sm.get(sp, "normal") + ". Affect: " + am.get(aff, "normal") + ". Thought: " + tm.get(th, "normal") + ". Insight: " + im.get(ins, "good") + ". Judgment: " + jm.get(jud, "intact") + ".")

def generate_ai_insights(top, sev, risk, formal):
    L = ["### Clinical Overview", "Primary presentation: **" + top + "** (" + sev.lower() + " severity)."]
    if formal:
        names = [d["diagnosis"] for d in formal if d.get("status") == "CRITERIA FULLY MET"]
        if names:
            L += ["", "### Criteria", "Meets criteria for: **" + ", ".join(names) + "** (decision support only)."]
    L += ["", "### Risk"]
    if "HIGH" in risk or "CRITICAL" in risk:
        L.append("High/critical risk - do not leave unattended; remove means; emergency services; consider admission.")
    elif "MODERATE" in risk:
        L.append("Moderate risk - enhanced monitoring and safety planning.")
    else:
        L.append("Low risk - routine monitoring.")
    L += ["", "### Notes - " + top]
    edu = {
        "Depressive Syndrome": ["SSRIs + CBT first-line.", "Monitor suicide risk early in treatment.", "Rule out medical causes."],
        "Manic Syndrome": ["Lithium/valproate first-line.", "Avoid antidepressants in acute mania.", "Monitor levels/LFTs."],
        "Psychotic Syndrome": ["Antipsychotics first-line.", "Early intervention improves outcomes.", "Rule out substance/medical causes."],
        "Delirium Syndrome": ["Medical emergency - treat cause.", "Non-pharm measures first.", "Haloperidol only if severe agitation."],
    }
    for x in edu.get(top, ["Correlate with full clinical assessment."]):
        L.append("- " + x)
    L += ["", "### Follow-up", "Reassess 1-2 weeks; monitor adherence/side effects; recheck risk each visit."]
    return "\n".join(L)

def phq9_severity(s):
    return ("None-Minimal" if s <= 4 else "Mild" if s <= 9 else "Moderate" if s <= 14 else "Moderately Severe" if s <= 19 else "Severe")

def gad7_severity(s):
    return ("Minimal" if s <= 4 else "Mild" if s <= 9 else "Moderate" if s <= 14 else "Severe")

def suggest_unique_patient_label(base_name, age, sex):
    base = (base_name or "").strip()
    if not base: return ""
    c = db()
    try:
        rows = c.execute("SELECT name FROM patients WHERE deleted_at IS NULL AND (name = ? OR name LIKE ?) ORDER BY id", (base, base + " (%")).fetchall()
    finally:
        c.close()
    existing = [r[0] for r in rows]
    if base not in existing:
        return base
    used = set()
    for label in existing:
        m = re.search(r"P(\d+)", label or "")
        if m: used.add(int(m.group(1)))
    n = 1
    while n in used: n += 1
    age_str = str(age).strip() if age else "?"
    sex_str = (sex or "?")[0].upper()
    code = "P" + str(n).zfill(4)
    return base + " (" + age_str + sex_str + " - " + code + ")"

def upsert_patient(name, age, sex):
    if not name or not name.strip(): return ""
    base = name.strip()
    now = str(datetime.now())
    c = db()
    try:
        rows = c.execute("SELECT name FROM patients WHERE deleted_at IS NULL AND (name = ? OR name LIKE ?)", (base, base + " (%")).fetchall()
        for r in rows:
            existing_label = r[0]
            if str(age) in existing_label and (sex or "")[:1].upper() in existing_label.upper():
                c.execute("UPDATE patients SET last_seen=? WHERE name=?", (now, existing_label))
                c.commit()
                return existing_label
        label = suggest_unique_patient_label(base, age, sex)
        c.execute("INSERT INTO patients (name, age, sex, first_seen, last_seen, created_at, created_by) VALUES (?,?,?,?,?,?,?)", (label, str(age), sex, now, now, now, st.session_state.get("user", "?")))
        c.commit()
        return label
    finally:
        c.close()

def report_to_pdf(text, title="PsychAssist Clinical Report"):
    if not HAS_FPDF: return None
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, title, ln=1)
    pdf.set_font("Helvetica", size=10)
    for line in text.split("\n"):
        pdf.multi_cell(0, 5, line)
    out = pdf.output(dest="S")
    if isinstance(out, str):
        return out.encode("latin-1", "replace")
    return bytes(out)

def export_excel(tables):
    if not HAS_OPENPYXL: return None
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xl:
        c = db()
        for t in tables:
            try:
                df = pd.read_sql_query("SELECT * FROM " + t, c._raw)
            except Exception:
                continue
            df.to_excel(xl, sheet_name=t[:31], index=False)
        c.close()
    return buf.getvalue()

def canvas_to_b64_png(arr):
    if arr is None: return ""
    if arr.dtype != "uint8": arr = arr.astype("uint8")
    buf = io.BytesIO()
    Image.fromarray(arr, "RGBA").save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

def _toggle_fullscreen():
    st.session_state.draw_fullscreen = not st.session_state.get("draw_fullscreen", False)

def _clipboard_history():
    if "canvas_history" not in st.session_state:
        st.session_state.canvas_history = []
    return st.session_state.canvas_history


def sidebar_context():
    with st.sidebar:
        st.title("PsychAssist v5.2")
        st.caption("Decision support only - not a diagnosis")
        if USE_AUTH:
            u = st.session_state.get("user", "?")
            st.caption("Signed in as: " + u)
            if st.button("Sign out"):
                st.session_state.authed = False
                st.rerun()
        c = db()
        try:
            pats = [r[0] for r in c.execute("SELECT name FROM patients WHERE deleted_at IS NULL ORDER BY name").fetchall()]
        except Exception:
            pats = []
        c.close()
        options = ["(none)"] + pats
        default = st.session_state.get("patient_name", "(none)")
        if default not in options:
            default = "(none)"
        sel = st.selectbox("Current patient", options, index=options.index(default), key="global_patient")
        st.caption("Duplicates appear as: Name (45M - P0002)")
        st.session_state.patient_name = "" if sel == "(none)" else sel
        c = db()
        try:
            overdue = c.execute("SELECT COUNT(*) FROM follow_ups WHERE status='Scheduled' AND follow_up_date < ? AND deleted_at IS NULL", (str(date.today()),)).fetchone()
            overdue = overdue[0] if overdue else 0
            high = c.execute("SELECT COUNT(*) FROM assessments WHERE (risk_level LIKE ? OR risk_level LIKE ?) AND deleted_at IS NULL", ("%HIGH%", "%CRITICAL%")).fetchone()
            high = high[0] if high else 0
        except Exception:
            overdue, high = 0, 0
        c.close()
        if overdue:
            st.error("Overdue follow-ups: " + str(overdue))
        if high:
            st.warning("Open high-risk: " + str(high))
        dark = st.toggle("Dark mode", key="dark_mode")
        if dark:
            st.markdown("<style>.stApp {background-color:#0e1117;color:#fafafa;}.block-container {color:#fafafa;}</style>", unsafe_allow_html=True)


def page_treatments():
    st.title("Treatment Tracker")
    with st.form("tx_add"):
        c1, c2, c3 = st.columns(3)
        with c1:
            name = st.text_input("Patient", value=st.session_state.get("patient_name", ""))
            med = st.text_input("Medication")
            cls = st.selectbox("Class", ["SSRI", "SNRI", "NDRI", "TCA", "MAOI", "Atypical Antipsychotic", "Typical Antipsychotic", "Mood Stabilizer", "Anticonvulsant", "Benzodiazepine", "Stimulant", "Other"])
        with c2:
            dose = st.text_input("Dose (e.g. 50mg)")
            freq = st.text_input("Frequency (e.g. OD)")
            route = st.selectbox("Route", ["Oral", "IM", "IV", "SC", "Other"])
        with c3:
            start = st.date_input("Start date", value=date.today())
            psycho = st.text_input("Psychotherapy (if any)")
            notes = st.text_area("Notes", height=80)
        add = st.form_submit_button("Start medication")
        if add and name.strip() and med.strip():
            c = db()
            c.execute("INSERT INTO treatments (patient_name, medication_name, medication_class, dose, frequency, route, start_date, status, psychotherapy, notes, created_by, timestamp) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (name.strip(), med.strip(), cls, dose, freq, route, str(start), "Active", psycho, notes, st.session_state.get("user", "?"), str(datetime.now())))
            c.commit()
            c.close()
            audit("insert", "treatments", detail=name + "/" + med)
            st.success("Saved.")
    st.divider()
    st.subheader("Active medications")
    c = db()
    rows = c.execute("SELECT id, patient_name, medication_name, medication_class, dose, frequency, start_date, status, adherence, side_effects FROM treatments WHERE deleted_at IS NULL AND status='Active' ORDER BY id DESC").fetchall()
    c.close()
    if not rows:
        st.info("No active medications.")
    else:
        for r in rows:
            with st.expander("#" + str(r[0]) + " - " + str(r[1]) + " - " + str(r[2]) + " " + str(r[4]) + " " + str(r[5])):
                a1, a2 = st.columns(2)
                with a1:
                    st.write("Class:", r[3])
                    st.write("Started:", r[6])
                with a2:
                    adh = st.selectbox("Adherence", ["Good", "Partial", "Poor"], key="adh_" + str(r[0]))
                    se = st.text_input("Side effects", value=r[9] or "", key="se_" + str(r[0]))
                    if st.button("Update", key="upd_" + str(r[0])):
                        c = db()
                        c.execute("UPDATE treatments SET adherence=?, side_effects=? WHERE id=?", (adh, se, r[0]))
                        c.commit()
                        c.close()
                        audit("update", "treatments", r[0])
                        st.success("Updated.")
                reason = st.text_input("Reason to stop (if stopping)", key="rs_" + str(r[0]))
                if st.button("Stop medication", key="stop_" + str(r[0])):
                    c = db()
                    c.execute("UPDATE treatments SET status='Stopped', end_date=?, reason_stop=? WHERE id=?", (str(date.today()), reason, r[0]))
                    c.commit()
                    c.close()
                    audit("stop", "treatments", r[0])
                    st.success("Stopped.")
                    st.rerun()
    st.divider()
    st.subheader("History")
    c = db()
    df = pd.read_sql_query("SELECT id, patient_name, medication_name, dose, start_date, end_date, status, adherence FROM treatments WHERE deleted_at IS NULL ORDER BY id DESC", c._raw)
    c.close()
    st.dataframe(df, use_container_width=True)


def page_more_scales():
    st.title("Additional Scales")
    sel = st.selectbox("Choose scale", list(SCALES.keys()))
    spec = SCALES[sel]
    name = st.text_input("Patient", value=st.session_state.get("patient_name", ""))
    scores = []
    for i, q in enumerate(spec["questions"]):
        v = st.selectbox(q, spec["options"], key="ms_" + sel + "_" + str(i))
        try:
            scores.append(int(v.split(" ")[0].split("(")[-1].rstrip(")") or 0))
        except Exception:
            scores.append(0)
    total = sum(scores)
    try:
        sev = spec["interpret"](total)
    except Exception:
        sev = "-"
    st.success("Total: " + str(total) + " | " + str(sev))
    if st.button("Save scale"):
        c = db()
        c.execute("INSERT INTO other_scales (patient_name, scale, score, severity, answers, created_by, timestamp) VALUES (?,?,?,?,?,?,?)", (name or "Unknown", sel, total, str(sev), str(scores), st.session_state.get("user", "?"), str(datetime.now())))
        c.commit()
        c.close()
        audit("insert", "other_scales", detail=sel)
        st.success("Saved.")


def page_icd():
    st.title("ICD-11 / DSM-5-TR Lookup")
    k = st.selectbox("Diagnosis", list(ICD_LOOKUP.keys()))
    info = ICD_LOOKUP[k]
    st.subheader(k)
    st.write("**ICD-11:**", info["icd11"])
    st.write("**DSM-5-TR:**", info["dsm5"])
    st.markdown("**Criteria summary**")
    st.write(info["criteria"])
    st.markdown("**Common differentials**")
    st.write(info["differential"])


def page_interactions():
    st.title("Drug Interaction Checker")
    st.caption("Curated table - non-exhaustive. Always confirm with a full interaction database.")
    st.subheader("Reference table")
    df = pd.DataFrame(DRUG_INTERACTIONS, columns=["Drug A", "Drug B", "Severity", "Comment"])
    st.dataframe(df, use_container_width=True)
    st.subheader("Check a patient's active medications")
    name = st.text_input("Patient", value=st.session_state.get("patient_name", ""))
    if name:
        c = db()
        meds = c.execute("SELECT medication_name, medication_class FROM treatments WHERE patient_name=? AND status='Active' AND deleted_at IS NULL", (name,)).fetchall()
        c.close()
        if not meds:
            st.info("No active medications for this patient.")
        else:
            classes = set(m[1] for m in meds)
            hits = [row for row in DRUG_INTERACTIONS if row[0] in classes and row[1] in classes]
            if hits:
                for h in hits:
                    st.error(h[0] + " + " + h[1] + " (" + h[2] + "): " + h[3])
            else:
                st.success("No known interactions from the curated table (this does not rule out others).")


def page_trends():
    st.title("Trends")
    name = st.text_input("Patient", value=st.session_state.get("patient_name", ""))
    if not name:
        st.info("Select a patient above.")
        return
    c = db()
    phq = pd.read_sql_query("SELECT timestamp, total_score FROM phq9_scores WHERE patient_name=? AND deleted_at IS NULL ORDER BY timestamp", c._raw, params=(name,))
    gad = pd.read_sql_query("SELECT timestamp, total_score FROM gad7_scores WHERE patient_name=? AND deleted_at IS NULL ORDER BY timestamp", c._raw, params=(name,))
    c.close()
    if not phq.empty:
        phq["t"] = pd.to_datetime(phq["timestamp"]).dt.date
        st.subheader("PHQ-9 over time")
        st.line_chart(phq.set_index("t")["total_score"])
    if not gad.empty:
        gad["t"] = pd.to_datetime(gad["timestamp"]).dt.date
        st.subheader("GAD-7 over time")
        st.line_chart(gad.set_index("t")["total_score"])
    if phq.empty and gad.empty:
        st.info("No scale data yet for this patient.")


def page_outcomes():
    st.title("Outcome Dashboard")
    c = db()
    try:
        fu = pd.read_sql_query("SELECT symptoms_improved, adherence, global_impression FROM follow_ups WHERE status='Completed' AND deleted_at IS NULL", c._raw)
    except Exception:
        fu = pd.DataFrame()
    c.close()
    if fu.empty:
        st.info("No completed follow-ups yet.")
        return
    a, b, d = st.columns(3)
    with a:
        st.subheader("Symptoms improved")
        st.bar_chart(fu["symptoms_improved"].value_counts())
    with b:
        st.subheader("Adherence")
        st.bar_chart(fu["adherence"].value_counts())
    with d:
        st.subheader("Global impression")
        st.bar_chart(fu["global_impression"].value_counts())
    n = len(fu)
    improved = (fu["symptoms_improved"].isin(["Yes", "Partially"])).sum()
    st.metric("Follow-ups completed", n)
    st.metric("% improved or partially improved", str(round(100 * improved / n, 1)) + "%")


def page_backup():
    st.title("Backup & Restore")
    st.subheader("Download backup")
    tables = ["assessments", "treatments", "phq9_scores", "gad7_scores", "adhd_scores", "other_scales", "counselling_notes", "follow_ups", "patients", "audit_log"]
    xl = export_excel(tables)
    if xl is None:
        st.warning("Install openpyxl for Excel backup.")
    else:
        st.download_button("Download backup (xlsx)", xl, file_name="psychassist_backup_" + str(date.today()) + ".xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    if not USE_PG and os.path.exists(DB_PATH):
        with open(DB_PATH, "rb") as f:
            st.download_button("Download SQLite DB", f.read(), file_name="psychassist_web.db", mime="application/x-sqlite3")
    st.divider()
    st.subheader("Restore SQLite DB")
    up = st.file_uploader("Upload a .db file", type=["db", "sqlite", "sqlite3"])
    if up and not USE_PG:
        with open(DB_PATH, "wb") as f:
            f.write(up.read())
        st.success("Restored. Reload the app.")
        st.rerun()


def page_audit():
    st.title("Audit Log")
    c = db()
    df = pd.read_sql_query("SELECT ts, user, action, table_name, row_id, detail FROM audit_log ORDER BY id DESC LIMIT 500", c._raw)
    c.close()
    st.dataframe(df, use_container_width=True)


if not check_auth():
    st.stop()
enforce_timeout()
sidebar_context()


pages = [
    "Register Patient",
    "Assessment", "PHQ-9", "GAD-7", "ADHD", "More Scales",
    "Counselling & Notes", "Treatment Tracker", "Report", "Trends",
    "ICD Lookup", "Drug Interactions", "Chat",
    "History", "Patient Database", "Follow-up",
    "Epidemiology", "Outcomes", "Audit Log",
    "Backup & Restore", "Export Data",
]
page = st.sidebar.radio("Navigation", pages)


if page == "Register Patient":
    st.title("Register Patient")
    st.caption("Register here first. Duplicate names get an auto-suggested code so you can tell them apart everywhere in the app.")
    c1, c2, c3 = st.columns(3)
    with c1:
        reg_name = st.text_input("Full name (as you type it)")
    with c2:
        reg_age = st.number_input("Age", min_value=1, max_value=120, value=30, step=1)
    with c3:
        reg_sex = st.selectbox("Sex", ["Male", "Female", "Other"])
    suggested = ""
    if reg_name.strip():
        suggested = suggest_unique_patient_label(reg_name, reg_age, reg_sex)
    if suggested:
        st.info("Suggested patient label: **" + suggested + "**")
        st.caption("If more than one patient shares this name, a code is appended so the two records never collide.")
    final_label = st.text_input("Final label (you can edit if you like)", value=suggested, key="register_final_label")
    if st.button("Register patient", type="primary"):
        if not final_label.strip():
            st.error("Enter a name first.")
        else:
            c = db()
            exists = c.execute("SELECT id FROM patients WHERE name=? AND deleted_at IS NULL", (final_label.strip(),)).fetchone()
            c.close()
            if exists:
                st.warning("A patient with this exact label already exists. Use the sidebar selector to pick them.")
            else:
                now = str(datetime.now())
                c = db()
                c.execute("INSERT INTO patients (name, age, sex, first_seen, last_seen, created_at, created_by) VALUES (?,?,?,?,?,?,?)", (final_label.strip(), str(reg_age), reg_sex, now, now, now, st.session_state.get("user", "?")))
                c.commit()
                c.close()
                audit("insert", "patients", detail=final_label)
                st.session_state.patient_name = final_label.strip()
                st.success("Registered as: **" + final_label.strip() + "**.")
                st.rerun()
    st.divider()
    st.subheader("Existing patients")
    c = db()
    rows = c.execute("SELECT name, age, sex, first_seen FROM patients WHERE deleted_at IS NULL ORDER BY id DESC LIMIT 100").fetchall()
    c.close()
    if rows:
        df = pd.DataFrame(rows, columns=["Label", "Age", "Sex", "First seen"])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No patients yet.")


if page == "Assessment":
    st.title("Clinical Assessment")
    with st.form("af"):
        c1, c2, c3 = st.columns(3)
        with c1:
            name = st.text_input("Patient Name", value=st.session_state.get("patient_name", ""))
            age = st.number_input("Age", 1, 120, 30)
            sex = st.selectbox("Sex", ["Male", "Female", "Other"])
        with c2:
            duration = st.selectbox("Duration", ["Hours", "Days", "Weeks", "Months", "Years"])
            onset = st.selectbox("Onset", ["Sudden", "Gradual"])
            pattern = st.selectbox("Pattern", ["Not specified", "Episodic", "Chronic", "Fluctuating"])
        with c3:
            speech = st.selectbox("Speech", ["Normal", "Pressured", "Slow", "Disorganized"])
            affect = st.selectbox("Affect", ["Normal", "Flat", "Depressed", "Labile"])
            thought = st.selectbox("Thought", ["Normal", "Tangential", "Disorganized", "Flight of ideas"])
            insight = st.selectbox("Insight", ["Good", "Partial", "Poor"])
            judgment = st.selectbox("Judgment", ["Good", "Fair", "Poor", "Impaired"])
        substance = st.multiselect("Substance Use", ["Alcohol", "Cannabis", "Stimulants", "Opioids", "Withdrawal"])
        neuro = st.multiselect("Neuro Findings", ["Head injury", "Fluctuating cognition", "Focal deficit", "Seizure disorder"])
        func_imp = st.multiselect("Impairment", ["Occupational", "Social", "Self-care"])
        selected = []
        for cat, items in symptom_categories.items():
            st.write("**" + cat + "**")
            for it in items:
                if st.checkbox(it, key="sy_" + it):
                    selected.append(it)
        risk_suicide = st.checkbox("Active suicidal plan")
        risk_command = st.checkbox("Command hallucinations")
        risk_violent = st.checkbox("Violent behavior")
        risk_means = st.checkbox("Access to means")
        sub = st.form_submit_button("Generate Report")
        if sub:
            if not name.strip():
                st.error("Enter patient name")
            else:
                final_label = upsert_patient(name, str(age), sex)
                st.session_state.patient_name = final_label
                name = final_label
                onset_s = "Sudden" if onset == "Sudden" else "Gradual"
                fluc = "Fluctuating cognition" in neuro
                sz = "Seizure disorder" in neuro
                focal = "Focal deficit" in neuro
                hi = "Head injury" in neuro
                scores = {
                    "Depressive Syndrome": depressive_logic(selected, duration, affect),
                    "Manic Syndrome": mania_logic(selected, duration, speech, thought),
                    "Psychotic Syndrome": psychosis_logic(selected, duration, speech, thought),
                    "Delirium Syndrome": delirium_logic(selected, duration, onset_s, fluc),
                }
                filt = {k: v for k, v in scores.items() if v > 0}
                if filt:
                    top = max(filt, key=filt.get)
                    sev = severity_grader(max(filt.values()))
                else:
                    top, sev = "Unknown", severity_grader(0)
                imp = " ".join(func_imp) if func_imp else "None reported"
                formal = [d for d in (diagnose_mdd(selected, duration, imp), diagnose_mania(selected, duration), diagnose_schizophrenia(selected, duration), diagnose_delirium(selected, duration, fluc)) if d]
                org_lvl, org_sc = organic_psychosis_detector(selected, onset_s, fluc, sz, focal, hi)
                risk_lvl, risk_rec, risk_sc = risk_assessment(selected, risk_suicide, risk_command, risk_violent, risk_means)
                mse = generate_mse(speech, affect, thought, insight, judgment)
                rep = "\n".join(["=" * 60, "PSYCHASSIST CLINICAL REPORT", "=" * 60, "", "Patient: " + name + " | Age: " + str(age) + " | Sex: " + sex, "Syndrome: " + top + " | Severity: " + sev, "", "MSE: " + mse, "", "Risk: " + risk_lvl + " (" + str(risk_sc) + "/20) - " + risk_rec, "Organic: " + org_lvl + " (" + str(org_sc) + "/25)"])
                ai = generate_ai_insights(top, sev, risk_lvl, formal)
                c = db()
                c.execute("INSERT INTO assessments (patient_name, age, sex, symptoms, syndrome, severity, risk_level, formal_diagnoses, organic_level, organic_score, functional_impairment, mse, duration, onset, pattern, speech, affect, thought_process, insight, judgment, substance_use, neuro_findings, report_text, ai_insights, mdd_criteria, mania_criteria, schizophrenia_criteria, delirium_criteria, mixed_features, symptom_weight, created_by, timestamp) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (name, str(age), sex, ", ".join(selected), top, sev, risk_lvl, str(formal), org_lvl, org_sc, ", ".join(func_imp), mse, duration, onset, pattern, speech, affect, thought, insight, judgment, ", ".join(substance), ", ".join(neuro), rep, ai, str(formal[0]) if formal else "", "", "", "", 1 if mixed_features_detector(selected) else 0, round(sum(0.1 for _ in selected), 2), st.session_state.get("user", "?"), str(datetime.now())))
                c.commit()
                c.close()
                audit("insert", "assessments", detail=name)
                st.session_state["current_report"] = rep
                st.session_state["current_ai"] = ai
                st.session_state.patient_name = name
                st.success("Report generated.")
                st.rerun()


if page == "PHQ-9":
    st.title("PHQ-9")
    name = st.text_input("Patient", value=st.session_state.get("patient_name", ""))
    sc = [st.slider(q, 0, 3, 0, key="p" + str(i)) for i, q in enumerate(PHQ9_QUESTIONS)]
    tot = sum(sc)
    st.success("Total: " + str(tot) + " | " + phq9_severity(tot))
    if st.button("Save PHQ-9"):
        c = db()
        c.execute("INSERT INTO phq9_scores (patient_name, total_score, severity, answers, created_by, timestamp) VALUES (?,?,?,?,?,?)", (name or "Unknown", tot, phq9_severity(tot), str(sc), st.session_state.get("user", "?"), str(datetime.now())))
        c.commit()
        c.close()
        audit("insert", "phq9_scores", detail=name)
        st.success("Saved.")


if page == "GAD-7":
    st.title("GAD-7")
    name = st.text_input("Patient", value=st.session_state.get("patient_name", ""))
    sc = [st.slider(q, 0, 3, 0, key="g" + str(i)) for i, q in enumerate(GAD7_QUESTIONS)]
    tot = sum(sc)
    st.success("Total: " + str(tot) + " | " + gad7_severity(tot))
    if st.button("Save GAD-7"):
        c = db()
        c.execute("INSERT INTO gad7_scores (patient_name, total_score, severity, answers, created_by, timestamp) VALUES (?,?,?,?,?,?)", (name or "Unknown", tot, gad7_severity(tot), str(sc), st.session_state.get("user", "?"), str(datetime.now())))
        c.commit()
        c.close()
        audit("insert", "gad7_scores", detail=name)
        st.success("Saved.")


if page == "ADHD":
    st.title("ADHD Assessment")
    name = st.text_input("Patient", value=st.session_state.get("patient_name", ""))
    typ = st.radio("Instrument", ["Adult (ASRS)", "Adult (CAARS)", "Child (ADHD-RS)"])
    if typ == "Adult (ASRS)":
        qs = ["Trouble wrapping up final details", "Difficulty getting things in order", "Problems remembering appointments", "Must read instructions over and over", "Start new task before finishing previous", "Trouble focusing when needed"]
        mx = 4
    elif typ == "Adult (CAARS)":
        qs = ["Difficulty concentrating", "Easily distracted", "Hard to sit still", "Talk too much", "Interrupt others", "Lose things", "Forget appointments", "Trouble organizing", "Feel restless", "Short attention span"]
        mx = 4
    else:
        qs = ["Fidgets", "Leaves seat", "Runs / climbs", "Difficulty playing quietly", "On the go", "Talks excessively", "Blurts answers", "Awkward waiting", "Interrupts others", "Difficulty organizing"]
        mx = 3
    sc = [st.slider(q, 0, mx, 0, key="a" + str(i)) for i, q in enumerate(qs)]
    tot = sum(sc)
    thr = {"Adult (ASRS)": 18, "Adult (CAARS)": 30, "Child (ADHD-RS)": 24}[typ]
    sev = ("None" if tot <= thr // 2 else "Mild" if tot <= thr else "Moderate" if tot <= thr * 1.5 else "Severe")
    st.success("Score: " + str(tot) + "/" + str(thr) + " | Severity: " + sev)
    if st.button("Save ADHD"):
        c = db()
        c.execute("INSERT INTO adhd_scores (patient_name, total_score, severity, answers, adhd_type, created_by, timestamp) VALUES (?,?,?,?,?,?,?)", (name or "Unknown", tot, sev, str(sc), typ, st.session_state.get("user", "?"), str(datetime.now())))
        c.commit()
        c.close()
        audit("insert", "adhd_scores", detail=name)
        st.success("Saved.")


if page == "More Scales":
    page_more_scales()
if page == "ICD Lookup":
    page_icd()
if page == "Drug Interactions":
    page_interactions()
if page == "Trends":
    page_trends()
if page == "Outcomes":
    page_outcomes()
if page == "Audit Log":
    page_audit()
if page == "Backup & Restore":
    page_backup()
if page == "Treatment Tracker":
    page_treatments()


if page == "Counselling & Notes":
    full_screen = st.checkbox("Full-screen drawing mode", key="draw_fullscreen")
    if full_screen:
        st.markdown("<style>section[data-testid='stSidebar']{display:none !important;}header[data-testid='stHeader']{display:none !important;}.block-container{padding:.5rem !important;max-width:100% !important;}.stDeployButton{display:none !important;}</style>", unsafe_allow_html=True)
    st.title("Counselling & Clinical Notes")
    c1, c2 = st.columns(2)
    with c1:
        note_name = st.text_input("Patient", value=st.session_state.get("patient_name", ""))
        note_age = st.number_input("Age", 1, 120, 30)
        note_sex = st.selectbox("Sex", ["Male", "Female", "Other"])
        note_date = st.date_input("Date", value=date.today())
    with c2:
        symptoms = st.text_area("Counselling Symptoms / Issues", height=140)
        important = st.text_area("Important Notes / Follow-up", height=140)
    st.subheader("Handwritten Notes")
    PALETTE = {"Black": "#000000", "Red": "#E53935", "Blue": "#1E88E5", "Green": "#43A047", "Purple": "#8E24AA", "Orange": "#FB8C00", "Brown": "#6D4C41", "Pink": "#EC407A"}
    t1, t2, t3, t4 = st.columns([2, 1, 1, 1])
    with t1:
        pc = st.selectbox("Pen colour", list(PALETTE.keys()) + ["Custom..."], key="pc")
    with t2:
        if pc == "Custom...":
            stroke_color = st.color_picker("Custom", "#000000")
        else:
            stroke_color = PALETTE[pc]
            st.color_picker("Selected", stroke_color, disabled=True)
    with t3:
        width = st.slider("Pen width", 1, 20, 2)
    with t4:
        tool = st.radio("Tool", ["Pen", "Eraser"], key="tool")
    if tool == "Eraser":
        width = st.slider("Eraser size", 5, 60, 20)
        drawing_mode = "eraser"
        stroke_color = "#000000"
    else:
        drawing_mode = "freedraw"
    if "cvs" not in st.session_state:
        st.session_state.cvs = 0
    if "bg_image" not in st.session_state:
        st.session_state.bg_image = None
    H = 900 if full_screen else 300
    W = 1600 if full_screen else 800
    bg = None
    if st.session_state.bg_image:
        try:
            b = st.session_state.bg_image
            if isinstance(b, str) and b.startswith("data:image"):
                b = b.split(",", 1)[1]
            raw = base64.b64decode(b) if isinstance(b, str) else b
            bg = Image.open(io.BytesIO(raw)).convert("RGBA")
        except Exception:
            bg = None
    canvas_result = st_canvas(fill_color="rgba(255,165,0,0)", stroke_width=width, stroke_color=stroke_color, background_color="#FFFFFF", background_image=bg, height=H, width=W, drawing_mode=drawing_mode, key="cv_" + str(st.session_state.cvs), update_streamlit=True)
    b1, b2, b3, b4, b5 = st.columns(5)
    with b1:
        if st.button("Save handwriting", use_container_width=True):
            arr = canvas_result.image_data
            ink = arr is not None and arr.ndim == 3 and arr.shape[2] == 4 and bool((arr[..., 3] > 0).any())
            if ink:
                st.session_state.handwritten_notes = canvas_to_b64_png(arr)
                st.success("Captured.")
            else:
                st.warning("Draw something first.")
    with b2:
        if st.button("Undo last", use_container_width=True):
            h = _clipboard_history()
            if h:
                h.pop()
                if h:
                    st.session_state.bg_image = h[-1]
                else:
                    st.session_state.bg_image = None
                st.session_state.cvs += 1
                st.rerun()
            else:
                st.session_state.cvs += 1
                st.session_state.handwritten_notes = None
                st.rerun()
    with b3:
        if st.button("Clear", use_container_width=True):
            st.session_state.cvs += 1
            st.session_state.bg_image = None
            st.session_state.handwritten_notes = None
            st.session_state.canvas_history = []
            st.rerun()
    with b4:
        st.button("Fullscreen" if not full_screen else "Exit fullscreen", use_container_width=True, on_click=_toggle_fullscreen)
    with b5:
        if st.button("Push snapshot", use_container_width=True):
            if st.session_state.get("handwritten_notes"):
                _clipboard_history().append(st.session_state.handwritten_notes)
                st.success("Snapshot added.")
    if canvas_result.json_data and canvas_result.json_data.get("objects"):
        import json
        svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="' + str(W) + '" height="' + str(H) + '">', '<rect width="100%" height="100%" fill="#ffffff"/>']
        for o in canvas_result.json_data["objects"]:
            if o.get("type") == "path":
                svg.append('<path d="' + str(o.get("path", [])) + '" fill="none" stroke="' + str(o.get("stroke", "#000")) + '" stroke-width="' + str(o.get("strokeWidth", 2)) + '"/>')
        svg.append("</svg>")
        st.download_button("Download handwriting (SVG)", "".join(svg).encode("utf-8"), file_name="handwriting.svg", mime="image/svg+xml")
    st.markdown("**Load a previous note to re-edit**")
    c = db()
    prev = c.execute("SELECT id, patient_name, date FROM counselling_notes WHERE handwritten_notes <> '' AND deleted_at IS NULL ORDER BY id DESC LIMIT 20").fetchall()
    c.close()
    if prev:
        opts = ["#" + str(r[0]) + " - " + str(r[1]) + " - " + str(r[2]) for r in prev]
        pick = st.selectbox("Previous notes", ["(none)"] + opts)
        if pick != "(none)":
            pid = prev[opts.index(pick)][0]
            if st.button("Load as background"):
                c = db()
                r = c.execute("SELECT handwritten_notes FROM counselling_notes WHERE id=?", (pid,)).fetchone()
                c.close()
                if r and r[0]:
                    st.session_state.bg_image = dec(r[0])
                    st.session_state.cvs += 1
                    st.rerun()
    components.html("""
        <div style="font-family:sans-serif">
          <button id="rec" style="padding:6px 12px">Start dictation</button>
          <span id="st" style="margin-left:8px">idle</span>
          <div id="out" style="margin-top:6px;border:1px solid #ccc;padding:6px;min-height:40px"></div>
          <script>
          const btn = document.getElementById('rec');
          const stx = document.getElementById('st');
          const out = document.getElementById('out');
          const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
          if (!SR) { btn.disabled = true; stx.textContent = 'not supported'; }
          else {
            const r = new SR();
            r.continuous = true; r.interimResults = true; r.lang = 'en-US';
            r.onresult = e => {
              let t = '';
              for (let i = e.resultIndex; i < e.results.length; i++) { t += e.results[i][0].transcript + ' '; }
              out.textContent += t;
            };
            let on = false;
            btn.onclick = () => {
              if (!on) { r.start(); on = true; btn.textContent = 'Stop'; stx.textContent = 'listening'; }
              else { r.stop(); on = false; btn.textContent = 'Start dictation'; stx.textContent = 'stopped'; }
            };
          }
          </script>
        </div>
        """, height=140)
    if st.session_state.get("handwritten_notes"):
        st.image(st.session_state.handwritten_notes, use_container_width=True)
    if st.button("Save All Notes", type="primary"):
        hw = st.session_state.get("handwritten_notes", "") or ""
        if not isinstance(hw, str):
            hw = canvas_to_b64_png(hw)
        c = db()
        c.execute("INSERT INTO counselling_notes (patient_name, age, sex, date, counselling_symptoms, important_notes, handwritten_notes, created_by, timestamp) VALUES (?,?,?,?,?,?,?,?,?)", (note_name or "Unknown", str(note_age), note_sex, str(note_date), symptoms, important, enc(hw), st.session_state.get("user", "?"), str(datetime.now())))
        c.commit()
        c.close()
        audit("insert", "counselling_notes", detail=note_name)
        st.success("Saved.")
    st.subheader("Saved notes")
    c = db()
    rows = c.execute("SELECT id, patient_name, date, counselling_symptoms, important_notes, handwritten_notes, timestamp FROM counselling_notes WHERE deleted_at IS NULL ORDER BY id DESC LIMIT 20").fetchall()
    c.close()
    for r in rows:
        with st.expander("#" + str(r[0]) + " - " + str(r[1]) + " - " + str(r[2])):
            st.write(r[3] or "-")
            st.write(r[4] or "-")
            if r[5]:
                st.image(dec(r[5]), use_container_width=True)
            st.caption("Saved: " + str(r[6]))


if page == "Report":
    st.title("Clinical Report")
    rep = st.session_state.get("current_report")
    ai = st.session_state.get("current_ai")
    if rep:
        st.code(rep, language="text")
        if ai:
            st.markdown(ai)
        d1, d2 = st.columns(2)
        with d1:
            st.download_button("Download .txt", rep, file_name="report.txt", mime="text/plain")
        with d2:
            pdf = report_to_pdf(rep) if HAS_FPDF else None
            if pdf:
                st.download_button("Download PDF", pdf, file_name="report.pdf", mime="application/pdf")
            else:
                st.caption("Install fpdf2 for PDF export.")
    else:
        st.info("No current report. Run an Assessment.")
    st.divider()
    st.subheader("Past reports")
    c = db()
    rows = c.execute("SELECT id, patient_name, syndrome, severity, risk_level, timestamp FROM assessments WHERE deleted_at IS NULL ORDER BY id DESC LIMIT 25").fetchall()
    c.close()
    for r in rows:
        with st.expander("#" + str(r[0]) + " - " + str(r[1]) + " - " + str(r[2])):
            c = db()
            f = c.execute("SELECT report_text, ai_insights FROM assessments WHERE id=?", (r[0],)).fetchone()
            c.close()
            if f:
                st.code(f[0] or "", language="text")
                if f[1]:
                    st.markdown(f[1])


if page == "Chat":
    st.title("Clinical Chat Assistant")
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    for role, msg in st.session_state.chat_history:
        with st.chat_message(role):
            st.write(msg)
    q = st.chat_input("Ask about depression, mania, risk, PHQ-9...")
    if q:
        st.session_state.chat_history.append(("user", q))
        with st.chat_message("user"):
            st.write(q)
        a = random.choice(["This is decision support only. Verify with guidelines.", "Document clinical reasoning.", "Regular follow-up is essential."])
        st.session_state.chat_history.append(("assistant", a))
        with st.chat_message("assistant"):
            st.write(a)


if page == "History":
    st.title("Assessment History")
    q = st.text_input("Search (name or syndrome)")
    pg = st.number_input("Page", 1, 999, 1) - 1
    per = 25
    c = db()
    where = "WHERE deleted_at IS NULL"
    params = []
    if q:
        where += " AND (patient_name LIKE ? OR syndrome LIKE ?)"
        params += ["%" + q + "%", "%" + q + "%"]
    if USE_PG:
        sql = "SELECT id, patient_name, age, sex, syndrome, severity, risk_level, timestamp FROM assessments " + where + " ORDER BY id DESC LIMIT " + str(per) + " OFFSET " + str(pg * per)
    else:
        sql = "SELECT id, patient_name, age, sex, syndrome, severity, risk_level, timestamp FROM assessments " + where + " ORDER BY id DESC LIMIT ? OFFSET ?"
        params += [per, pg * per]
    rows = c.execute(sql, tuple(params)).fetchall()
    c.close()
    if not rows:
        st.info("No results.")
    else:
        df = pd.DataFrame(rows, columns=["id", "patient", "age", "sex", "syndrome", "severity", "risk", "ts"])
        st.dataframe(df, use_container_width=True)


if page == "Patient Database":
    st.title("Patient Database")
    q = st.text_input("Search name")
    c = db()
    if q:
        rows = c.execute("SELECT id, name, age, sex, first_seen, last_seen FROM patients WHERE deleted_at IS NULL AND name LIKE ? ORDER BY last_seen DESC", ("%" + q + "%",)).fetchall()
    else:
        rows = c.execute("SELECT id, name, age, sex, first_seen, last_seen FROM patients WHERE deleted_at IS NULL ORDER BY last_seen DESC LIMIT 200").fetchall()
    c.close()
    if not rows:
        st.info("No patients.")
    else:
        df = pd.DataFrame(rows, columns=["id", "name", "age", "sex", "first_seen", "last_seen"])
        st.dataframe(df, use_container_width=True)
        pick = st.selectbox("Select patient to view", df["name"].tolist())
        if pick:
            c = db()
            a = pd.read_sql_query("SELECT id, syndrome, severity, risk_level, timestamp FROM assessments WHERE patient_name=? AND deleted_at IS NULL ORDER BY id DESC", c._raw, params=(pick,))
            t = pd.read_sql_query("SELECT id, medication_name, dose, status, start_date FROM treatments WHERE patient_name=? AND deleted_at IS NULL ORDER BY id DESC", c._raw, params=(pick,))
            c.close()
            st.subheader("Assessments")
            st.dataframe(a, use_container_width=True)
            st.subheader("Treatments")
            st.dataframe(t, use_container_width=True)


if page == "Follow-up":
    st.title("Follow-up")
    c1, c2 = st.columns(2)
    with c1:
        name = st.text_input("Patient", value=st.session_state.get("patient_name", ""))
        d = st.date_input("Date", value=date.today() + timedelta(days=14))
        notes = st.text_area("Notes", height=100)
        if st.button("Schedule"):
            if name.strip():
                c = db()
                c.execute("INSERT INTO follow_ups (patient_name, follow_up_date, status, notes, created_by, created_at) VALUES (?,?,?,?,?,?)", (name.strip(), str(d), "Scheduled", notes, st.session_state.get("user", "?"), str(datetime.now())))
                c.commit()
                c.close()
                audit("insert", "follow_ups", detail=name)
                st.success("Scheduled.")
                st.rerun()
    with c2:
        c = db()
        pending = c.execute("SELECT id, patient_name, follow_up_date FROM follow_ups WHERE status='Scheduled' AND deleted_at IS NULL ORDER BY follow_up_date").fetchall()
        c.close()
        if pending:
            opts = ["#" + str(r[0]) + " - " + str(r[1]) + " - " + str(r[2]) for r in pending]
            pick = st.selectbox("Pending", opts)
            fid = pending[opts.index(pick)][0]
            imp = st.radio("Improved?", ["Yes", "Partially", "No"], horizontal=True)
            adh = st.selectbox("Adherence", ["Good", "Partial", "Poor"])
            se = st.text_input("Side effects")
            gi = st.selectbox("Global impression", ["Much improved", "Improved", "No change", "Worse"])
            if st.button("Mark complete"):
                c = db()
                c.execute("UPDATE follow_ups SET status='Completed', symptoms_improved=?, adherence=?, side_effects=?, global_impression=?, completed_at=? WHERE id=?", (imp, adh, se, gi, str(datetime.now()), fid))
                c.commit()
                c.close()
                audit("update", "follow_ups", fid)
                st.success("Saved.")
                st.rerun()
        else:
            st.info("No pending follow-ups.")
    st.subheader("All")
    c = db()
    df = pd.read_sql_query("SELECT * FROM follow_ups WHERE deleted_at IS NULL ORDER BY id DESC", c._raw)
    c.close()
    st.dataframe(df, use_container_width=True)


if page == "Epidemiology":
    st.title("Epidemiology")
    days = st.slider("Look-back window (days)", 7, 3650, 365)
    since = str(date.today() - timedelta(days=days))
    c = db()
    df = pd.read_sql_query("SELECT syndrome, severity, risk_level, age, sex FROM assessments WHERE deleted_at IS NULL AND timestamp >= ?", c._raw, params=(since,))
    c.close()
    if df.empty:
        st.info("No data in that window.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("By syndrome"); st.bar_chart(df["syndrome"].value_counts())
            st.subheader("By severity"); st.bar_chart(df["severity"].value_counts())
        with c2:
            st.subheader("By risk"); st.bar_chart(df["risk_level"].value_counts())
            st.subheader("By sex"); st.bar_chart(df["sex"].value_counts())


if page == "Export Data":
    st.title("Export Data")
    tables = ["assessments", "treatments", "phq9_scores", "gad7_scores", "adhd_scores", "other_scales", "counselling_notes", "follow_ups", "patients", "audit_log"]
    xl = export_excel(tables)
    if xl:
        st.download_button("Download all tables (.xlsx)", xl, file_name="psychassist_export_" + str(date.today()) + ".xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        st.warning("Install openpyxl to enable multi-sheet Excel export.")
    for t in tables:
        c = db()
        try:
            df = pd.read_sql_query("SELECT * FROM " + t, c._raw)
        except Exception:
            c.close()
            continue
        c.close()
        st.subheader(t + " (" + str(len(df)) + " rows)")
        st.download_button("Download " + t + ".csv", df.to_csv(index=False).encode("utf-8"), file_name=t + "_" + str(date.today()) + ".csv", mime="text/csv", key="dl_" + t)


st.markdown("<style>@media print {.stSidebar, header, .stDeployButton, .stButton, .stDownloadButton {display:none !important;}}</style>", unsafe_allow_html=True)