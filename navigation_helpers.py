import streamlit as st
from constants import PILOT_MODE

STAGE_TO_PAGE = {
    "consent": "streamlit_app.py",
    "priming": "streamlit_app.py",
    "task": "streamlit_app.py",
    "likert": "pages/1_Likert_Survey.py",
    "open": "pages/2_Open_Questions.py",
    "pilot": "pages/4_Pilot_Feedback.py",
    "thankyou": "pages/3_Thank_You.py",
    "done": "pages/3_Thank_You.py",
}


def init_navigation_state():
    if "page" not in st.session_state:
        st.session_state.page = "consent"

    if "survey_stage" not in st.session_state:
        st.session_state.survey_stage = st.session_state.page


def set_survey_stage(stage: str):
    init_navigation_state()
    st.session_state.survey_stage = stage


def hide_streamlit_page_nav():
    st.markdown(
        """
        <style>
            [data-testid="stSidebarNav"] {display: none;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def redirect_to_current_stage():
    init_navigation_state()

    stage = st.session_state.get("survey_stage", "consent")

    if stage == "pilot" and not PILOT_MODE:
        stage = "thankyou"
        st.session_state.survey_stage = "thankyou"

    target = STAGE_TO_PAGE.get(stage, "streamlit_app.py")
    st.switch_page(target)
    st.stop()


def require_stage(*allowed_stages):
    init_navigation_state()

    current_stage = st.session_state.get("survey_stage", "consent")
    if current_stage not in allowed_stages:
        redirect_to_current_stage()
