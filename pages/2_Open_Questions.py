import streamlit as st
import streamlit.components.v1 as components
from constants import PILOT_MODE
from navigation_helpers import require_stage, set_survey_stage, hide_streamlit_page_nav

st.set_page_config(
    page_title="Final questions - Part 2",
    layout="centered",
    initial_sidebar_state="expanded"
)

hide_streamlit_page_nav()
require_stage("open")


if "data" not in st.session_state:
    st.session_state.data = {}


st.title("Final questions - Part 2")

st.write(
    "Thank you. You may now answer a few final questions about the task and the experiment."
)

st.info(
    "Please answer each statement using the scale below, where 1 means strongly disagree and 7 means strongly agree."
)

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

with st.form("post_survey_open_form"):
    st.subheader("Final questions - Part 2")

    realism_1 = st.radio(
        "1. The team interaction felt realistic.",
        likert_options,
        horizontal=True,
        index=None,
        key="open_realism_1",
    )
    realism_2 = st.radio(
        "2. I felt like I was interacting with real teammates.",
        likert_options,
        horizontal=True,
        index=None,
        key="open_realism_2",
    )
    realism_3 = st.radio(
        "3. I responded as I would in a real team situation.",
        likert_options,
        horizontal=True,
        index=None,
        key="open_realism_3",
    )
    realism_4 = st.radio(
        "4. The responses of the other team members felt natural.",
        likert_options,
        horizontal=True,
        index=None,
        key="open_realism_4",
    )

    st.markdown("---")
    st.subheader("Final questions - Part 3")

    leader_perception_1 = st.radio(
        "5. Which statement felt most applicable to the team leader?",
        [
            "The team leader showed genuine concern for the well-being of team members.",
            "The team leader focused strongly on completing the task efficiently.",
            "The team leader made decisions in a controlling or directive manner.",
        ],
        index=None,
        key="open_leader_perception_1",
    )

    leader_perception_2 = st.radio(
        "6. The leader made me feel valued.",
        likert_options,
        horizontal=True,
        index=None,
        key="open_leader_perception_2",
    )
    leader_perception_3 = st.radio(
        "7. The leader communicated in a warm and supportive way.",
        likert_options,
        horizontal=True,
        index=None,
        key="open_leader_perception_3",
    )
    leader_perception_4 = st.radio(
        "8. The leader seemed concerned with our well-being.",
        likert_options,
        horizontal=True,
        index=None,
        key="open_leader_perception_4",
    )

    feedback_1 = st.text_area(
        "9. What did you think of the experiment?",
        height=150,
        key="open_feedback_1",
    )

    feedback_2 = st.text_area(
        "10. Do you have any final thoughts or comments you would like to share?",
        height=150,
        key="open_feedback_2",
    )

    submitted = st.form_submit_button("Submit final answers")

    if submitted:
        realism_answers = [realism_1, realism_2, realism_3, realism_4]
        leader_love_answers = [
            leader_perception_2,
            leader_perception_3,
            leader_perception_4,
        ]

        if any(a is None for a in realism_answers):
            st.error("Please answer all realism questions before continuing.")
            st.stop()

        if leader_perception_1 is None:
            st.error("Please select which statement best describes the team leader.")
            st.stop()

        if any(a is None for a in leader_love_answers):
            st.error("Please answer all leader questions before continuing.")
            st.stop()

        if not feedback_1.strip():
            st.error("Please answer the question: What did you think of the experiment?")
            st.stop()

        if not feedback_2.strip():
            st.error("Please answer the question: Do you have any final thoughts or comments you would like to share?")
            st.stop()

        st.session_state.data["post_survey_open"] = {
            "realism_team_interaction": realism_1,
            "realism_social_presence": realism_2,
            "realism_behavior": realism_3,
            "realism_natural_responses": realism_4,
            "leader_perception_statement": leader_perception_1,
            "leader_made_me_feel_valued": leader_perception_2,
            "leader_warm_supportive": leader_perception_3,
            "leader_concerned_with_wellbeing": leader_perception_4,
            "open_feedback_1": feedback_1.strip(),
            "open_feedback_2": feedback_2.strip(),
        }

        if PILOT_MODE:
            st.session_state.pilot_scroll_done = False
            set_survey_stage("pilot")
            st.switch_page("pages/4_Pilot_Feedback.py")
        else:
            st.session_state.thankyou_scroll_done = False
            set_survey_stage("thankyou")
            st.switch_page("pages/3_Thank_You.py")


if "open_scroll_done" not in st.session_state:
    st.session_state.open_scroll_done = False

if not st.session_state.open_scroll_done:
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
    st.session_state.open_scroll_done = True
