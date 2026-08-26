"""

### 3. File name: `PsychAssist_streamlit.py`

This is the main (long) file. Copy **everything** below:

```python
"""
PsychAssist Web v2 - Clinical Decision Support (Streamlit)
Mobile-friendly | Works on Android browsers
Features: Assessment, PHQ-9, GAD-7, Treatment Tracker, Chatbot, History
This is a decision-support tool only — not a diagnosis.
"""

import streamlit as st
import sqlite3
from datetime import datetime, date
from collections import defaultdict
import json
import random

# =========================================
# PAGE CONFIG
# =========================================
st.set_page_config(
    page_title="PsychAssist Web",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================================
# DATABASE
# =========================================
DB_PATH = "psychassist_web.db"

def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS assessments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_name TEXT,
        age TEXT,
        sex TEXT,
        symptoms TEXT,
        syndrome TEXT,
        severity TEXT,
        risk_level TEXT,
        formal_diagnoses TEXT,
        organic_level TEXT,
        organic_score INTEGER,
        functional_impairment TEXT,
        mse TEXT,
        duration TEXT,
        onset TEXT,
        report_text TEXT,
        ai_insights TEXT,
        phq9_score INTEGER,
        gad7_score INTEGER,
        timestamp TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS treatments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_name TEXT,
        medication_name TEXT,
        medication_class TEXT,
        dose TEXT,
        frequency TEXT,
        start_date TEXT,
        end_date TEXT,
        status TEXT,
        adherence TEXT,
        side_effects TEXT,
        psychotherapy TEXT,
        notes TEXT,
        timestamp TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS phq9_scores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_name TEXT,
        assessment_id INTEGER,
        total_score INTEGER,
        severity TEXT,
        answers TEXT,
        timestamp TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS gad7_scores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_name TEXT,
        assessment_id INTEGER,
        total_score INTEGER,
        severity TEXT,
        answers TEXT,
        timestamp TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# =========================================
# DATA
# =========================================
symptom_categories = {
    "Mood Symptoms": [
        "Low mood", "Anhedonia", "Fatigue", "Hopelessness", "Excessive guilt",
        "Suicidal thoughts", "Sleep disturbance", "Irritability"
    ],
    "Mania Symptoms": [
        "Reduced sleep", "Increased energy", "Grandiosity", "Pressured speech",
        "Racing thoughts", "Risk-taking behavior", "Distractibility"
    ],
    "Psychotic Symptoms": [
        "Auditory hallucinations", "Visual hallucinations", "Delusions", "Paranoia",
        "Thought broadcasting", "Disorganized speech", "Negative symptoms"
    ],
    "Anxiety Symptoms": [
        "Panic attacks", "Excessive worry", "Palpitations", "Sweating",
        "Tremor", "Avoidance behavior", "Fear of dying"
    ],
    "OCD Symptoms": ["Obsessions", "Compulsions"],
    "Trauma Symptoms": ["Flashbacks", "Nightmares", "Hypervigilance"],
    "Cognitive Symptoms": [
        "Memory loss", "Confusion", "Disorientation", "Fluctuating attention",
        "Personality change", "Poor concentration"
    ],
    "Neurological Symptoms": [
        "Seizure", "Weakness", "Tremor (neurological)", "Gait disturbance",
        "Headache", "Loss of consciousness"
    ],
    "Behavioral Symptoms": [
        "Aggression", "Self-harm", "Catatonia", "Social withdrawal"
    ]
}

icd11_codes = {
    "Major Depressive Disorder": "6A70 (Single episode depressive disorder)",
    "Bipolar I Disorder - Manic Episode": "6A60 (Bipolar type I disorder)",
    "Schizophrenia Spectrum Disorder": "6A20 (Schizophrenia)",
    "Delirium": "6D70 (Delirium)",
    "Generalized Anxiety Disorder": "6B00 (Generalized anxiety disorder)",
}

medication_database = {
    "Major Depressive Disorder": {
        "first_line": [
            {"name": "Sertraline", "class": "SSRI", "starting_dose": "50mg", "max_dose": "200mg",
             "side_effects": "Nausea, headache, insomnia, sexual dysfunction"},
            {"name": "Escitalopram", "class": "SSRI", "starting_dose": "10mg", "max_dose": "20mg",
             "side_effects": "Nausea, fatigue, insomnia, sexual dysfunction"},
            {"name": "Fluoxetine", "class": "SSRI", "starting_dose": "20mg", "max_dose": "80mg",
             "side_effects": "Nervousness, anxiety, insomnia, weight changes"}
        ],
        "second_line": [
            {"name": "Bupropion", "class": "NDRI", "starting_dose": "150mg", "max_dose": "300mg",
             "side_effects": "Agitation, dry mouth, insomnia, seizures (high dose)"}
        ]
    },
    "Bipolar I Disorder - Manic Episode": {
        "first_line": [
            {"name": "Lithium", "class": "Mood Stabilizer", "starting_dose": "300mg", "max_dose": "1800mg",
             "side_effects": "Tremor, polydipsia, polyuria, weight gain"},
            {"name": "Valproate", "class": "Anticonvulsant", "starting_dose": "250mg", "max_dose": "60mg/kg",
             "side_effects": "Sedation, tremor, weight gain, hepatotoxicity"}
        ]
    },
    "Schizophrenia Spectrum Disorder": {
        "first_line": [
            {"name": "Risperidone", "class": "Atypical Antipsychotic", "starting_dose": "2mg", "max_dose": "8mg",
             "side_effects": "Extrapyramidal symptoms, weight gain"},
            {"name": "Aripiprazole", "class": "Atypical Antipsychotic", "starting_dose": "10mg", "max_dose": "30mg",
             "side_effects": "Akathisia, insomnia, nausea"}
        ]
    },
    "Delirium": {
        "first_line": [
            {"name": "Haloperidol", "class": "Typical Antipsychotic", "starting_dose": "0.5mg", "max_dose": "5mg",
             "side_effects": "EPS, QT prolongation, sedation"}
        ]
    },
    "Generalized Anxiety Disorder": {
        "first_line": [
            {"name": "Sertraline", "class": "SSRI", "starting_dose": "25mg", "max_dose": "200mg",
             "side_effects": "Nausea, diarrhea, insomnia, sexual dysfunction"}
        ]
    }
}

# PHQ-9 questions
PHQ9_QUESTIONS = [
    "Little interest or pleasure in doing things",
    "Feeling down, depressed, or hopeless",
    "Trouble falling or staying asleep, or sleeping too much",
    "Feeling tired or having little energy",
    "Poor appetite or overeating",
    "Feeling bad about yourself — or that you are a failure or have let yourself or your family down",
    "Trouble concentrating on things, such as reading the newspaper or watching television",
    "Moving or speaking so slowly that other people could have noticed? Or the opposite — being so fidgety or restless that you have been moving around a lot more than usual",
    "Thoughts that you would be better off dead or of hurting yourself in some way"
]

# GAD-7 questions
GAD7_QUESTIONS = [
    "Feeling nervous, anxious, or on edge",
    "Not being able to stop or control worrying",
    "Worrying too much about different things",
    "Trouble relaxing",
    "Being so restless that it is hard to sit still",
    "Becoming easily annoyed or irritable",
    "Feeling afraid, as if something awful might happen"
]

PHQ9_OPTIONS = ["Not at all (0)", "Several days (1)", "More than half the days (2)", "Nearly every day (3)"]
GAD7_OPTIONS = ["Not at all (0)", "Several days (1)", "More than half the days (2)", "Nearly every day (3)"]

# Simple chatbot responses
CHATBOT_RESPONSES = {
    "depression": [
        "Major depression typically requires 4–6 weeks of antidepressant treatment to see full response.",
        "Common side effects of SSRIs include nausea, headache, and sexual dysfunction.",
        "CBT (Cognitive Behavioral Therapy) is highly effective for depression.",
        "Electroconvulsive therapy (ECT) is reserved for treatment-resistant cases."
    ],
    "mania": [
        "Lithium levels should be monitored (therapeutic range usually 0.6–1.2 mEq/L).",
        "Valproate requires liver function monitoring at baseline and periodically.",
        "Sleep deprivation can trigger manic episodes in bipolar disorder.",
        "Lamotrigine is often preferred for bipolar depression maintenance."
    ],
    "psychosis": [
        "First-episode psychosis has better outcomes with early intervention.",
        "Clozapine is indicated for treatment-resistant schizophrenia (failed ≥2 antipsychotics).",
        "EPS can be managed with anticholinergics.",
        "Metabolic monitoring is essential with atypical antipsychotics."
    ],
    "delirium": [
        "Delirium is often reversible if the underlying cause is identified and treated.",
        "Common precipitants: infection, dehydration, medications, metabolic disturbance.",
        "Non-pharmacological measures are first-line: reorientation, clock, family presence.",
        "Low-dose haloperidol may be used for severe agitation."
    ],
    "risk": [
        "Suicide risk assessment should be repeated at each visit.",
        "Safety plans should include triggers, coping strategies, and support contacts.",
        "Remove firearms and stockpiles of medication during high-risk periods.",
        "Involve family in suicide prevention when appropriate."
    ],
    "medication": [
        "Start low, go slow — titrate medications gradually.",
        "Therapeutic response may take 4–8 weeks for full effect.",
        "Monitor for side effects at each visit.",
        "Always check drug interactions before prescribing."
    ],
    "phq9": [
        "PHQ-9 score 5–9 = Mild, 10–14 = Moderate, 15–19 = Moderately severe, ≥20 = Severe.",
        "A score ≥10 usually indicates need for treatment.",
        "Question 9 (suicidality) should always be reviewed carefully."
    ],
    "gad7": [
        "GAD-7 score 5–9 = Mild, 10–14 = Moderate, ≥15 = Severe anxiety.",
        "A score ≥10 suggests clinically significant anxiety.",
        "SSRIs and CBT are first-line for GAD."
    ]
}

GENERAL_RESPONSES = [
    "This is a clinical decision support tool. Always verify with current guidelines.",
    "Consider consulting psychiatry for complex cases.",
    "Document your clinical reasoning and treatment plan.",
    "Regular follow-up is essential for monitoring response."
]

def chatbot_reply(question: str) -> str:
    q = question.lower()
    keyword_map = {
        "depression": "depression", "depressive": "depression", "mdd": "depression", "phq": "phq9",
        "mania": "mania", "bipolar": "mania", "manic": "mania",
        "psychosis": "psychosis", "schizophrenia": "psychosis", "psychotic": "psychosis",
        "delirium": "delirium", "confusion": "delirium",
        "risk": "risk", "suicide": "risk", "safety": "risk",
        "medication": "medication", "drug": "medication", "side effect": "medication",
        "gad": "gad7", "anxiety": "gad7"
    }
    for keyword, category in keyword_map.items():
        if keyword in q:
            return random.choice(CHATBOT_RESPONSES.get(category, GENERAL_RESPONSES))
    return random.choice(GENERAL_RESPONSES)

# =========================================
# LOGIC FUNCTIONS
# =========================================
def has_symptom(selected, symptom):
    return symptom in selected

def severity_grader(score):
    if score <= 5:
        return "Mild"
    elif score <= 12:
        return "Moderate"
    elif score <= 20:
        return "Severe"
    else:
        return "Very Severe"

def normalize_scores(score_dict):
    total = sum(score_dict.values())
    if total == 0:
        return score_dict
    return {k: round((v / total) * 100, 2) for k, v in score_dict.items()}

def depressive_logic(selected, duration, affect):
    if not (has_symptom(selected, "Low mood") or has_symptom(selected, "Anhedonia")):
        return 0
    score = 12
    for s in ["Fatigue", "Hopelessness", "Excessive guilt", "Suicidal thoughts",
              "Sleep disturbance", "Poor concentration"]:
        if has_symptom(selected, s):
            score += 2
    if sum(1 for s in ["Grandiosity", "Increased energy", "Reduced sleep"] if has_symptom(selected, s)) >= 2:
        score -= 8
    if duration in ["Weeks", "Months"]:
        score += 2
    if affect == "Depressed":
        score += 3
    return max(score, 0)

def mania_logic(selected, duration, speech, thought):
    if not (has_symptom(selected, "Reduced sleep") and has_symptom(selected, "Increased energy")):
        return 0
    score = 12
    for s in ["Grandiosity", "Pressured speech", "Racing thoughts",
              "Risk-taking behavior", "Distractibility"]:
        if has_symptom(selected, s):
            score += 2
    if duration in ["Days", "Weeks"]:
        score += 2
    if speech == "Pressured":
        score += 3
    if thought == "Flight of ideas":
        score += 3
    return max(score, 0)

def psychosis_logic(selected, duration, speech, thought):
    core = sum(1 for s in ["Auditory hallucinations", "Visual hallucinations", "Delusions"]
               if has_symptom(selected, s))
    if core < 1:
        return 0
    score = 12
    for s in ["Paranoia", "Disorganized speech", "Negative symptoms"]:
        if has_symptom(selected, s):
            score += 2
    if duration in ["Months", "Years"]:
        score += 3
    if speech == "Disorganized":
        score += 3
    if thought == "Disorganized":
        score += 4
    return max(score, 0)

def delirium_logic(selected, duration, onset, fluctuating_cognition):
    if not (has_symptom(selected, "Confusion") and has_symptom(selected, "Disorientation")):
        return 0
    score = 15
    for s in ["Fluctuating attention", "Visual hallucinations"]:
        if has_symptom(selected, s):
            score += 3
    if duration in ["Hours", "Days"]:
        score += 5
    if onset == "Sudden":
        score += 4
    if fluctuating_cognition:
        score += 4
    return max(score, 0)

def diagnose_mdd(selected, duration, functional_impairment):
    symptoms_count = sum(1 for s in [
        "Low mood", "Anhedonia", "Fatigue", "Hopelessness", "Excessive guilt",
        "Suicidal thoughts", "Sleep disturbance", "Poor concentration"
    ] if has_symptom(selected, s))
    core_present = has_symptom(selected, "Low mood") or has_symptom(selected, "Anhedonia")
    mania_exclusion = not (has_symptom(selected, "Grandiosity") or has_symptom(selected, "Increased energy"))
    duration_ok = duration in ["Weeks", "Months"]
    impairment = functional_impairment != "None reported"

    if symptoms_count >= 5 and core_present and mania_exclusion and duration_ok and impairment:
        return {"diagnosis": "Major Depressive Disorder", "status": "CRITERIA FULLY MET",
                "symptom_count": symptoms_count, "confidence": "HIGH"}
    elif symptoms_count >= 3:
        return {"diagnosis": "Major Depressive Disorder", "status": "PARTIAL CRITERIA",
                "symptom_count": symptoms_count, "confidence": "MODERATE"}
    return None

def diagnose_mania(selected, duration):
    symptoms_count = sum(1 for s in [
        "Reduced sleep", "Increased energy", "Grandiosity", "Pressured speech",
        "Racing thoughts", "Risk-taking behavior", "Distractibility"
    ] if has_symptom(selected, s))
    required = has_symptom(selected, "Reduced sleep") and has_symptom(selected, "Increased energy")
    duration_ok = duration in ["Days", "Weeks"]

    if symptoms_count >= 4 and required and duration_ok:
        return {"diagnosis": "Bipolar I Disorder - Manic Episode", "status": "CRITERIA FULLY MET",
                "symptom_count": symptoms_count, "confidence": "HIGH"}
    return None

def diagnose_schizophrenia(selected, duration):
    psychotic_core = has_symptom(selected, "Delusions") or has_symptom(selected, "Auditory hallucinations")
    symptom_count = sum(1 for s in [
        "Auditory hallucinations", "Visual hallucinations", "Delusions",
        "Paranoia", "Disorganized speech", "Negative symptoms"
    ] if has_symptom(selected, s))
    chronicity = duration in ["Months", "Years"]

    if psychotic_core and symptom_count >= 2 and chronicity:
        return {"diagnosis": "Schizophrenia Spectrum Disorder", "status": "CRITERIA FULLY MET",
                "symptom_count": symptom_count, "confidence": "HIGH"}
    return None

def diagnose_delirium(selected, duration, fluctuating_cognition):
    core = has_symptom(selected, "Confusion") and has_symptom(selected, "Disorientation")
    fluctuation = has_symptom(selected, "Fluctuating attention") or fluctuating_cognition
    acute = duration in ["Hours", "Days"]

    if core and fluctuation and acute:
        return {"diagnosis": "Delirium", "status": "CRITERIA FULLY MET", "confidence": "HIGH"}
    return None

def organic_psychosis_detector(selected, onset, fluctuating_cognition, seizure, focal, head_injury):
    organic_score = 0
    if has_symptom(selected, "Visual hallucinations"):
        organic_score += 3
    if has_symptom(selected, "Confusion"):
        organic_score += 4
    if fluctuating_cognition:
        organic_score += 4
    if seizure:
        organic_score += 4
    if focal:
        organic_score += 5
    if onset == "Sudden":
        organic_score += 3
    if head_injury:
        organic_score += 4

    if organic_score >= 15:
        level = "🔴 VERY HIGH suspicion of organic psychosis"
    elif organic_score >= 10:
        level = "🟠 HIGH suspicion of organic psychosis"
    elif organic_score >= 6:
        level = "🟡 MODERATE suspicion of organic psychosis"
    else:
        level = "🟢 LOW suspicion of organic psychosis"
    return level, organic_score

def risk_assessment(selected, suicide_plan, command_hallucination, violent, access_means):
    risk_score = 0
    if has_symptom(selected, "Suicidal thoughts"):
        risk_score += 3
    if suicide_plan:
        risk_score += 6
    if command_hallucination:
        risk_score += 6
    if violent:
        risk_score += 5
    if access_means:
        risk_score += 4

    if risk_score >= 15:
        level = "🔴 CRITICAL RISK"
        rec = "🚨 IMMEDIATE HOSPITALIZATION REQUIRED"
    elif risk_score >= 10:
        level = "🟠 HIGH RISK"
        rec = "⚠️ URGENT psychiatric consultation required"
    elif risk_score >= 5:
        level = "🟡 MODERATE RISK"
        rec = "⚠️ Enhanced monitoring required"
    else:
        level = "🟢 LOW RISK"
        rec = "Routine monitoring"
    return level, rec, risk_score

def mixed_features_detector(selected):
    depressive = sum(1 for s in ["Low mood", "Anhedonia", "Hopelessness",
                                 "Excessive guilt", "Suicidal thoughts"] if has_symptom(selected, s))
    manic = sum(1 for s in ["Reduced sleep", "Increased energy", "Grandiosity",
                            "Pressured speech", "Racing thoughts"] if has_symptom(selected, s))
    return depressive >= 3 and manic >= 3

def generate_mse_report(speech, affect, thought, insight, judgment):
    speech_map = {
        "Normal": "normal rate and rhythm", "Pressured": "rapid, difficult to interrupt",
        "Slow": "reduced rate", "Disorganized": "disorganized, difficult to follow"
    }
    affect_map = {
        "Normal": "full range", "Flat": "severely reduced",
        "Depressed": "sad, discouraged", "Labile": "rapidly changing"
    }
    thought_map = {
        "Normal": "logical and goal-directed", "Tangential": "off-topic",
        "Disorganized": "illogical", "Flight of ideas": "rapid shifts"
    }
    insight_map = {"Good": "excellent awareness", "Partial": "partial recognition", "Poor": "limited awareness"}
    judgment_map = {"Good": "intact", "Fair": "mildly impaired", "Poor": "moderately impaired", "Impaired": "markedly impaired"}
    return (f"Speech: {speech_map.get(speech, 'normal')}. "
            f"Affect: {affect_map.get(affect, 'normal')}. "
            f"Thought Process: {thought_map.get(thought, 'normal')}. "
            f"Insight: {insight_map.get(insight, 'good')}. "
            f"Judgment: {judgment_map.get(judgment, 'intact')}.")

def generate_ai_insights(top_syndrome, severity, risk_level, formal_diagnoses, phq9=None, gad7=None):
    insights = []
    insights.append("### 🔍 Clinical Overview")
    insights.append(f"Primary presentation is consistent with **{top_syndrome}** of **{severity.lower()}** severity.")

    if formal_diagnoses:
        dx_names = [dx["diagnosis"] for dx in formal_diagnoses if dx.get("status") == "CRITERIA FULLY MET"]
        if dx_names:
            insights.append("\n### 📋 Diagnostic Considerations")
            insights.append(f"Symptom pattern meets criteria for: **{', '.join(dx_names)}**")
            insights.append("*This is decision support only. Final diagnosis requires clinical correlation.*")

    if phq9 is not None:
        insights.append(f"\n**PHQ-9 score:** {phq9}")
    if gad7 is not None:
        insights.append(f"**GAD-7 score:** {gad7}")

    insights.append("\n### ⚠️ Risk Assessment")
    if "HIGH" in risk_level or "CRITICAL" in risk_level:
        insights.append("Significant safety concerns identified:")
        insights.append("- Do not leave patient unattended")
        insights.append("- Remove access to lethal means")
        insights.append("- Contact emergency psychiatric services")
        insights.append("- Consider hospitalization")
    elif "MODERATE" in risk_level:
        insights.append("Moderate risk factors present. Recommend enhanced monitoring and safety planning.")
    else:
        insights.append("Low risk factors identified. Routine monitoring recommended.")

    insights.append(f"\n### 📚 Educational Notes – {top_syndrome}")
    edu = {
        "Depressive Syndrome": [
            "Major depression typically needs 4–6 weeks of antidepressant treatment for full response.",
            "First-line: SSRIs (sertraline, escitalopram) + CBT.",
            "Monitor closely for suicidal ideation in the first weeks of treatment.",
            "Rule out medical causes (thyroid, B12, etc.)."
        ],
        "Manic Syndrome": [
            "Mood stabilizers (lithium, valproate) are first-line.",
            "Sleep deprivation is a common trigger.",
            "Avoid antidepressants in acute mania.",
            "Monitor lithium levels and liver function as appropriate."
        ],
        "Psychotic Syndrome": [
            "Early intervention improves long-term outcomes.",
            "Antipsychotics are first-line.",
            "Family psychoeducation reduces relapse.",
            "Always rule out substance-induced and medical causes."
        ],
        "Delirium Syndrome": [
            "Delirium is a medical emergency — identify and treat the underlying cause.",
            "Common precipitants: infection, medications, metabolic disturbance, dehydration.",
            "Non-pharmacological measures first (reorientation, lighting, family presence).",
            "Use antipsychotics only for severe agitation."
        ]
    }
    for item in edu.get(top_syndrome, ["Clinical correlation with full history and examination is essential."]):
        insights.append(f"- {item}")

    insights.append("\n### 💊 Treatment Considerations")
    if top_syndrome == "Depressive Syndrome":
        insights.append("- First-line: SSRIs (sertraline 50 mg, escitalopram 10 mg)")
        insights.append("- Augmentation options: aripiprazole, bupropion")
        insights.append("- Psychotherapy: CBT or IPT")
    elif top_syndrome == "Manic Syndrome":
        insights.append("- First-line: Lithium or valproate")
        insights.append("- Second-line: atypical antipsychotics")
        insights.append("- Avoid antidepressants in acute mania")
    elif top_syndrome == "Psychotic Syndrome":
        insights.append("- First-line atypical: risperidone, aripiprazole, olanzapine")
        insights.append("- Clozapine for treatment-resistant cases")
        insights.append("- Metabolic monitoring is essential")
    else:
        insights.append("- Treat underlying cause")
        insights.append("- Symptomatic management as needed")

    insights.append("\n### 📅 Follow-up")
    insights.append("- Reassess in 1–2 weeks")
    insights.append("- Monitor adherence and side effects")
    insights.append("- Re-evaluate risk at every visit")
    return "\n".join(insights)

def phq9_severity(score):
    if score <= 4:
        return "None–Minimal"
    elif score <= 9:
        return "Mild"
    elif score <= 14:
        return "Moderate"
    elif score <= 19:
        return "Moderately Severe"
    else:
        return "Severe"

def gad7_severity(score):
    if score <= 4:
        return "Minimal"
    elif score <= 9:
        return "Mild"
    elif score <= 14:
        return "Moderate"
    else:
        return "Severe"

# =========================================
# SIDEBAR
# =========================================
st.sidebar.title("🧠 PsychAssist Web")
st.sidebar.caption("Clinical Decision Support • Not a diagnosis")

page = st.sidebar.radio(
    "Navigation",
    ["New Assessment", "PHQ-9", "GAD-7", "Treatment Tracker", "Chatbot", "History", "About"],
    index=0
)

st.sidebar.markdown("---")
st.sidebar.info(
    "**Android tip**\n\n"
    "Chrome → ⋮ → Add to Home screen\n\n"
    "Landscape mode helps with long forms."
)

# =========================================
# PAGE: NEW ASSESSMENT
# =========================================
if page == "New Assessment":
    st.title("🧠 Clinical Assessment")
    st.markdown("Complete the sections, then generate the report.")

    with st.expander("📋 Patient Information", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            patient_name = st.text_input("Name", placeholder="Patient name", key="name")
        with col2:
            age = st.text_input("Age", placeholder="e.g. 34", key="age")
        with col3:
            sex = st.selectbox("Sex", ["", "Male", "Female", "Other / Prefer not to say"], key="sex")

    with st.expander("⏱️ Clinical Course", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            duration_unit = st.selectbox("Duration unit", ["Hours", "Days", "Weeks", "Months", "Years"])
            duration_number = st.text_input("Duration number", value="1")
        with col2:
            onset = st.selectbox("Onset", ["Sudden", "Gradual"])
            pattern = st.selectbox("Pattern", ["Not specified", "Episodic", "Chronic", "Fluctuating"])
        with col3:
            previous_episodes = st.checkbox("Previous similar episodes")

    with st.expander("📊 Functional Impairment"):
        occupational = st.checkbox("Occupational dysfunction (work/study)")
        social = st.checkbox("Social dysfunction (relationships)")
        selfcare = st.checkbox("Self-care impairment (ADLs)")

    with st.expander("🧠 Mental Status Exam"):
        col1, col2 = st.columns(2)
        with col1:
            speech = st.selectbox("Speech", ["Normal", "Pressured", "Slow", "Disorganized"])
            affect = st.selectbox("Affect", ["Normal", "Flat", "Depressed", "Labile"])
            thought = st.selectbox("Thought Process", ["Normal", "Tangential", "Disorganized", "Flight of ideas"])
        with col2:
            insight = st.selectbox("Insight", ["Good", "Partial", "Poor"])
            judgment = st.selectbox("Judgment", ["Good", "Fair", "Poor", "Impaired"])

    with st.expander("🍺 Substance Use"):
        col1, col2, col3 = st.columns(3)
        with col1:
            alcohol = st.checkbox("Alcohol")
            cannabis = st.checkbox("Cannabis")
        with col2:
            stimulants = st.checkbox("Stimulants")
            opioids = st.checkbox("Opioids")
        with col3:
            withdrawal = st.checkbox("Withdrawal symptoms")
            polysubstance = st.checkbox("Multiple substances")

    with st.expander("🧠 Neuropsychiatric Findings"):
        col1, col2 = st.columns(2)
        with col1:
            head_injury = st.checkbox("Head injury")
            fluctuating_cognition = st.checkbox("Fluctuating cognition")
            executive = st.checkbox("Executive dysfunction")
            parkinson = st.checkbox("Parkinsonian features")
        with col2:
            focal_deficit = st.checkbox("Focal neurological deficit")
            seizure_disorder = st.checkbox("Seizure disorder")
            stroke = st.checkbox("Stroke history")

    with st.expander("⚡ Risk Assessment", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            suicide_plan = st.checkbox("⚠ Active suicidal plan / intent")
            command_hallucination = st.checkbox("⚠ Command hallucinations")
            violent = st.checkbox("⚠ Violent behavior")
        with col2:
            neglect = st.checkbox("Self-neglect")
            impulsive = st.checkbox("Impulsivity")
            access_means = st.checkbox("Access to means")

    with st.expander("📋 Symptoms (select all that apply)", expanded=True):
        selected_symptoms = []
        for category, symptoms in symptom_categories.items():
            st.markdown(f"**{category}**")
            cols = st.columns(2)
            for i, symptom in enumerate(symptoms):
                with cols[i % 2]:
                    if st.checkbox(symptom, key=f"sym_{symptom}"):
                        selected_symptoms.append(symptom)

    st.markdown("---")
    if st.button("🧠 Generate Clinical Report", type="primary", use_container_width=True):
        if not selected_symptoms:
            st.warning("Please select at least one symptom.")
            st.stop()

        impairment_list = []
        if occupational:
            impairment_list.append("Occupational dysfunction")
        if social:
            impairment_list.append("Social dysfunction")
        if selfcare:
            impairment_list.append("Self-care impairment")
        functional_impairment = ", ".join(impairment_list) if impairment_list else "None reported"

        scores = {
            "Depressive Syndrome": depressive_logic(selected_symptoms, duration_unit, affect),
            "Manic Syndrome": mania_logic(selected_symptoms, duration_unit, speech, thought),
            "Psychotic Syndrome": psychosis_logic(selected_symptoms, duration_unit, speech, thought),
            "Delirium Syndrome": delirium_logic(selected_symptoms, duration_unit, onset, fluctuating_cognition)
        }

        if cannabis or stimulants:
            scores["Psychotic Syndrome"] = scores.get("Psychotic Syndrome", 0) + 4
        if stimulants:
            scores["Manic Syndrome"] = scores.get("Manic Syndrome", 0) + 3
        if alcohol and withdrawal:
            scores["Delirium Syndrome"] = scores.get("Delirium Syndrome", 0) + 6
        if fluctuating_cognition:
            scores["Delirium Syndrome"] = scores.get("Delirium Syndrome", 0) + 5

        filtered = {k: v for k, v in scores.items() if v > 0}
        if not filtered:
            st.warning("No matching syndrome pattern found.")
            st.stop()

        probs = normalize_scores(filtered)
        top_syndrome = max(filtered, key=filtered.get)
        severity = severity_grader(filtered[top_syndrome])

        risk_level, risk_rec, risk_score = risk_assessment(
            selected_symptoms, suicide_plan, command_hallucination, violent, access_means
        )
        organic_level, organic_score = organic_psychosis_detector(
            selected_symptoms, onset, fluctuating_cognition,
            seizure_disorder, focal_deficit, head_injury
        )
        mixed = mixed_features_detector(selected_symptoms)

        formal = []
        mdd = diagnose_mdd(selected_symptoms, duration_unit, functional_impairment)
        if mdd:
            formal.append(mdd)
        mania = diagnose_mania(selected_symptoms, duration_unit)
        if mania:
            formal.append(mania)
        schiz = diagnose_schizophrenia(selected_symptoms, duration_unit)
        if schiz:
            formal.append(schiz)
        deli = diagnose_delirium(selected_symptoms, duration_unit, fluctuating_cognition)
        if deli:
            formal.append(deli)

        if any("Delirium" in d["diagnosis"] for d in formal):
            formal = [d for d in formal if "Schizophrenia" not in d["diagnosis"]]

        mse_text = generate_mse_report(speech, affect, thought, insight, judgment)
        primary_dx = formal[0]["diagnosis"] if formal else top_syndrome
        icd_code = icd11_codes.get(primary_dx, "Not specified")

        if has_symptom(selected_symptoms, "Suicidal thoughts") and suicide_plan:
            st.error("⚠️ PSYCHIATRIC EMERGENCY — Active suicidal plan/intent. Do not leave patient alone. Seek emergency services immediately.")

        report = f"""
