"""
PsychAssist Web v4 - Clinical Decision Support (Streamlit)
Includes: Assessment, PHQ-9, GAD-7, Treatments, Chatbot,
Epidemiology, Patient Database, Follow-up routine, Export.
Decision support only - not a diagnosis.
"""

import streamlit as st
import sqlite3
from datetime import datetime, date, timedelta
import json
import random
import csv
import io
import zipfile

st.set_page_config(
    page_title="PsychAssist Web",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

DB_PATH = "psychassist_web.db"

def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS assessments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_name TEXT, age TEXT, sex TEXT, symptoms TEXT, syndrome TEXT,
        severity TEXT, risk_level TEXT, formal_diagnoses TEXT,
        organic_level TEXT, organic_score INTEGER, functional_impairment TEXT,
        mse TEXT, duration TEXT, onset TEXT, pattern TEXT,
        speech TEXT, affect TEXT, thought_process TEXT, insight TEXT, judgment TEXT,
        substance_use TEXT, neuro_findings TEXT,
        report_text TEXT, ai_insights TEXT,
        mdd_criteria TEXT, mania_criteria TEXT, schizophrenia_criteria TEXT, delirium_criteria TEXT,
        mixed_features INTEGER, symptom_weight REAL,
        phq9_score INTEGER, gad7_score INTEGER, timestamp TEXT
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS treatments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_name TEXT, medication_name TEXT, medication_class TEXT,
        dose TEXT, frequency TEXT, route TEXT, start_date TEXT, end_date TEXT,
        status TEXT, adherence TEXT, side_effects TEXT, psychotherapy TEXT,
        reason_start TEXT, reason_stop TEXT, notes TEXT, timestamp TEXT
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS phq9_scores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_name TEXT, total_score INTEGER, severity TEXT, answers TEXT, timestamp TEXT
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS gad7_scores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_name TEXT, total_score INTEGER, severity TEXT, answers TEXT, timestamp TEXT
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS follow_ups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_name TEXT, assessment_id INTEGER, follow_up_date TEXT,
        status TEXT, notes TEXT, symptoms_improved TEXT, adherence TEXT,
        side_effects TEXT, global_impression TEXT, created_at TEXT, completed_at TEXT
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS patients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE, age TEXT, sex TEXT, phone TEXT, notes TEXT,
        first_seen TEXT, last_seen TEXT, created_at TEXT
    )
    """)
    conn.commit()
    conn.close()

init_db()

# ========== DATA ==========
symptom_categories = {
    "Mood Symptoms": ["Low mood", "Anhedonia", "Fatigue", "Hopelessness", "Excessive guilt", "Suicidal thoughts", "Sleep disturbance", "Irritability"],
    "Mania Symptoms": ["Reduced sleep", "Increased energy", "Grandiosity", "Pressured speech", "Racing thoughts", "Risk-taking behavior", "Distractibility"],
    "Psychotic Symptoms": ["Auditory hallucinations", "Visual hallucinations", "Delusions", "Paranoia", "Thought broadcasting", "Disorganized speech", "Negative symptoms"],
    "Anxiety Symptoms": ["Panic attacks", "Excessive worry", "Palpitations", "Sweating", "Tremor", "Avoidance behavior", "Fear of dying"],
    "OCD Symptoms": ["Obsessions", "Compulsions"],
    "Trauma Symptoms": ["Flashbacks", "Nightmares", "Hypervigilance"],
    "Cognitive Symptoms": ["Memory loss", "Confusion", "Disorientation", "Fluctuating attention", "Personality change", "Poor concentration"],
    "Neurological Symptoms": ["Seizure", "Weakness", "Tremor (neurological)", "Gait disturbance", "Headache", "Loss of consciousness"],
    "Behavioral Symptoms": ["Aggression", "Self-harm", "Catatonia", "Social withdrawal"]
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
    "Negative symptoms": 0.15, "Poor concentration": 0.10
}

medication_database = {
    "Major Depressive Disorder": {
        "first_line": [
            {"name": "Sertraline", "class": "SSRI", "starting_dose": "50mg", "max_dose": "200mg", "side_effects": "Nausea, headache, insomnia, sexual dysfunction", "contraindications": "MAOIs within 14 days"},
            {"name": "Escitalopram", "class": "SSRI", "starting_dose": "10mg", "max_dose": "20mg", "side_effects": "Nausea, fatigue, insomnia, sexual dysfunction", "contraindications": "MAOIs, pimozide"},
            {"name": "Fluoxetine", "class": "SSRI", "starting_dose": "20mg", "max_dose": "80mg", "side_effects": "Nervousness, anxiety, insomnia, weight changes", "contraindications": "MAOIs, thioridazine"}
        ],
        "second_line": [{"name": "Bupropion", "class": "NDRI", "starting_dose": "150mg", "max_dose": "300mg", "side_effects": "Agitation, dry mouth, insomnia", "contraindications": "Seizure disorder, eating disorders"}],
        "augmentation": [{"name": "Aripiprazole", "class": "Atypical Antipsychotic", "starting_dose": "2-5mg", "max_dose": "15mg", "side_effects": "Akathisia, weight gain", "contraindications": "Hypersensitivity"}]
    },
    "Bipolar I Disorder - Manic Episode": {
        "first_line": [
            {"name": "Lithium", "class": "Mood Stabilizer", "starting_dose": "300mg", "max_dose": "1800mg", "side_effects": "Tremor, polydipsia, polyuria", "contraindications": "Severe renal disease"},
            {"name": "Valproate", "class": "Anticonvulsant", "starting_dose": "250mg", "max_dose": "60mg/kg", "side_effects": "Sedation, tremor, weight gain", "contraindications": "Hepatic disease, pregnancy"}
        ],
        "second_line": [{"name": "Olanzapine", "class": "Atypical Antipsychotic", "starting_dose": "10mg", "max_dose": "20mg", "side_effects": "Weight gain, metabolic syndrome", "contraindications": "Dementia-related psychosis"}]
    },
    "Schizophrenia Spectrum Disorder": {
        "first_line": [
            {"name": "Risperidone", "class": "Atypical Antipsychotic", "starting_dose": "2mg", "max_dose": "8mg", "side_effects": "EPS, weight gain", "contraindications": "Hypersensitivity"},
            {"name": "Aripiprazole", "class": "Atypical Antipsychotic", "starting_dose": "10mg", "max_dose": "30mg", "side_effects": "Akathisia, insomnia", "contraindications": "Hypersensitivity"}
        ]
    },
    "Delirium": {
        "first_line": [{"name": "Haloperidol", "class": "Typical Antipsychotic", "starting_dose": "0.5mg", "max_dose": "5mg", "side_effects": "EPS, QT prolongation", "contraindications": "Parkinson's disease"}]
    },
    "Generalized Anxiety Disorder": {
        "first_line": [{"name": "Sertraline", "class": "SSRI", "starting_dose": "25mg", "max_dose": "200mg", "side_effects": "Nausea, insomnia", "contraindications": "MAOIs"}]
    }
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
    "Thoughts that you would be better off dead or of hurting yourself"
]
GAD7_QUESTIONS = [
    "Feeling nervous, anxious, or on edge",
    "Not being able to stop or control worrying",
    "Worrying too much about different things",
    "Trouble relaxing",
    "Being so restless that it is hard to sit still",
    "Becoming easily annoyed or irritable",
    "Feeling afraid as if something awful might happen"
]
OPTIONS = ["Not at all (0)", "Several days (1)", "More than half the days (2)", "Nearly every day (3)"]

CHATBOT = {
    "depression": ["Major depression typically requires 4-6 weeks of antidepressant treatment for full response.", "SSRIs are common first-line options.", "CBT is highly effective for depression.", "Monitor suicidal ideation early in treatment."],
    "mania": ["Lithium therapeutic range usually 0.6-1.2 mEq/L.", "Valproate needs liver monitoring.", "Sleep deprivation can trigger mania.", "Avoid antidepressants in acute mania."],
    "psychosis": ["Early intervention improves outcomes.", "Clozapine for treatment-resistant schizophrenia.", "Metabolic monitoring with atypicals is essential."],
    "delirium": ["Delirium is often reversible if cause is treated.", "Common causes: infection, meds, metabolic issues.", "Non-drug measures first."],
    "risk": ["Repeat suicide risk assessment each visit.", "Safety plans: triggers, coping, contacts.", "Remove access to lethal means when high risk."],
    "medication": ["Start low, go slow.", "Full response may take 4-8 weeks.", "Check drug interactions."],
    "phq9": ["PHQ-9: 5-9 Mild, 10-14 Moderate, 15-19 Moderately severe, 20+ Severe.", "Score >=10 usually needs treatment."],
    "gad7": ["GAD-7: 5-9 Mild, 10-14 Moderate, 15+ Severe.", "Score >=10 suggests clinically significant anxiety."]
}
GENERAL = ["This is decision support only. Verify with guidelines.", "Document clinical reasoning.", "Regular follow-up is essential."]

def chatbot_reply(q):
    q = q.lower()
    km = {"depression":"depression","depressive":"depression","mdd":"depression","phq":"phq9","mania":"mania","bipolar":"mania","psychosis":"psychosis","schizophrenia":"psychosis","delirium":"delirium","risk":"risk","suicide":"risk","medication":"medication","drug":"medication","gad":"gad7","anxiety":"gad7"}
    for k, cat in km.items():
        if k in q: return random.choice(CHATBOT.get(cat, GENERAL))
    return random.choice(GENERAL)

# ========== CLINICAL LOGIC ==========
def has_s(selected, s): return s in selected

def severity_grader(score):
    if score <= 5: return "Mild"
    if score <= 12: return "Moderate"
    if score <= 20: return "Severe"
    return "Very Severe"

def normalize_scores(d):
    t = sum(d.values())
    if t == 0: return d
    return {k: round((v/t)*100, 2) for k, v in d.items()}

def depressive_logic(selected, duration, affect):
    if not (has_s(selected, "Low mood") or has_s(selected, "Anhedonia")): return 0
    score = 12
    for s in ["Fatigue","Hopelessness","Excessive guilt","Suicidal thoughts","Sleep disturbance","Poor concentration"]:
        if has_s(selected, s): score += 2
    if sum(1 for s in ["Grandiosity","Increased energy","Reduced sleep"] if has_s(selected, s)) >= 2: score -= 8
    if duration in ["Weeks","Months"]: score += 2
    if affect == "Depressed": score += 3
    return max(score, 0)

def mania_logic(selected, duration, speech, thought):
    if not (has_s(selected, "Reduced sleep") and has_s(selected, "Increased energy")): return 0
    score = 12
    for s in ["Grandiosity","Pressured speech","Racing thoughts","Risk-taking behavior","Distractibility"]:
        if has_s(selected, s): score += 2
    if duration in ["Days","Weeks"]: score += 2
    if speech == "Pressured": score += 3
    if thought == "Flight of ideas": score += 3
    return max(score, 0)

def psychosis_logic(selected, duration, speech, thought):
    if not (has_s(selected,"Auditory hallucinations") or has_s(selected,"Visual hallucinations") or has_s(selected,"Delusions")): return 0
    score = 12
    for s in ["Paranoia","Disorganized speech","Negative symptoms"]:
        if has_s(selected, s): score += 2
    if duration in ["Months","Years"]: score += 3
    if speech == "Disorganized": score += 3
    if thought == "Disorganized": score += 4
    return max(score, 0)

def delirium_logic(selected, duration, onset, fluctuating):
    if not (has_s(selected,"Confusion") and has_s(selected,"Disorientation")): return 0
    score = 15
    if has_s(selected,"Fluctuating attention") or has_s(selected,"Visual hallucinations"): score += 3
    if duration in ["Hours","Days"]: score += 5
    if onset == "Sudden": score += 4
    if fluctuating: score += 4
    return max(score, 0)

def diagnose_mdd(selected, duration, impairment):
    cnt = sum(1 for s in ["Low mood","Anhedonia","Fatigue","Hopelessness","Excessive guilt","Suicidal thoughts","Sleep disturbance","Poor concentration"] if has_s(selected, s))
    core = has_s(selected,"Low mood") or has_s(selected,"Anhedonia")
    no_mania = not (has_s(selected,"Grandiosity") or has_s(selected,"Increased energy"))
    if cnt >= 5 and core and no_mania and duration in ["Weeks","Months"] and impairment != "None reported":
        return {"diagnosis":"Major Depressive Disorder","status":"CRITERIA FULLY MET","confidence":"HIGH"}
    if cnt >= 3:
        return {"diagnosis":"Major Depressive Disorder","status":"PARTIAL CRITERIA","confidence":"MODERATE"}
    return None

def diagnose_mania(selected, duration):
    cnt = sum(1 for s in ["Reduced sleep","Increased energy","Grandiosity","Pressured speech","Racing thoughts","Risk-taking behavior","Distractibility"] if has_s(selected, s))
    if cnt >= 4 and has_s(selected,"Reduced sleep") and has_s(selected,"Increased energy") and duration in ["Days","Weeks"]:
        return {"diagnosis":"Bipolar I Disorder - Manic Episode","status":"CRITERIA FULLY MET","confidence":"HIGH"}
    return None

def diagnose_schizophrenia(selected, duration):
    core = has_s(selected,"Delusions") or has_s(selected,"Auditory hallucinations")
    cnt = sum(1 for s in ["Auditory hallucinations","Visual hallucinations","Delusions","Paranoia","Disorganized speech","Negative symptoms"] if has_s(selected, s))
    if core and cnt >= 2 and duration in ["Months","Years"]:
        return {"diagnosis":"Schizophrenia Spectrum Disorder","status":"CRITERIA FULLY MET","confidence":"HIGH"}
    return None

def diagnose_delirium(selected, duration, fluctuating):
    if has_s(selected,"Confusion") and has_s(selected,"Disorientation") and (has_s(selected,"Fluctuating attention") or fluctuating) and duration in ["Hours","Days"]:
        return {"diagnosis":"Delirium","status":"CRITERIA FULLY MET","confidence":"HIGH"}
    return None

def organic_psychosis_detector(selected, onset, fluctuating, seizure, focal, head_injury):
    score = 0
    if has_s(selected,"Visual hallucinations"): score += 3
    if has_s(selected,"Confusion"): score += 4
    if fluctuating: score += 4
    if seizure: score += 4
    if focal: score += 5
    if onset == "Sudden": score += 3
    if head_injury: score += 4
    if score >= 15: level = "VERY HIGH suspicion of organic psychosis"
    elif score >= 10: level = "HIGH suspicion of organic psychosis"
    elif score >= 6: level = "MODERATE suspicion of organic psychosis"
    else: level = "LOW suspicion of organic psychosis"
    return level, score

def risk_assessment(selected, suicide_plan, command_hall, violent, access_means):
    score = 0
    if has_s(selected,"Suicidal thoughts"): score += 3
    if suicide_plan: score += 6
    if command_hall: score += 6
    if violent: score += 5
    if access_means: score += 4
    if score >= 15: return "CRITICAL RISK", "IMMEDIATE HOSPITALIZATION REQUIRED", score
    if score >= 10: return "HIGH RISK", "URGENT psychiatric consultation required", score
    if score >= 5: return "MODERATE RISK", "Enhanced monitoring required", score
    return "LOW RISK", "Routine monitoring", score

def mixed_features_detector(selected):
    dep = sum(1 for s in ["Low mood","Anhedonia","Hopelessness","Excessive guilt","Suicidal thoughts"] if has_s(selected, s))
    man = sum(1 for s in ["Reduced sleep","Increased energy","Grandiosity","Pressured speech","Racing thoughts"] if has_s(selected, s))
    return dep >= 3 and man >= 3

def calculate_symptom_weight(selected):
    return round(sum(symptom_weights.get(s, 0) for s in selected if s in symptom_weights), 2)

def generate_mse(speech, affect, thought, insight, judgment):
    sm = {"Normal":"normal rate and rhythm","Pressured":"rapid, difficult to interrupt","Slow":"reduced rate","Disorganized":"disorganized"}
    am = {"Normal":"full range","Flat":"severely reduced","Depressed":"sad, discouraged","Labile":"rapidly changing"}
    tm = {"Normal":"logical and goal-directed","Tangential":"off-topic","Disorganized":"illogical","Flight of ideas":"rapid shifts"}
    im = {"Good":"excellent awareness","Partial":"partial recognition","Poor":"limited awareness"}
    jm = {"Good":"intact","Fair":"mildly impaired","Poor":"moderately impaired","Impaired":"markedly impaired"}
    return f"Speech: {sm.get(speech,'normal')}. Affect: {am.get(affect,'normal')}. Thought: {tm.get(thought,'normal')}. Insight: {im.get(insight,'good')}. Judgment: {jm.get(judgment,'intact')}."

def generate_ai_insights(top, severity, risk_level, formal):
    lines = [f"### Clinical Overview\nPrimary presentation: **{top}** ({severity.lower()} severity)."]
    if formal:
        names = [d["diagnosis"] for d in formal if d.get("status")=="CRITERIA FULLY MET"]
        if names:
            lines.append(f"\n### Criteria\nMeets criteria for: **{', '.join(names)}** (decision support only).")
    lines.append("\n### Risk")
    if "HIGH" in risk_level or "CRITICAL" in risk_level:
        lines.append("High/critical risk - do not leave unattended; remove means; emergency services; consider admission.")
    elif "MODERATE" in risk_level:
        lines.append("Moderate risk - enhanced monitoring and safety planning.")
    else:
        lines.append("Low risk - routine monitoring.")
    lines.append(f"\n### Notes - {top}")
    edu = {
        "Depressive Syndrome": ["SSRIs + CBT first-line.", "Monitor suicide risk early in treatment.", "Rule out medical causes."],
        "Manic Syndrome": ["Lithium/valproate first-line.", "Avoid antidepressants in acute mania.", "Monitor levels/LFTs."],
        "Psychotic Syndrome": ["Antipsychotics first-line.", "Early intervention improves outcomes.", "Rule out substance/medical causes."],
        "Delirium Syndrome": ["Medical emergency - treat cause.", "Non-pharm measures first.", "Haloperidol only if severe agitation."]
    }
    for x in edu.get(top, ["Correlate with full clinical assessment."]):
        lines.append(f"- {x}")
    lines.append("\n### Follow-up\nReassess 1-2 weeks; monitor adherence/side effects; recheck risk each visit.")
    return "\n".join(lines)

def phq9_severity(score):
    if score <= 4: return "None-Minimal"
    if score <= 9: return "Mild"
    if score <= 14: return "Moderate"
    if score <= 19: return "Moderately Severe"
    return "Severe"

def gad7_severity(score):
    if score <= 4: return "Minimal"
    if score <= 9: return "Mild"
    if score <= 14: return "Moderate"
    return "Severe"

def upsert_patient(name, age, sex):
    if not name or not name.strip(): return
    conn = get_conn()
    c = conn.cursor()
    now = str(datetime.now())
    c.execute("SELECT id FROM patients WHERE name = ?", (name.strip(),))
    row = c.fetchone()
    if row:
        c.execute("UPDATE patients SET age=?, sex=?, last_seen=? WHERE name=?", (age, sex, now, name.strip()))
    else:
        c.execute("INSERT INTO patients (name, age, sex, first_seen, last_seen, created_at) VALUES (?,?,?,?,?,?)",
                  (name.strip(), age, sex, now, now, now))
    conn.commit()
    conn.close()

# ========== SIDEBAR ==========
st.sidebar.title("🧠 PsychAssist Web")
st.sidebar.caption("Decision support only - not a diagnosis")
page = st.sidebar.radio(
    "Navigation",
    ["New Assessment", "PHQ-9", "GAD-7", "Treatment Tracker", "Follow-up",
     "Patient Database", "Epidemiology", "Export Data", "Chatbot", "History", "About"],
    index=0
)
st.sidebar.markdown("---")
st.sidebar.info("Chrome → Add to Home screen for app-like use on Android.")

# ========== NEW ASSESSMENT ==========
if page == "New Assessment":
    st.title("🧠 Clinical Assessment")
    with st.expander("📋 Patient Information", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1: patient_name = st.text_input("Name", placeholder="Patient name")
        with c2: age = st.text_input("Age", placeholder="e.g. 34")
        with c3: sex = st.selectbox("Sex", ["", "Male", "Female", "Other"])

    with st.expander("⏱️ Clinical Course", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            duration_unit = st.selectbox("Duration unit", ["Hours", "Days", "Weeks", "Months", "Years"])
            duration_number = st.text_input("Duration number", value="1")
        with c2:
            onset = st.selectbox("Onset", ["Sudden", "Gradual"])
            pattern = st.selectbox("Pattern", ["Not specified", "Episodic", "Chronic", "Fluctuating"])
        with c3:
            previous_episodes = st.checkbox("Previous similar episodes")

    with st.expander("📊 Functional Impairment"):
        occupational = st.checkbox("Occupational dysfunction")
        social = st.checkbox("Social dysfunction")
        selfcare = st.checkbox("Self-care impairment")

    with st.expander("🧠 Mental Status Exam"):
        c1, c2 = st.columns(2)
        with c1:
            speech = st.selectbox("Speech", ["Normal", "Pressured", "Slow", "Disorganized"])
            affect = st.selectbox("Affect", ["Normal", "Flat", "Depressed", "Labile"])
            thought = st.selectbox("Thought Process", ["Normal", "Tangential", "Disorganized", "Flight of ideas"])
        with c2:
            insight = st.selectbox("Insight", ["Good", "Partial", "Poor"])
            judgment = st.selectbox("Judgment", ["Good", "Fair", "Poor", "Impaired"])

    with st.expander("🍺 Substance Use"):
        c1, c2, c3 = st.columns(3)
        with c1:
            alcohol = st.checkbox("Alcohol")
            cannabis = st.checkbox("Cannabis")
        with c2:
            stimulants = st.checkbox("Stimulants")
            opioids = st.checkbox("Opioids")
        with c3:
            withdrawal = st.checkbox("Withdrawal")
            polysubstance = st.checkbox("Polysubstance")

    with st.expander("🧠 Neuropsychiatric"):
        c1, c2 = st.columns(2)
        with c1:
            head_injury = st.checkbox("Head injury")
            fluctuating_cognition = st.checkbox("Fluctuating cognition")
            executive = st.checkbox("Executive dysfunction")
            parkinson = st.checkbox("Parkinsonian features")
        with c2:
            focal_deficit = st.checkbox("Focal deficit")
            seizure_disorder = st.checkbox("Seizure disorder")
            stroke = st.checkbox("Stroke")

    with st.expander("⚡ Risk Assessment", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            suicide_plan = st.checkbox("Active suicidal plan/intent")
            command_hallucination = st.checkbox("Command hallucinations")
            violent = st.checkbox("Violent behavior")
        with c2:
            neglect = st.checkbox("Self-neglect")
            impulsive = st.checkbox("Impulsivity")
            access_means = st.checkbox("Access to means")

    with st.expander("📋 Symptoms", expanded=True):
        selected_symptoms = []
        for category, symptoms in symptom_categories.items():
            st.markdown(f"**{category}**")
            cols = st.columns(2)
            for i, symptom in enumerate(symptoms):
                with cols[i % 2]:
                    if st.checkbox(symptom, key=f"sym_{symptom}"):
                        selected_symptoms.append(symptom)

    with st.expander("📅 Schedule Follow-up (optional)"):
        schedule_fu = st.checkbox("Create follow-up after this assessment")
        fu_days = st.number_input("Follow-up in (days)", min_value=1, max_value=365, value=14) if schedule_fu else 14

    if st.button("🧠 Generate Clinical Report", type="primary", use_container_width=True):
        if not selected_symptoms:
            st.warning("Select at least one symptom.")
            st.stop()

        impairment_list = []
        if occupational: impairment_list.append("Occupational")
        if social: impairment_list.append("Social")
        if selfcare: impairment_list.append("Self-care")
        functional_impairment = ", ".join(impairment_list) if impairment_list else "None reported"

        scores = {
            "Depressive Syndrome": depressive_logic(selected_symptoms, duration_unit, affect),
            "Manic Syndrome": mania_logic(selected_symptoms, duration_unit, speech, thought),
            "Psychotic Syndrome": psychosis_logic(selected_symptoms, duration_unit, speech, thought),
            "Delirium Syndrome": delirium_logic(selected_symptoms, duration_unit, onset, fluctuating_cognition)
        }
        if cannabis or stimulants: scores["Psychotic Syndrome"] = scores.get("Psychotic Syndrome", 0) + 4
        if stimulants: scores["Manic Syndrome"] = scores.get("Manic Syndrome", 0) + 3
        if alcohol and withdrawal: scores["Delirium Syndrome"] = scores.get("Delirium Syndrome", 0) + 6
        if fluctuating_cognition: scores["Delirium Syndrome"] = scores.get("Delirium Syndrome", 0) + 5

        filtered = {k: v for k, v in scores.items() if v > 0}
        if not filtered:
            st.warning("No matching syndrome pattern.")
            st.stop()

        probs = normalize_scores(filtered)
        top_syndrome = max(filtered, key=filtered.get)
        severity = severity_grader(filtered[top_syndrome])
        risk_level, risk_rec, risk_score = risk_assessment(selected_symptoms, suicide_plan, command_hallucination, violent, access_means)
        organic_level, organic_score = organic_psychosis_detector(selected_symptoms, onset, fluctuating_cognition, seizure_disorder, focal_deficit, head_injury)
        mixed = mixed_features_detector(selected_symptoms)
        ml_weight = calculate_symptom_weight(selected_symptoms)

        formal = []
        mdd = diagnose_mdd(selected_symptoms, duration_unit, functional_impairment)
        if mdd: formal.append(mdd)
        mania = diagnose_mania(selected_symptoms, duration_unit)
        if mania: formal.append(mania)
        schiz = diagnose_schizophrenia(selected_symptoms, duration_unit)
        if schiz: formal.append(schiz)
        deli = diagnose_delirium(selected_symptoms, duration_unit, fluctuating_cognition)
        if deli: formal.append(deli)
        if any("Delirium" in d["diagnosis"] for d in formal):
            formal = [d for d in formal if "Schizophrenia" not in d["diagnosis"]]

        mse_text = generate_mse(speech, affect, thought, insight, judgment)
        primary_dx = formal[0]["diagnosis"] if formal else top_syndrome
        icd_code = icd11_codes.get(primary_dx, "N/A")

        if has_s(selected_symptoms, "Suicidal thoughts") and suicide_plan:
            st.error("PSYCHIATRIC EMERGENCY - Active suicidal plan. Do not leave alone. Seek emergency care now.")

        substances = [x for x, f in [("Alcohol",alcohol),("Cannabis",cannabis),("Stimulants",stimulants),("Opioids",opioids),("Withdrawal",withdrawal),("Polysubstance",polysubstance)] if f]
        sub_text = ", ".join(substances) if substances else "None"
        neuro_list = [x for x, f in [("Head injury",head_injury),("Fluctuating cognition",fluctuating_cognition),("Executive",executive),("Parkinsonian",parkinson),("Focal deficit",focal_deficit),("Seizure",seizure_disorder),("Stroke",stroke)] if f]
        neuro_text = ", ".join(neuro_list) if neuro_list else "None"

        report = f"""════════════════════════════════════════
