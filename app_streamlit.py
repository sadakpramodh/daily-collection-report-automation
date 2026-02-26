# app.py
import streamlit as st
import requests
from bs4 import BeautifulSoup
from collections import defaultdict
import datetime
import logging

# -------------------------
# CONFIG
# -------------------------
SECRET_KEY = "Qwerty@123"
AUTH_DURATION_HOURS = 24

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(page_title="Daily Collection Report", layout="wide")

# -------------------------
# SESSION STATE INIT
# -------------------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "auth_time" not in st.session_state:
    st.session_state.auth_time = None


# -------------------------
# AUTHENTICATION CHECK
# -------------------------
def check_auth():
    if st.session_state.authenticated:
        elapsed = datetime.datetime.now() - st.session_state.auth_time
        if elapsed.total_seconds() < AUTH_DURATION_HOURS * 3600:
            return True
        else:
            # Expired
            st.session_state.authenticated = False
            st.session_state.auth_time = None
            return False
    return False


# -------------------------
# SECRET LOGIN UI
# -------------------------
if not check_auth():
    st.title("🔐 Secure Access Required")

    secret_input = st.text_input("Enter Secret Key", type="password")

    if st.button("Login"):
        if secret_input == SECRET_KEY:
            st.session_state.authenticated = True
            st.session_state.auth_time = datetime.datetime.now()
            st.success("Access Granted ✅")
            st.rerun()
        else:
            st.error("Invalid Secret ❌")

    st.stop()


# -------------------------
# FETCH DATA FUNCTION
# -------------------------
def fetch_data(from_date, to_date):
    try:
        session = requests.Session()
        url = "https://tirupati.emunicipal.ap.gov.in/ptis/report/dailyCollection"

        response = session.get(url, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')

        csrf_token = soup.find('meta', {'name': '_csrf'})
        csrf_header = soup.find('meta', {'name': '_csrf_header'})

        if not csrf_token or not csrf_header:
            return {"error": "CSRF token not found"}

        csrf_token = csrf_token['content']
        csrf_header = csrf_header['content']

        headers = {
            "accept": "*/*",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            csrf_header: csrf_token,
            "x-requested-with": "XMLHttpRequest"
        }

        data = {
            "fromDate": from_date,
            "toDate": to_date,
            "collectionMode": "",
            "collectionOperator": "",
            "status": "",
            "revenueWard": ""
        }

        response = session.post(url, headers=headers, data=data, timeout=15)

        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Failed: {response.status_code}"}

    except Exception as e:
        return {"error": str(e)}


# -------------------------
# PROCESS DATA
# -------------------------
def process_data(data):
    if isinstance(data, dict) and "error" in data:
        return data

    if not isinstance(data, list):
        return {"error": "Unexpected data format"}

    grouped_data = defaultdict(lambda: {"count": 0, "totalAmount": 0, "owners": []})

    for entry in data:
        ward = entry.get('secretariatWard', 'Unknown')
        grouped_data[ward]['count'] += 1
        grouped_data[ward]['totalAmount'] += entry.get('totalAmount', 0)
        consumer_name = entry.get('consumerName', 'Unknown')
        consumer_code = entry.get('consumerCode', 'Unknown')
        grouped_data[ward]['owners'].append(f"{consumer_name} ({consumer_code})")

    return dict(grouped_data)


# -------------------------
# MAIN APP UI
# -------------------------
st.title("📊 Daily Collection Report")

# Date options (last 30 days)
today = datetime.datetime.now()
date_options = [
    (today - datetime.timedelta(days=i)).strftime('%d/%m/%Y')
    for i in range(30)
]

selected_date = st.selectbox("Select Date", ["-- Select a date --"] + date_options)

if st.button("Fetch Report"):

    if selected_date == "-- Select a date --":
        st.warning("Please select a date.")
    else:
        with st.spinner("Fetching data... Please wait"):
            raw_data = fetch_data(selected_date, selected_date)
            processed = process_data(raw_data)

        if "error" in processed:
            st.error(processed["error"])
        elif not processed:
            st.info("No data found for selected date.")
        else:
            st.subheader(f"Collection Report for {selected_date}")

            for ward, details in processed.items():
                with st.expander(f"Ward: {ward}"):
                    st.metric("Number of Bills", details["count"])
                    st.metric("Total Amount (₹)", f"{details['totalAmount']:.2f}")
                    st.write("### Owners")
                    st.write(details["owners"])

st.markdown("---")
st.caption("Session remains authenticated for 24 hours.")
