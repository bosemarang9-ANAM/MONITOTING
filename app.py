import streamlit as st
import pandas as pd
import requests
import random
import time
import json

from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# =====================================================
# CONFIG
# =====================================================

FORM_URL = (
    "https://docs.google.com/forms/d/e/"
    "1FAIpQLSctpoBfTJgwKF-OlWTSskmE8_nnxHL08gPLdweUzJb4xx5XSw"
    "/formResponse"
)

PROGRESS_FILE = "progress.json"

# =====================================================
# PROGRESS
# =====================================================

def load_progress():

    try:

        if Path(PROGRESS_FILE).exists():

            with open(PROGRESS_FILE, "r") as f:

                data = json.load(f)

            return data.get("last_success", 0)

    except:
        pass

    return 0


def save_progress(row_number):

    with open(PROGRESS_FILE, "w") as f:

        json.dump(
            {"last_success": row_number},
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


def get_pickup_time():

    """
    Waktu server WIB
    dikurangi random 1-3 menit
    """

    now = datetime.now(
        ZoneInfo("Asia/Jakarta")
    )

    pickup = now - timedelta(
        minutes=random.randint(1, 3)
    )

    return pickup

# =====================================================
# BUILD PAYLOAD
# =====================================================

def build_payload(row):

    payload = {}

    # ---------------------------------
    # PICK UP TIME
    # ---------------------------------

    pickup = get_pickup_time()

    payload["entry.1413751263_hour"] = (
        pickup.strftime("%H")
    )

    payload["entry.1413751263_minute"] = (
        pickup.strftime("%M")
    )

    payload["entry.1413751263_second"] = (
        pickup.strftime("%S")
    )

    # ---------------------------------
    # CREATE DATE & TIME DARI EXCEL
    # ---------------------------------

    create_dt = pd.to_datetime(
        f"{row['Create Ticket Date']} "
        f"{row['Create Ticket Time']}",
        dayfirst=True
    )

    payload["entry.898331271_hour"] = (
        create_dt.strftime("%H")
    )

    payload["entry.898331271_minute"] = (
        create_dt.strftime("%M")
    )

    payload["entry.898331271_second"] = (
        create_dt.strftime("%S")
    )

    payload["entry.192424872_day"] = (
        create_dt.strftime("%d")
    )

    payload["entry.192424872_month"] = (
        create_dt.strftime("%m")
    )

    payload["entry.192424872_year"] = (
        create_dt.strftime("%Y")
    )

    # ---------------------------------
    # FIELD FORM
    # ---------------------------------

    payload["entry.1884265043"] = clean(
        row["Nama"]
    )

    payload["entry.7318026"] = clean(
        row["SBU"]
    )

    payload["entry.1212348438"] = clean(
        row["ID TICKET"]
    )

    payload["entry.800105676"] = clean(
        row.get(
            "Keterangan Tambahan",
            ""
        )
    )

    payload["entry.513669972"] = clean(
        row["Eskalasi Back Office"]
    )

    payload["entry.286520927"] = clean(
        row["Hasil Eskalasi"]
    )

    # sentinel

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

    for attempt in range(3):

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
                f"HTTP "
                f"{response.status_code}"
            )

        except Exception as e:

            last_error = str(e)

        time.sleep(3)

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
# PROCESS
# =====================================================

if file:

    df = pd.read_excel(
        file,
        engine="openpyxl"
    )

    st.dataframe(df.head())

    required_cols = [

        "Nama",
        "ID TICKET",
        "SBU",
        "Eskalasi Back Office",
        "Create Ticket Date",
        "Create Ticket Time",
        "Hasil Eskalasi"

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

    st.write(
        f"Total Data : {len(df)}"
    )

    if st.button(
        "START IMPORT"
    ):

        start_row = load_progress()

        session = requests.Session()

        progress_bar = st.progress(0)

        status_box = st.empty()

        debug_box = st.empty()

        success = 0
        failed = 0

        for idx in range(
            start_row,
            len(df)
        ):

            row = df.iloc[idx]

            payload = build_payload(
                row
            )

            debug_box.json(
                payload
            )

            ok, err = submit_form(
                session,
                payload
            )

            if ok:

                save_progress(
                    idx + 1
                )

                success += 1

                status_box.success(
                    f"✓ {row['ID TICKET']}"
                )

            else:

                failed += 1

                status_box.error(
                    f"✗ {row['ID TICKET']} "
                    f"| {err}"
                )

            progress_bar.progress(
                (idx + 1) / len(df)
            )

            if idx < len(df) - 1:

                delay = random.randint(
                    min_delay,
                    max_delay
                )

                time.sleep(delay)

        st.success(
            f"""
Import selesai

Berhasil : {success}

Gagal : {failed}
"""
        )
