import streamlit as st
import pdfplumber
import pandas as pd
import json
import re
import os
import google.generativeai as genai

# Configure Gemini API
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

st.title("OCU Spec Extractor (Free Version)")

uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])


# -----------------------------
# Extract text from PDF
# -----------------------------
def extract_text(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text


# -----------------------------
# Rule-based extraction
# -----------------------------
def rule_extract(text):
    data = {}

    h2s = re.findall(r'H2S.*?(\d+\.?\d*\s*ppm)', text, re.IGNORECASE)
    if h2s:
        data["H2S Values"] = ", ".join(set(h2s))

    ip = re.findall(r'IP\s?\d{2}', text)
    if ip:
        data["IP Rating"] = ", ".join(set(ip))

    temp = re.findall(r'(\d+\s?-\s?\d+\s?°?C)', text)
    if temp:
        data["Temperature Range"] = ", ".join(set(temp))

    return data


# -----------------------------
# AI extraction (ROBUST)
# -----------------------------
def ai_extract(text):
    prompt = f"""
    You are an expert in wastewater and odour control systems.

    Extract the following parameters:

    - System Type (STP, SPS, ETP)
    - H2S Average (ppm)
    - H2S Peak (ppm)
    - H2S Outlet Limit
    - Removal Efficiency (%)
    - Technology Type
    - Fan Type
    - Fan MOC
    - Duty/Standby Configuration
    - Air Changes Per Hour (ACPH)
    - Duct Material
    - Hazardous Area Classification
    - Instrumentation

    Return ONLY valid JSON.
    If not found, return "Not specified".

    TEXT:
    {text[:12000]}
    """

    try:
        # Use stable model name
        model = genai.GenerativeModel("models/text-bison-001")

        response = model.generate_content(prompt)

        raw_text = response.text.strip()

        # Try JSON parsing
        try:
            return json.loads(raw_text)
        except:
            return {"Raw Output": raw_text}

    except Exception as e:
        return {"Error": str(e)}


# -----------------------------
# Main execution
# -----------------------------
if uploaded_file:
    st.write("Processing...")

    text = extract_text(uploaded_file)

    data = {}
    data.update(rule_extract(text))
    data.update(ai_extract(text))

    df = pd.DataFrame(list(data.items()), columns=["Parameter", "Value"])

    st.subheader("Extracted Data")
    st.dataframe(df)

    st.download_button(
        label="Download Excel",
        data=df.to_csv(index=False),
        file_name="extracted_data.csv",
        mime="text/csv"
    )