══════════════════════════════════════════════════════════════
                 PSYCHASSIST CLINICAL REPORT
          Decision Support System — Not a Diagnosis
══════════════════════════════════════════════════════════════

PATIENT: {patient_name or 'Not provided'} | Age: {age or '—'} | Sex: {sex or '—'}
Report Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}
ICD-11 Reference: {icd_code}

──────────────────────────────────────────────────────────────
CLINICAL COURSE
──────────────────────────────────────────────────────────────
Duration: {duration_number} {duration_unit}
Onset: {onset} | Pattern: {pattern}
Previous episodes: {'Yes' if previous_episodes else 'No'}
Functional Impairment: {functional_impairment}

MENTAL STATUS (auto-generated)
{mse_text}

PRIMARY SYNDROME: {top_syndrome}
SEVERITY: {severity}

PROBABILITY DISTRIBUTION
"""
        for s, p in probs.items():
            bar = "█" * int(p / 5) + "░" * (20 - int(p / 5))
            report += f"  {s:<22} {p:>5}%  {bar}\n"

        if formal:
            report += "\nFORMAL DIAGNOSTIC CRITERIA (DSM-5 style)\n"
            for dx in formal:
                report += f"  ✓ {dx['status']}\n    → {dx['diagnosis']}  (Confidence: {dx.get('confidence', '—')})\n"

        report += f"""
