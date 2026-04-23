import streamlit as st
import pdfplumber
import pandas as pd
import json
import re
import os
import requests

st.title("OCU Spec Extractor (Stable Version)")

uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])


def extract_text(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text


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


def ai_extract(text):
    api_key = os.getenv("GOOGLE_API_KEY")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"

    prompt = f"""
    Extract key engineering parameters from this document.
    Return JSON format.

    TEXT:
    {text[:8000]}
    """

    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }

    try:
        response = requests.post(url, json=payload)
        result = response.json()

        # DEBUG: show full response
        return {"AI Raw Response": str(result)}

    except Exception as e:
        return {"AI Error": str(e)}


if uploaded_file:
    st.write("Processing...")

    text = extract_text(uploaded_file)

    data = {}
    data.update(rule_extract(text))

    # Try AI but don't break app
    try:
        ai_data = ai_extract(text)
        data.update(ai_data)
    except:
        data["AI"] = "Failed"

    df = pd.DataFrame(list(data.items()), columns=["Parameter", "Value"])

    st.subheader("Extracted Data")
    st.dataframe(df)

    st.download_button(
        label="Download Excel",
        data=df.to_csv(index=False),
        file_name="extracted_data.csv",
        mime="text/csv"
    )
