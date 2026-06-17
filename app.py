import streamlit as st
import pandas as pd
import requests
import random
import time
import json
from pathlib import Path
from datetime import timedelta

# =====================================
# GOOGLE FORM
# =====================================

FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSctpoBfTJgwKF-OlWTSskmE8_nnxHL08gPLdweUzJb4xx5XSw/formResponse"

# =====================================
# FILE
# =====================================

PROGRESS_FILE = "progress.json"

# =====================================
# PROGRESS
# =====================================

def load_progress():

    if Path(PROGRESS_FILE).exists():

        with open(PROGRESS_FILE, "r") as f:

            return json.load(f).get(
                "last_success",
                0
            )

    return 0


def save_progress(row):

    with open(PROGRESS_FILE, "w") as f:

        json.dump(
            {
                "last_success": row
            },
            f
        )


def reset_progress():

    save_progress(0)

# =====================================
# PAYLOAD
# =====================================

def build_payload(row):

    create_dt = pd.to_datetime(
        f"{row['Create Ticket Date']} {row['Create Ticket Time']}",
        dayfirst=True
    )

    pickup_dt = create_dt - timedelta(
        minutes=random.randint(1, 3)
    )

    payload = {

        # Nama
        "entry.1884265043":
        str(row["Nama"]).strip(),

        # SBU
        "entry.7318026":
        str(row["SBU"]).strip(),

        # ID TICKET
        "entry.1212348438":
        str(row["ID TICKET"]).strip(),

        # Keterangan
        "entry.800105676":
        str(
            row.get(
                "Keterangan Tambahan",
                "tidak ada"
            )
        ),

        # Eskalasi
        "entry.513669972":
        str(
            row["Eskalasi Back Office"]
        ).strip(),

        # Hasil
        "entry.286520927":
        str(
            row["Hasil Eskalasi"]
        ).strip(),

        # PICKUP TIME
        "entry.1413751263_hour":
        pickup_dt.strftime("%H"),

        "entry.1413751263_minute":
        pickup_dt.strftime("%M"),

        "entry.1413751263_second":
        pickup_dt.strftime("%S"),

        # CREATE TIME
        "entry.898331271_hour":
        create_dt.strftime("%H"),

        "entry.898331271_minute":
        create_dt.strftime("%M"),

        "entry.898331271_second":
        create_dt.strftime("%S"),

        # CREATE DATE
        "entry.192424872_day":
        create_dt.strftime("%d"),

        "entry.192424872_month":
        create_dt.strftime("%m"),

        "entry.192424872_year":
        create_dt.strftime("%Y"),

        # GOOGLE INTERNAL
        "entry.513669972_sentinel": "",
        "entry.286520927_sentinel": "",

        "fvv": "1",
        "pageHistory": "0"

    }

    return payload

# =====================================
# SUBMIT
# =====================================

def submit_form(session, payload):

    for retry in range(3):

        try:

            r = session.post(
                FORM_URL,
                data=payload,
                timeout=60,
                headers={
                    "User-Agent":
                    "Mozilla/5.0"
                }
            )

            if r.status_code in [
                200,
                302
            ]:

                return True

        except:
            pass

        time.sleep(5)

    return False

# =====================================
# UI
# =====================================

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
            "Progress direset"
        )

with col2:

    st.info(
        f"Last Success Row : "
        f"{load_progress()}"
    )

min_delay = st.number_input(
    "Min Delay",
    value=10
)

max_delay = st.number_input(
    "Max Delay",
    value=30
)

file = st.file_uploader(
    "Upload Excel",
    type=["xlsx"]
)

if file:

    df = pd.read_excel(
        file,
        engine="openpyxl"
    )

    st.dataframe(df.head())

    st.write(
        f"Total Data : {len(df)}"
    )

    required = [

        "Nama",
        "ID TICKET",
        "SBU",
        "Eskalasi Back Office",
        "Create Ticket Date",
        "Create Ticket Time",
        "Hasil Eskalasi"

    ]

    missing = [
        c for c in required
        if c not in df.columns
    ]

    if missing:

        st.error(
            f"Kolom tidak ditemukan: {missing}"
        )

        st.stop()

    if st.button(
        "START IMPORT"
    ):

        session = requests.Session()

        progress = st.progress(0)

        start_row = load_progress()

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

            ok = submit_form(
                session,
                payload
            )

            if ok:

                save_progress(
                    idx + 1
                )

                success += 1

                st.success(
                    f"✓ {row['ID TICKET']}"
                )

            else:

                failed += 1

                st.error(
                    f"✗ {row['ID TICKET']}"
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

        st.success(
            f"""
Selesai

Berhasil : {success}

Gagal : {failed}
"""
        )
