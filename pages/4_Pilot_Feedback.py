import streamlit as st
import streamlit.components.v1 as components
from constants import PILOT_MODE
from navigation_helpers import require_stage, set_survey_stage, hide_streamlit_page_nav

st.set_page_config(
    page_title="Pilot Feedback",
    layout="centered",
    initial_sidebar_state="expanded"
)

hide_streamlit_page_nav()
require_stage("pilot")

def page_pilot_feedback():
    # Safety check: if pilot mode is off, skip this page
    if not PILOT_MODE:
        st.session_state.thankyou_scroll_done = False
        set_survey_stage("thankyou")
        st.switch_page("pages/3_Thank_You.py")
        return

    st.title("Pilot testing feedback😄")
    st.info(
        "You are seeing this page because you are participating in the pilot test. "
        "These questions are only for pilot participants and help improve the experiment before the actual study. "
        "After answering these questions, you will see the result of the NASA task you just did."
    )

    st.write(
        "Please answer the questions below as honestly and specifically as possible. "
        "Critical feedback is very helpful here."
    )

    with st.form("pilot_feedback_form"):
        st.subheader("General pilot feedback")

        device = st.radio(
            "1. Which type of device are you using now",
            [
                "Mobile",
                "Laptop",
                "Tablet",
                "Something else",
            ],
            index=None,
        )

        clarity = st.radio(
            "2. How clear was the experiment overall?",
            [
                "Very unclear",
                "Somewhat unclear",
                "Neutral",
                "Mostly clear",
                "Very clear",
            ],
            index=None,
        )

        realism = st.radio(
            "3. How realistic did the team chat feel?",
            [
                "Very unrealistic",
                "Somewhat unrealistic",
                "Neutral",
                "Mostly realistic",
                "Very realistic",
            ],
            index=None,
        )

        flow = st.radio(
            "4. Did the flow of the experiment make sense?",
            [
                "Not at all",
                "Mostly no",
                "Neutral",
                "Mostly yes",
                "Completely yes",
            ],
            index=None,
        )

        length = st.radio(
            "5. How did the length of the experiment feel?",
            [
                "Much too short",
                "A bit too short",
                "About right",
                "A bit too long",
                "Much too long",
            ],
            index=None,
        )

        st.subheader("Improvement questions")

        unclear_parts = st.text_area(
            "5. Was anything unclear? If yes, what exactly was unclear?",
            height=120
        )

        technical_issues = st.text_area(
            "6. Did you experience any technical issues or bugs? If yes, describe them.",
            height=120
        )

        unrealistic_parts = st.text_area(
            "7. Did any part of the chat feel unrealistic, repetitive, or strange? If yes, which part(s)?",
            height=120
        )

        instructions_feedback = st.text_area(
            "8. What do you think about the instructions? What should be improved?",
            height=120
        )

        missing_feedback = st.text_area(
            "9. Was there any question, explanation, or feature missing that would have helped you?",
            height=120
        )

        improve_first = st.text_area(
            "10. If I could improve only one thing before launching the real experiment, what should it be?",
            height=120
        )

        final_suggestions = st.text_area(
            "11. Any other comments or suggestions for improving the experiment?",
            height=140
        )

        submitted = st.form_submit_button("Submit pilot feedback")

    if submitted:
        # Save into session_state.data
        if "data" not in st.session_state:
            st.session_state.data = {}

        st.session_state.data["pilot_device"] = device
        st.session_state.data["pilot_clarity"] = clarity
        st.session_state.data["pilot_realism"] = realism
        st.session_state.data["pilot_flow"] = flow
        st.session_state.data["pilot_length"] = length
        st.session_state.data["pilot_unclear_parts"] = unclear_parts.strip()
        st.session_state.data["pilot_technical_issues"] = technical_issues.strip()
        st.session_state.data["pilot_unrealistic_parts"] = unrealistic_parts.strip()
        st.session_state.data["pilot_instructions_feedback"] = instructions_feedback.strip()
        st.session_state.data["pilot_missing_feedback"] = missing_feedback.strip()
        st.session_state.data["pilot_improve_first"] = improve_first.strip()
        st.session_state.data["pilot_final_suggestions"] = final_suggestions.strip()

        st.session_state.thankyou_scroll_done = False
        st.switch_page("pages/3_Thank_You.py")

page_pilot_feedback()

if "pilot_scroll_done" not in st.session_state:
    st.session_state.pilot_scroll_done = False

if not st.session_state.pilot_scroll_done:
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
    st.session_state.pilot_scroll_done = True