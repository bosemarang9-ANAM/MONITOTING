import streamlit as st
import pandas as pd
import requests
import time
import random
import traceback

from datetime import datetime
from datetime import time as dt_time

# =====================================================
# GOOGLE FORM
# =====================================================

FORM_URL = "https://docs.google.com/forms/u/0/d/e/1FAIpQLSdYY2hbRIhrCY_a06uH0keEsBBu8x6P3AzpZ2BmcmVERjaxpQ/formResponse"

# =====================================================
# SESSION STATE
# =====================================================

if "last_success" not in st.session_state:
    st.session_state.last_success = 0

# =====================================================
# HELPER
# =====================================================

def clean_value(val):

    if pd.isna(val):
        return ""

    return str(val).strip()


def parse_time_excel(value):
    """
    Support:
    23:59:59
    23:59:59.106000
    1900-09-30 23:59:59.106000
    datetime
    datetime.time
    """

    if pd.isna(value):
        return None

    try:

        if isinstance(value, dt_time):
            return value.strftime("%H:%M:%S")

        if isinstance(value, datetime):
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

    payload = {}

    payload["entry.154565194"] = clean_value(
        row.get("Nama")
    )

    payload["entry.1778899713"] = clean_value(
        row.get("SBU")
    )

    payload["entry.1802806380"] = clean_value(
        row.get("ID TICKET")
    )

    payload["entry.822984039"] = clean_value(
        row.get("Eskalasi Back Office")
    )

    payload["entry.49503729"] = (
        clean_value(
            row.get("Hasil Eskalasi")
        ) or "No respon"
    )

    payload["entry.564067612"] = (
        clean_value(
            row.get("Keterangan Tambahan")
        ) or "-"
    )

    # ====================================
    # PICK UP TIME
    # ====================================

    pickup = parse_time_excel(
        row.get("Pick Up Time")
    )

    if pickup:

        h, m, s = pickup.split(":")

        payload["entry.141665543_hour"] = h
        payload["entry.141665543_minute"] = m
        payload["entry.141665543_second"] = s

    # ====================================
    # CREATE DATE
    # ====================================

    try:

        tanggal = pd.to_datetime(
            row.get("Create Ticket Date"),
            dayfirst=True
        )

        payload["entry.1418866853_day"] = str(
            tanggal.day
        )

        payload["entry.1418866853_month"] = str(
            tanggal.month
        )

        payload["entry.1418866853_year"] = str(
            tanggal.year
        )

    except:
        pass

    # ====================================
    # CREATE TIME
    # ====================================

    create_time = parse_time_excel(
        row.get("Create Ticket Time")
    )

    if create_time:

        h, m, s = create_time.split(":")

        payload["entry.2062984122_hour"] = h
        payload["entry.2062984122_minute"] = m
        payload["entry.2062984122_second"] = s

    return payload


# =====================================================
# UI
# =====================================================

st.set_page_config(
    page_title="Excel ➜ Google Form Importer",
    layout="wide"
)

st.title("Excel ➜ Google Form Importer")

max_delay = st.slider(
    "Jeda Maksimum Antar Data (detik)",
    min_value=1,
    max_value=30,
    value=20,
    step=1
)

st.caption(
    f"Jeda akan diacak otomatis antara "
    f"{max(3,max_delay//3)} - {max_delay} detik"
)

file = st.file_uploader(
    "Upload Excel",
    type=["xlsx"]
)

col1, col2 = st.columns(2)

with col1:

    if st.button("Reset Progress"):

        st.session_state.last_success = 0

        st.success(
            "Progress berhasil direset"
        )

with col2:

    st.info(
        f"Baris terakhir berhasil : "
        f"{st.session_state.last_success}"
    )

# =====================================================
# LOAD FILE
# =====================================================

if file:

    df = pd.read_excel(file)

    df = df.dropna(how="all")

    st.dataframe(df.head())

    st.write(
        f"Total data : {len(df)}"
    )

    avg_delay = (
        max(3, max_delay // 3)
        + max_delay
    ) / 2

    estimasi = int(
        (len(df) - st.session_state.last_success)
        * avg_delay
    )

    menit = estimasi // 60
    detik = estimasi % 60

    st.info(
        f"Estimasi waktu proses : "
        f"{menit} menit {detik} detik"
    )

    if st.button("Kirim ke Google Form"):

        progress = st.progress(0)

        status_box = st.empty()

        countdown_box = st.empty()

        log_box = st.empty()

        sukses = 0
        gagal = 0

        session = requests.Session()

        start_row = st.session_state.last_success

        for nomor in range(
            start_row,
            len(df)
        ):

            row = df.iloc[nomor]

            try:

                payload = build_payload(row)

                if payload.get(
                    "entry.154565194",
                    ""
                ) == "":

                    gagal += 1

                    continue

                berhasil = False

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

                        if response.status_code in [200, 302]:

                            berhasil = True
                            break

                    except:

                        time.sleep(5)

                if berhasil:

                    sukses += 1

                    st.session_state.last_success = (
                        nomor + 1
                    )

                    status_box.success(
                        f"✓ Baris {nomor+1} berhasil "
                        f"({payload.get('entry.1802806380','-')})"
                    )

                else:

                    gagal += 1

                    status_box.error(
                        f"✗ Baris {nomor+1} gagal"
                    )

                progress.progress(
                    (nomor + 1)
                    / len(df)
                )

                log_box.info(
                    f"""
Progress : {nomor+1}/{len(df)}

Berhasil : {sukses}

Gagal : {gagal}

Last Success :
{st.session_state.last_success}
"""
                )

                # ==================================
                # RANDOM DELAY
                # ==================================

                if nomor < len(df) - 1:

                    random_delay = random.randint(
                        max(3, max_delay // 3),
                        max_delay
                    )

                    for sisa in range(
                        random_delay,
                        0,
                        -1
                    ):

                        countdown_box.info(
                            f"""
Jeda Acak :
{random_delay} detik

Data ke-{nomor+1}
berhasil dikirim

Menunggu :
{sisa} detik
"""
                        )

                        time.sleep(1)

                    countdown_box.empty()

            except Exception as e:

                gagal += 1

                st.error(
                    f"""
Baris {nomor+1} ERROR

{str(e)}

{traceback.format_exc()}
"""
                )

        st.success(
            f"""
SELESAI

Berhasil : {sukses}

Gagal : {gagal}

Total : {len(df)}

Progress tersimpan :
{st.session_state.last_success}
"""
        )
