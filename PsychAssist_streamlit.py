# -*- coding: utf-8 -*-
# PsychAssist Web v4.4 - Clinical Decision Support (Streamlit)
#
# Decision support only - not a diagnosis.
#
# v4.4
#   * Fixed StreamlitWidgetAlreadyInstantiatedError on the full-screen
#     toggle button: state change moved into an on_click callback.
#
# v4.3
#   * Enhanced handwriting canvas: multi-colour pen, eraser,
#     full-screen mode, clear, empty-canvas detection.
#
# v4.2
#   * Replaced invalid st.canvas() with streamlit-drawable-canvas.
#   * Handwriting saved as base64 PNG data URLs.
#   * Fixed column indices when listing saved counselling notes.
#   * Fixed undefined conn in Assessment / ADHD pages.
#   * Fixed ADHD INSERT column names.
#   * Fixed placeholder count in Assessment INSERT.
#   * Removed non-ASCII box characters from report text.

import io
import base64
import random
import sqlite3
from datetime import datetime, date

import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image
from streamlit_drawable_canvas import st_canvas

st.set_page_config(
    page_title="PsychAssist Web",
    page_icon="brain",
    layout="wide",
    initial_sidebar_state="expanded",
)

DB_PATH = "psychassist_web.db"


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute(
        "CREATE TABLE IF NOT EXISTS assessments ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "patient_name TEXT, age TEXT, sex TEXT, symptoms TEXT, syndrome TEXT,"
        "severity TEXT, risk_level TEXT, formal_diagnoses TEXT,"
        "organic_level TEXT, organic_score INTEGER, functional_impairment TEXT,"
        "mse TEXT, duration TEXT, onset TEXT, pattern TEXT,"
        "speech TEXT, affect TEXT, thought_process TEXT, insight TEXT, judgment TEXT,"
        "substance_use TEXT, neuro_findings TEXT,"
        "report_text TEXT, ai_insights TEXT,"
        "mdd_criteria TEXT, mania_criteria TEXT, schizophrenia_criteria TEXT, delirium_criteria TEXT,"
        "mixed_features INTEGER, symptom_weight REAL,"
        "phq9_score INTEGER, gad7_score INTEGER, adhd_score INTEGER, adhd_type TEXT,"
        "adhd_severity TEXT, differential TEXT, treatment_recommendations TEXT,"
        "timestamp TEXT)"
    )

    c.execute(
        "CREATE TABLE IF NOT EXISTS treatments ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "patient_name TEXT, medication_name TEXT, medication_class TEXT,"
        "dose TEXT, frequency TEXT, route TEXT, start_date TEXT, end_date TEXT,"
        "status TEXT, adherence TEXT, side_effects TEXT, psychotherapy TEXT,"
        "reason_start TEXT, reason_stop TEXT, notes TEXT, timestamp TEXT)"
    )

    c.execute(
        "CREATE TABLE IF NOT EXISTS phq9_scores ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "patient_name TEXT, total_score INTEGER, severity TEXT, answers TEXT, timestamp TEXT)"
    )

    c.execute(
        "CREATE TABLE IF NOT EXISTS gad7_scores ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "patient_name TEXT, total_score INTEGER, severity TEXT, answers TEXT, timestamp TEXT)"
    )

    c.execute(
        "CREATE TABLE IF NOT EXISTS adhd_scores ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "patient_name TEXT, total_score INTEGER, severity TEXT, answers TEXT, adhd_type TEXT, timestamp TEXT)"
    )

    c.execute(
        "CREATE TABLE IF NOT EXISTS counselling_notes ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "patient_name TEXT, age TEXT, sex TEXT, date TEXT,"
        "counselling_symptoms TEXT, important_notes TEXT, handwritten_notes TEXT,"
        "timestamp TEXT)"
    )

    c.execute(
        "CREATE TABLE IF NOT EXISTS follow_ups ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "patient_name TEXT, assessment_id INTEGER, follow_up_date TEXT,"
        "status TEXT, notes TEXT, symptoms_improved TEXT, adherence TEXT,"
        "side_effects TEXT, global_impression TEXT, created_at TEXT, completed_at TEXT)"
    )

    c.execute(
        "CREATE TABLE IF NOT EXISTS patients ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "name TEXT UNIQUE, age TEXT, sex TEXT, phone TEXT, notes TEXT,"
        "first_seen TEXT, last_seen TEXT, created_at TEXT)"
    )

    conn.commit()
    conn.close()


init_db()


# ---------------------------------------------------------------------------
# Static data
# ---------------------------------------------------------------------------
symptom_categories = {
    "Mood Symptoms": ["Low mood", "Anhedonia", "Fatigue", "Hopelessness",
                      "Excessive guilt", "Suicidal thoughts",
                      "Sleep disturbance", "Irritability"],
    "Mania Symptoms": ["Reduced sleep", "Increased energy", "Grandiosity",
                       "Pressured speech", "Racing thoughts",
                       "Risk-taking behavior", "Distractibility"],
    "Psychotic Symptoms": ["Auditory hallucinations", "Visual hallucinations",
                           "Delusions", "Paranoia", "Thought broadcasting",
                           "Disorganized speech", "Negative symptoms"],
    "Anxiety Symptoms": ["Panic attacks", "Excessive worry", "Palpitations",
                         "Sweating", "Tremor", "Avoidance behavior",
                         "Fear of dying"],
    "OCD Symptoms": ["Obsessions", "Compulsions"],
    "Trauma Symptoms": ["Flashbacks", "Nightmares", "Hypervigilance"],
    "Cognitive Symptoms": ["Memory loss", "Confusion", "Disorientation",
                           "Fluctuating attention", "Personality change",
                           "Poor concentration"],
    "Neurological Symptoms": ["Seizure", "Weakness", "Tremor (neurological)",
                              "Gait disturbance", "Headache",
                              "Loss of consciousness"],
    "Behavioral Symptoms": ["Aggression", "Self-harm", "Catatonia",
                            "Social withdrawal"],
}

icd11_codes = {
    "Major Depressive Disorder": "6A70",
    "Bipolar I Disorder - Manic Episode": "6A60",
    "Schizophrenia Spectrum Disorder": "6A20",
    "Delirium": "6D70",
    "Generalized Anxiety Disorder": "6B00",
}

symptom_weights = {
    "Low mood": 0.15, "Anhedonia": 0.15, "Fatigue": 0.10, "Hopelessness": 0.12,
    "Excessive guilt": 0.08, "Suicidal thoughts": 0.20, "Sleep disturbance": 0.10,
    "Irritability": 0.05, "Reduced sleep": 0.15, "Increased energy": 0.15,
    "Grandiosity": 0.12, "Pressured speech": 0.10, "Racing thoughts": 0.12,
    "Auditory hallucinations": 0.20, "Delusions": 0.20, "Paranoia": 0.12,
    "Negative symptoms": 0.15, "Poor concentration": 0.10,
}

