import os
from datetime import date
import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")
st.set_page_config(page_title="ClaimLens AI", page_icon="📄", layout="wide")
st.title("ClaimLens AI")
st.caption("Milestone 1 · deterministic policy PDF ingestion and traceability")

with st.sidebar:
    st.header("Policy metadata")
    carrier = st.text_input("Carrier")
    policy_number = st.text_input("Policy number")
    product_name = st.text_input("Product name")
    jurisdiction = st.text_input("Jurisdiction", value="")
    policy_holder = st.text_input("Policy holder", value="")
    effective_date = st.date_input("Effective date", value=date.today())
    expiry_date = st.date_input("Expiry date", value=date.today())
    version_label = st.text_input("Version label", value="1.0")

uploaded = st.file_uploader("Policy PDF (maximum 25 MB)", type=["pdf"])

if uploaded:
    st.caption(f"{uploaded.name} · {len(uploaded.getvalue()) / 1024:.1f} KiB")
    if st.button("Validate and ingest", type="primary", disabled=not (carrier and policy_number and product_name)):
        files = {"file": (uploaded.name, uploaded.getvalue(), uploaded.type or "application/pdf")}
        data = {
            "carrier": carrier, "policy_number": policy_number, "product_name": product_name,
            "jurisdiction": jurisdiction, "policy_holder": policy_holder,
            "effective_date": effective_date.isoformat(), "expiry_date": expiry_date.isoformat(),
            "version_label": version_label,
        }
        try:
            response = requests.post(f"{API_URL}/api/v1/documents/ingest", data=data, files=files, timeout=120)
            if response.status_code >= 400:
                try:
                    detail = response.json().get("detail", "Ingestion rejected.")
                except ValueError:
                    detail = response.text[:500] or "Ingestion rejected."
                st.error(detail)
            else:
                try:
                    result = response.json()
                except ValueError:
                    st.error(f"The ingestion API returned an invalid response: {response.text[:500]}")
                    st.stop()
                if result["duplicate"]:
                    st.warning("Duplicate document fingerprint. No new database rows were created.")
                else:
                    st.success("Document committed transactionally.")
                c1, c2, c3 = st.columns(3)
                c1.metric("Document ID", result["document"]["id"])
                c2.metric("Pages", result["page_count"])
                c3.metric("Clauses", result["clause_count"])
                st.code(result["document"]["sha256"])
                st.session_state["document_id"] = result["document"]["id"]
        except requests.RequestException as exc:
            st.error(f"Could not reach the ingestion API: {exc.__class__.__name__}")

document_id = st.session_state.get("document_id")
if document_id:
    st.divider()
    left, right = st.columns([1, 2])
    try:
        pages = requests.get(f"{API_URL}/api/v1/documents/{document_id}/pages", timeout=30).json()
        clauses = requests.get(f"{API_URL}/api/v1/documents/{document_id}/clauses", timeout=30).json()
        page_no = left.selectbox("Source page", sorted({p["page_number"] for p in pages}))
        for clause in clauses:
            if clause["page_number"] == page_no:
                right.markdown(f"### {clause['heading'] or 'Clause'}")
                right.write(clause["text"])
                right.caption(f"Page {clause['page_number']} · offsets {clause['start_offset']}–{clause['end_offset']} · ordinal {clause['ordinal']}")
    except requests.RequestException:
        st.error("Could not load document traceability.")
