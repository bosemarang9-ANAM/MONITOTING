import streamlit as st
import pandas as pd
import requests
import random
import time
import json
from pathlib import Path
from datetime import datetime

FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSctpoBfTJgwKF-OlWTSskmE8_nnxHL08gPLdweUzJb4xx5XSw/formResponse"

PROGRESS_FILE = "progress.json"
LOG_SUCCESS = "success_log.xlsx"
LOG_FAILED = "failed_log.xlsx"


def load_progress():
    if Path(PROGRESS_FILE).exists():
        try:
            with open(PROGRESS_FILE, "r") as f:
                return json.load(f).get("last_row", 0)
        except:
            pass
    return 0


def save_progress(row_number):
    with open(PROGRESS_FILE, "w") as f:
        json.dump({"last_row": row_number}, f)


def reset_progress():
    save_progress(0)


def clean(v):
    if pd.isna(v):
        return ""
    return str(v).strip()


def parse_time(value):
    if pd.isna(value):
        return None

    try:
        if isinstance(value, (datetime, )):
            return value.strftime("%H:%M:%S")

        value = str(value).strip()

        if value == "":
            return None

        if " " in value:
            value = value.split(" ")[-1]

        if "." in value:
            value = value.split(".")[0]

        dt = pd.to_datetime(value)
        return dt.strftime("%H:%M:%S")

    except:
        return None


def build_payload(row):

    payload = {
        "entry.1884265043": clean(row.get("Nama")),
        "entry.7318026": clean(row.get("SBU")),
        "entry.1212348438": clean(row.get("ID TICKET")),
        "entry.800105676": clean(row.get("Keterangan Tambahan")),
        "entry.513669972": clean(row.get("Eskalasi Back Office")),
        "entry.286520927": clean(row.get("Hasil Eskalasi")),
    }

    pickup = parse_time(row.get("Pick Up Time"))
    if pickup:
        h, m, s = pickup.split(":")
        payload["entry.1413751263_hour"] = h
        payload["entry.1413751263_minute"] = m
        payload["entry.1413751263_second"] = s

    create_time = parse_time(row.get("Create Ticket Time"))
    if create_time:
        h, m, s = create_time.split(":")
        payload["entry.898331271_hour"] = h
        payload["entry.898331271_minute"] = m
        payload["entry.898331271_second"] = s

    try:
        tgl = pd.to_datetime(row.get("Create Ticket Date"), dayfirst=True)
        payload["entry.192424872_day"] = str(tgl.day)
        payload["entry.192424872_month"] = str(tgl.month)
        payload["entry.192424872_year"] = str(tgl.year)
    except:
        pass

    return payload


def submit_form(session, payload):

    for _ in range(3):

        try:
            r = session.post(
                FORM_URL,
                data=payload,
                headers={
                    "User-Agent": "Mozilla/5.0",
                    "Referer": FORM_URL.replace("formResponse", "viewform")
                },
                timeout=60
            )

            if r.status_code in [200, 302]:
                return True

        except:
            pass

        time.sleep(5)

    return False


st.set_page_config(page_title="MONIT Importer", layout="wide")

st.title("Excel ➜ Google Form MONIT")

col1, col2 = st.columns(2)

with col1:
    if st.button("Reset Progress"):
        reset_progress()
        st.success("Progress direset")

with col2:
    st.info(f"Last Success Row : {load_progress()}")

min_delay = st.number_input("Min Delay", 10, 60, 10)
max_delay = st.number_input("Max Delay", 10, 120, 30)

file = st.file_uploader("Upload Excel", type=["xlsx"])

if file:

    df = pd.read_excel(file)
    df = df.dropna(how="all")

    st.dataframe(df.head())
    st.write("Total Data :", len(df))

    required_cols = [
        "Nama",
        "ID TICKET",
        "SBU",
        "Eskalasi Back Office",
        "Pick Up Time",
        "Create Ticket Date",
        "Create Ticket Time",
        "Hasil Eskalasi",
        "Keterangan Tambahan"
    ]

    missing = [c for c in required_cols if c not in df.columns]

    if missing:
        st.error(f"Kolom tidak ditemukan: {missing}")
        st.stop()

    if st.button("START IMPORT"):

        start_row = load_progress()

        progress = st.progress(0)
        status = st.empty()

        success_log = []
        failed_log = []

        session = requests.Session()

        sukses = 0
        gagal = 0

        for idx in range(start_row, len(df)):

            row = df.iloc[idx]

            payload = build_payload(row)

            result = submit_form(session, payload)

            if result:

                sukses += 1

                save_progress(idx + 1)

                success_log.append({
                    "row": idx + 1,
                    "ticket": row["ID TICKET"],
                    "status": "SUCCESS"
                })

                status.success(
                    f"✓ Row {idx+1} berhasil - {row['ID TICKET']}"
                )

            else:

                gagal += 1

                failed_log.append(row.to_dict())

                status.error(
                    f"✗ Row {idx+1} gagal - {row['ID TICKET']}"
                )

            progress.progress((idx + 1) / len(df))

            if idx < len(df) - 1:
                delay = random.randint(min_delay, max_delay)
                time.sleep(delay)

        if success_log:
            pd.DataFrame(success_log).to_excel(
                LOG_SUCCESS,
                index=False
            )

        if failed_log:
            pd.DataFrame(failed_log).to_excel(
                LOG_FAILED,
                index=False
            )

        st.success(
            f"Selesai | Berhasil={sukses} | Gagal={gagal}"
        )
