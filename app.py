import streamlit as st
import pdfplumber
import pandas as pd
import json
import re
import os
import requests

st.title("OCU Spec Extractor (Free Version)")

uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])


# -----------------------------
# Extract text
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

    return data


# -----------------------------
# AI extraction (REST API)
# -----------------------------
def ai_extract(text):
    api_key = os.getenv("GOOGLE_API_KEY")

    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"

    prompt = f"""
    Extract the following parameters:

    - System Type
    - H2S Average
    - H2S Peak
    - H2S Outlet
    - Removal Efficiency
    - Technology Type
    - Fan MOC
    - Duty Standby
    - ACPH
    - Duct Material
    - Hazardous Area
    - Instruments

    Return ONLY JSON.

    TEXT:
    {text[:10000]}
    """

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }

    try:
        response = requests.post(url, json=payload)
        result = response.json()

        output_text = result["candidates"][0]["content"]["parts"][0]["text"]

        try:
            return json.loads(output_text)
        except:
            return {"Raw Output": output_text}

    except Exception as e:
        return {"Error": str(e)}


# -----------------------------
# Main
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
