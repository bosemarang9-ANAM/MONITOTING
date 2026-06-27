import streamlit as st
import pandas as pd
import requests
import random
import time
import json
import secrets

from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="MONIT Importer",
    layout="wide"
)

# =====================================================
# SESSION
# =====================================================

DEFAULT_SESSION = {
    "logged_in": False,
    "username": "",
    "otp": "",
    "otp_sent": False,
    "otp_expired": None,
    "otp_try": 0
}

for key, value in DEFAULT_SESSION.items():
    if key not in st.session_state:
        st.session_state[key] = value

# =====================================================
# CONFIG
# =====================================================

FORM_URL = (
    "https://docs.google.com/forms/u/0/d/e/"
    "1FAIpQLSdYY2hbRIhrCY_a06uH0keEsBBu8x6P3AzpZ2BmcmVERjaxpQ"
    "/formResponse"
)

PROGRESS_FILE = "progress.json"

last_submit_time = None

# =====================================================
# LOGIN
# =====================================================

def check_login(username, password):

    users = st.secrets["users"]

    if username not in users:
        return False

    return users[username] == password

# =====================================================
# OTP
# =====================================================

def generate_otp():

    return str(
        secrets.randbelow(900000) + 100000
    )

def send_otp(username):

    otp = generate_otp()

    st.session_state.otp = otp
    st.session_state.otp_sent = True
    st.session_state.otp_try = 0
    st.session_state.otp_expired = (
        datetime.now() + timedelta(minutes=5)
    )

    phone = st.secrets["phone"].get(username)
    token = st.secrets["fonnte"].get(username)

    if not phone:
        st.error(f"Nomor WhatsApp untuk '{username}' belum dikonfigurasi.")
        return False

    if not token:
        st.error(f"Token Fonnte untuk '{username}' belum dikonfigurasi.")
        return False

    message = f"""
    
🔐 LOGIN MONIT

Kode OTP Anda

{otp}

OTP berlaku selama 5 menit.

Jangan berikan kode ini kepada siapa pun.
"""

    r = requests.post(
        "https://api.fonnte.com/send",
        headers={
            "Authorization": token
        },
        data={
            "target": phone,
            "message": message
        },
        timeout=30
    )

    return r.status_code == 200
🔐 LOGIN MONIT

Kode OTP Anda

{otp}

OTP berlaku selama 5 menit.

Jangan berikan kode ini kepada siapa pun.
"""

    r = requests.post(
        "https://api.fonnte.com/send",
        headers={
            "Authorization": token
        },
        data={
            "target": phone,
            "message": message
        },
        timeout=30
    )

    return r.status_code == 200
    
🔐 LOGIN MONIT

Kode OTP Anda

{otp}

OTP berlaku selama 5 menit.

Jangan berikan kode ini kepada siapa pun.
"""

    r = requests.post(
        "https://api.fonnte.com/send",
        headers={
            "Authorization": token
        },
        data={
            "target": phone,
            "message": message
        },
        timeout=30
    )

    return r.status_code == 200

# =====================================================
# LOGIN PAGE
# =====================================================