PSYCHASSIST CLINICAL REPORT
Decision Support - Not a Diagnosis
════════════════════════════════════════
PATIENT: {patient_name or 'N/A'} | Age: {age or '-'} | Sex: {sex or '-'}
Date: {datetime.now().strftime('%Y-%m-%d %H:%M')} | ICD-11: {icd_code}

COURSE: {duration_number} {duration_unit} | Onset: {onset} | Pattern: {pattern}
Previous: {'Yes' if previous_episodes else 'No'} | Impairment: {functional_impairment}

MSE: {mse_text}

PRIMARY: {top_syndrome} | SEVERITY: {severity} | Weight: {ml_weight}
PROBABILITIES:
"""
        for s, p in probs.items():
            report += f"  {s}: {p}%\n"
        if formal:
            report += "\nFORMAL CRITERIA:\n"
            for dx in formal:
                report += f"  ✓ {dx['status']} → {dx['diagnosis']} ({dx.get('confidence','-')})\n"
        report += f"""
ORGANIC: {organic_level} ({organic_score}/25)
RISK: {risk_level} ({risk_score}/20) → {risk_rec}
{"MIXED FEATURES DETECTED" if mixed else ""}
SUBSTANCE: {sub_text} | NEURO: {neuro_text}
SYMPTOMS ({len(selected_symptoms)}): {" | ".join(selected_symptoms)}