medication_database = {
    "Major Depressive Disorder": {
        "first_line": [
            {"name": "Sertraline", "class": "SSRI", "starting_dose": "50mg",
             "max_dose": "200mg",
             "side_effects": "Nausea, headache, insomnia, sexual dysfunction",
             "contraindications": "MAOIs within 14 days"},
            {"name": "Escitalopram", "class": "SSRI", "starting_dose": "10mg",
             "max_dose": "20mg",
             "side_effects": "Nausea, fatigue, insomnia, sexual dysfunction",
             "contraindications": "MAOIs, pimozide"},
            {"name": "Fluoxetine", "class": "SSRI", "starting_dose": "20mg",
             "max_dose": "80mg",
             "side_effects": "Nervousness, anxiety, insomnia, weight changes",
             "contraindications": "MAOIs, thioridazine"},
        ],
        "second_line": [
            {"name": "Bupropion", "class": "NDRI", "starting_dose": "150mg",
             "max_dose": "300mg",
             "side_effects": "Agitation, dry mouth, insomnia",
             "contraindications": "Seizure disorder, eating disorders"},
        ],
        "augmentation": [
            {"name": "Aripiprazole", "class": "Atypical Antipsychotic",
             "starting_dose": "2-5mg", "max_dose": "15mg",
             "side_effects": "Akathisia, weight gain",
             "contraindications": "Hypersensitivity"},
        ],
    },
    "Bipolar I Disorder - Manic Episode": {
        "first_line": [
            {"name": "Lithium", "class": "Mood Stabilizer",
             "starting_dose": "300mg", "max_dose": "1800mg",
             "side_effects": "Tremor, polydipsia, polyuria",
             "contraindications": "Severe renal disease"},
            {"name": "Valproate", "class": "Anticonvulsant",
             "starting_dose": "250mg", "max_dose": "60mg/kg",
             "side_effects": "Sedation, tremor, weight gain",
             "contraindications": "Hepatic disease, pregnancy"},
        ],
        "second_line": [
            {"name": "Olanzapine", "class": "Atypical Antipsychotic",
             "starting_dose": "10mg", "max_dose": "20mg",
             "side_effects": "Weight gain, metabolic syndrome",
             "contraindications": "Dementia-related psychosis"},
        ],
    },
    "Schizophrenia Spectrum Disorder": {
        "first_line": [
            {"name": "Risperidone", "class": "Atypical Antipsychotic",
             "starting_dose": "2mg", "max_dose": "8mg",
             "side_effects": "EPS, weight gain",
             "contraindications": "Hypersensitivity"},
            {"name": "Aripiprazole", "class": "Atypical Antipsychotic",
             "starting_dose": "10mg", "max_dose": "30mg",
             "side_effects": "Akathisia, insomnia",
             "contraindications": "Hypersensitivity"},
        ],
    },
    "Delirium": {
        "first_line": [
            {"name": "Haloperidol", "class": "Typical Antipsychotic",
             "starting_dose": "0.5mg", "max_dose": "5mg",
             "side_effects": "EPS, QT prolongation",
             "contraindications": "Parkinson's disease"},
        ],
    },
    "Generalized Anxiety Disorder": {
        "first_line": [
            {"name": "Sertraline", "class": "SSRI", "starting_dose": "25mg",
             "max_dose": "200mg",
             "side_effects": "Nausea, insomnia",
             "contraindications": "MAOIs"},
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

OPTIONS = ["Not at all (0)", "Several days (1)",
           "More than half the days (2)", "Nearly every day (3)"]

CHATBOT = {
    "depression": [
        "Major depression typically requires 4-6 weeks of antidepressant treatment for full response.",
        "SSRIs are common first-line options.",
        "CBT is highly effective for depression.",
        "Monitor suicidal ideation early in treatment.",
    ],
    "mania": [
        "Lithium therapeutic range usually 0.6-1.2 mEq/L.",
        "Valproate needs liver monitoring.",
        "Sleep deprivation can trigger mania.",
        "Avoid antidepressants in acute mania.",
    ],
    "psychosis": [
        "Early intervention improves outcomes.",
        "Clozapine for treatment-resistant schizophrenia.",
        "Metabolic monitoring with atypicals is essential.",
    ],
    "delirium": [
        "Delirium is often reversible if cause is treated.",
        "Common causes: infection, meds, metabolic issues.",
        "Non-drug measures first.",
    ],
    "risk": [
        "Repeat suicide risk assessment each visit.",
        "Safety plans: triggers, coping, contacts.",
        "Remove access to lethal means when high risk.",
    ],
    "medication": [
        "Start low, go slow.",
        "Full response may take 4-8 weeks.",
        "Check drug interactions.",
    ],
    "phq9": [
        "PHQ-9: 5-9 Mild, 10-14 Moderate, 15-19 Moderately severe, 20+ Severe.",
        "Score >=10 usually needs treatment.",
    ],
    "gad7": [
        "GAD-7: 5-9 Mild, 10-14 Moderate, 15+ Severe.",
        "Score >=10 suggests clinically significant anxiety.",
    ],
}

GENERAL = [
    "This is decision support only. Verify with guidelines.",
    "Document clinical reasoning.",
    "Regular follow-up is essential.",
]


def chatbot_reply(q):
    q = q.lower()
    km = {
        "depression": "depression", "depressive": "depression", "mdd": "depression",
        "phq": "phq9", "mania": "mania", "bipolar": "mania",
        "psychosis": "psychosis", "schizophrenia": "psychosis",
        "delirium": "delirium", "risk": "risk", "suicide": "risk",
        "medication": "medication", "drug": "medication",
        "gad": "gad7", "anxiety": "gad7",
    }
    for k, cat in km.items():
        if k in q:
            return random.choice(CHATBOT.get(cat, GENERAL))
    return random.choice(GENERAL)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def canvas_to_b64_png(image_data):
    """Convert st_canvas numpy RGBA array to a base64 PNG data URL."""
    if image_data is None:
        return ""
    arr = image_data
    if arr.dtype != "uint8":
        arr = arr.astype("uint8")
    img = Image.fromarray(arr, "RGBA")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _toggle_fullscreen():
    """on_click callback for the full-screen toggle button.

    Runs BEFORE widgets are re-instantiated, so it is safe to mutate
    a widget's session_state key here.
    """
    st.session_state.draw_fullscreen = not st.session_state.get(
        "draw_fullscreen", False
    )


def has_s(selected, s):
    return s in selected


def severity_grader(score):
    if score <= 5:
        return "Mild"
    if score <= 12:
        return "Moderate"
    if score <= 20:
        return "Severe"
    return "Very Severe"


def normalize_scores(d):
    t = sum(d.values())
    if t == 0:
        return d
    return {k: round((v / t) * 100, 2) for k, v in d.items()}


def depressive_logic(selected, duration, affect):
    if not (has_s(selected, "Low mood") or has_s(selected, "Anhedonia")):
        return 0
    score = 12
    for s in ["Fatigue", "Hopelessness", "Excessive guilt",
              "Suicidal thoughts", "Sleep disturbance", "Poor concentration"]:
        if has_s(selected, s):
            score += 2
    if sum(1 for s in ["Grandiosity", "Increased energy", "Reduced sleep"]
           if has_s(selected, s)) >= 2:
        score -= 8
    if duration in ["Weeks", "Months"]:
        score += 2
    if affect == "Depressed":
        score += 3
    return max(score, 0)


def mania_logic(selected, duration, speech, thought):
    if not (has_s(selected, "Reduced sleep") and has_s(selected, "Increased energy")):
        return 0
    score = 12
    for s in ["Grandiosity", "Pressured speech", "Racing thoughts",
              "Risk-taking behavior", "Distractibility"]:
        if has_s(selected, s):
            score += 2
    if duration in ["Days", "Weeks"]:
        score += 2
    if speech == "Pressured":
        score += 3
    if thought == "Flight of ideas":
        score += 3
    return max(score, 0)


def psychosis_logic(selected, duration, speech, thought):
    if not (has_s(selected, "Auditory hallucinations")
            or has_s(selected, "Visual hallucinations")
            or has_s(selected, "Delusions")):
        return 0
    score = 12
    for s in ["Paranoia", "Disorganized speech", "Negative symptoms"]:
        if has_s(selected, s):
            score += 2
    if duration in ["Months", "Years"]:
        score += 3
    if speech == "Disorganized":
        score += 3
    if thought == "Disorganized":
        score += 4
    return max(score, 0)


def delirium_logic(selected, duration, onset, fluctuating):
    if not (has_s(selected, "Confusion") and has_s(selected, "Disorientation")):
        return 0
    score = 15
    if has_s(selected, "Fluctuating attention") or has_s(selected, "Visual hallucinations"):
        score += 3
    if duration in ["Hours", "Days"]:
        score += 5
    if onset == "Sudden":
        score += 4
    if fluctuating:
        score += 4
    return max(score, 0)


def diagnose_mdd(selected, duration, impairment):
    cnt = sum(1 for s in ["Low mood", "Anhedonia", "Fatigue", "Hopelessness",
                          "Excessive guilt", "Suicidal thoughts",
                          "Sleep disturbance", "Poor concentration"]
              if has_s(selected, s))
    core = has_s(selected, "Low mood") or has_s(selected, "Anhedonia")
    no_mania = not (has_s(selected, "Grandiosity") or has_s(selected, "Increased energy"))
    if (cnt >= 5 and core and no_mania
            and duration in ["Weeks", "Months"]
            and impairment != "None reported"):
        return {"diagnosis": "Major Depressive Disorder",
                "status": "CRITERIA FULLY MET", "confidence": "HIGH"}
    if cnt >= 3:
        return {"diagnosis": "Major Depressive Disorder",
                "status": "PARTIAL CRITERIA", "confidence": "MODERATE"}
    return None


def diagnose_mania(selected, duration):
    cnt = sum(1 for s in ["Reduced sleep", "Increased energy", "Grandiosity",
                          "Pressured speech", "Racing thoughts",
                          "Risk-taking behavior", "Distractibility"]
              if has_s(selected, s))
    if (cnt >= 4
            and has_s(selected, "Reduced sleep")
            and has_s(selected, "Increased energy")
            and duration in ["Days", "Weeks"]):
        return {"diagnosis": "Bipolar I Disorder - Manic Episode",
                "status": "CRITERIA FULLY MET", "confidence": "HIGH"}
    return None


def diagnose_schizophrenia(selected, duration):
    core = has_s(selected, "Delusions") or has_s(selected, "Auditory hallucinations")
    cnt = sum(1 for s in ["Auditory hallucinations", "Visual hallucinations",
                          "Delusions", "Paranoia", "Disorganized speech",
                          "Negative symptoms"] if has_s(selected, s))
    if core and cnt >= 2 and duration in ["Months", "Years"]:
        return {"diagnosis": "Schizophrenia Spectrum Disorder",
                "status": "CRITERIA FULLY MET", "confidence": "HIGH"}
    return None


def diagnose_delirium(selected, duration, fluctuating):
    if (has_s(selected, "Confusion")
            and has_s(selected, "Disorientation")
            and (has_s(selected, "Fluctuating attention") or fluctuating)
            and duration in ["Hours", "Days"]):
        return {"diagnosis": "Delirium", "status": "CRITERIA FULLY MET",
                "confidence": "HIGH"}
    return None


def organic_psychosis_detector(selected, onset, fluctuating, seizure, focal, head_injury):
    score = 0
    if has_s(selected, "Visual hallucinations"):
        score += 3
    if has_s(selected, "Confusion"):
        score += 4
    if fluctuating:
        score += 4
    if seizure:
        score += 4
    if focal:
        score += 5
    if onset == "Sudden":
        score += 3
    if head_injury:
        score += 4
    if score >= 15:
        level = "VERY HIGH suspicion of organic psychosis"
    elif score >= 10:
        level = "HIGH suspicion of organic psychosis"
    elif score >= 6:
        level = "MODERATE suspicion of organic psychosis"
    else:
        level = "LOW suspicion of organic psychosis"
    return level, score


def risk_assessment(selected, suicide_plan, command_hall, violent, access_means):
    score = 0
    if has_s(selected, "Suicidal thoughts"):
        score += 3
    if suicide_plan:
        score += 6
    if command_hall:
        score += 6
    if violent:
        score += 5
    if access_means:
        score += 4
    if score >= 15:
        return "CRITICAL RISK", "IMMEDIATE HOSPITALIZATION REQUIRED", score
    if score >= 10:
        return "HIGH RISK", "URGENT psychiatric consultation required", score
    if score >= 5:
        return "MODERATE RISK", "Enhanced monitoring required", score
    return "LOW RISK", "Routine monitoring", score


def mixed_features_detector(selected):
    dep = sum(1 for s in ["Low mood", "Anhedonia", "Hopelessness",
                          "Excessive guilt", "Suicidal thoughts"]
              if has_s(selected, s))
    man = sum(1 for s in ["Reduced sleep", "Increased energy", "Grandiosity",
                          "Pressured speech", "Racing thoughts"]
              if has_s(selected, s))
    return dep >= 3 and man >= 3


def calculate_symptom_weight(selected):
    return round(sum(symptom_weights.get(s, 0) for s in selected
                     if s in symptom_weights), 2)


def generate_mse(speech, affect, thought, insight, judgment):
    sm = {"Normal": "normal rate and rhythm",
          "Pressured": "rapid, difficult to interrupt",
          "Slow": "reduced rate",
          "Disorganized": "disorganized"}
    am = {"Normal": "full range", "Flat": "severely reduced",
          "Depressed": "sad, discouraged", "Labile": "rapidly changing"}
    tm = {"Normal": "logical and goal-directed", "Tangential": "off-topic",
          "Disorganized": "illogical", "Flight of ideas": "rapid shifts"}
    im = {"Good": "excellent awareness", "Partial": "partial recognition",
          "Poor": "limited awareness"}
    jm = {"Good": "intact", "Fair": "mildly impaired",
          "Poor": "moderately impaired", "Impaired": "markedly impaired"}
    return (
        "Speech: " + sm.get(speech, "normal") + ". "
        "Affect: " + am.get(affect, "normal") + ". "
        "Thought: " + tm.get(thought, "normal") + ". "
        "Insight: " + im.get(insight, "good") + ". "
        "Judgment: " + jm.get(judgment, "intact") + "."
    )


def generate_ai_insights(top, severity, risk_level, formal):
    lines = []
    lines.append("### Clinical Overview")
    lines.append("Primary presentation: **" + top + "** (" + severity.lower() + " severity).")

    if formal:
        names = [d["diagnosis"] for d in formal if d.get("status") == "CRITERIA FULLY MET"]
        if names:
            lines.append("")
            lines.append("### Criteria")
            lines.append("Meets criteria for: **" + ", ".join(names) + "** (decision support only).")

    lines.append("")
    lines.append("### Risk")
    if "HIGH" in risk_level or "CRITICAL" in risk_level:
        lines.append("High/critical risk - do not leave unattended; remove means; "
                     "emergency services; consider admission.")
    elif "MODERATE" in risk_level:
        lines.append("Moderate risk - enhanced monitoring and safety planning.")
    else:
        lines.append("Low risk - routine monitoring.")

    lines.append("")
    lines.append("### Notes - " + top)
    edu = {
        "Depressive Syndrome": [
            "SSRIs + CBT first-line.",
            "Monitor suicide risk early in treatment.",
            "Rule out medical causes.",
        ],
        "Manic Syndrome": [
            "Lithium/valproate first-line.",
            "Avoid antidepressants in acute mania.",
            "Monitor levels/LFTs.",
        ],
        "Psychotic Syndrome": [
            "Antipsychotics first-line.",
            "Early intervention improves outcomes.",
            "Rule out substance/medical causes.",
        ],
        "Delirium Syndrome": [
            "Medical emergency - treat cause.",
            "Non-pharm measures first.",
            "Haloperidol only if severe agitation.",
        ],
    }
    for x in edu.get(top, ["Correlate with full clinical assessment."]):
        lines.append("- " + x)

    lines.append("")
    lines.append("### Follow-up")
    lines.append("Reassess 1-2 weeks; monitor adherence/side effects; recheck risk each visit.")

    return "\n".join(lines)


def phq9_severity(score):
    if score <= 4:
        return "None-Minimal"
    if score <= 9:
        return "Mild"
    if score <= 14:
        return "Moderate"
    if score <= 19:
        return "Moderately Severe"
    return "Severe"


def gad7_severity(score):
    if score <= 4:
        return "Minimal"
    if score <= 9:
        return "Mild"
    if score <= 14:
        return "Moderate"
    return "Severe"


def upsert_patient(name, age, sex):
    if not name or not name.strip():
        return
    conn = get_conn()
    c = conn.cursor()
    now = str(datetime.now())
    c.execute("SELECT id FROM patients WHERE name = ?", (name.strip(),))
    row = c.fetchone()
    if row:
        c.execute(
            "UPDATE patients SET age=?, sex=?, last_seen=? WHERE name=?",
            (age, sex, now, name.strip()),
        )
    else:
        c.execute(
            "INSERT INTO patients (name, age, sex, first_seen, last_seen, created_at) "
            "VALUES (?,?,?,?,?,?)",
            (name.strip(), age, sex, now, now, now),
        )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
st.sidebar.title("PsychAssist Web v4.4")
st.sidebar.caption("Decision support only - not a diagnosis")

page = st.sidebar.radio("Navigation", [
    "Assessment", "PHQ-9", "GAD-7", "ADHD",
    "Counselling & Notes", "Report",
    "Chat", "History", "Patient Database", "Follow-up",
    "Epidemiology", "Export Data",
])


# ---------------------------------------------------------------------------
# Assessment
# ---------------------------------------------------------------------------
if page == "Assessment":
    st.title("Clinical Assessment")

    with st.form("assessment_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            name = st.text_input("Patient Name", placeholder="Full name")
            age = st.number_input("Age", min_value=1, max_value=120, value=30)
            sex = st.selectbox("Sex", ["Male", "Female", "Other"])
        with col2:
            duration = st.selectbox("Duration",
                                    ["Hours", "Days", "Weeks", "Months", "Years"])
            onset = st.selectbox("Onset", ["Sudden", "Gradual"])
            pattern = st.selectbox("Pattern",
                                   ["Not specified", "Episodic", "Chronic", "Fluctuating"])
        with col3:
            speech = st.selectbox("Speech",
                                  ["Normal", "Pressured", "Slow", "Disorganized"])
            affect = st.selectbox("Affect",
                                  ["Normal", "Flat", "Depressed", "Labile"])
            thought = st.selectbox("Thought",
                                   ["Normal", "Tangential", "Disorganized",
                                    "Flight of ideas"])
            insight = st.selectbox("Insight", ["Good", "Partial", "Poor"])
            judgment = st.selectbox("Judgment",
                                    ["Good", "Fair", "Poor", "Impaired"])

        substance = st.multiselect(
            "Substance Use",
            ["Alcohol", "Cannabis", "Stimulants", "Opioids", "Withdrawal"],
        )
        neuro = st.multiselect(
            "Neuro Findings",
            ["Head injury", "Fluctuating cognition", "Focal deficit",
             "Seizure disorder"],
        )
        func_imp = st.multiselect(
            "Impairment", ["Occupational", "Social", "Self-care"]
        )

        selected = []
        for cat, items in symptom_categories.items():
            st.write("**" + cat + "**")
            for item in items:
                if st.checkbox(item, key="sym_" + item):
                    selected.append(item)

        risk_suicide = st.checkbox("Active suicidal plan")
        risk_command = st.checkbox("Command hallucinations")
        risk_violent = st.checkbox("Violent behavior")
        risk_means = st.checkbox("Access to means")

        submitted = st.form_submit_button("Generate Report")

        if submitted:
            if not name:
                st.error("Please enter patient name")
            else:
                upsert_patient(name, str(age), sex)
                st.session_state.patient_name = name

                onset_s = "Sudden" if onset == "Sudden" else "Gradual"
                fluctuating = "Fluctuating cognition" in neuro
                seizure = "Seizure disorder" in neuro
                focal = "Focal deficit" in neuro
                head_injury = "Head injury" in neuro

                dep_score = depressive_logic(selected, duration, affect)
                man_score = mania_logic(selected, duration, speech, thought)
                psych_score = psychosis_logic(selected, duration, speech, thought)
                del_score = delirium_logic(selected, duration, onset_s, fluctuating)

                filtered = {}
                for k, v in [
                    ("Depressive Syndrome", dep_score),
                    ("Manic Syndrome", man_score),
                    ("Psychotic Syndrome", psych_score),
                    ("Delirium Syndrome", del_score),
                ]:
                    if v > 0:
                        filtered[k] = v

                if filtered:
                    top_syndrome = max(filtered, key=filtered.get)
                    severity = severity_grader(max(filtered.values()))
                else:
                    top_syndrome = "Unknown"
                    severity = severity_grader(0)

                impairment_str = " ".join(func_imp) if func_imp else "None reported"

                formal = []
                mdd = diagnose_mdd(selected, duration, impairment_str)
                man = diagnose_mania(selected, duration)
                sch = diagnose_schizophrenia(selected, duration)
                dlm = diagnose_delirium(selected, duration, fluctuating)
                for d in (mdd, man, sch, dlm):
                    if d:
                        formal.append(d)

                organic_level, organic_score = organic_psychosis_detector(
                    selected, onset_s, fluctuating, seizure, focal, head_injury
                )
                risk_level, risk_rec, risk_score = risk_assessment(
                    selected, risk_suicide, risk_command, risk_violent, risk_means
                )

                report_lines = [
                    "============================================================",
                    "                  PSYCHASSIST CLINICAL REPORT",
                    "============================================================",
                    "",
                    "Patient: " + str(name) + " | Age: " + str(age) + " | Sex: " + str(sex),
                    "Syndrome: " + str(top_syndrome) + " | Severity: " + str(severity),
                    "",
                    "MSE: " + generate_mse(speech, affect, thought, insight, judgment),
                    "",
                    "Risk: " + str(risk_level) + " (" + str(risk_score) + "/20) - " + str(risk_rec),
                    "Organic: " + str(organic_level) + " (" + str(organic_score) + "/25)",
                ]
                report_text = "\n".join(report_lines)

                ai_text = generate_ai_insights(top_syndrome, severity,
                                               risk_level, formal)

                conn = get_conn()
                c = conn.cursor()
                c.execute(
                    "INSERT INTO assessments ("
                    "patient_name, age, sex, symptoms, syndrome, severity, risk_level,"
                    "formal_diagnoses, organic_level, organic_score, functional_impairment,"
                    "mse, duration, onset, pattern, speech, affect, thought_process,"
                    "insight, judgment, substance_use, neuro_findings, report_text,"
                    "ai_insights, mdd_criteria, mania_criteria, schizophrenia_criteria,"
                    "delirium_criteria, mixed_features, symptom_weight, timestamp"
                    ") VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        name, str(age), sex, ", ".join(selected), top_syndrome,
                        severity, risk_level, str(formal), organic_level,
                        organic_score, ", ".join(func_imp),
                        generate_mse(speech, affect, thought, insight, judgment),
                        duration, onset, pattern, speech, affect, thought, insight,
                        judgment, ", ".join(substance), ", ".join(neuro),
                        report_text, ai_text,
                        str(mdd) if mdd else "",
                        str(man) if man else "",
                        str(sch) if sch else "",
                        str(dlm) if dlm else "",
                        1 if mixed_features_detector(selected) else 0,
                        calculate_symptom_weight(selected),
                        str(datetime.now()),
                    ),
                )
                conn.commit()
                conn.close()

                st.session_state["current_report"] = report_text
                st.session_state["current_ai"] = ai_text
                st.success("Report generated! Open the Report page to view it.")
                st.rerun()


# ---------------------------------------------------------------------------
# PHQ-9
# ---------------------------------------------------------------------------
if page == "PHQ-9":
    st.title("PHQ-9 Assessment")
    st.session_state.patient_name = st.text_input(
        "Patient Name", value=st.session_state.get("patient_name", "")
    )
    scores = {}
    for i, q in enumerate(PHQ9_QUESTIONS):
        scores[i] = st.slider(q, 0, 3, 0, key="phq9_" + str(i))
    total = sum(scores.values())
    st.success("Total: " + str(total) + " | " + phq9_severity(total))
    if st.button("Save PHQ-9"):
        conn = get_conn()
        conn.execute(
            "INSERT INTO phq9_scores (patient_name, total_score, severity, answers, timestamp) "
            "VALUES (?,?,?,?,?)",
            (st.session_state.get("patient_name", "Unknown"), total,
             phq9_severity(total), str(scores), str(datetime.now())),
        )
        conn.commit()
        conn.close()
        st.success("Saved!")


# ---------------------------------------------------------------------------
# GAD-7
# ---------------------------------------------------------------------------
if page == "GAD-7":
    st.title("GAD-7 Assessment")
    st.session_state.patient_name = st.text_input(
        "Patient Name", value=st.session_state.get("patient_name", "")
    )
    scores = {}
    for i, q in enumerate(GAD7_QUESTIONS):
        scores[i] = st.slider(q, 0, 3, 0, key="gad7_" + str(i))
    total = sum(scores.values())
    st.success("Total: " + str(total) + " | " + gad7_severity(total))
    if st.button("Save GAD-7"):
        conn = get_conn()
        conn.execute(
            "INSERT INTO gad7_scores (patient_name, total_score, severity, answers, timestamp) "
            "VALUES (?,?,?,?,?)",
            (st.session_state.get("patient_name", "Unknown"), total,
             gad7_severity(total), str(scores), str(datetime.now())),
        )
        conn.commit()
        conn.close()
        st.success("Saved!")


# ---------------------------------------------------------------------------
# ADHD
# ---------------------------------------------------------------------------
if page == "ADHD":
    st.title("ADHD Assessment")
    st.session_state.patient_name = st.text_input(
        "Patient Name", value=st.session_state.get("patient_name", "")
    )

    col1, col2 = st.columns(2)
    with col1:
        adhd_type = st.radio(
            "ADHD Type",
            ["Adult (ASRS)", "Adult (CAARS)", "Child (ADHD-RS)"],
            horizontal=True,
        )
        age_group = st.selectbox(
            "Age Group", ["Adult", "Adolescent", "Child (<13 years)"]
        )

    with col2:
        if adhd_type == "Adult (ASRS)":
            asrs_questions = [
                "How often do you have trouble wrapping up the final details of a project, once the challenging parts have been done?",
                "How often do you have difficulty getting things in order when you have to do a task that requires organization?",
                "How often do you have problems remembering appointments or obligations?",
                "How often do you find that you have to read instructions over and over to understand them?",
                "How often do you find yourself starting a new task before finishing the previous one?",
                "How often do you find that you have trouble focusing your attention when you need to focus hard?",
            ]
            total = 0
            for i, q in enumerate(asrs_questions):
                total += st.slider(q, 0, 4, 0, key="asrs_" + str(i))
            st.session_state.adhd_asrs = total
        elif adhd_type == "Adult (CAARS)":
            caars_questions = [
                "I have difficulty concentrating on tasks.",
                "I am easily distracted.",
                "I find it hard to sit still in meetings.",
                "I talk too much.",
                "I interrupt others.",
                "I lose things.",
                "I forget appointments.",
                "I have trouble organizing my daily activities.",
                "I feel restless.",
                "I have a short attention span.",
            ]
            total = 0
            for i, q in enumerate(caars_questions):
                total += st.slider(q, 0, 4, 0, key="caars_" + str(i))
            st.session_state.adhd_caars = total
        else:
            adhd_rs_questions = [
                "Often fidgets with hands or feet or squirms in seat",
                "Leaves seat in classroom or in other situations in which remaining seated is expected",
                "Runs about or climbs excessively in situations in which it is inappropriate",
                "Has difficulty playing or engaging in leisure activities quietly",
                "Is often on the go or acts as if 'driven by a motor'",
                "Talks excessively",
                "Blurts out answers before questions have been completed",
                "Has difficulty awaiting turn",
                "Interrupts or intrudes on others",
                "Has difficulty organizing tasks and activities",
            ]
            total = 0
            for i, q in enumerate(adhd_rs_questions):
                total += st.slider(q, 0, 3, 0, key="adhd_rs_" + str(i))
            st.session_state.adhd_rs = total

    if st.button("Calculate ADHD Score & Diagnosis"):
        if adhd_type == "Adult (ASRS)":
            score = st.session_state.get("adhd_asrs", 0)
            threshold = 18
        elif adhd_type == "Adult (CAARS)":
            score = st.session_state.get("adhd_caars", 0)
            threshold = 30
        else:
            score = st.session_state.get("adhd_rs", 0)
            threshold = 24

        if score <= threshold // 2:
            severity = "None"
        elif score <= threshold:
            severity = "Mild"
        elif score <= threshold * 1.5:
            severity = "Moderate"
        else:
            severity = "Severe"

        st.success("ADHD Score: " + str(score) + "/" + str(threshold)
                   + " | Severity: " + severity)

        st.subheader("Differential Diagnosis")
        diff = st.selectbox(
            "Compare with",
            ["No other diagnosis", "Major Depression", "Generalized Anxiety",
             "Bipolar Disorder", "Learning Disorder", "Trauma/PTSD",
             "Sleep Disorder"],
        )
        st.info("ADHD vs " + diff + ": Overlap possible in most cases.")

        st.subheader("Treatment Recommendations")
        if severity in ["Mild", "Moderate"]:
            st.write("- Non-stimulant: Atomoxetine 40-100mg/day or Guanfacine 1-4mg")
            st.write("- Behavioral therapy: CBT for ADHD or Coaching")
            tx = "Non-stimulant; Behavioral therapy"
        else:
            st.write("- First-line stimulant: Methylphenidate 10-60mg or Amphetamine 10-60mg")
            st.write("- Monitoring: BP, weight, sleep, growth in children")
            tx = "Stimulant; Behavioral therapy; Monitoring"

        conn = get_conn()
        conn.execute(
            "INSERT INTO assessments ("
            "patient_name, syndrome, severity, adhd_score, adhd_type, adhd_severity, "
            "differential, treatment_recommendations, timestamp"
            ") VALUES (?,?,?,?,?,?,?,?,?)",
            (
                st.session_state.get("patient_name", "Unknown"),
                "ADHD", severity, score, adhd_type, severity, diff, tx,
                str(datetime.now()),
            ),
        )
        conn.commit()
        conn.close()

        st.session_state.adhd_score = score
        st.session_state.adhd_severity = severity


# ---------------------------------------------------------------------------
# Counselling & Notes (ENHANCED CANVAS)
# ---------------------------------------------------------------------------
if page == "Counselling & Notes":
    # ---- Full-screen mode: hide Streamlit chrome ----
    full_screen = st.checkbox("Full-screen drawing mode",
                              key="draw_fullscreen",
                              help="Hide the sidebar and expand the canvas.")

    if full_screen:
        st.markdown(
            """
            <style>
              section[data-testid="stSidebar"] {display: none !important;}
              header[data-testid="stHeader"] {display: none !important;}
              .block-container {padding: 0.5rem 0.5rem 0.5rem 0.5rem !important;
                                 max-width: 100% !important;}
              .stDeployButton {display:none !important;}
            </style>
            """,
            unsafe_allow_html=True,
        )

    # ---- Header / patient fields ----
    st.title("Counselling & Clinical Notes")
    st.caption("Decision support only - not a diagnosis. Write, draw or type your notes.")

    col1, col2 = st.columns(2)
    with col1:
        st.session_state.note_name = st.text_input(
            "Patient Name", value=st.session_state.get("patient_name", "")
        )
        st.session_state.note_age = st.number_input(
            "Age", min_value=1, max_value=120, value=30, step=1
        )
        st.session_state.note_sex = st.selectbox("Sex", ["Male", "Female", "Other"])
        st.session_state.note_date = st.date_input("Date", value=date.today())

    with col2:
        st.session_state.counselling_symptoms = st.text_area(
            "Counselling Symptoms / Issues", height=150
        )
        st.session_state.important_notes = st.text_area(
            "Important Notes / Follow-up Reminders", height=150
        )

    # ---- Handwriting toolbar ----
    st.subheader("Handwritten Notes (Stylus Friendly)")

    PALETTE = {
        "Black":  "#000000",
        "Red":    "#E53935",
        "Blue":   "#1E88E5",
        "Green":  "#43A047",
        "Purple": "#8E24AA",
        "Orange": "#FB8C00",
        "Brown":  "#6D4C41",
        "Pink":   "#EC407A",
    }

    tcol1, tcol2, tcol3, tcol4 = st.columns([2, 1, 1, 1])

    with tcol1:
        pen_choice = st.selectbox(
            "Pen colour",
            list(PALETTE.keys()) + ["Custom..."],
            key="pen_choice",
        )
    with tcol2:
        if pen_choice == "Custom...":
            stroke_color = st.color_picker("Custom colour", "#000000",
                                           key="pen_custom_color")
        else:
            stroke_color = PALETTE[pen_choice]
            st.color_picker("Selected", stroke_color,
                            key="pen_shown_color", disabled=True)
    with tcol3:
        stroke_width = st.slider("Pen width", 1, 20, 2, key="stroke_width")
    with tcol4:
        tool = st.radio("Tool", ["Pen", "Eraser"],
                        horizontal=False, key="draw_tool")

    if tool == "Eraser":
        eraser_size = st.slider("Eraser size", 5, 60, 20, key="eraser_size")
        drawing_mode = "eraser"
        stroke_width = eraser_size
        stroke_color = "#000000"
    else:
        drawing_mode = "freedraw"

    # Canvas key trick: change key to clear the canvas
    if "canvas_key_suffix" not in st.session_state:
        st.session_state.canvas_key_suffix = 0

    if full_screen:
        canvas_h = 900
        canvas_w = 1600
    else:
        canvas_h = 300
        canvas_w = 800

    canvas_result = st_canvas(
        fill_color="rgba(255, 165, 0, 0.0)",
        stroke_width=stroke_width,
        stroke_color=stroke_color,
        background_color="#FFFFFF",
        height=canvas_h,
        width=canvas_w,
        drawing_mode=drawing_mode,
        key="handwritten_canvas_" + str(st.session_state.canvas_key_suffix),
        update_streamlit=True,
    )

    # ---- Toolbar buttons ----
    b1, b2, b3, b4 = st.columns(4)

    with b1:
        if st.button("Save handwriting", use_container_width=True):
            arr = canvas_result.image_data
            has_ink = False
            if arr is not None and arr.ndim == 3 and arr.shape[2] == 4:
                has_ink = bool((arr[..., 3] > 0).any())
            if has_ink:
                st.session_state.handwritten_notes = canvas_to_b64_png(arr)
                st.success("Handwriting captured. Click 'Save All' to persist.")
            else:
                st.warning("Draw something first!")

    with b2:
        if st.button("Clear canvas", use_container_width=True):
            st.session_state.canvas_key_suffix += 1
            st.session_state.handwritten_notes = None
            st.rerun()

    with b3:
        if st.button("Undo last stroke", use_container_width=True,
                     help="Clears the canvas (fastest reliable undo)."):
            st.session_state.canvas_key_suffix += 1
            st.rerun()

    with b4:
        # Use on_click so the state change happens before widget creation.
        st.button(
            "Exit full-screen" if full_screen else "Enter full-screen",
            use_container_width=True,
            on_click=_toggle_fullscreen,
        )

    # ---- Preview of captured handwriting ----
    if st.session_state.get("handwritten_notes"):
        st.caption("Preview of captured handwriting:")
        st.image(st.session_state.handwritten_notes, use_container_width=True)

    # ---- Save all notes ----
    if st.button("Save All Counselling Notes", type="primary"):
        hw = st.session_state.get("handwritten_notes", "")
        if hw is None:
            hw = ""
        elif not isinstance(hw, str):
            hw = canvas_to_b64_png(hw)

        conn = get_conn()
        conn.execute(
            "INSERT INTO counselling_notes ("
            "patient_name, age, sex, date, counselling_symptoms, important_notes, "
            "handwritten_notes, timestamp"
            ") VALUES (?,?,?,?,?,?,?,?)",
            (
                st.session_state.note_name or st.session_state.get("patient_name", "Unknown"),
                str(st.session_state.note_age),
                st.session_state.note_sex,
                str(st.session_state.note_date),
                st.session_state.counselling_symptoms,
                st.session_state.important_notes,
                hw,
                str(datetime.now()),
            ),
        )
        conn.commit()
        conn.close()
        st.success("All notes saved!")

    # ---- Saved notes ----
    st.subheader("Saved Counselling Notes")
    conn = get_conn()
    notes = conn.execute(
        "SELECT id, patient_name, date, counselling_symptoms, important_notes, "
        "handwritten_notes, timestamp FROM counselling_notes "
        "ORDER BY timestamp DESC"
    ).fetchall()
    conn.close()

    if notes:
        for n in notes[:10]:
            header = str(n[1]) + " - " + str(n[2])
            with st.expander(header):
                st.markdown("**Counselling Symptoms / Issues:**")
                st.write(n[3] or "-")
                st.markdown("**Important Notes / Follow-up Reminders:**")
                st.write(n[4] or "-")
                if n[5]:
                    st.markdown("**Handwritten notes:**")
                    st.image(n[5], use_container_width=True)
                st.caption("Saved: " + str(n[6]))
    else:
        st.info("No notes saved yet.")


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
if page == "Report":
    st.title("Clinical Report")
    rep = st.session_state.get("current_report")
    ai = st.session_state.get("current_ai")

    if rep:
        st.code(rep, language="text")
        if ai:
            st.markdown(ai)
        st.download_button(
            "Download Report (txt)",
            rep,
            file_name="report_" + str(date.today()) + ".txt",
            mime="text/plain",
        )
    else:
        st.info("No report yet. Run an Assessment first.")

    st.divider()
    st.subheader("Past Reports")
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, patient_name, syndrome, severity, risk_level, timestamp "
        "FROM assessments ORDER BY id DESC LIMIT 25"
    ).fetchall()
    conn.close()

    if rows:
        for r in rows:
            with st.expander("#" + str(r[0]) + " - " + str(r[1]) + " - "
                             + str(r[2]) + " (" + str(r[4]) + ") - "
                             + str(r[5])[:16]):
                conn = get_conn()
                full = conn.execute(
                    "SELECT report_text, ai_insights FROM assessments WHERE id=?",
                    (r[0],),
                ).fetchone()
                conn.close()
                if full:
                    st.code(full[0] or "", language="text")
                    if full[1]:
                        st.markdown(full[1])
    else:
        st.info("No past assessments found.")


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------
if page == "Chat":
    st.title("Clinical Chat Assistant")
    st.caption("Decision support only - not a substitute for clinical judgement.")

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
        a = chatbot_reply(q)
        st.session_state.chat_history.append(("assistant", a))
        with st.chat_message("assistant"):
            st.write(a)


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------
if page == "History":
    st.title("Assessment History")
    conn = get_conn()
    df = pd.read_sql_query(
        "SELECT id, patient_name, age, sex, syndrome, severity, risk_level, "
        "organic_level, symptom_weight, timestamp FROM assessments ORDER BY id DESC",
        conn,
    )
    conn.close()

    if df.empty:
        st.info("No assessments recorded yet.")
    else:
        st.dataframe(df, use_container_width=True)
        sel = st.selectbox("Open assessment by ID", df["id"].tolist())
        if sel:
            conn = get_conn()
            row = conn.execute(
                "SELECT report_text, ai_insights FROM assessments WHERE id=?",
                (int(sel),),
            ).fetchone()
            conn.close()
            if row:
                st.code(row[0] or "", language="text")
                if row[1]:
                    st.markdown(row[1])


# ---------------------------------------------------------------------------
# Patient Database
# ---------------------------------------------------------------------------
if page == "Patient Database":
    st.title("Patient Database")
    conn = get_conn()
    df = pd.read_sql_query(
        "SELECT id, name, age, sex, phone, first_seen, last_seen "
        "FROM patients ORDER BY last_seen DESC",
        conn,
    )
    conn.close()

    if df.empty:
        st.info("No patients yet. Save an assessment to create a patient record.")
    else:
        st.dataframe(df, use_container_width=True)
        pat = st.selectbox("Select patient", df["name"].tolist())
        if pat:
            c1, c2, c3 = st.columns(3)
            conn = get_conn()
            with c1:
                st.subheader("Assessments")
                a = pd.read_sql_query(
                    "SELECT id, syndrome, severity, risk_level, timestamp "
                    "FROM assessments WHERE patient_name=? ORDER BY id DESC",
                    conn, params=(pat,),
                )
                st.dataframe(a, use_container_width=True)
            with c2:
                st.subheader("Counselling Notes")
                n = pd.read_sql_query(
                    "SELECT id, date, counselling_symptoms "
                    "FROM counselling_notes WHERE patient_name=? ORDER BY id DESC",
                    conn, params=(pat,),
                )
                st.dataframe(n, use_container_width=True)
            with c3:
                st.subheader("Follow-ups")
                f = pd.read_sql_query(
                    "SELECT id, follow_up_date, status "
                    "FROM follow_ups WHERE patient_name=? ORDER BY id DESC",
                    conn, params=(pat,),
                )
                st.dataframe(f, use_container_width=True)
            conn.close()


# ---------------------------------------------------------------------------
# Follow-up
# ---------------------------------------------------------------------------
if page == "Follow-up":
    st.title("Follow-up")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Schedule Follow-up")
        fu_name = st.text_input(
            "Patient Name", value=st.session_state.get("patient_name", ""),
            key="fu_name",
        )
        fu_date = st.date_input("Follow-up date", value=date.today(), key="fu_date")
        fu_notes = st.text_area("Notes", height=100, key="fu_notes")
        if st.button("Schedule"):
            if fu_name.strip():
                conn = get_conn()
                conn.execute(
                    "INSERT INTO follow_ups (patient_name, follow_up_date, status, notes, created_at) "
                    "VALUES (?,?,?,?,?)",
                    (fu_name.strip(), str(fu_date), "Scheduled", fu_notes,
                     str(datetime.now())),
                )
                conn.commit()
                conn.close()
                st.success("Follow-up scheduled.")
                st.rerun()
            else:
                st.warning("Enter patient name.")

    with col2:
        st.subheader("Complete Follow-up")
        conn = get_conn()
        pending = conn.execute(
            "SELECT id, patient_name, follow_up_date FROM follow_ups "
            "WHERE status='Scheduled' ORDER BY follow_up_date"
        ).fetchall()
        conn.close()

        if pending:
            labels = ["#" + str(r[0]) + " - " + str(r[1]) + " - " + str(r[2])
                      for r in pending]
            opt = st.selectbox("Pending follow-ups", labels)
            fu_id = pending[labels.index(opt)][0]

            improved = st.radio("Symptoms improved?", ["Yes", "Partially", "No"],
                                horizontal=True, key="fu_improved")
            adherence = st.selectbox("Adherence", ["Good", "Partial", "Poor"],
                                     key="fu_adh")
            se = st.text_input("Side effects", key="fu_se")
            gi = st.selectbox("Global impression",
                              ["Much improved", "Improved", "No change", "Worse"],
                              key="fu_gi")

            if st.button("Mark complete"):
                conn = get_conn()
                conn.execute(
                    "UPDATE follow_ups SET status='Completed', symptoms_improved=?, "
                    "adherence=?, side_effects=?, global_impression=?, completed_at=? "
                    "WHERE id=?",
                    (improved, adherence, se, gi, str(datetime.now()), fu_id),
                )
                conn.commit()
                conn.close()
                st.success("Follow-up recorded.")
                st.rerun()
        else:
            st.info("No scheduled follow-ups.")

    st.divider()
    st.subheader("All Follow-ups")
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM follow_ups ORDER BY id DESC", conn)
    conn.close()
    st.dataframe(df, use_container_width=True)


# ---------------------------------------------------------------------------
# Epidemiology
# ---------------------------------------------------------------------------
if page == "Epidemiology":
    st.title("Epidemiology (local DB)")
    conn = get_conn()
    df = pd.read_sql_query(
        "SELECT syndrome, severity, risk_level, age, sex FROM assessments", conn
    )
    conn.close()

    if df.empty:
        st.info("No data yet.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("By syndrome")
            st.bar_chart(df["syndrome"].value_counts())
            st.subheader("By severity")
            st.bar_chart(df["severity"].value_counts())
        with c2:
            st.subheader("By risk level")
            st.bar_chart(df["risk_level"].value_counts())
            st.subheader("By sex")
            st.bar_chart(df["sex"].value_counts())


# ---------------------------------------------------------------------------
# Export Data
# ---------------------------------------------------------------------------
if page == "Export Data":
    st.title("Export Data")
    tables = ["assessments", "treatments", "phq9_scores", "gad7_scores",
              "adhd_scores", "counselling_notes", "follow_ups", "patients"]
    conn = get_conn()
    for t in tables:
        try:
            df = pd.read_sql_query("SELECT * FROM " + t, conn)
        except Exception:
            continue
        st.subheader(t)
        st.write(str(len(df)) + " rows")
        st.download_button(
            "Download " + t + ".csv",
            df.to_csv(index=False).encode("utf-8"),
            file_name=t + "_" + str(date.today()) + ".csv",
            mime="text/csv",
            key="dl_" + t,
        )
    conn.close()


# ---------------------------------------------------------------------------
# End of file
# ---------------------------------------------------------------------------
