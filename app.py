import streamlit as st
import pdfplumber
import pandas as pd
import json
import re
import os
from openai import OpenAI

# Initialize OpenAI client using Streamlit secrets
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

st.title("OCU Spec Extractor")

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

    # H2S values
    h2s = re.findall(r'H2S.*?(\d+\.?\d*\s*ppm)', text, re.IGNORECASE)
    if h2s:
        data["H2S Values"] = ", ".join(set(h2s))

    # IP rating
    ip = re.findall(r'IP\s?\d{2}', text)
    if ip:
        data["IP Rating"] = ", ".join(set(ip))

    # Temperature range
    temp = re.findall(r'(\d+\s?-\s?\d+\s?°?C)', text)
    if temp:
        data["Temperature Range"] = ", ".join(set(temp))

    return data


# -----------------------------
# AI extraction (UPDATED API)
# -----------------------------
def ai_extract(text):

    prompt = f"""
    You are an expert in wastewater and odour control systems.

    Extract the following parameters from the text:

    - System Type (STP, SPS, ETP)
    - H2S Average (ppm)
    - H2S Peak (ppm)
    - H2S Outlet Limit
    - Removal Efficiency (%)
    - Technology Type (Bio, Chemical, Activated Carbon, etc.)
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
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        result = response.choices[0].message.content

        return json.loads(result)

    except Exception as e:
        return {"Error": str(e)}


# -----------------------------
# Main processing
# -----------------------------
if uploaded_file:
    st.write("Processing...")

    text = extract_text(uploaded_file)

    data = {}

    # Rule-based extraction
    data.update(rule_extract(text))

    # AI extraction
    ai_data = ai_extract(text)
    data.update(ai_data)

    # Convert to DataFrame
    df = pd.DataFrame(list(data.items()), columns=["Parameter", "Value"])

    st.subheader("Extracted Data")
    st.dataframe(df)

    # Download button
    st.download_button(
        label="Download Excel",
        data=df.to_csv(index=False),
        file_name="extracted_data.csv",
        mime="text/csv"
    )
    )
