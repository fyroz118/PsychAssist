from PsychAssist_streamlit import (
    severity_grader, depressive_logic, mania_logic, psychosis_logic,
    delirium_logic, risk_assessment, phq9_severity, gad7_severity,
)

def test_severity_grader():
    assert severity_grader(0) == "Mild"
    assert severity_grader(8) == "Moderate"
    assert severity_grader(15) == "Severe"
    assert severity_grader(30) == "Very Severe"

def test_depressive_logic_core():
    s = ["Low mood", "Anhedonia", "Fatigue", "Hopelessness", "Suicidal thoughts"]
    assert depressive_logic(s, "Weeks", "Depressed") > 10

def test_mania_requires_core():
    assert mania_logic(["Grandiosity"], "Days", "Normal", "Normal") == 0
    assert mania_logic(["Reduced sleep", "Increased energy", "Grandiosity"],
                       "Days", "Pressured", "Flight of ideas") > 12

def test_psychosis_requires_core():
    assert psychosis_logic(["Paranoia"], "Months", "Normal", "Normal") == 0
    assert psychosis_logic(["Delusions", "Auditory hallucinations"], "Months",
                           "Normal", "Normal") > 10

def test_delirium_requires_confusion_and_disorientation():
    assert delirium_logic(["Confusion"], "Days", "Sudden", True) == 0
    assert delirium_logic(["Confusion", "Disorientation", "Fluctuating attention"],
                          "Days", "Sudden", True) > 15

def test_risk_levels():
    lvl, rec, score = risk_assessment(
        ["Suicidal thoughts"], True, False, False, True)
    assert lvl in ("HIGH RISK", "CRITICAL RISK")

def test_scale_severities():
    assert phq9_severity(3) == "None-Minimal"
    assert phq9_severity(27) == "Severe"
    assert gad7_severity(4) == "Minimal"
    assert gad7_severity(20) == "Severe"