ORGANIC PSYCHOSIS SCREEN
  {organic_level} (Score: {organic_score}/25)

RISK ASSESSMENT
  {risk_level} (Score: {risk_score}/20)
  {risk_rec}
"""
        if mixed:
            report += "\n⚠️ MIXED FEATURES DETECTED — Consider bipolar spectrum\n"

        report += f"\nSELECTED SYMPTOMS ({len(selected_symptoms)})\n"
        report += "  " + " | ".join(selected_symptoms) + "\n"

        report += """
──────────────────────────────────────────────────────────────
IMPORTANT DISCLAIMER
──────────────────────────────────────────────────────────────
This is a DECISION SUPPORT TOOL only.
• NOT a definitive medical diagnosis
• MUST be verified by a qualified clinician
• Does NOT replace a complete psychiatric assessment

If the patient has an active suicidal plan or command hallucinations:
→ Do NOT leave the patient alone
→ Seek immediate psychiatric emergency services
══════════════════════════════════════════════════════════════
"""

        ai_text = generate_ai_insights(top_syndrome, severity, risk_level, formal)

        st.success("Report generated")
        tab1, tab2, tab3 = st.tabs(["📋 Clinical Report", "🧠 AI Clinical Overview", "💊 Medication Suggestions"])

        with tab1:
            st.code(report, language=None)
            st.download_button(
                "⬇️ Download Report (TXT)",
                data=report,
                file_name=f"PsychAssist_{patient_name or 'patient'}_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                mime="text/plain"
            )

        with tab2:
            st.markdown(ai_text)

        with tab3:
            med_key = primary_dx if primary_dx in medication_database else None
            if not med_key:
                if "Depressive" in top_syndrome:
                    med_key = "Major Depressive Disorder"
                elif "Manic" in top_syndrome:
                    med_key = "Bipolar I Disorder - Manic Episode"
                elif "Psychotic" in top_syndrome:
                    med_key = "Schizophrenia Spectrum Disorder"
                elif "Delirium" in top_syndrome:
                    med_key = "Delirium"

            if med_key and med_key in medication_database:
                st.subheader(f"Suggestions for {med_key}")
                for line in medication_database[med_key].get("first_line", []):
                    st.markdown(f"**{line['name']}** ({line['class']})  \n"
                                f"Start: {line['starting_dose']} → Max: {line['max_dose']}  \n"
                                f"Side effects: {line['side_effects']}")
                if "second_line" in medication_database[med_key]:
                    st.markdown("---")
                    st.markdown("**Second-line options**")
                    for line in medication_database[med_key]["second_line"]:
                        st.markdown(f"**{line['name']}** ({line['class']}) — {line['starting_dose']}")
            else:
                st.info("No specific medication suggestions for this presentation.")

        # Save
        try:
            conn = get_conn()
            c = conn.cursor()
            c.execute("""
                INSERT INTO assessments (
                    patient_name, age, sex, symptoms, syndrome, severity, risk_level,
                    formal_diagnoses, organic_level, organic_score, functional_impairment,
                    mse, duration, onset, report_text, ai_insights, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                patient_name, age, sex, ", ".join(selected_symptoms), top_syndrome, severity,
                risk_level, json.dumps(formal), organic_level, organic_score,
                functional_impairment, mse_text, f"{duration_number} {duration_unit}",
                onset, report, ai_text, str(datetime.now())
            ))
            conn.commit()
            conn.close()
            st.caption("Assessment saved to local history.")
        except Exception as e:
            st.warning(f"Could not save: {e}")

