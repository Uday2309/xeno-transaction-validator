import io
import json
import os
import re
import zipfile
from pathlib import Path

import pandas as pd
import streamlit as st

# -----------------------------
# Page setup
# -----------------------------
st.set_page_config(
    page_title="Xeno Part 4 - Transaction Validator",
    page_icon="✅",
    layout="wide"
)

BASE_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = BASE_DIR / "uploads"
OUTPUTS_DIR = BASE_DIR / "outputs"
RULES_FILE = BASE_DIR / "validation_rules.json"

UPLOADS_DIR.mkdir(exist_ok=True)
OUTPUTS_DIR.mkdir(exist_ok=True)


# -----------------------------
# Helpers
# -----------------------------
def load_rules():
    if not RULES_FILE.exists():
        return {}
    with open(RULES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def is_blank(value):
    return pd.isna(value) or str(value).strip() == ""


def clean_text(value):
    if is_blank(value):
        return ""
    return str(value).strip()


def resolve_country_code(raw_country, rules):
    """
    Returns a country code like IN/SG/DEFAULT.
    Accepts either code (IN) or country name (India).
    """
    if is_blank(raw_country):
        return "DEFAULT"

    raw = str(raw_country).strip().upper()

    # Direct match on code
    if raw in rules:
        return raw

    # Match by country_name
    for code, cfg in rules.items():
        if code == "DEFAULT":
            continue
        if str(cfg.get("country_name", "")).strip().upper() == raw:
            return code

    return "DEFAULT"


def validate_phone(phone_value, expected_length):
    digits = re.sub(r"\D", "", clean_text(phone_value))
    if digits == "":
        return False, digits, "Phone number missing"
    if len(digits) != int(expected_length):
        return False, digits, f"Phone length should be {expected_length} digits"
    return True, digits, ""


def validate_from_formats(value, formats):
    """
    Try multiple datetime formats and return (is_valid, normalized_value, reason)
    """
    txt = clean_text(value)
    if txt == "":
        return False, "", "Value missing"

    for fmt in formats:
        try:
            parsed = pd.to_datetime(txt, format=fmt, errors="raise")
            return True, parsed.strftime("%Y-%m-%d"), ""
        except Exception:
            pass

    return False, "", f"Invalid format: {txt}"


def validate_time_formats(value, formats):
    txt = clean_text(value)
    if txt == "":
        return False, "", "Value missing"

    for fmt in formats:
        try:
            parsed = pd.to_datetime(txt, format=fmt, errors="raise")
            return True, parsed.strftime("%H:%M:%S"), ""
        except Exception:
            pass

    return False, "", f"Invalid time format: {txt}"


def to_float(value):
    txt = clean_text(value)
    if txt == "":
        return None
    try:
        return float(txt)
    except Exception:
        return None


def to_int(value):
    txt = clean_text(value)
    if txt == "":
        return None
    try:
        # Handles values like 5.0 safely
        return int(float(txt))
    except Exception:
        return None


def dataframe_to_bytes_csv(df):
    return df.to_csv(index=False).encode("utf-8")


def zip_chunks_to_bytes(df, chunk_size):
    """
    Create a zip in memory containing chunked CSV files.
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        if len(df) == 0:
            zf.writestr("empty.csv", "")
        else:
            for i, start in enumerate(range(0, len(df), chunk_size), start=1):
                chunk = df.iloc[start:start + chunk_size]
                zf.writestr(f"cleaned_chunk_{i}.csv", chunk.to_csv(index=False))
    buffer.seek(0)
    return buffer.getvalue()


def process_transactions(df, mapping, rules, chunk_size):
    """
    Validate, clean, and split transaction data.
    Returns cleaned_df, rejected_df, summary dict.
    """
    cleaned_rows = []
    rejected_rows = []

    seen_keys = set()

    for idx, row in df.iterrows():
        row_data = row.to_dict()
        reasons = []

        # Read mapped fields
        order_id_col = mapping["order_id"]
        product_id_col = mapping["product_id"]
        country_col = mapping["country_code"]
        phone_col = mapping["phone_number"]
        order_date_col = mapping["order_date"]
        order_time_col = mapping["order_time"]
        payment_col = mapping["payment_mode"]
        amount_col = mapping["amount"]
        quantity_col = mapping["quantity"]

        # Required general fields
        order_id = clean_text(row_data.get(order_id_col, "")) if order_id_col else ""
        product_id = clean_text(row_data.get(product_id_col, "")) if product_id_col else ""
        payment_mode = clean_text(row_data.get(payment_col, "")) if payment_col else ""
        country_value = clean_text(row_data.get(country_col, "")) if country_col else "DEFAULT"

        if order_id == "":
            reasons.append("order_id missing")
        if product_id == "":
            reasons.append("product_id missing")
        if payment_mode == "":
            reasons.append("payment_mode missing")

        # Resolve country config
        country_code = resolve_country_code(country_value, rules)
        cfg = rules.get(country_code, rules.get("DEFAULT", {}))

        # Phone validation
        phone_raw = row_data.get(phone_col, "") if phone_col else ""
        phone_ok, phone_digits, phone_reason = validate_phone(
            phone_raw,
            cfg.get("phone_length", rules.get("DEFAULT", {}).get("phone_length", 10))
        )
        if not phone_ok:
            reasons.append(phone_reason)

        # Date validation
        date_raw = row_data.get(order_date_col, "") if order_date_col else ""
        date_ok, order_date_norm, date_reason = validate_from_formats(
            date_raw,
            cfg.get("date_formats", rules.get("DEFAULT", {}).get("date_formats", ["%Y-%m-%d"]))
        )
        if not date_ok:
            reasons.append(f"order_date: {date_reason}")

        # Time validation
        time_raw = row_data.get(order_time_col, "") if order_time_col else ""
        time_ok, order_time_norm, time_reason = validate_time_formats(
            time_raw,
            cfg.get("time_formats", rules.get("DEFAULT", {}).get("time_formats", ["%H:%M:%S"]))
        )
        if not time_ok:
            reasons.append(f"order_time: {time_reason}")

        # Payment mode validation
        allowed_payments = [x.upper() for x in cfg.get(
            "allowed_payment_modes",
            rules.get("DEFAULT", {}).get("allowed_payment_modes", [])
        )]
        if payment_mode.upper() not in allowed_payments:
            reasons.append(f"payment_mode not allowed for {country_code}")

        # Amount validation
        amount_val = to_float(row_data.get(amount_col, "")) if amount_col else None
        if amount_val is None:
            reasons.append("amount invalid")
        elif amount_val <= 0:
            reasons.append("amount must be > 0")

        # Quantity validation
        quantity_val = to_int(row_data.get(quantity_col, "")) if quantity_col else None
        if quantity_val is None:
            reasons.append("quantity invalid")
        elif quantity_val <= 0:
            reasons.append("quantity must be > 0")

        # Duplicate check using key columns
        duplicate_key = (
            order_id,
            product_id,
            country_code,
            order_date_norm if date_ok else clean_text(date_raw),
            order_time_norm if time_ok else clean_text(time_raw),
            payment_mode.upper()
        )
        if duplicate_key in seen_keys:
            reasons.append("duplicate transaction")
        else:
            seen_keys.add(duplicate_key)

        # Final row object
        out_row = dict(row_data)
        out_row["normalized_country_code"] = country_code
        out_row["normalized_phone"] = phone_digits
        out_row["normalized_order_date"] = order_date_norm if date_ok else ""
        out_row["normalized_order_time"] = order_time_norm if time_ok else ""
        out_row["validation_status"] = "VALID" if len(reasons) == 0 else "INVALID"
        out_row["validation_reason"] = "; ".join(reasons)

        if len(reasons) == 0:
            cleaned_rows.append(out_row)
        else:
            rejected_rows.append(out_row)

    cleaned_df = pd.DataFrame(cleaned_rows)
    rejected_df = pd.DataFrame(rejected_rows)

    # Save outputs
    cleaned_path = OUTPUTS_DIR / "cleaned_transactions.csv"
    rejected_path = OUTPUTS_DIR / "rejected_rows.csv"

    cleaned_df.to_csv(cleaned_path, index=False)
    rejected_df.to_csv(rejected_path, index=False)

    # Chunk cleaned file
    chunk_files = []
    if len(cleaned_df) > 0:
        for i, start in enumerate(range(0, len(cleaned_df), chunk_size), start=1):
            chunk = cleaned_df.iloc[start:start + chunk_size]
            chunk_path = OUTPUTS_DIR / f"cleaned_chunk_{i}.csv"
            chunk.to_csv(chunk_path, index=False)
            chunk_files.append(chunk_path)

    summary = {
        "total_rows": len(df),
        "clean_rows": len(cleaned_df),
        "rejected_rows": len(rejected_df),
        "chunk_count": len(chunk_files),
        "duplicate_rows": int(df.duplicated().sum())
    }

    return cleaned_df, rejected_df, summary


# -----------------------------
# UI
# -----------------------------
st.title("Xeno Part 4 — Transaction Data Validation Platform")
st.caption("Upload a transaction CSV, validate it, clean it, and download the final output.")

rules = load_rules()
if not rules:
    st.error("validation_rules.json not found or empty. Please create it in the same folder as app.py.")
    st.stop()

with st.sidebar:
    st.header("Validation Settings")
    chunk_size = st.slider("Chunk size for output files", min_value=50, max_value=1000, value=200, step=50)
    st.markdown("### Available country codes")
    st.write(", ".join([k for k in rules.keys() if k != "DEFAULT"]))

uploaded_file = st.file_uploader("Upload transaction CSV", type=["csv"])

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
    except Exception as e:
        st.error(f"Could not read CSV: {e}")
        st.stop()

    st.subheader("Preview of uploaded data")
    st.dataframe(df.head(10), use_container_width=True)

    st.markdown("### Map your dataset columns")

    cols = ["-- Not Present --"] + list(df.columns)

    col1, col2, col3 = st.columns(3)

    with col1:
        order_id_col = st.selectbox("Order ID column", cols, index=0)
        product_id_col = st.selectbox("Product ID column", cols, index=0)
        phone_col = st.selectbox("Phone number column", cols, index=0)
        amount_col = st.selectbox("Amount column", cols, index=0)

    with col2:
        order_date_col = st.selectbox("Order date column", cols, index=0)
        order_time_col = st.selectbox("Order time column", cols, index=0)
        payment_mode_col = st.selectbox("Payment mode column", cols, index=0)
        quantity_col = st.selectbox("Quantity column", cols, index=0)

    with col3:
        country_source = st.radio(
            "Country source",
            ["Use a country code column", "Use one fixed country code"],
            horizontal=False
        )

        if country_source == "Use a country code column":
            country_col = st.selectbox("Country code column", cols, index=0)
            fixed_country = "DEFAULT"
        else:
            available_country_codes = [k for k in rules.keys() if k != "DEFAULT"]
            fixed_country = st.selectbox("Fixed country code", available_country_codes, index=0)
            country_col = None

    mapping = {
        "order_id": None if order_id_col == "-- Not Present --" else order_id_col,
        "product_id": None if product_id_col == "-- Not Present --" else product_id_col,
        "phone_number": None if phone_col == "-- Not Present --" else phone_col,
        "order_date": None if order_date_col == "-- Not Present --" else order_date_col,
        "order_time": None if order_time_col == "-- Not Present --" else order_time_col,
        "payment_mode": None if payment_mode_col == "-- Not Present --" else payment_mode_col,
        "amount": None if amount_col == "-- Not Present --" else amount_col,
        "quantity": None if quantity_col == "-- Not Present --" else quantity_col,
        "country_code": None if country_col is None or country_col == "-- Not Present --" else country_col,
    }

    st.info("Click Validate to generate cleaned output, rejected rows, and chunked files.")

    if st.button("Validate and Process", type="primary"):
        with st.spinner("Validating rows..."):
            # If fixed country selected, create a helper column in memory
            work_df = df.copy()
            if country_source == "Use one fixed country code":
                helper_col = "__fixed_country_code__"
                work_df[helper_col] = fixed_country
                mapping["country_code"] = helper_col

            cleaned_df, rejected_df, summary = process_transactions(
                work_df, mapping, rules, chunk_size
            )

        st.success("Validation complete!")

        metric1, metric2, metric3, metric4 = st.columns(4)
        metric1.metric("Total Rows", summary["total_rows"])
        metric2.metric("Valid Rows", summary["clean_rows"])
        metric3.metric("Rejected Rows", summary["rejected_rows"])
        metric4.metric("Chunk Files", summary["chunk_count"])

        st.markdown("### Validation Results")
        st.write("Rows marked VALID are included in the cleaned output. Rows marked INVALID are written to the rejected file.")

        tab1, tab2 = st.tabs(["Cleaned Data", "Rejected Data"])

        with tab1:
            st.dataframe(cleaned_df.head(50), use_container_width=True)
            cleaned_csv = dataframe_to_bytes_csv(cleaned_df)
            st.download_button(
                "Download Cleaned CSV",
                data=cleaned_csv,
                file_name="cleaned_transactions.csv",
                mime="text/csv"
            )

        with tab2:
            st.dataframe(rejected_df.head(50), use_container_width=True)
            rejected_csv = dataframe_to_bytes_csv(rejected_df)
            st.download_button(
                "Download Rejected Rows CSV",
                data=rejected_csv,
                file_name="rejected_rows.csv",
                mime="text/csv"
            )

        st.markdown("### Chunked Output")
        zip_bytes = zip_chunks_to_bytes(cleaned_df, chunk_size)
        st.download_button(
            "Download All Cleaned Chunks (ZIP)",
            data=zip_bytes,
            file_name="cleaned_chunks.zip",
            mime="application/zip"
        )

        if summary["rejected_rows"] > 0:
            st.markdown("### Common validation reasons")
            reason_counts = {}
            for reason_text in rejected_df.get("validation_reason", pd.Series(dtype=str)).fillna(""):
                for reason in [r.strip() for r in str(reason_text).split(";") if r.strip()]:
                    reason_counts[reason] = reason_counts.get(reason, 0) + 1

            if reason_counts:
                reason_df = pd.DataFrame(
                    [{"Reason": k, "Count": v} for k, v in sorted(reason_counts.items(), key=lambda x: x[1], reverse=True)]
                )
                st.dataframe(reason_df, use_container_width=True)

        st.markdown("### What this app does")
        st.write(
            "It validates phone numbers using country-specific rules, checks date/time formats, "
            "flags missing or invalid fields, removes duplicates, generates a cleaned CSV, "
            "creates rejected-row output, and splits cleaned data into smaller chunk files."
        )
else:
    st.info("Upload a CSV file to begin.")
    st.markdown("### Expected columns")
    st.write(
        "Typical transaction columns are: order_id, product_id, customer_id, phone_number, "
        "country_code, order_date, order_time, payment_mode, amount, quantity."
    )
    st.markdown("### Supported validation rules")
    st.write("Phone length, date formats, time formats, and allowed payment modes are all controlled by validation_rules.json.")