DISCLAIMER: Decision support only. Not a diagnosis. Verify clinically.
If active suicidal plan/command hallucinations → emergency services.
════════════════════════════════════════"""
        ai_text = generate_ai_insights(top_syndrome, severity, risk_level, formal)

        st.success("Report generated")
        t1, t2, t3 = st.tabs(["📋 Report", "🧠 Overview", "💊 Medications"])
        with t1:
            st.code(report, language=None)
            st.download_button("⬇️ Download TXT", data=report, file_name=f"PsychAssist_{patient_name or 'pt'}_{datetime.now().strftime('%Y%m%d_%H%M')}.txt", mime="text/plain")
        with t2:
            st.markdown(ai_text)
        with t3:
            med_key = primary_dx if primary_dx in medication_database else None
            if not med_key:
                if "Depressive" in top_syndrome: med_key = "Major Depressive Disorder"
                elif "Manic" in top_syndrome: med_key = "Bipolar I Disorder - Manic Episode"
                elif "Psychotic" in top_syndrome: med_key = "Schizophrenia Spectrum Disorder"
                elif "Delirium" in top_syndrome: med_key = "Delirium"
            if med_key and med_key in medication_database:
                for line in medication_database[med_key].get("first_line", []):
                    st.markdown(f"**{line['name']}** ({line['class']}) — {line['starting_dose']} → {line['max_dose']}  \nSE: {line['side_effects']}  \nCI: {line.get('contraindications','-')}")
                for section in ["second_line", "augmentation"]:
                    if section in medication_database[med_key]:
                        st.markdown(f"**{section.replace('_',' ').title()}**")
                        for line in medication_database[med_key][section]:
                            st.markdown(f"- {line['name']} ({line['class']}) {line['starting_dose']}")
            else:
                st.info("No specific med suggestions. Use clinical judgment.")

        try:
            upsert_patient(patient_name, age, sex)
            conn = get_conn()
            c = conn.cursor()
            c.execute("""INSERT INTO assessments (
                patient_name, age, sex, symptoms, syndrome, severity, risk_level, formal_diagnoses,
                organic_level, organic_score, functional_impairment, mse, duration, onset, pattern,
                speech, affect, thought_process, insight, judgment, substance_use, neuro_findings,
                report_text, ai_insights, mdd_criteria, mania_criteria, schizophrenia_criteria, delirium_criteria,
                mixed_features, symptom_weight, timestamp
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (patient_name, age, sex, ", ".join(selected_symptoms), top_syndrome, severity, risk_level, json.dumps(formal),
             organic_level, organic_score, functional_impairment, mse_text, f"{duration_number} {duration_unit}", onset, pattern,
             speech, affect, thought, insight, judgment, sub_text, neuro_text, report, ai_text,
             mdd["diagnosis"] if mdd else "", mania["diagnosis"] if mania else "",
             schiz["diagnosis"] if schiz else "", deli["diagnosis"] if deli else "",
             1 if mixed else 0, ml_weight, str(datetime.now())))
            aid = c.lastrowid
            if schedule_fu and patient_name:
                fu_date = (date.today() + timedelta(days=int(fu_days))).isoformat()
                c.execute("INSERT INTO follow_ups (patient_name, assessment_id, follow_up_date, status, notes, created_at) VALUES (?,?,?,?,?,?)",
                          (patient_name, aid, fu_date, "Pending", f"Auto after assessment #{aid}", str(datetime.now())))
            conn.commit()
            conn.close()
            st.caption("Saved to history" + (" + follow-up scheduled" if schedule_fu else ""))
        except Exception as e:
            st.warning(f"Save error: {e}")

