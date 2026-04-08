import streamlit as st
import gspread
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Thank you",
    layout="centered",
    initial_sidebar_state="expanded"
)

NASA_EXPERT_RANK = {
    "Box of matches": 15,
    "Food concentrate": 4,
    "50 feet of nylon rope": 6,
    "Parachute silk": 8,
    "Portable heating unit": 13,
    "Two .45 caliber pistols": 11,
    "One case of dehydrated milk": 12,
    "Two 100-lb tanks of oxygen": 1,
    "Stellar map (of the moon's constellations)": 3,
    "Self-inflating life raft": 9,
    "Magnetic compass": 14,
    "5 gallons of water": 2,
    "Signal flares": 10,
    "First aid kit (including injection needle)": 7,
    "Solar-powered FM receiver-transmitter": 5,
}

def compute_nasa_score(user_ranking):
    score = 0
    for item, correct_rank in NASA_EXPERT_RANK.items():
        user_rank = user_ranking.get(item)
        if user_rank is not None:
            score += abs(user_rank - correct_rank)
    return score

def connect_to_gsheet():
    gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
    sheet = gc.open(st.secrets["sheets"]["spreadsheet_name"]).sheet1
    return sheet

def save_to_gsheet(data):
    sheet = connect_to_gsheet()

    column_order = [
        "participant_id",
        "leadership_style",
        "prime",
        "priming_text",
        "age_category",
        "gender",
        "country",
        "nasa_score",
        "discussion_log",
        "q1_positive_connection",
        "q2_motivated_to_work_together",
        "q3_proud_to_be_part_of_team",
        "q4_mistakes_held_against_you",
        "q5_bring_up_problems",
        "q6_reject_others_for_being_different",
        "q7_safe_to_take_risk",
        "q8_difficult_to_ask_for_help",
        "q9_no_one_undermines_efforts",
        "q10_skills_valued",
        "q11_communication_clear",
        "q12_listened_to_input",
        "q13_team_coordinated_well",
        "q14_collaboration_smooth",
        "q15_satisfied_with_teamwork",
        "realism_team_interaction",
        "realism_social_presence",
        "realism_behavior",
        "realism_natural_responses",
        "leader_perception_statement",
        "open_feedback_1",
        "open_feedback_2",
        "pilot_device",
        "pilot_clarity",
        "pilot_realism",
        "pilot_flow",
        "pilot_length",
        "pilot_unclear_parts",
        "pilot_technical_issues",
        "pilot_unrealistic_parts",
        "pilot_instructions_feedback",
        "pilot_missing_feedback",
        "pilot_improve_first",
        "pilot_final_suggestions",
    ]

    row = [data.get(col, "") for col in column_order]
    existing_values = sheet.get_all_values()

    if not existing_values:
        sheet.append_row(column_order)

    sheet.append_row(row)

if "data" not in st.session_state:
    st.session_state.data = {}

if "participant_id" not in st.session_state:
    st.session_state.participant_id = None

if st.session_state.data.get("nasa_score") is None and st.session_state.data.get("nasa_ranking"):
    st.session_state.data["nasa_score"] = compute_nasa_score(
        st.session_state.data["nasa_ranking"]
    )

if "saved" not in st.session_state:
    st.session_state.saved = False

if not st.session_state.saved:
    participant_data = {
        "participant_id": st.session_state.get("participant_id"),
        "leadership_style": st.session_state.data.get("leadership_style"),
        "prime": st.session_state.data.get("prime"),
        "priming_text": st.session_state.data.get("priming_text"),
        "age_category": st.session_state.data.get("age_category"),
        "gender": st.session_state.data.get("gender"),
        "country": st.session_state.data.get("country"),
        "nasa_score": st.session_state.data.get("nasa_score"),
        "discussion_log": st.session_state.data.get("discussion_log", ""),
        **st.session_state.data.get("post_survey_likert", {}),
        **st.session_state.data.get("post_survey_open", {}),

        # pilot feedback fields
        "pilot_device": st.session_state.data.get("pilot_device"),
        "pilot_clarity": st.session_state.data.get("pilot_clarity"),
        "pilot_realism": st.session_state.data.get("pilot_realism"),
        "pilot_flow": st.session_state.data.get("pilot_flow"),
        "pilot_length": st.session_state.data.get("pilot_length"),
        "pilot_unclear_parts": st.session_state.data.get("pilot_unclear_parts"),
        "pilot_technical_issues": st.session_state.data.get("pilot_technical_issues"),
        "pilot_unrealistic_parts": st.session_state.data.get("pilot_unrealistic_parts"),
        "pilot_instructions_feedback": st.session_state.data.get("pilot_instructions_feedback"),
        "pilot_missing_feedback": st.session_state.data.get("pilot_missing_feedback"),
        "pilot_improve_first": st.session_state.data.get("pilot_improve_first"),
        "pilot_final_suggestions": st.session_state.data.get("pilot_final_suggestions"),
    }

    save_to_gsheet(participant_data)
    st.session_state.saved = True

score = st.session_state.data.get("nasa_score")

st.title("Thank you for participating 🚀")

st.write(
    "Your responses have been recorded successfully. You have completed the experiment. Your participation was highly valued! If you'd like, you can see how your ranking compares to NASA’s expert solution below:"
)

st.subheader("🧠 Your performance")
st.write(f"Your NASA score: **{score}** (lower = better)")

if score is None:
    st.warning("NASA score could not be calculated.")
else:
    if score <= 25:
        feedback = "🌟 Excellent — you would likely survive the mission!"
    elif score <= 32:
        feedback = "👍 Good — strong survival reasoning."
    elif score <= 45:
        feedback = "👌 Average — not bad, but some key improvements possible."
    elif score <= 55:
        feedback = "⚠️ Fair — your choices relied partly on incorrect assumptions."
    elif score <= 70:
        feedback = "🚨 Not good — suggests use of Earth-based logic."
    else:
        feedback = "💀 Very poor — you might not survive this mission..."

    st.info(feedback)

st.subheader("📊 NASA expert ranking")
nasa_sorted = sorted(NASA_EXPERT_RANK.items(), key=lambda x: x[1])

for item, rank in nasa_sorted:
    st.write(f"**#{rank}** — {item}")

st.subheader("🧪 Why these answers?")
with st.expander("Click to see explanations"):
    st.write(
        '''
Here are a few key insights from NASA’s reasoning:

- **Oxygen (#1)** is the most critical resource for survival.  
- **Water (#2)** is essential due to rapid dehydration.  
- **Stellar map (#3)** works for navigation, unlike a compass.  
- **Matches (#15)** are useless — there is no oxygen on the moon.  
- **Magnetic compass (#14)** does not function because the moon has no magnetic field.

Many incorrect choices come from applying **Earth-based logic** in an environment where conditions are completely different.

This exercise was originally developed by NASA to study decision-making and teamwork under pressure.
'''
    )

if "thankyou_scroll_done" not in st.session_state:
    st.session_state.thankyou_scroll_done = False

if not st.session_state.thankyou_scroll_done:
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
    st.session_state.thankyou_scroll_done = True