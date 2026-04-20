import streamlit as st
import gspread
import streamlit.components.v1 as components
from datetime import datetime, timezone
from constants import EXPERIMENT_VERSION
from navigation_helpers import require_stage, set_survey_stage, hide_streamlit_page_nav


st.set_page_config(
    page_title="Thank you",
    layout="centered",
    initial_sidebar_state="expanded"
)

hide_streamlit_page_nav()
require_stage("thankyou", "done")


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




NASA_EXPLANATIONS = {
    "Two 100-lb tanks of oxygen": "Oxygen is the most important item because breathing is the first priority for survival.",
    "5 gallons of water": "Water is essential to prevent dehydration and stay alive during the journey.",
    "Stellar map (of the moon's constellations)": "The stellar map helps with navigation on the moon, where normal Earth tools are less useful.",
    "Food concentrate": "Food gives energy, but it is slightly less urgent than oxygen, water, and navigation.",
    "Solar-powered FM receiver-transmitter": "The transmitter may help with communication and rescue, especially because it is solar-powered.",
    "50 feet of nylon rope": "The rope is useful for climbing, pulling, tying, and helping injured team members move.",
    "First aid kit (including injection needle)": "The first aid kit can help treat injuries and keep the crew in better condition.",
    "Parachute silk": "Parachute silk can be used for protection from the sun or for carrying materials.",
    "Self-inflating life raft": "The life raft can be used to carry equipment or people across the moon surface.",
    "Signal flares": "Signal flares have some use, but they are less important than the stronger survival and navigation items.",
    "Two .45 caliber pistols": "The pistols have limited use and are not major survival tools in this situation.",
    "One case of dehydrated milk": "Dehydrated milk is less useful because it needs water, and water is too valuable.",
    "Portable heating unit": "The heating unit is not very important because the trip is expected to happen on the sunlit side of the moon.",
    "Magnetic compass": "A magnetic compass is almost useless on the moon because the moon does not have a magnetic field like Earth.",
    "Box of matches": "Matches are useless because there is no oxygen-rich atmosphere on the moon to make them burn.",
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
        "submitted_at_utc",
        "experiment_version",
        "leadership_style",
        "prime",
        "priming_text",
        "age_category",
        "gender",
        "education_level",
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
        "leader_made_me_feel_valued",
        "leader_warm_supportive",
        "leader_concerned_with_wellbeing",
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
        "submitted_at_utc": datetime.now(timezone.utc).isoformat(),
        "experiment_version": EXPERIMENT_VERSION,
        "leadership_style": st.session_state.data.get("leadership_style"),
        "prime": st.session_state.data.get("prime"),
        "priming_text": st.session_state.data.get("priming_text"),
        "age_category": st.session_state.data.get("age_category"),
        "gender": st.session_state.data.get("gender"),
        "education_level": st.session_state.data.get("education_level"),
        "country": st.session_state.data.get("country"),
        "nasa_score": st.session_state.data.get("nasa_score"),
        "discussion_log": st.session_state.data.get("discussion_log", ""),
        **st.session_state.data.get("post_survey_likert", {}),
        **st.session_state.data.get("post_survey_open", {}),
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


    try:
        save_to_gsheet(participant_data)
        st.session_state.saved = True
        set_survey_stage("done")
    except Exception as e:
        st.error("Your responses could not be saved correctly. Please contact me at +31657346173 and do not close this page yet.")
        st.stop()




score = st.session_state.data.get("nasa_score")


st.title("Thank you for participating 🚀")


st.write(
    "Your responses have been recorded successfully. You have completed the experiment. "
    "Thank you for your participation. Below, you can compare your ranking with NASA’s expert solution."
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
        feedback = "👌 Average — not bad, but some key improvements are possible."
    elif score <= 55:
        feedback = "⚠️ Fair — some choices were based on incorrect assumptions."
    elif score <= 70:
        feedback = "🚨 Not good — this suggests Earth-based logic was used too often."
    else:
        feedback = "💀 Very poor — survival would be unlikely with this ranking."


    st.info(feedback)


st.subheader("📊 NASA expert ranking")
nasa_sorted = sorted(NASA_EXPERT_RANK.items(), key=lambda x: x[1])


for item, rank in nasa_sorted:
    st.write(f"**#{rank}** — {item}")


st.subheader("🧪 Why these answers?")
with st.expander("Click to see the full explanation for all 15 items"):
    for item, rank in nasa_sorted:
        explanation = NASA_EXPLANATIONS.get(item, "No explanation available.")
        st.markdown(f"**#{rank} — {item}**")
        st.caption(explanation)


    st.markdown("---")
    st.write(
        "Many mistakes in this task happen because people use **Earth-based logic** "
        "in a moon environment, where conditions are very different."
    )
    st.write(
        "This exercise was originally developed by NASA to study decision-making "
        "and teamwork under pressure."
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