def login_page():

    st.title("🔐 MONIT LOGIN")

    st.markdown("---")

    # ==================================
    # STEP 1
    # ==================================

    if not st.session_state.otp_sent:

        username = st.text_input(
            "Username"
        )

        password = st.text_input(
            "Password",
            type="password"
        )

        if st.button(
            "Login",
            use_container_width=True
        ):

            if check_login(
                username,
                password
            ):

                st.session_state.username = username

                ok = send_otp(username)

                if ok:

                    st.success(
                        "OTP berhasil dikirim ke WhatsApp."
                    )

                    st.rerun()

                else:

                    st.error(
                        "Gagal mengirim OTP."
                    )

            else:

                st.error(
                    "Username atau Password salah."
                )

    # ==================================
    # STEP 2
    # ==================================

    else:

        st.success(
            f"OTP telah dikirim ke nomor admin."
        )

        otp = st.text_input(
            "Masukkan OTP"
        )

        col1, col2 = st.columns(2)

        with col1:

            if st.button(
                "Verifikasi OTP",
                use_container_width=True
            ):

                if datetime.now() > st.session_state.otp_expired:

                    st.error(
                        "OTP sudah kedaluwarsa."
                    )

                    st.session_state.otp_sent = False

                    st.rerun()

                elif otp == st.session_state.otp:

                    st.session_state.logged_in = True
                    st.session_state.otp_sent = False
                    st.session_state.otp = ""

                    st.rerun()

                else:

                    st.session_state.otp_try += 1

                    if st.session_state.otp_try >= 3:

                        st.error(
                            "OTP salah 3 kali. Login direset."
                        )

                        st.session_state.otp_sent = False

                        st.rerun()

                    else:

                        st.error(
                            f"OTP salah ({st.session_state.otp_try}/3)"
                        )

        with col2:

            if st.button(
                "Kirim Ulang OTP",
                use_container_width=True
            ):

                send_otp(
                    st.session_state.username
                )

                st.success(
                    "OTP baru telah dikirim."
                )

                st.rerun()

# =====================================================
# AUTH
# =====================================================

if not st.session_state.logged_in:
    login_page()
    st.stop()

# =====================================================
# PROGRESS
# =====================================================

def load_progress():

    try:

        if Path(PROGRESS_FILE).exists():

            with open(PROGRESS_FILE, "r") as f:

                data = json.load(f)

            return data.get(
                "last_success",
                0
            )

    except Exception:

        pass

    return 0


