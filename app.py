import streamlit as st
import pdfplumber
import pandas as pd
import json
import re
import os
from openai import OpenAI

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

st.title("OCU Spec Extractor")

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
    prompt = f"""
    Extract the following:

    - System Type
    - H2S Avg
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

    Return JSON only.

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