# ========== PHQ-9 / GAD-7 ==========
elif page == "PHQ-9":
    st.title("📋 PHQ-9")
    patient = st.text_input("Patient name (optional)", key="phq_n")
    answers = []
    for i, q in enumerate(PHQ9_QUESTIONS):
        ans = st.radio(f"{i+1}. {q}", OPTIONS, key=f"phq_{i}", horizontal=True)
        answers.append(int(ans[-2]))
    if st.button("Calculate PHQ-9", type="primary"):
        total = sum(answers)
        sev = phq9_severity(total)
        st.metric("Score", total)
        st.info(f"Severity: **{sev}**")
        if answers[8] > 0: st.error("Suicidality item endorsed - full risk assessment required.")
        try:
            conn = get_conn(); c = conn.cursor()
            c.execute("INSERT INTO phq9_scores (patient_name, total_score, severity, answers, timestamp) VALUES (?,?,?,?,?)",
                      (patient, total, sev, json.dumps(answers), str(datetime.now())))
            conn.commit(); conn.close()
            st.success("Saved.")
        except Exception as e: st.warning(str(e))

elif page == "GAD-7":
    st.title("😰 GAD-7")
    patient = st.text_input("Patient name (optional)", key="gad_n")
    answers = []
    for i, q in enumerate(GAD7_QUESTIONS):
        ans = st.radio(f"{i+1}. {q}", OPTIONS, key=f"gad_{i}", horizontal=True)
        answers.append(int(ans[-2]))
    if st.button("Calculate GAD-7", type="primary"):
        total = sum(answers)
        sev = gad7_severity(total)
        st.metric("Score", total)
        st.info(f"Severity: **{sev}**")
        try:
            conn = get_conn(); c = conn.cursor()
            c.execute("INSERT INTO gad7_scores (patient_name, total_score, severity, answers, timestamp) VALUES (?,?,?,?,?)",
                      (patient, total, sev, json.dumps(answers), str(datetime.now())))
            conn.commit(); conn.close()
            st.success("Saved.")
        except Exception as e: st.warning(str(e))