def save_progress(row_number):

    with open(
        PROGRESS_FILE,
        "w"
    ) as f:

        json.dump(
            {
                "last_success": row_number
            },
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

    global last_submit_time

    now = datetime.now(
        ZoneInfo("Asia/Jakarta")
    )

    if last_submit_time is None:

        pickup = now - timedelta(
            seconds=random.randint(
                30,
                60
            )
        )

    else:

        pickup = last_submit_time

    return pickup


# =====================================================
# BUILD PAYLOAD
# =====================================================

def build_payload(row):

    payload = {}

    # -----------------------------
    # PICKUP TIME
    # -----------------------------

    pickup = get_pickup_time()

    payload["entry.141665543_hour"] = pickup.strftime("%H")
    payload["entry.141665543_minute"] = pickup.strftime("%M")
    payload["entry.141665543_second"] = pickup.strftime("%S")

    # -----------------------------
    # CREATE DATE TIME
    # -----------------------------

    create_dt = pd.to_datetime(

        f"{row['Create Ticket Date']} "
        f"{row['Create Ticket Time']}",

        dayfirst=True

    )

    payload["entry.2062984122_hour"] = create_dt.strftime("%H")
    payload["entry.2062984122_minute"] = create_dt.strftime("%M")
    payload["entry.2062984122_second"] = create_dt.strftime("%S")

    payload["entry.1418866853_day"] = create_dt.strftime("%d")
    payload["entry.1418866853_month"] = create_dt.strftime("%m")
    payload["entry.1418866853_year"] = create_dt.strftime("%Y")

    # -----------------------------
    # FIELD FORM
    # -----------------------------

    payload["entry.154565194"] = clean(
        row["Nama"]
    )

    payload["entry.1778899713"] = clean(
        row["SBU"]
    )

    payload["entry.1802806380"] = clean(
        row["ID TICKET"]
    )

    payload["entry.564067612"] = clean(

        row.get(
            "Keterangan Tambahan",
            ""
        )

    )

    payload["entry.822984039"] = clean(
        row["Eskalasi Back Office"]
    )

    payload["entry.49503729"] = clean(
        row["Hasil Eskalasi"]
    )

    # -----------------------------
    # Sentinel
    # -----------------------------

    payload["entry.822984039_sentinel"] = ""
    payload["entry.49503729_sentinel"] = ""

    payload["fvv"] = "1"
    payload["pageHistory"] = "0"

    return payload


# =====================================================
# SUBMIT GOOGLE FORM
# =====================================================

def submit_form(

    session,
    payload

):

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

    return (

        False,

        last_error

    )


# =====================================================
# VALIDASI EXCEL
# =====================================================

REQUIRED_COLUMNS = [

    "Nama",

    "ID TICKET",

    "SBU",

    "Eskalasi Back Office",

    "Create Ticket Date",

    "Create Ticket Time",

    "Hasil Eskalasi"

]


def validate_dataframe(df):

    missing = [

        col

        for col in REQUIRED_COLUMNS

        if col not in df.columns

    ]

    return missing

# =====================================================
# MAIN UI
# =====================================================

col1, col2 = st.columns([8, 2])

with col1:

    st.title("📊 Excel → Google Form MONIT")

with col2:

    st.write(
        f"👤 **{st.session_state.username}**"
    )

    if st.button(
        "Logout",
        use_container_width=True
    ):

        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.otp = ""
        st.session_state.otp_sent = False
        st.session_state.otp_expired = None
        st.session_state.otp_try = 0

        st.rerun()

st.divider()

# =====================================================
# STATUS
# =====================================================

col1, col2 = st.columns(2)

with col1:

    if st.button(
        "🔄 Reset Progress",
        use_container_width=True
    ):

        reset_progress()

        st.success(
            "Progress berhasil direset."
        )

with col2:

    st.info(
        f"Last Success Row : {load_progress()}"
    )

st.divider()

# =====================================================
# DELAY
# =====================================================

col1, col2 = st.columns(2)

with col1:

    min_delay = st.number_input(

        "Min Delay (detik)",

        min_value=1,

        max_value=60,

        value=10

    )

with col2:

    max_delay = st.number_input(

        "Max Delay (detik)",

        min_value=1,

        max_value=120,

        value=30

    )

st.divider()

# =====================================================
# UPLOAD
# =====================================================

file = st.file_uploader(

    "Upload Excel",

    type=["xlsx"]

)

if file is None:

    st.info(
        "Silakan upload file Excel."
    )

    st.stop()

# =====================================================
# READ EXCEL
# =====================================================

try:

    df = pd.read_excel(

        file,

        engine="openpyxl"

    )

except Exception as e:

    st.error(str(e))

    st.stop()

# =====================================================
# VALIDASI
# =====================================================

missing = validate_dataframe(df)

if missing:

    st.error(

        f"Kolom berikut tidak ditemukan:\n\n{missing}"

    )

    st.stop()

# =====================================================
# PREVIEW
# =====================================================

st.success(

    f"Total Data : {len(df)}"

)

st.dataframe(

    df.head(10),

    use_container_width=True

)

st.divider()

# =====================================================
# IMPORT
# =====================================================

if st.button(

    "🚀 START IMPORT",

    use_container_width=True,

    type="primary"

):

    start_row = load_progress()

    session = requests.Session()

    progress = st.progress(0)

    status = st.empty()

    success = 0

    failed = 0

    for idx in range(

        start_row,

        len(df)

    ):

        row = df.iloc[idx]

        payload = build_payload(row)

        ok, err = submit_form(

            session,

            payload

        )

        if ok:

            last_submit_time = datetime.now(

                ZoneInfo("Asia/Jakarta")

            )

            save_progress(

                idx + 1

            )

            success += 1

            status.success(

                f"✅ {row['ID TICKET']} berhasil"

            )

        else:

            failed += 1

            status.error(

                f"❌ {row['ID TICKET']} | {err}"

            )

        progress.progress(

            (idx + 1) / len(df)

        )

        if idx < len(df) - 1:

            delay = random.randint(

                min_delay,

                max_delay

            )

            time.sleep(delay)

    st.balloons()

    st.success(

        f"""
### Import Selesai

✅ Berhasil : **{success}**

❌ Gagal : **{failed}**

Total Data : **{len(df)}**
"""
    )
