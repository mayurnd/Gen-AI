import re
import nltk
import pandas as pd
import gspread
import streamlit as st
import tempfile
import os
import speech_recognition as sr
from nltk.tokenize import word_tokenize
from google.oauth2.service_account import Credentials

# Download NLTK data if not already downloaded
nltk.download('punkt')
nltk.download('averaged_perceptron_tagger')

# --- Helper Functions ---

def transcribe_audio(file_path):
    recognizer = sr.Recognizer()
    with sr.AudioFile(file_path) as source:
        audio = recognizer.record(source)
    try:
        return recognizer.recognize_google(audio)
    except sr.UnknownValueError:
        return "Could not understand the audio."
    except sr.RequestError:
        return "Could not reach the speech recognition service."

def extract_materials(text):
    materials = ['cement', 'sand', 'stone', 'brick', 'steel', 'gravel', 'concrete', 'wood', 'glass', 'aluminum', 'plastic', 'bitumen', 'clay', 'gypsum', 'asphalt', 'lime', 'marble', 'granite', 'tiles', 'paint', 'PVC', 'iron', 'fiber', 'rebar', 'mortar', 'aggregate', 'plaster', 'ceramic', 'bamboo']
    units = ['kg', 'kgs', 'ton', 'tons', 'bags', 'm3', 'liters', 'liter', 'l', 'cft', 'cuft', 'ft', 'feet', 'inch', 'inches', 'mm', 'cm', 'meter', 'meters', 'sqm', 'sqft', 'nos', 'pieces', 'units', 'rolls', 'bundle', 'bundles', 'set', 'sets', 'pair', 'pairs']

    data = []
    tokens = word_tokenize(text.lower())

    for i in range(len(tokens)):
        word = tokens[i]
        if word in materials:
            for j in range(i-1, -1, -1):
                if re.match(r'\d+', tokens[j]):
                    quantity = tokens[j]
                    unit = tokens[j+1] if (j+1 < len(tokens)) and tokens[j+1] in units else ''
                    data.append({
                        'Material': word,
                        'Quantity': f"{quantity} {unit}".strip()
                    })
                    break

    return data

def upload_to_gs(data, json_file_path, spreadsheet_url):
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials = Credentials.from_service_account_file(json_file_path, scopes=scopes)
    gc = gspread.authorize(credentials)

    sh = gc.open_by_url(spreadsheet_url)
    worksheet = sh.sheet1
    worksheet.update('A1', [["S.No", "Material", "Quantity"]])

    for idx, item in enumerate(data, start=1):
        worksheet.append_row([idx, item['Material'], item['Quantity']])

# --- Streamlit UI ---
st.set_page_config(page_title="Construction Material Logger", layout="centered")
st.title("🛠️ AI Construction Material Logger")

# Input: Upload JSON & Spreadsheet URL
json_file = st.file_uploader("Upload your Google API JSON file", type="json")
spreadsheet_url = st.text_input("Enter Google Spreadsheet URL")

# Input: Audio file OR Real-time mic
option = st.radio("Select Input Method", ("Audio File", "Real-Time Microphone"))

if json_file and spreadsheet_url:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp_json:
        tmp_json.write(json_file.read())
        tmp_json_path = tmp_json.name

    if option == "Audio File":
        audio_file = st.file_uploader("Upload Audio File (WAV/MP3)", type=["wav", "mp3"])
        if audio_file is not None:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                tmp.write(audio_file.read())
                tmp_path = tmp.name
            text = transcribe_audio(tmp_path)
            st.success("Audio Transcription Complete")
            st.write(f"**Transcript:** {text}")
            data = extract_materials(text)
            st.write("### Extracted Data")
            st.dataframe(pd.DataFrame(data))
            upload_to_gs(data, tmp_json_path, spreadsheet_url)
            st.success("Data uploaded to Google Sheet")

    elif option == "Real-Time Microphone":
        st.info("Click below and speak clearly...")
        if st.button("Start Recording"):
            recognizer = sr.Recognizer()
            with sr.Microphone() as source:
                st.write("Listening...")
                audio = recognizer.listen(source, timeout=5)
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                    with open(tmp.name, 'wb') as f:
                        f.write(audio.get_wav_data())
                    tmp_path = tmp.name

            text = transcribe_audio(tmp_path)
            st.success("Microphone Audio Transcribed")
            st.write(f"**Transcript:** {text}")
            data = extract_materials(text)
            st.write("### Extracted Data")
            st.dataframe(pd.DataFrame(data))
            upload_to_gs(data, tmp_json_path, spreadsheet_url)
            st.success("Data uploaded to Google Sheet")
