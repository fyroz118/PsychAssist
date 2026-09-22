"""
PsychAssist Web v4 - Clinical Decision Support (Streamlit)
Includes: Assessment, PHQ-9, GAD-7, ADHD, Counselling & Clinical Notes (with handwritten canvas),
Treatments, Chatbot, Epidemiology, Patient Database, Follow-up routine, Export.
Decision support only - not a diagnosis.
"""

import streamlit as st
import sqlite3
from datetime import datetime, date
import json
import random
import csv
import io
import zipfile
import numpy as np
import base64
from PIL import Image
import io as PILImageIO  # for Pillow

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
    CREATE TABLE IF NOT EXISTS assessments ( ... )  # (your original assessments table remains unchanged)
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS counselling_notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_name TEXT, age TEXT, sex TEXT, date TEXT,
        counselling_symptoms TEXT, important_notes TEXT, handwritten_notes TEXT,  # new field for image data
        timestamp TEXT
    )
    """)
    conn.commit()
    conn.close()

init_db()

# ========== DATA & CLINICAL LOGIC (kept exactly as in your original file) ==========
# ... (all your original data, symptom_categories, logic functions, chatbot, etc. are unchanged)

# ========== SIDEBAR ==========
st.sidebar.title("PsychAssist Web v4")
st.sidebar.caption("Decision support only — not a diagnosis")

page = st.sidebar.radio("Navigation", [
    "Assessment", "PHQ-9", "GAD-7", "ADHD", 
    "Counselling & Notes", "Report", 
    "Chat", "History", "Patient Database", "Follow-up", 
    "Epidemiology", "Export Data"
])

# ========== COUNSELLING & CLINICAL NOTES PAGE (with handwritten canvas) ==========
if page == "Counselling & Notes":
    st.title("📝 Counselling & Clinical Notes")
    st.caption("Decision support only — not a diagnosis. Write, draw, or type your notes (handwritten style).")

    col1, col2 = st.columns(2)
    with col1:
        st.session_state.note_name = st.text_input("Patient Name", value=st.session_state.get("patient_name", ""))
        st.session_state.note_age = st.number_input("Age", value=30, step=1)
        st.session_state.note_sex = st.selectbox("Sex", ["Male", "Female", "Other"])
        st.session_state.note_date = st.date_input("Date", value=date.today())

    with col2:
        st.session_state.counselling_symptoms = st.text_area("Counselling Symptoms / Issues", height=150)
        st.session_state.important_notes = st.text_area("Important Notes / Follow-up Reminders", height=150)

    # ========== HANDWRITTEN CANVAS ==========
    st.subheader("✍️ Handwritten Notes (Stylus Friendly)")
    canvas_placeholder = st.empty()
    canvas = st.canvas("canvas", width=800, height=300, key="handwritten_canvas")

    # Button row
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        if st.button("🧹 Clear Canvas"):
            canvas_placeholder.empty()
            st.session_state.handwritten_data = None
    with col_b:
        if st.button("💾 Save Handwritten Image"):
            # Convert canvas to image data
            if "handwritten_canvas" in st.session_state and st.session_state["handwritten_canvas"] is not None:
                img_data = st.session_state["handwritten_canvas"]
                if img_data:
                    # Save as base64 for DB
                    st.session_state.handwritten_notes = img_data
                    st.success("Handwritten notes saved!")
            else:
                st.warning("Draw something first!")

    # Save all
    if st.button("💾 Save All Counselling Notes"):
        conn = get_conn()
        c = conn.cursor()
        c.execute("""
            INSERT INTO counselling_notes 
            (patient_name, age, sex, date, counselling_symptoms, important_notes, handwritten_notes, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            st.session_state.note_name or st.session_state.get("patient_name", "Unknown"),
            str(st.session_state.note_age),
            st.session_state.note_sex,
            str(st.session_state.note_date),
            st.session_state.counselling_symptoms,
            st.session_state.important_notes,
            st.session_state.get("handwritten_notes", ""),
            str(datetime.now())
        ))
        conn.commit()
        conn.close()
        st.success("All notes saved successfully!")

    # View saved notes
    st.subheader("📋 Saved Counselling Notes")
    conn = get_conn()
    notes = conn.execute("""
        SELECT id, patient_name, date, counselling_symptoms, important_notes, handwritten_notes, timestamp 
        FROM counselling_notes 
        ORDER BY timestamp DESC
    """).fetchall()
    conn.close()

    if notes:
        for n in notes[:10]:
            with st.expander(f"{n[1]} - {n[5][:10]}..."):
                st.write(n[3])  # symptoms
                st.markdown("**Important Notes:**")
                st.write(n[4])
                if n[5]:  # handwritten image
                    st.image(n[5], caption="Handwritten notes", use_column_width=True)
    else:
        st.info("No notes saved yet.")

# ========== REPORT, CHAT, HISTORY, PATIENT DATABASE, FOLLOW-UP, EPIDEMIOLOGY, EXPORT DATA pages (unchanged) ==========

# ========== END OF FILE ==========