# =========================================
# PAGE: PHQ-9
# =========================================
elif page == "PHQ-9":
    st.title("📋 PHQ-9 – Patient Health Questionnaire")
    st.caption("Over the last 2 weeks, how often have you been bothered by the following problems?")

    patient = st.text_input("Patient name (optional)", key="phq9_name")

    answers = []
    for i, q in enumerate(PHQ9_QUESTIONS):
        ans = st.radio(f"{i+1}. {q}", PHQ9_OPTIONS, key=f"phq9_{i}", horizontal=True)
        answers.append(int(ans[-2]))  # extract the number

    if st.button("Calculate PHQ-9 Score", type="primary"):
        total = sum(answers)
        sev = phq9_severity(total)

        st.metric("PHQ-9 Total Score", total)
        st.info(f"**Severity:** {sev}")

        if answers[8] > 0:  # question 9
            st.error("⚠️ Suicidality item endorsed. Perform full risk assessment and safety planning.")

        interpretation = {
            "None–Minimal": "Symptoms may not require treatment. Monitor.",
            "Mild": "Watchful waiting; consider counseling or lifestyle interventions.",
            "Moderate": "Consider treatment (psychotherapy and/or medication).",
            "Moderately Severe": "Active treatment recommended (medication ± psychotherapy).",
            "Severe": "Immediate treatment indicated; consider specialist referral / hospitalization if high risk."
        }
        st.markdown(f"**Clinical note:** {interpretation.get(sev, '')}")

        # Save
        try:
            conn = get_conn()
            c = conn.cursor()
            c.execute("""
                INSERT INTO phq9_scores (patient_name, total_score, severity, answers, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (patient, total, sev, json.dumps(answers), str(datetime.now())))
            conn.commit()
            conn.close()
            st.success("Score saved.")
        except Exception as e:
            st.warning(str(e))

# =========================================
# PAGE: GAD-7
# =========================================
elif page == "GAD-7":
    st.title("😰 GAD-7 – Generalized Anxiety Disorder Scale")
    st.caption("Over the last 2 weeks, how often have you been bothered by the following problems?")

    patient = st.text_input("Patient name (optional)", key="gad7_name")

    answers = []
    for i, q in enumerate(GAD7_QUESTIONS):
        ans = st.radio(f"{i+1}. {q}", GAD7_OPTIONS, key=f"gad7_{i}", horizontal=True)
        answers.append(int(ans[-2]))

    if st.button("Calculate GAD-7 Score", type="primary"):
        total = sum(answers)
        sev = gad7_severity(total)

        st.metric("GAD-7 Total Score", total)
        st.info(f"**Severity:** {sev}")

        interpretation = {
            "Minimal": "Anxiety symptoms are minimal.",
            "Mild": "Mild anxiety — monitor, consider brief intervention.",
            "Moderate": "Moderate anxiety — consider treatment (SSRI / CBT).",
            "Severe": "Severe anxiety — active treatment recommended."
        }
        st.markdown(f"**Clinical note:** {interpretation.get(sev, '')}")

        try:
            conn = get_conn()
            c = conn.cursor()
            c.execute("""
                INSERT INTO gad7_scores (patient_name, total_score, severity, answers, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (patient, total, sev, json.dumps(answers), str(datetime.now())))
            conn.commit()
            conn.close()
            st.success("Score saved.")
        except Exception as e:
            st.warning(str(e))

# =========================================
# PAGE: TREATMENT TRACKER
# =========================================
elif page == "Treatment Tracker":
    st.title("💊 Treatment Tracker")

    tab_add, tab_view = st.tabs(["Add Treatment", "View Treatments"])

    with tab_add:
        with st.form("treatment_form"):
            patient = st.text_input("Patient name *")
            med_name = st.text_input("Medication name")
            med_class = st.selectbox("Class", ["SSRI", "SNRI", "NDRI", "Atypical Antipsychotic",
                                               "Typical Antipsychotic", "Mood Stabilizer",
                                               "Anticonvulsant", "Benzodiazepine", "Other"])
            dose = st.text_input("Dose", placeholder="e.g. 50 mg")
            frequency = st.selectbox("Frequency", ["Daily", "BID", "TID", "QID", "PRN", "Weekly", "Monthly"])
            start = st.date_input("Start date", value=date.today())
            end = st.date_input("End date (optional)", value=None)
            status = st.selectbox("Status", ["Active", "Completed", "Discontinued", "Changed"])
            adherence = st.selectbox("Adherence", ["Excellent", "Good", "Fair", "Poor", "Unknown"])
            side_effects = st.text_area("Side effects")
            therapy = st.selectbox("Psychotherapy", ["None", "CBT", "IPT", "Psychodynamic",
                                                     "Supportive", "Family Therapy", "Group Therapy"])
            notes = st.text_area("Notes")

            submitted = st.form_submit_button("Save Treatment", type="primary")
            if submitted:
                if not patient:
                    st.warning("Patient name is required.")
                else:
                    try:
                        conn = get_conn()
                        c = conn.cursor()
                        c.execute("""
                            INSERT INTO treatments (
                                patient_name, medication_name, medication_class, dose, frequency,
                                start_date, end_date, status, adherence, side_effects,
                                psychotherapy, notes, timestamp
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            patient, med_name, med_class, dose, frequency,
                            str(start), str(end) if end else "", status, adherence,
                            side_effects, therapy, notes, str(datetime.now())
                        ))
                        conn.commit()
                        conn.close()
                        st.success("Treatment saved.")
                    except Exception as e:
                        st.error(str(e))

    with tab_view:
        try:
            conn = get_conn()
            c = conn.cursor()
            c.execute("""
                SELECT id, patient_name, medication_name, dose, status, start_date, adherence
                FROM treatments ORDER BY timestamp DESC LIMIT 100
            """)
            rows = c.fetchall()
            conn.close()

            if not rows:
                st.info("No treatments recorded yet.")
            else:
                for r in rows:
                    with st.expander(f"{r[1]} — {r[2]} {r[3]} ({r[4]})"):
                        st.write(f"**Start:** {r[5]}  |  **Adherence:** {r[6]}")
        except Exception as e:
            st.error(str(e))

# =========================================
# PAGE: CHATBOT
# =========================================
elif page == "Chatbot":
    st.title("💬 Clinical Assistant")
    st.caption("Ask about depression, mania, psychosis, delirium, risk, medications, PHQ-9, GAD-7…")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            {"role": "assistant", "content": "Hello. I can provide educational information about common psychiatric topics. What would you like to know?"}
        ]

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    if prompt := st.chat_input("Type your question…"):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        reply = chatbot_reply(prompt)
        st.session_state.chat_history.append({"role": "assistant", "content": reply})
        with st.chat_message("assistant"):
            st.write(reply)

    st.markdown("---")
    st.markdown("**Quick questions**")
    cols = st.columns(4)
    examples = ["Treatment for depression", "Lithium monitoring", "Suicide risk management", "PHQ-9 interpretation"]
    for i, ex in enumerate(examples):
        if cols[i].button(ex, key=f"ex_{i}"):
            st.session_state.chat_history.append({"role": "user", "content": ex})
            reply = chatbot_reply(ex)
            st.session_state.chat_history.append({"role": "assistant", "content": reply})
            st.rerun()

# =========================================
# PAGE: HISTORY
# =========================================
elif page == "History":
    st.title("📊 History")

    hist_tab1, hist_tab2, hist_tab3 = st.tabs(["Assessments", "PHQ-9 / GAD-7", "Treatments"])

    with hist_tab1:
        try:
            conn = get_conn()
            c = conn.cursor()
            c.execute("""
                SELECT id, patient_name, age, sex, syndrome, severity, risk_level, timestamp
                FROM assessments ORDER BY timestamp DESC LIMIT 50
            """)
            rows = c.fetchall()
            conn.close()

            if not rows:
                st.info("No assessments yet.")
            else:
                for row in rows:
                    with st.expander(f"#{row[0]}  {row[1] or 'Unnamed'}  —  {row[4]}  ({str(row[7])[:16]})"):
                        st.write(f"**Age / Sex:** {row[2]} / {row[3]}")
                        st.write(f"**Syndrome:** {row[4]}  |  **Severity:** {row[5]}")
                        st.write(f"**Risk:** {row[6]}")
                        if st.button("View full report", key=f"view_{row[0]}"):
                            conn = get_conn()
                            c = conn.cursor()
                            c.execute("SELECT report_text, ai_insights FROM assessments WHERE id = ?", (row[0],))
                            full = c.fetchone()
                            conn.close()
                            if full:
                                st.code(full[0], language=None)
                                st.markdown("---")
                                st.markdown(full[1])
        except Exception as e:
            st.error(str(e))

    with hist_tab2:
        try:
            conn = get_conn()
            c = conn.cursor()
            c.execute("SELECT patient_name, total_score, severity, timestamp FROM phq9_scores ORDER BY timestamp DESC LIMIT 20")
            phq_rows = c.fetchall()
            c.execute("SELECT patient_name, total_score, severity, timestamp FROM gad7_scores ORDER BY timestamp DESC LIMIT 20")
            gad_rows = c.fetchall()
            conn.close()

            st.subheader("Recent PHQ-9")
            if phq_rows:
                for r in phq_rows:
                    st.write(f"{r[0] or '—'}  |  Score: **{r[1]}** ({r[2]})  |  {str(r[3])[:16]}")
            else:
                st.caption("No PHQ-9 scores yet.")

            st.subheader("Recent GAD-7")
            if gad_rows:
                for r in gad_rows:
                    st.write(f"{r[0] or '—'}  |  Score: **{r[1]}** ({r[2]})  |  {str(r[3])[:16]}")
            else:
                st.caption("No GAD-7 scores yet.")
        except Exception as e:
            st.error(str(e))

    with hist_tab3:
        try:
            conn = get_conn()
            c = conn.cursor()
            c.execute("""
                SELECT patient_name, medication_name, dose, status, start_date, adherence
                FROM treatments ORDER BY timestamp DESC LIMIT 50
            """)
            rows = c.fetchall()
            conn.close()
            if not rows:
                st.info("No treatments yet.")
            else:
                for r in rows:
                    st.write(f"**{r[0]}** — {r[1]} {r[2]} ({r[3]})  |  Start: {r[4]}  |  Adherence: {r[5]}")
        except Exception as e:
            st.error(str(e))

# =========================================
# PAGE: ABOUT
# =========================================
else:
    st.title("About PsychAssist Web")
    st.markdown("""
### Purpose
PsychAssist is a **clinical decision-support tool** that helps structure psychiatric assessments, calculate syndrome scores, check diagnostic criteria, score PHQ-9 / GAD-7, track treatments, and provide educational overviews.

### Features in this version
- Full clinical assessment with syndrome scoring
- Formal diagnostic criteria checks (MDD, Mania, Schizophrenia, Delirium)
- Organic psychosis screen & mixed-features detector
- Risk stratification with emergency alerts
- PHQ-9 and GAD-7 scoring with interpretation
- Treatment tracker
- Simple clinical chatbot
- Local history & report download

### Important Disclaimer
- This tool is **not a medical device** and does **not** provide diagnoses.
- All outputs must be interpreted and verified by a qualified clinician.
- It does not replace a full history, examination, investigations, or clinical judgment.
- In cases of active suicidal plan, command hallucinations, or high risk → seek emergency services immediately.

### How to use on Android
1. Open this page in Chrome.
2. Tap the menu (⋮) → **Add to Home screen**.
3. Open it like a regular app.
4. Landscape mode often works better for long forms.

### Data
All data is stored only in a local SQLite file on the machine running the app.  
No data is sent to external servers by this code.

### Version
PsychAssist Web v2 (Streamlit) — 2026
""")

st.sidebar.markdown("---")
st.sidebar.caption("PsychAssist Web v2 • Decision support only")
