import streamlit as st
import streamlit.components.v1 as components

from navigation_helpers import require_stage, set_survey_stage, hide_streamlit_page_nav


st.set_page_config(
    page_title="Final questions - Part 1",
    layout="centered",
    initial_sidebar_state="expanded"
)

hide_streamlit_page_nav()
require_stage("likert")

if "data" not in st.session_state:
    st.session_state.data = {}

st.title("Final questions - Part 1")

st.write(
    "You have completed the task. Please answer a few final questions about your experience during the task."
)

st.info("Please answer each statement using the scale below, where 1 means strongly disagree and 7 means strongly agree.")

st.markdown("**Response scale**")
scale_cols = st.columns(7)
scale_labels = [
    "Strongly disagree",
    "Disagree",
    "Somewhat disagree",
    "Neutral",
    "Somewhat agree",
    "Agree",
    "Strongly agree",
]

for i, label in enumerate(scale_labels):
    scale_cols[i].markdown(
        f"<div style='text-align:center; font-size:0.9rem; line-height:1.2;'>{label}<br><strong>{i+1}</strong></div>",
        unsafe_allow_html=True
    )

st.markdown("---")

likert_options = list(range(1, 8))

with st.form("post_survey_likert_form"):
    st.subheader("Section 1: Statements")

    q1 = st.radio("1. I felt a positive connection with the other members of my team.", likert_options, horizontal=True, index=None, key="likert_q1")
    q2 = st.radio("2. I felt motivated to work together with my team to successfully complete the task.", likert_options, horizontal=True, index=None, key="likert_q2")
    q3 = st.radio("3. I felt proud to be part of this team.", likert_options, horizontal=True, index=None, key="likert_q3")
    q4 = st.radio("4. If you make a mistake on this team, it is often held against you.", likert_options, horizontal=True, index=None, key="likert_q4")
    q5 = st.radio("5. Members of this team are able to bring up problems and tough issues.", likert_options, horizontal=True, index=None, key="likert_q5")
    q6 = st.radio("6. People on this team sometimes reject others for being different.", likert_options, horizontal=True, index=None, key="likert_q6")
    q7 = st.radio("7. It is safe to take a risk on this team.", likert_options, horizontal=True, index=None, key="likert_q7")
    q8 = st.radio("8. It is difficult to ask other members of this team for help.", likert_options, horizontal=True, index=None, key="likert_q8")
    q9 = st.radio("9. No one on this team would deliberately act in a way that undermines my efforts.", likert_options, horizontal=True, index=None, key="likert_q9")
    q10 = st.radio("10. Working with members of this team, my unique skills and talents are valued and utilized.", likert_options, horizontal=True, index=None, key="likert_q10")
    q11 = st.radio("11. Communication within the team was clear and effective during the task.", likert_options, horizontal=True, index=None, key="likert_q11")
    q12 = st.radio("12. Team members listened to and considered each other’s input.", likert_options, horizontal=True, index=None, key="likert_q12")
    q13 = st.radio("13. The team coordinated well while working on the task.", likert_options, horizontal=True, index=None, key="likert_q13")
    q14 = st.radio("14. I felt that collaboration within the team was smooth and constructive.", likert_options, horizontal=True, index=None, key="likert_q14")
    q15 = st.radio("15. Overall, I am satisfied with how the team worked together.", likert_options, horizontal=True, index=None, key="likert_q15")

    submitted = st.form_submit_button("Continue")


    if submitted:
        answers = [q1, q2, q3, q4, q5, q6, q7, q8, q9, q10, q11, q12, q13, q14, q15]

        if any(a is None for a in answers):
            st.error("Please answer all questions before continuing.")
            st.stop()

        st.session_state.data["post_survey_likert"] = {
            "q1_positive_connection": q1,
            "q2_motivated_to_work_together": q2,
            "q3_proud_to_be_part_of_team": q3,
            "q4_mistakes_held_against_you": q4,
            "q5_bring_up_problems": q5,
            "q6_reject_others_for_being_different": q6,
            "q7_safe_to_take_risk": q7,
            "q8_difficult_to_ask_for_help": q8,
            "q9_no_one_undermines_efforts": q9,
            "q10_skills_valued": q10,
            "q11_communication_clear": q11,
            "q12_listened_to_input": q12,
            "q13_team_coordinated_well": q13,
            "q14_collaboration_smooth": q14,
            "q15_satisfied_with_teamwork": q15,
        }

        st.session_state.open_scroll_done = False
        set_survey_stage("open")
        st.switch_page("pages/2_Open_Questions.py")

if "likert_scroll_done" not in st.session_state:
    st.session_state.likert_scroll_done = False

if not st.session_state.likert_scroll_done:
    components.html(
        """
        <script>
            const scrollTopNow = () => {
                try {
                    window.parent.scrollTo(0, 0);
                    window.parent.document.documentElement.scrollTop = 0;
                    window.parent.document.body.scrollTop = 0;
                } catch (e) {
                    window.scrollTo(0, 0);
                }
            };

            setTimeout(scrollTopNow, 50);
            setTimeout(scrollTopNow, 150);
            setTimeout(scrollTopNow, 300);
        </script>
        """,
        height=0,
    )
    st.session_state.likert_scroll_done = True