# ========== TREATMENT ==========
elif page == "Treatment Tracker":
    st.title("💊 Treatment Tracker")
    t_add, t_view = st.tabs(["Add", "View"])
    with t_add:
        with st.form("tx_form"):
            patient = st.text_input("Patient name *")
            med_name = st.text_input("Medication")
            med_class = st.selectbox("Class", ["SSRI","SNRI","NDRI","Atypical Antipsychotic","Typical Antipsychotic","Mood Stabilizer","Anticonvulsant","Benzodiazepine","Other"])
            dose = st.text_input("Dose")
            frequency = st.selectbox("Frequency", ["Daily","BID","TID","QID","PRN","Weekly","Monthly"])
            route = st.selectbox("Route", ["Oral","IM","IV","Sublingual","Topical"])
            start = st.date_input("Start", value=date.today())
            end = st.date_input("End (optional)", value=None)
            status = st.selectbox("Status", ["Active","Completed","Discontinued","Changed"])
            adherence = st.selectbox("Adherence", ["Excellent","Good","Fair","Poor","Unknown"])
            side_effects = st.text_area("Side effects")
            therapy = st.selectbox("Psychotherapy", ["None","CBT","IPT","Psychodynamic","Supportive","Family Therapy","Group Therapy"])
            reason_start = st.text_input("Reason start")
            reason_stop = st.text_input("Reason stop")
            notes = st.text_area("Notes")
            if st.form_submit_button("Save", type="primary"):
                if not patient: st.warning("Name required.")
                else:
                    try:
                        conn = get_conn(); c = conn.cursor()
                        c.execute("""INSERT INTO treatments (patient_name, medication_name, medication_class, dose, frequency, route,
                            start_date, end_date, status, adherence, side_effects, psychotherapy, reason_start, reason_stop, notes, timestamp)
                            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (patient, med_name, med_class, dose, frequency, route, str(start), str(end) if end else "", status, adherence, side_effects, therapy, reason_start, reason_stop, notes, str(datetime.now())))
                        conn.commit(); conn.close()
                        st.success("Saved.")
                    except Exception as e: st.error(str(e))
    with t_view:
        try:
            conn = get_conn(); c = conn.cursor()
            c.execute("SELECT patient_name, medication_name, dose, status, start_date, adherence FROM treatments ORDER BY timestamp DESC LIMIT 100")
            rows = c.fetchall(); conn.close()
            if not rows: st.info("No treatments yet.")
            else:
                for r in rows:
                    st.write(f"**{r[0]}** — {r[1]} {r[2]} ({r[3]}) | Start {r[4]} | Adherence {r[5]}")
        except Exception as e: st.error(str(e))

# ========== FOLLOW-UP ==========
elif page == "Follow-up":
    st.title("📅 Follow-up Routine")
    fu_tab1, fu_tab2, fu_tab3 = st.tabs(["Schedule / Pending", "Overdue", "Complete / Log"])

    with fu_tab1:
        st.subheader("Schedule new follow-up")
        with st.form("fu_new"):
            pn = st.text_input("Patient name *")
            fu_d = st.date_input("Follow-up date", value=date.today() + timedelta(days=14))
            notes = st.text_area("Notes")
            if st.form_submit_button("Schedule", type="primary"):
                if not pn: st.warning("Name required.")
                else:
                    try:
                        conn = get_conn(); c = conn.cursor()
                        c.execute("INSERT INTO follow_ups (patient_name, follow_up_date, status, notes, created_at) VALUES (?,?,?,?,?)",
                                  (pn, fu_d.isoformat(), "Pending", notes, str(datetime.now())))
                        conn.commit(); conn.close()
                        st.success("Scheduled.")
                    except Exception as e: st.error(str(e))
        st.subheader("Pending follow-ups")
        try:
            conn = get_conn(); c = conn.cursor()
            c.execute("SELECT id, patient_name, follow_up_date, notes FROM follow_ups WHERE status='Pending' ORDER BY follow_up_date ASC")
            rows = c.fetchall(); conn.close()
            if not rows: st.info("No pending follow-ups.")
            else:
                for r in rows:
                    st.write(f"**#{r[0]} {r[1]}** — due {r[2]}  \n{r[3] or ''}")
        except Exception as e: st.error(str(e))

    with fu_tab2:
        st.subheader("Overdue (>0 days past due)")
        try:
            conn = get_conn(); c = conn.cursor()
            today = date.today().isoformat()
            c.execute("SELECT id, patient_name, follow_up_date, notes FROM follow_ups WHERE status='Pending' AND follow_up_date < ? ORDER BY follow_up_date ASC", (today,))
            rows = c.fetchall(); conn.close()
            if not rows: st.success("No overdue follow-ups.")
            else:
                st.warning(f"{len(rows)} overdue")
                for r in rows:
                    st.write(f"**#{r[0]} {r[1]}** — was due {r[2]}")
        except Exception as e: st.error(str(e))

    with fu_tab3:
        st.subheader("Mark complete / log visit")
        try:
            conn = get_conn(); c = conn.cursor()
            c.execute("SELECT id, patient_name, follow_up_date FROM follow_ups WHERE status='Pending' ORDER BY follow_up_date")
            pending = c.fetchall(); conn.close()
            options = {f"#{r[0]} {r[1]} ({r[2]})": r[0] for r in pending}
            if not options:
                st.info("No pending items.")
            else:
                choice = st.selectbox("Select follow-up", list(options.keys()))
                improved = st.selectbox("Symptoms improved?", ["Yes", "Partial", "No", "Worse"])
                adher = st.selectbox("Medication adherence", ["Excellent", "Good", "Fair", "Poor", "N/A"])
                se = st.text_input("Side effects")
                cgi = st.selectbox("Global impression", ["Much improved", "Improved", "Unchanged", "Worse", "Much worse"])
                log_notes = st.text_area("Visit notes")
                if st.button("Complete follow-up", type="primary"):
                    fid = options[choice]
                    try:
                        conn = get_conn(); c = conn.cursor()
                        c.execute("""UPDATE follow_ups SET status='Completed', symptoms_improved=?, adherence=?, side_effects=?, global_impression=?, notes=?, completed_at=? WHERE id=?""",
                                  (improved, adher, se, cgi, log_notes, str(datetime.now()), fid))
                        conn.commit(); conn.close()
                        st.success("Follow-up completed.")
                    except Exception as e: st.error(str(e))
        except Exception as e: st.error(str(e))

# ========== PATIENT DATABASE ==========
elif page == "Patient Database":
    st.title("👤 Patient Database")
    search = st.text_input("Search by name")
    try:
        conn = get_conn(); c = conn.cursor()
        if search:
            c.execute("SELECT name, age, sex, first_seen, last_seen, notes FROM patients WHERE name LIKE ? ORDER BY last_seen DESC", (f"%{search}%",))
        else:
            c.execute("SELECT name, age, sex, first_seen, last_seen, notes FROM patients ORDER BY last_seen DESC LIMIT 100")
        patients = c.fetchall()
        conn.close()
        st.caption(f"{len(patients)} patients shown")
        for p in patients:
            with st.expander(f"{p[0]}  |  Age {p[1] or '-'}  |  {p[2] or '-'}  |  Last: {str(p[4])[:16] if p[4] else '-'}"):
                st.write(f"First seen: {p[3]}  \nNotes: {p[5] or '-'}")
                conn = get_conn(); c = conn.cursor()
                c.execute("SELECT id, syndrome, severity, risk_level, timestamp FROM assessments WHERE patient_name=? ORDER BY timestamp DESC LIMIT 10", (p[0],))
                asses = c.fetchall()
                c.execute("SELECT medication_name, dose, status, start_date FROM treatments WHERE patient_name=? ORDER BY timestamp DESC LIMIT 5", (p[0],))
                txs = c.fetchall()
                c.execute("SELECT follow_up_date, status FROM follow_ups WHERE patient_name=? ORDER BY follow_up_date DESC LIMIT 5", (p[0],))
                fus = c.fetchall()
                conn.close()
                st.markdown("**Assessments**")
                for a in asses:
                    st.write(f"#{a[0]} {a[1]} | {a[2]} | Risk {a[3]} | {str(a[4])[:16]}")
                st.markdown("**Treatments**")
                for t in txs or []:
                    st.write(f"{t[0]} {t[1]} ({t[2]}) from {t[3]}")
                st.markdown("**Follow-ups**")
                for f in fus or []:
                    st.write(f"{f[0]} — {f[1]}")
        if not patients:
            st.info("No patients in database yet. They are added automatically when you save an assessment.")
    except Exception as e:
        st.error(str(e))

# ========== EPIDEMIOLOGY ==========
elif page == "Epidemiology":
    st.title("📊 Epidemiology Dashboard")
    st.caption("Aggregate statistics from local assessments (de-identified counts).")
    try:
        conn = get_conn(); c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM assessments"); total_a = c.fetchone()[0]
        c.execute("SELECT COUNT(DISTINCT patient_name) FROM assessments WHERE patient_name IS NOT NULL AND patient_name != ''"); total_p = c.fetchone()[0]
        c.execute("SELECT syndrome, COUNT(*) FROM assessments GROUP BY syndrome ORDER BY COUNT(*) DESC")
        by_syn = c.fetchall()
        c.execute("SELECT severity, COUNT(*) FROM assessments GROUP BY severity ORDER BY COUNT(*) DESC")
        by_sev = c.fetchall()
        c.execute("SELECT risk_level, COUNT(*) FROM assessments GROUP BY risk_level ORDER BY COUNT(*) DESC")
        by_risk = c.fetchall()
        c.execute("SELECT sex, COUNT(*) FROM assessments WHERE sex IS NOT NULL AND sex != '' GROUP BY sex")
        by_sex = c.fetchall()
        c.execute("SELECT COUNT(*) FROM assessments WHERE mixed_features=1"); mixed_n = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM follow_ups WHERE status='Pending'"); pend_fu = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM follow_ups WHERE status='Pending' AND follow_up_date < ?", (date.today().isoformat(),))
        overdue_fu = c.fetchone()[0]
        c.execute("SELECT AVG(CAST(age AS REAL)) FROM assessments WHERE age GLOB '[0-9]*'")
        avg_age = c.fetchone()[0]
        conn.close()

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total assessments", total_a)
        m2.metric("Unique patients", total_p)
        m3.metric("Pending follow-ups", pend_fu)
        m4.metric("Overdue follow-ups", overdue_fu)

        c1, c2 = st.columns(2)
        with c1:
            st.subheader("By syndrome")
            if by_syn:
                for s, n in by_syn:
                    pct = round(100*n/total_a, 1) if total_a else 0
                    st.write(f"**{s or 'Unknown'}**: {n} ({pct}%)")
                    st.progress(min(n/max(total_a,1), 1.0))
            else:
                st.info("No data yet.")
            st.subheader("By sex")
            for s, n in by_sex:
                st.write(f"{s}: {n}")
            if avg_age:
                st.write(f"Mean age (where numeric): **{avg_age:.1f}**")
        with c2:
            st.subheader("By severity")
            for s, n in by_sev:
                st.write(f"**{s or '-'}**: {n}")
            st.subheader("By risk level")
            for s, n in by_risk:
                st.write(f"**{s or '-'}**: {n}")
            st.write(f"Mixed features cases: **{mixed_n}**")

        st.markdown("---")
        st.subheader("Clinical interpretation notes")
        st.markdown("""
- These are **local counts only** (this app instance), not population epidemiology.
- Use for clinic workload, case-mix awareness, and quality improvement.
- High-risk and overdue follow-up counts should drive safety and continuity actions.
- Always protect patient confidentiality when exporting or sharing aggregates.
        """)
    except Exception as e:
        st.error(str(e))

# ========== EXPORT ==========
elif page == "Export Data":
    st.title("📤 Export Patient Data")
    st.caption("Download CSV files for backup or research analysis. Handle as confidential clinical data.")

    def _csv_bytes(headers, rows):
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(headers)
        w.writerows(rows)
        return buf.getvalue().encode("utf-8")

    try:
        conn = get_conn()
        c = conn.cursor()
        stamp = datetime.now().strftime("%Y%m%d_%H%M")

        # Pull all tables
        c.execute("""SELECT id, patient_name, age, sex, syndrome, severity, risk_level, duration, onset,
                     functional_impairment, substance_use, neuro_findings, mixed_features, symptom_weight, timestamp
                     FROM assessments ORDER BY timestamp DESC""")
        arows = c.fetchall()
        aheaders = [d[0] for d in c.description]

        c.execute("SELECT name, age, sex, phone, notes, first_seen, last_seen FROM patients ORDER BY last_seen DESC")
        prows = c.fetchall()
        pheaders = [d[0] for d in c.description]

        c.execute("""SELECT patient_name, medication_name, medication_class, dose, frequency, status,
                     start_date, end_date, adherence, side_effects, psychotherapy, timestamp
                     FROM treatments ORDER BY timestamp DESC""")
        trows = c.fetchall()
        theaders = [d[0] for d in c.description]

        c.execute("""SELECT patient_name, follow_up_date, status, symptoms_improved, adherence,
                     side_effects, global_impression, notes, created_at, completed_at
                     FROM follow_ups ORDER BY follow_up_date DESC""")
        frows = c.fetchall()
        fheaders = [d[0] for d in c.description]

        c.execute("SELECT patient_name, total_score, severity, timestamp FROM phq9_scores ORDER BY timestamp DESC")
        phq = c.fetchall()
        c.execute("SELECT patient_name, total_score, severity, timestamp FROM gad7_scores ORDER BY timestamp DESC")
        gad = c.fetchall()
        conn.close()

        # --- Combined research ZIP ---
        st.subheader("Research package (recommended)")
        st.markdown(
            "One ZIP with **all tables** as separate CSVs + a short README. "
            "Best for backup and research analysis."
        )
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("assessments.csv", _csv_bytes(aheaders, arows))
            zf.writestr("patients.csv", _csv_bytes(pheaders, prows))
            zf.writestr("treatments.csv", _csv_bytes(theaders, trows))
            zf.writestr("followups.csv", _csv_bytes(fheaders, frows))
            zf.writestr("phq9.csv", _csv_bytes(["patient_name", "total_score", "severity", "timestamp"], phq))
            zf.writestr("gad7.csv", _csv_bytes(["patient_name", "total_score", "severity", "timestamp"], gad))
            readme = f"""PsychAssist research export
Generated: {datetime.now().isoformat()}
Contents:
- assessments.csv  : clinical assessments
- patients.csv     : patient registry
- treatments.csv   : medication / therapy records
- followups.csv    : follow-up schedule and outcomes
- phq9.csv         : PHQ-9 scores
- gad7.csv         : GAD-7 scores

Privacy: may contain identifiable data. Store and share securely.
This is decision-support data only, not a formal clinical database.
"""
            zf.writestr("README.txt", readme)
        zip_buf.seek(0)
        st.download_button(
            "📦 Download ALL data (ZIP for research)",
            data=zip_buf.getvalue(),
            file_name=f"PsychAssist_research_export_{stamp}.zip",
            mime="application/zip",
            type="primary",
            use_container_width=True,
        )
        st.caption(
            f"Includes: {len(arows)} assessments · {len(prows)} patients · "
            f"{len(trows)} treatments · {len(frows)} follow-ups · {len(phq)} PHQ-9 · {len(gad)} GAD-7"
        )

        st.markdown("---")
        st.subheader("Individual CSV files")
        c1, c2 = st.columns(2)
        with c1:
            st.download_button("Assessments (CSV)", data=_csv_bytes(aheaders, arows),
                               file_name=f"assessments_{stamp}.csv", mime="text/csv")
            st.download_button("Patients (CSV)", data=_csv_bytes(pheaders, prows),
                               file_name=f"patients_{stamp}.csv", mime="text/csv")
            st.download_button("Treatments (CSV)", data=_csv_bytes(theaders, trows),
                               file_name=f"treatments_{stamp}.csv", mime="text/csv")
        with c2:
            st.download_button("Follow-ups (CSV)", data=_csv_bytes(fheaders, frows),
                               file_name=f"followups_{stamp}.csv", mime="text/csv")
            st.download_button("PHQ-9 (CSV)",
                               data=_csv_bytes(["patient_name", "total_score", "severity", "timestamp"], phq),
                               file_name=f"phq9_{stamp}.csv", mime="text/csv")
            st.download_button("GAD-7 (CSV)",
                               data=_csv_bytes(["patient_name", "total_score", "severity", "timestamp"], gad),
                               file_name=f"gad7_{stamp}.csv", mime="text/csv")

        st.success("Use the ZIP for research archives. Open CSVs in Excel, Google Sheets, SPSS, R, or Python.")
        st.warning("Exported files may contain identifiable patient data. Store and share securely. Export regularly — free Streamlit Cloud storage is not permanent.")
    except Exception as e:
        st.error(str(e))

# ========== CHATBOT ==========
elif page == "Chatbot":
    st.title("💬 Clinical Assistant")
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [{"role":"assistant","content":"Hello. Ask about depression, mania, psychosis, delirium, risk, meds, PHQ-9 or GAD-7."}]
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
    if prompt := st.chat_input("Your question…"):
        st.session_state.chat_history.append({"role":"user","content":prompt})
        with st.chat_message("user"): st.write(prompt)
        reply = chatbot_reply(prompt)
        st.session_state.chat_history.append({"role":"assistant","content":reply})
        with st.chat_message("assistant"): st.write(reply)

# ========== HISTORY ==========
elif page == "History":
    st.title("📊 History")
    ht1, ht2, ht3 = st.tabs(["Assessments", "Scales", "Treatments"])
    with ht1:
        try:
            conn = get_conn(); c = conn.cursor()
            c.execute("SELECT id, patient_name, age, sex, syndrome, severity, risk_level, timestamp FROM assessments ORDER BY timestamp DESC LIMIT 50")
            rows = c.fetchall(); conn.close()
            if not rows: st.info("No assessments yet.")
            else:
                for row in rows:
                    with st.expander(f"#{row[0]} {row[1] or 'Unnamed'} — {row[4]} ({str(row[7])[:16]})"):
                        st.write(f"Age/Sex: {row[2]}/{row[3]} | Severity: {row[5]} | Risk: {row[6]}")
                        if st.button("View report", key=f"vr_{row[0]}"):
                            conn = get_conn(); c = conn.cursor()
                            c.execute("SELECT report_text, ai_insights FROM assessments WHERE id=?", (row[0],))
                            full = c.fetchone(); conn.close()
                            if full:
                                st.code(full[0], language=None)
                                st.markdown(full[1])
        except Exception as e: st.error(str(e))
    with ht2:
        try:
            conn = get_conn(); c = conn.cursor()
            c.execute("SELECT patient_name, total_score, severity, timestamp FROM phq9_scores ORDER BY timestamp DESC LIMIT 20")
            phq = c.fetchall()
            c.execute("SELECT patient_name, total_score, severity, timestamp FROM gad7_scores ORDER BY timestamp DESC LIMIT 20")
            gad = c.fetchall(); conn.close()
            st.subheader("PHQ-9"); 
            for r in phq or []: st.write(f"{r[0] or '-'} | {r[1]} ({r[2]}) | {str(r[3])[:16]}")
            st.subheader("GAD-7")
            for r in gad or []: st.write(f"{r[0] or '-'} | {r[1]} ({r[2]}) | {str(r[3])[:16]}")
        except Exception as e: st.error(str(e))
    with ht3:
        try:
            conn = get_conn(); c = conn.cursor()
            c.execute("SELECT patient_name, medication_name, dose, status, start_date, adherence FROM treatments ORDER BY timestamp DESC LIMIT 50")
            rows = c.fetchall(); conn.close()
            for r in rows or []:
                st.write(f"**{r[0]}** — {r[1]} {r[2]} ({r[3]}) | {r[4]} | Adherence {r[5]}")
            if not rows: st.info("No treatments.")
        except Exception as e: st.error(str(e))

# ========== ABOUT ==========
else:
    st.title("About PsychAssist Web v4")
    st.markdown("""
### Purpose
Clinical decision-support tool aligned with the original PsychAssist system, extended for web use.

### Modules
- **New Assessment** – full syndrome scoring, criteria, risk, MSE, med suggestions
- **PHQ-9 / GAD-7** – standardized scales
- **Treatment Tracker** – medications and psychotherapy
- **Follow-up** – schedule, pending, overdue, complete with outcome log
- **Patient Database** – searchable patient list with linked history
- **Epidemiology** – local case-mix dashboard (syndrome, severity, risk, sex, follow-up burden)
- **Export Data** – Individual CSVs + one research ZIP package (all tables)
- **Chatbot / History** – educational Q&A and past records

### Disclaimer
Not a medical device. Not a diagnosis. Verify all output clinically.  
Active suicidal plan or command hallucinations → emergency services immediately.

### Privacy
Data stays in the local SQLite database of this deployment. Exports may contain identifiers — handle securely.

### Version
PsychAssist Web v4 — 2026
""")

st.sidebar.markdown("---")
st.sidebar.caption("PsychAssist Web v4 • Decision support only")
