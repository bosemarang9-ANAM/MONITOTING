import streamlit as st
import pandas as pd
import requests
import random
import time
import json
from pathlib import Path
from datetime import timedelta

# =====================================================
# CONFIG
# =====================================================

FORM_URL = (
    "https://docs.google.com/forms/d/e/"
    "1FAIpQLSctpoBfTJgwKF-OlWTSskmE8_nnxHL08gPLdweUzJb4xx5XSw"
    "/formResponse"
)

PROGRESS_FILE = "progress.json"
SUCCESS_LOG = "success_log.xlsx"
FAILED_LOG = "failed_log.xlsx"

# =====================================================
# PROGRESS
# =====================================================

def load_progress():

    try:

        if Path(PROGRESS_FILE).exists():

            with open(PROGRESS_FILE, "r") as f:

                return json.load(f).get(
                    "last_success",
                    0
                )

    except:
        pass

    return 0


def save_progress(row):

    with open(PROGRESS_FILE, "w") as f:

        json.dump(
            {"last_success": row},
            f
        )


def reset_progress():

    save_progress(0)

# =====================================================
# HELPER
# =====================================================

def clean(value):

    if pd.isna(value):
        return ""

    return str(value).strip()


def generate_pickup_time(timestamp_value):

    try:

        ts = pd.to_datetime(
            timestamp_value,
            dayfirst=True
        )

        minus_minutes = random.randint(
            1,
            3
        )

        pickup = ts - timedelta(
            minutes=minus_minutes
        )

        return pickup

    except:
        return None

# =====================================================
# BUILD PAYLOAD
# =====================================================

def build_payload(row):

    payload = {}

    # =====================
    # FIELD UTAMA
    # =====================

    payload["entry.1884265043"] = clean(
        row.get("Nama")
    )

    payload["entry.7318026"] = clean(
        row.get("SBU")
    )

    payload["entry.1212348438"] = clean(
        row.get("ID TICKET")
    )

    payload["entry.800105676"] = (
        clean(
            row.get("Keterangan Tambahan")
        ) or "tidak ada"
    )

    payload["entry.513669972"] = clean(
        row.get("Eskalasi Back Office")
    )

    payload["entry.286520927"] = clean(
        row.get("Hasil Eskalasi")
    )

    # =====================
    # TIMESTAMP
    # =====================

    ts = pd.to_datetime(
        row.get("Timestamp"),
        dayfirst=True
    )

    # =====================
    # PICK UP TIME
    # =====================

    pickup = generate_pickup_time(
        row.get("Timestamp")
    )

    payload["entry.1413751263_hour"] = \
        pickup.strftime("%H")

    payload["entry.1413751263_minute"] = \
        pickup.strftime("%M")

    payload["entry.1413751263_second"] = \
        pickup.strftime("%S")

    # =====================
    # CREATE TIME
    # =====================

    payload["entry.898331271_hour"] = \
        ts.strftime("%H")

    payload["entry.898331271_minute"] = \
        ts.strftime("%M")

    payload["entry.898331271_second"] = \
        ts.strftime("%S")

    # =====================
    # CREATE DATE
    # =====================

    payload["entry.192424872_day"] = \
        ts.strftime("%d")

    payload["entry.192424872_month"] = \
        ts.strftime("%m")

    payload["entry.192424872_year"] = \
        ts.strftime("%Y")

    # =====================
    # GOOGLE INTERNAL
    # =====================

    payload["entry.513669972_sentinel"] = ""
    payload["entry.286520927_sentinel"] = ""

    payload["fvv"] = "1"
    payload["pageHistory"] = "0"

    return payload

# =====================================================
# SUBMIT
# =====================================================

def submit_form(session, payload):

    last_error = ""

    for retry in range(3):

        try:

            response = session.post(
                FORM_URL,
                data=payload,
                headers={
                    "User-Agent":
                    "Mozilla/5.0",

                    "Referer":
                    FORM_URL.replace(
                        "formResponse",
                        "viewform"
                    )
                },
                timeout=60
            )

            if response.status_code in [
                200,
                302
            ]:

                return True, ""

            last_error = (
                f"HTTP {response.status_code}"
            )

        except Exception as e:

            last_error = str(e)

        time.sleep(5)

    return False, last_error

# =====================================================
# UI
# =====================================================

st.set_page_config(
    page_title="MONIT Importer",
    layout="wide"
)

st.title(
    "Excel → Google Form MONIT"
)

col1, col2 = st.columns(2)

with col1:

    if st.button(
        "Reset Progress"
    ):

        reset_progress()

        st.success(
            "Progress berhasil direset"
        )

with col2:

    st.info(
        f"Last Success Row : "
        f"{load_progress()}"
    )

min_delay = st.number_input(
    "Min Delay",
    min_value=1,
    max_value=60,
    value=10
)

max_delay = st.number_input(
    "Max Delay",
    min_value=1,
    max_value=120,
    value=30
)

file = st.file_uploader(
    "Upload Excel",
    type=["xlsx"]
)

# =====================================================
# LOAD FILE
# =====================================================

if file:

    try:

        df = pd.read_excel(
            file,
            engine="openpyxl"
        )

    except Exception as e:

        st.error(
            f"Gagal membaca file: {e}"
        )

        st.stop()

    df = df.dropna(how="all")

    st.dataframe(df.head())

    st.write(
        f"Total Data : {len(df)}"
    )

    required_cols = [

        "Timestamp",

        "Nama",

        "ID TICKET",

        "SBU",

        "Eskalasi Back Office",

        "Hasil Eskalasi",

        "Keterangan Tambahan"
    ]

    missing = [

        c for c in required_cols

        if c not in df.columns
    ]

    if missing:

        st.error(
            f"Kolom tidak ditemukan: "
            f"{missing}"
        )

        st.stop()

    if st.button(
        "START IMPORT"
    ):

        start_row = load_progress()

        progress = st.progress(0)

        status_box = st.empty()

        payload_box = st.empty()

        session = requests.Session()

        success_log = []

        failed_log = []

        sukses = 0

        gagal = 0

        for idx in range(
            start_row,
            len(df)
        ):

            row = df.iloc[idx]

            payload = build_payload(
                row
            )

            payload_box.json(
                payload
            )

            berhasil, error = submit_form(
                session,
                payload
            )

            if berhasil:

                sukses += 1

                save_progress(
                    idx + 1
                )

                success_log.append({

                    "Row":
                    idx + 1,

                    "Ticket":
                    row["ID TICKET"],

                    "Status":
                    "SUCCESS"
                })

                status_box.success(
                    f"✓ Row {idx+1} berhasil "
                    f"- {row['ID TICKET']}"
                )

            else:

                gagal += 1

                failed_log.append(
                    row.to_dict()
                )

                status_box.error(
                    f"✗ Row {idx+1} gagal "
                    f"- {row['ID TICKET']} "
                    f"| {error}"
                )

            progress.progress(
                (idx + 1)
                / len(df)
            )

            if idx < len(df) - 1:

                delay = random.randint(
                    min_delay,
                    max_delay
                )

                time.sleep(delay)

        if success_log:

            pd.DataFrame(
                success_log
            ).to_excel(
                SUCCESS_LOG,
                index=False
            )

        if failed_log:

            pd.DataFrame(
                failed_log
            ).to_excel(
                FAILED_LOG,
                index=False
            )

        st.success(
            f"""
SELESAI

Berhasil : {sukses}

Gagal : {gagal}
"""
        )
