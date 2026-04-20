import streamlit as st
import random
import uuid
import time
from streamlit_autorefresh import st_autorefresh

from constants import (
    LEADERSHIP_STYLES,
    PRIMES,
    NASA_ITEMS,
    NASA_EXPERT_RANK,
    LEADER_OPENING,
    LEADER_HINTS,
    GOOD_TOP_ITEMS,
    BAD_TOP_ITEMS,
)

from text_parsing import (
    extract_items_from_text,
    classify_proposal,
    parse_message_features,
    normalize_text,
)

from ranking_helpers import (
    init_ranking_helper_state,
    update_group_rank_memory_from_message,
    update_slot_memory_from_message,
    format_slot_memory,
    format_group_rank_memory,
    get_ui_ranking_summary,
    detect_ui_rank_changes,
    store_ui_rank_changes,
    store_pending_ui_rank_changes,
    get_pending_ui_rank_changes,
    clear_pending_ui_rank_changes,
    get_available_ranks_for_item,
)

from chat_logic import (
    leader_reply,
    teammate_reply_persona,
    ui_rank_change_reaction,
    detect_bad_teammate_claim,
    leader_reply_to_teammate,
    should_trigger_team_micro_conflict,
    build_team_micro_conflict,
    choose_speaking_flow,
    extract_named_teammates_from_text,
    recent_role_messages,
    get_next_slot_text,
    is_david_hurry_message,
)

from navigation_helpers import (
    init_navigation_state,
    set_survey_stage,
    hide_streamlit_page_nav,
)

st.set_page_config(
    page_title="Leadership styles",
    layout="centered",
    initial_sidebar_state="expanded"
)

hide_streamlit_page_nav()


# ----------------------------
# Helpers
# ----------------------------


def format_discussion_log():
    chat = st.session_state.get("chat", [])
    if not chat:
        return ""

    lines = []
    for msg in chat:
        role = msg.get("role", "")
        text = msg.get("text", "")
        lines.append(f"{role}: {text}")

    return "\n".join(lines)


def reset_discussion_state(preserve_chat=False):
    leadership_style = st.session_state.condition[0]

    if not preserve_chat:
        st.session_state.chat = []
        leader_intro = LEADER_OPENING.get(leadership_style)
        if leader_intro:
            st.session_state.chat.append({
                "role": "Leader",
                "text": leader_intro
            })

    st.session_state.turns = 0
    st.session_state.suggested_items = []
    st.session_state.teammate_step = 0
    st.session_state.last_bot_msg = ""
    st.session_state.leader_hint_index = 0

    st.session_state.pending_bot_msgs = []
    st.session_state.bot_reveal_active = False
    st.session_state.typing_role = None
    st.session_state.next_reveal_time = 0.0
    st.session_state.first_bot_reply_sent = False
    st.session_state.last_speaking_flow = None
    st.session_state.last_user_chat_time = 0.0


    st.session_state.teammate_memory = {
        "Anna": {"likes": set(), "dislikes": set()},
        "Bas": {"likes": set(), "dislikes": set()},
        "Carlos": {"likes": set(), "dislikes": set()},
        "David": {"likes": set(), "dislikes": set()},
        "Emily": {"likes": set(), "dislikes": set()},
    }

    if "group_rank_memory" in st.session_state:
        st.session_state.group_rank_memory = {}

    st.session_state.slot_memory = {
        "resolved": {},
        "tentative": {},
        "current_focus_slot": None,
        "current_focus_item": None,
    }

    st.session_state.last_seen_ui_ranking = {item: None for item in NASA_ITEMS}
    st.session_state.recent_ui_rank_changes = []
    st.session_state.pending_ui_rank_changes = []
    st.session_state.last_ui_reaction_turn = -999
    st.session_state.last_ui_reaction_time = 0.0
    st.session_state.david_hurry_count = 0
    st.session_state.team_micro_conflict_used = False
    st.session_state.last_micro_conflict_turn = -999


def init_discussion_state():
    leadership_style = st.session_state.condition[0]

    init_ranking_helper_state()

    if "teammate_memory" not in st.session_state:
        st.session_state.teammate_memory = {
            "Anna": {"likes": set(), "dislikes": set()},
            "Bas": {"likes": set(), "dislikes": set()},
            "Carlos": {"likes": set(), "dislikes": set()},
            "David": {"likes": set(), "dislikes": set()},
            "Emily": {"likes": set(), "dislikes": set()},
        }

    if "chat" not in st.session_state:
        st.session_state.chat = []

        leader_intro = LEADER_OPENING.get(leadership_style)
        if leader_intro:
            st.session_state.chat.append({
                "role": "Leader",
                "text": leader_intro
            })

    if "turns" not in st.session_state:
        st.session_state.turns = 0
    if "suggested_items" not in st.session_state:
        st.session_state.suggested_items = []
    if "teammate_step" not in st.session_state:
        st.session_state.teammate_step = 0
    if "last_bot_msg" not in st.session_state:
        st.session_state.last_bot_msg = ""
    if "leader_hint_index" not in st.session_state:
        st.session_state.leader_hint_index = 0

    if "pending_bot_msgs" not in st.session_state:
        st.session_state.pending_bot_msgs = []
    if "bot_reveal_active" not in st.session_state:
        st.session_state.bot_reveal_active = False
    if "typing_role" not in st.session_state:
        st.session_state.typing_role = None
    if "next_reveal_time" not in st.session_state:
        st.session_state.next_reveal_time = 0.0
    if "first_bot_reply_sent" not in st.session_state:
        st.session_state.first_bot_reply_sent = False
    if "last_speaking_flow" not in st.session_state:
        st.session_state.last_speaking_flow = None
    if "last_user_chat_time" not in st.session_state:
        st.session_state.last_user_chat_time = 0.0
    if "david_hurry_count" not in st.session_state:
        st.session_state.david_hurry_count = 0
    if "team_micro_conflict_used" not in st.session_state:
        st.session_state.team_micro_conflict_used = False
    if "last_micro_conflict_turn" not in st.session_state:
        st.session_state.last_micro_conflict_turn = -999


def clear_discussion():
    reset_discussion_state(preserve_chat=False)

    if "user_message" in st.session_state:
        del st.session_state["user_message"]


def add_msg(role, text):
    st.session_state.chat.append({"role": role, "text": text})


def get_typing_delay_for_role(role):
    # Make the very first bot reply almost immediate
    if not st.session_state.get("first_bot_reply_sent", False):
        return random.uniform(0.15, 0.35)

    if role == "Leader":
        return random.uniform(1.8, 2.8)
    elif role == "Anna":
        return random.uniform(1.2, 2.0)
    elif role == "Emily":
        return random.uniform(1.3, 2.1)
    elif role == "David":
        return random.uniform(1.0, 1.7)
    elif role == "Carlos":
        return random.uniform(0.9, 1.5)
    elif role == "Bas":
        return random.uniform(0.8, 1.4)
    return random.uniform(1.0, 1.8)


def process_pending_bot_messages():
    now = time.time()

    if not st.session_state.pending_bot_msgs:
        st.session_state.bot_reveal_active = False
        st.session_state.typing_role = None
        st.session_state.next_reveal_time = 0.0
        return

    if not st.session_state.bot_reveal_active:
        next_role, _ = st.session_state.pending_bot_msgs[0]
        st.session_state.bot_reveal_active = True
        st.session_state.typing_role = next_role
        st.session_state.next_reveal_time = now + get_typing_delay_for_role(next_role)
        return

    if now >= st.session_state.next_reveal_time:
        role, text = st.session_state.pending_bot_msgs.pop(0)
        add_msg(role, text)
        st.session_state.last_bot_msg = text
        st.session_state.first_bot_reply_sent = True

        if st.session_state.pending_bot_msgs:
            next_role, _ = st.session_state.pending_bot_msgs[0]
            st.session_state.typing_role = next_role
            st.session_state.next_reveal_time = now + get_typing_delay_for_role(next_role)
        else:
            st.session_state.bot_reveal_active = False
            st.session_state.typing_role = None
            st.session_state.next_reveal_time = 0.0


def init_session():
    init_navigation_state()
 
    if "participant_id" not in st.session_state:
        st.session_state.participant_id = str(uuid.uuid4())

    if "condition" not in st.session_state:
        st.session_state.condition = (
            random.choice(LEADERSHIP_STYLES),
            random.choice(PRIMES),
        )

    if "page" not in st.session_state:
        st.session_state.page = "consent"

    if "data" not in st.session_state:
        st.session_state.data = {}

    if "participant_id" not in st.session_state.data:
        st.session_state.data["participant_id"] = st.session_state.participant_id

    if "saved" not in st.session_state:
        st.session_state.saved = False

    if "show_clear_warning" not in st.session_state:
        st.session_state.show_clear_warning = False

init_session()

leadership, prime = st.session_state.condition

# ----------------------------
# Pages
# ----------------------------
def page_consent():
    st.title("Leadership — Study")

    st.write("""
 Dear respondent, 
             
Thank you in advance for filling in this survey, and therefore participating in this research conducted by a master student at Erasmus University Rotterdam. This research aims to investigate the relationship between leadership and team performance.

First, some general information is needed, afterwards you will complete a short writing tasks and a group decision-making task. Lastly, a short survey is presented in which you can talk about your experience of the experiment. Your participation in this research is highly valued. 
             
The entire experiment will take about 15 to 20 minutes, and the data will be used for research purposes only. The experiment is done anonymously. The responses will be kept confidential and will not be shared with any third parties. Moreover, the main language for the experiment is English, there are no right or wrong answers, and you are free to stop the experiment at any moment.  

For further information or questions, feel free to send an email to Nora Remijnse at 569443gr@eur.nl. 
 
Please select the “I consent to participate in this study” box below if you: 

- Are above 18 years old 
- Have read the information above and agree to this 

    """)

    st.subheader("Consent")
    consent = st.checkbox("I consent to participate in this study.")

    st.subheader("Demographics")

    age_category = st.selectbox(
        "What is your age?",
        [
            "18–24",
            "25–34",
            "35–44",
            "45–54",
            "55–64",
            "65+",
            "Prefer not to say",
        ],
        index=None,
        placeholder="Select an option",
    )

    gender = st.selectbox(
        "What is your gender?",
        [
            "Male",
            "Female",
            "Non-binary",
            "Prefer not to say",
        ],
        index=None,
        placeholder="Select an option",
    )

    education_level = st.selectbox(
        "What is your highest completed level of education?",
        [
            "Primary or middle secondary education (Dutch: primary school / VMBO)",
            "Upper secondary or practice-oriented education (Dutch: HAVO / VWO / MBO)",
            "Higher professional or undergraduate university education (Dutch: HBO bachelor/master / WO bachelor)",
            "Graduate university education (Dutch: WO master / PhD)",
            "Prefer not to say",
        ],
        index=None,
        placeholder="Select an option",
    )

    country = st.text_input("What is your nationality?")

    if st.button("Next"):
        if not consent:
            st.error("Please provide consent to continue.")
            return

        if age_category is None:
            st.error("Please select your age before continuing.")
            return

        if gender is None:
            st.error("Please select your gender before continuing.")
            return

        if education_level is None:
            st.error("Please select your highest completed level of education before continuing.")
            return

        if not country.strip():
            st.error("Please fill in your country before continuing.")
            return

        st.session_state.saved = False
        st.session_state.data["participant_id"] = st.session_state.participant_id
        st.session_state.data["consent"] = True
        st.session_state.data["age_category"] = age_category
        st.session_state.data["gender"] = gender
        st.session_state.data["education_level"] = education_level
        st.session_state.data["country"] = country.strip()

        st.session_state.page = "priming"
        set_survey_stage("priming")
        st.rerun()


def page_priming():
    st.title("Writing task")

    if prime == "love":
        prompt = "Please write about a situation in which you would feel cared for / loved."
    else:
        prompt = "Please write directions to the supermarket nearest to your home."

    st.write(prompt)
    st.caption("You may write this part in either English or Dutch")
    text = st.text_area("Your response", height=200)

    st.caption("Minimum 100 characters to continue.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Back"):
            st.session_state.page = "consent"
            set_survey_stage("consent")
            st.rerun()

    with col2:
        if st.button("Next"):
            if len(text.strip()) < 100:
                st.error("Please write a bit more (at least 100 characters).")
                return
            st.session_state.data["priming_text"] = text.strip()
            st.session_state.page = "task"
            set_survey_stage("task")
            st.rerun()


def compute_nasa_score(user_ranking):
    score = 0
    for item, correct_rank in NASA_EXPERT_RANK.items():
        user_rank = user_ranking.get(item)
        if user_rank is not None:
            score += abs(user_rank - correct_rank)
    return score


def render_task_sidebar():
    st.sidebar.header("Controls")
    st.sidebar.caption(f"Messages sent: {st.session_state.turns} / 2")

    if st.sidebar.button("🧹 Clear discussion", key="clear_discussion_btn"):
        st.session_state.show_clear_warning = True

    if st.session_state.get("show_clear_warning"):
        st.sidebar.warning("⚠️ This will reset the conversation AND team memory.")

        col1, col2 = st.sidebar.columns(2)
        with col1:
            if st.button("Yes, reset", key="confirm_reset_btn"):
                clear_discussion()
                st.session_state.show_clear_warning = False
                st.rerun()
        with col2:
            if st.button("Cancel", key="cancel_reset_btn"):
                st.session_state.show_clear_warning = False
                st.rerun()

    st.sidebar.subheader("📝 Notes (optional)")
    st.sidebar.text_area(
        "Write down your thoughts here",
        height=150,
        key="user_notes"
    )


def render_task_instructions():
    with st.expander("Instructions", expanded=True):
        st.write("""
You are now starting the experiment.

Please take your time and make sure you are in a quiet place where you will not be distracted. You may use pencil and paper to make notes if you want.

Try to stay focused during the task.

Good luck, and have fun! 🚀

---

**Scenario 🌕**

Imagine the following situation:

Your spaceship has crash-landed on the sunlit side of the moon.
The ship is damaged, so you cannot use it for transport or communication.
You do not have contact with rescue.
Base your decisions only on the 15 items shown below.

Your goal is to decide which items are **most important for survival** until help arrives.

---

**Step 1 – Team discussion 🗣️**

You are working together with a team that includes:
- 1 leader
- 5 other team members
- you

Use the chat to discuss the items.

You can:
- say which items you think are important
- react to what others say
- work together with the team to decide on the ranking

Please send **at least 2 chat messages** before the ranking section opens. 💬

---

**Step 2 – Final ranking 🔢**

After the discussion, **you** submit the final ranking yourself.

- Rank all 15 items
- **1 = most important**
- **15 = least important**
- You can use each number only **once**

**You may already start filling in the ranking during the discussion. The team members may comment on your choices.**

---

**Step 3 – Submit your answers ✅**

When you are done:

- check your ranking carefully
- make sure each number is used once

Then click **Submit ranking** to continue.
""")


def render_items_reference():
    st.subheader("Items")
    with st.container():
        for i, item in enumerate(NASA_ITEMS, start=1):
            st.write(f"{i}. {item}")

    st.divider()
    st.caption(f"Messages sent: **{st.session_state.turns} / 2**")


def is_wrong_or_weak_message(text, mentioned, label):
    lower = text.lower().strip()

    return (
        label == "bad" or
        (mentioned and any(item in BAD_TOP_ITEMS for item in mentioned)) or
        ("matches" in lower) or
        ("heating" in lower) or
        ("milk" in lower and any(x in lower for x in ["4", "3", "top", "high"])) or
        ("food" in lower and "#1" in lower) or
        ("food" in lower and "number 1" in lower)
    )


def page_task():
    st.title("NASA Moon Survival Task")

    # --- Initialize discussion state ---
    init_discussion_state()

    render_task_sidebar()
    render_task_instructions()

    st.caption("After at least 2 chat messages, the ranking section unlocks. You submit the final top 15, made together with your team.")

    # --- Layout: chat left, items right ---
    left, right = st.columns([2, 1], gap="large")

    # ----------------------------
    # RIGHT COLUMN: items reference + controls
    # ----------------------------
    with right:
        render_items_reference()

    # ----------------------------
    # LEFT COLUMN: chat
    # ----------------------------
    with left:
        st.subheader("Team chat")
        ui_slots = get_ui_ranking_summary()
        remembered_slots = format_slot_memory()
        remembered_positions = format_group_rank_memory()

        if ui_slots:
            st.caption(f"Current selected ranks: {ui_slots}")
        elif remembered_slots:
            st.caption(f"Current team slots: {remembered_slots}")
        elif remembered_positions:
            st.caption(f"Current team ideas: {remembered_positions}")

        process_pending_bot_messages()

        if st.session_state.bot_reveal_active:
            st_autorefresh(interval=300, key="bot_queue_refresh")

        # Render normal Streamlit chat
        for msg in st.session_state.get("chat", []):
            with st.chat_message("user" if msg["role"] == "You" else "assistant"):
                st.markdown(f"**{msg['role']}:** {msg['text']}")

        if st.session_state.bot_reveal_active and st.session_state.typing_role:
            st.caption(f"{st.session_state.typing_role} is typing...")

        user_text = st.chat_input(
            "Type your message…",
            disabled=st.session_state.bot_reveal_active
        )

        if user_text:
            text = user_text.strip()

            if not text:
                st.rerun()

            # store participant message
            add_msg("You", text)
            st.session_state.turns += 1
            st.session_state.last_user_chat_time = time.time()

            # prevent old dropdown reactions from surfacing much later in unrelated discussion
            clear_pending_ui_rank_changes()

            # extract items mentioned
            mentioned = extract_items_from_text(text)

            # update teammate memory
            for tm in st.session_state.teammate_memory:
                for item in mentioned:
                    if item in GOOD_TOP_ITEMS:
                        st.session_state.teammate_memory[tm]["likes"].add(item)
                    elif item in BAD_TOP_ITEMS:
                        st.session_state.teammate_memory[tm]["dislikes"].add(item)

            # update shared rank memory
            update_group_rank_memory_from_message(text, mentioned)
            update_slot_memory_from_message(text, mentioned)

            # classify
            label, info = classify_proposal(mentioned)

            # --- Parse message features once ---
            features = parse_message_features(text)
            normalized_user_text = normalize_text(text)

            meta_intent = features["meta_intent"]
            question_type = features["question_type"]
            explicit_slot = features["slot_request"]
            asking_direct_item = features["direct_item_question"]
            lower = features["normalized_text"]

            repeated_slot_asking = sum(
                1 for msg in st.session_state.get("chat", [])
                if msg.get("role") == "You"
                and parse_message_features(msg.get("text", "")).get("slot_request") is not None
            )

            slot_prompt_starters = (
                "what should be number",
                "what should number",
                "what is number",
                "what about number",
                "and number",
                "what is #",
                "what is ",
                "and ",
            )

            user_is_only_asking_for_slot = explicit_slot is not None and not mentioned

            is_lazy_ranking = (
                user_is_only_asking_for_slot
                and (
                    repeated_slot_asking >= 2
                    or normalized_user_text.startswith(slot_prompt_starters)
                )
                and st.session_state.turns >= 3
            )

            wrong_or_weak = is_wrong_or_weak_message(text, mentioned, label)

            if is_lazy_ranking:
                leader_text = {
                    "servant": (
                        "I’d like us to avoid filling the ranking one slot at a time. "
                        "Tell me which item you think belongs in that range, and we’ll react to your reasoning."
                    ),
                    "task_focused": (
                        "Do not ask for each slot individually. "
                        "Propose the item you think belongs there and give a short reason."
                    ),
                    "authoritarian": (
                        "Stop asking for each slot one by one. "
                        "State the item you would place there and justify it."
                    ),
                }[leadership]
            else:
                leader_text = leader_reply(leadership, text)

            step = st.session_state.teammate_step
            last_bot = st.session_state.last_bot_msg
            all_teammates = ["Anna", "Bas", "Carlos", "David", "Emily"]
            addressed_teammates = extract_named_teammates_from_text(text)

            short_simple_input = (
                len(text.strip()) < 24 and
                len(mentioned) <= 1 and
                question_type in ["item_check", "confirmation", "none"] and
                meta_intent == "none"
            )

            reasoning_themes = features["reasoning_themes"]

            def recent_teammates_used(n=6):
                recent = []
                for msg in reversed(st.session_state.get("chat", [])):
                    role = msg.get("role")
                    if role in all_teammates and role not in recent:
                        recent.append(role)
                    if len(recent) >= n:
                        break
                return recent

            def last_teammate_used():
                for msg in reversed(st.session_state.get("chat", [])):
                    if msg.get("role") in all_teammates:
                        return msg.get("role")
                return None

            def choose_distinct(pool, k):
                chosen = []
                recent = recent_teammates_used()
                last_used = last_teammate_used()

                ranked_pool = sorted(
                    pool,
                    key=lambda tm: (
                        tm == last_used,
                        tm in recent[:2],
                        tm in recent[:4],
                        all_teammates.index(tm)
                    )
                )

                for tm in ranked_pool:
                    if tm not in chosen:
                        chosen.append(tm)
                    if len(chosen) == k:
                        break

                for tm in all_teammates:
                    if tm not in chosen and tm in pool:
                        chosen.append(tm)
                    if len(chosen) == k:
                        break

                return chosen

            def choose_teammates(
                user_text,
                mentioned,
                label,
                question_type,
                meta_intent,
                explicit_slot,
                asking_direct_item,
                short_simple_input,
                is_lazy_ranking,
                addressed_teammates,
                reasoning_themes,
            ):
                wrong_or_weak_local = is_wrong_or_weak_message(user_text, mentioned, label)
                named_targets = [tm for tm in addressed_teammates if tm in all_teammates]

                if named_targets:
                    num_teammates = 1
                elif meta_intent in ["confused", "next_step", "boundary_check", "scenario_question"]:
                    num_teammates = random.choice([2, 2, 3])
                elif explicit_slot is not None:
                    num_teammates = random.choice([2, 2, 3])
                elif asking_direct_item:
                    num_teammates = random.choice([2, 2, 3])
                elif short_simple_input:
                    num_teammates = random.choice([1, 2])
                elif is_lazy_ranking:
                    num_teammates = random.choice([1, 2])
                elif wrong_or_weak_local:
                    num_teammates = random.choice([2, 3])
                else:
                    num_teammates = random.choice([2, 3])

                if named_targets:
                    primary = named_targets[0]
                    target_sets = {
                        "Anna": [["Anna", "Emily"], ["Anna", "David"], ["Anna", "Carlos"]],
                        "Bas": [["Bas", "Emily"], ["Bas", "Carlos"], ["Bas", "Anna"]],
                        "Carlos": [["Carlos", "Anna"], ["Carlos", "Emily"], ["Carlos", "David"]],
                        "David": [["David", "Emily"], ["David", "Anna"], ["David", "Carlos"]],
                        "Emily": [["Emily", "Anna"], ["Emily", "David"], ["Emily", "Carlos"]],
                    }
                    candidate_sets = target_sets.get(primary, [["Anna", "Emily"]])
                elif reasoning_themes:
                    candidate_sets = [
                        ["Emily", "Anna"],
                        ["Emily", "Carlos"],
                        ["Anna", "Bas"],
                    ]
                elif meta_intent == "confused":
                    candidate_sets = [
                        ["Anna", "Emily"],
                        ["David", "Emily"],
                        ["Anna", "David"],
                    ]
                elif meta_intent == "next_step":
                    candidate_sets = [
                        ["David", "Anna"],
                        ["David", "Emily"],
                        ["Anna", "Carlos"],
                    ]
                elif meta_intent == "boundary_check":
                    candidate_sets = [
                        ["Emily", "Anna"],
                        ["David", "Emily"],
                    ]
                elif meta_intent == "scenario_question":
                    candidate_sets = [
                        ["Emily", "Anna"],
                        ["Emily", "David"],
                        ["Anna", "Carlos"],
                    ]
                elif explicit_slot is not None:
                    candidate_sets = [
                        ["Anna", "Emily"],
                        ["Emily", "Carlos"],
                        ["Anna", "David"],
                        ["Bas", "Emily"],
                    ]
                elif asking_direct_item:
                    candidate_sets = [
                        ["Anna", "Emily"],
                        ["Anna", "Carlos"],
                        ["Emily", "David"],
                        ["Bas", "Anna"],
                    ]
                elif wrong_or_weak_local:
                    candidate_sets = [
                        ["Emily", "Anna"],
                        ["Emily", "David"],
                        ["Anna", "Bas"],
                        ["Carlos", "Emily"],
                    ]
                elif label == "good":
                    candidate_sets = [
                        ["Anna", "Carlos"],
                        ["Anna", "David"],
                        ["Emily", "Carlos"],
                        ["Bas", "Anna"],
                    ]
                elif question_type in ["comparison", "why", "rank_check"]:
                    candidate_sets = [
                        ["Emily", "Anna"],
                        ["Emily", "Carlos"],
                        ["Anna", "David"],
                        ["Bas", "Emily"],
                    ]
                else:
                    candidate_sets = [
                        ["Anna", "Carlos"],
                        ["Anna", "David"],
                        ["Bas", "Carlos"],
                        ["Emily", "David"],
                        ["Anna", "Emily"],
                    ]

                selected = random.choice(candidate_sets)

                if named_targets:
                    primary = named_targets[0]
                    return [primary]

                david_hurry_count = st.session_state.get("david_hurry_count", 0)

                if (
                    not st.session_state.get("team_micro_conflict_used", False)
                    and meta_intent == "none"
                    and "David" not in selected
                    and (
                        1 <= st.session_state.turns <= 4
                        or (david_hurry_count == 1 and st.session_state.turns <= 8)
                    )
                ):
                    if num_teammates <= 1:
                        selected = ["David"]
                    else:
                        selected = ["David"] + [tm for tm in selected if tm != "David"]
                        selected = selected[:num_teammates]

                if num_teammates == 3:
                    remaining = [tm for tm in all_teammates if tm not in selected]
                    remaining = choose_distinct(remaining, len(remaining))
                    if remaining:
                        selected.append(remaining[0])

                selected = choose_distinct(selected, num_teammates)

                for tm in reversed(named_targets):
                    if tm in selected:
                        selected.remove(tm)
                        selected.insert(0, tm)

                return selected[:num_teammates]        

            selected_teammates = choose_teammates(
                user_text=text,
                mentioned=mentioned,
                label=label,
                question_type=question_type,
                meta_intent=meta_intent,
                explicit_slot=explicit_slot,
                asking_direct_item=asking_direct_item,
                short_simple_input=short_simple_input,
                is_lazy_ranking=is_lazy_ranking,
                addressed_teammates=addressed_teammates,
                reasoning_themes=reasoning_themes,
            )


            if is_lazy_ranking:
                selected_teammates = []
                speaking_flow = "leader_first"
            else:
                speaking_flow = choose_speaking_flow(
                    leadership_style=leadership,
                    meta_intent=meta_intent,
                    explicit_slot=explicit_slot,
                    asking_direct_item=asking_direct_item,
                    wrong_or_weak=wrong_or_weak,
                    question_type=question_type,
                )

                if addressed_teammates and selected_teammates:
                    speaking_flow = "teammate_first"

            queue_plan = []

            if speaking_flow == "leader_first":
                queue_plan.append(("Leader", leader_text, None, None))
                for tm in selected_teammates:
                    queue_plan.append((tm, None, "You", text))

            elif speaking_flow == "teammate_first":
                first_tm = selected_teammates[0]
                queue_plan.append((first_tm, None, "You", text))

                if random.random() < 0.65:
                    queue_plan.append(("Leader", leader_text, first_tm, None))

                for tm in selected_teammates[1:]:
                    queue_plan.append((tm, None, first_tm, None))

            elif speaking_flow == "teammate_then_leader":
                first_tm = selected_teammates[0]
                queue_plan.append((first_tm, None, "You", text))
                queue_plan.append(("Leader", leader_text, first_tm, None))

                for tm in selected_teammates[1:]:
                    queue_plan.append((tm, None, first_tm, None))

            elif speaking_flow == "leader_then_teammate_reaction":
                queue_plan.append(("Leader", leader_text, None, None))
                first_tm = selected_teammates[0]
                queue_plan.append((first_tm, None, "Leader", leader_text))

                for tm in selected_teammates[1:]:
                    queue_plan.append((tm, None, first_tm, None))

            # If the first teammate says something weak, let another teammate or leader react
            generated_texts = {}

            last_generated_role = None
            last_generated_text = None
            for idx, entry in enumerate(queue_plan):
                role_name, prepared_text, reply_to_role, reply_to_text = entry
                effective_reply_text = reply_to_text or ""

                if role_name == "Leader":
                    if prepared_text is not None:
                        final_text = prepared_text
                    else:
                        if reply_to_role in generated_texts:
                            target_text = generated_texts[reply_to_role]
                            final_text = leader_reply_to_teammate(leadership, reply_to_role, target_text)
                        else:
                            final_text = leader_text

                else:
                    if prepared_text is not None:
                        final_text = prepared_text
                    else:
                        if reply_to_role == "You":
                            source_text = text
                        elif reply_to_role and reply_to_role == last_generated_role and last_generated_text:
                            source_text = last_generated_text
                        else:
                            source_text = generated_texts.get(reply_to_role, reply_to_text or "")

                        effective_reply_text = source_text

                        final_text = teammate_reply_persona(
                            teammate_name=role_name,
                            user_text=text,
                            leader_text=leader_text,
                            label=label,
                            proposed_items=mentioned,
                            last_bot_msg=last_bot,
                            step=step + idx,
                            reply_to_role=reply_to_role,
                            reply_to_text=source_text
                        )

                st.session_state.pending_bot_msgs.append((role_name, final_text))
                generated_texts[role_name] = final_text
                last_bot = final_text
                last_generated_role = role_name
                last_generated_text = final_text

                if role_name == "David" and is_david_hurry_message(final_text):
                    st.session_state.david_hurry_count = st.session_state.get("david_hurry_count", 0) + 1

                if role_name == "David" and should_trigger_team_micro_conflict(
                    david_text=final_text,
                    current_hurry_count=st.session_state.get("david_hurry_count", 0),
                    user_text=text,
                    reply_to_text=effective_reply_text,
                ):
                    conflict_bundle = build_team_micro_conflict(
                        leadership_style=leadership,
                        david_text=final_text,
                        user_text=text,
                        reply_to_text=effective_reply_text,
                    )
                    st.session_state.team_micro_conflict_used = True
                    st.session_state.last_micro_conflict_turn = st.session_state.turns

                    for conflict_role, conflict_text, conflict_reply_to_role, conflict_reply_to_text in conflict_bundle:
                        st.session_state.pending_bot_msgs.append((conflict_role, conflict_text))
                        generated_texts[conflict_role] = conflict_text
                        last_bot = conflict_text
                        last_generated_role = conflict_role
                        last_generated_text = conflict_text


                # If Bas says something dumb, sometimes add a correction right after
                if role_name == "Bas":
                    bad_claim = detect_bad_teammate_claim(final_text)
                    if bad_claim and random.random() < 0.75:
                        already_scheduled_roles = [role for role, _ in st.session_state.pending_bot_msgs]
                        possible_correctors = [
                            x for x in ["Emily", "Anna", "David"]
                            if x != role_name and x not in already_scheduled_roles[-2:]
                        ]

                        if not possible_correctors:
                            possible_correctors = [x for x in ["Emily", "Anna", "David"] if x != role_name]

                        corrector = random.choice(possible_correctors)

                        correction_text = teammate_reply_persona(
                            teammate_name=corrector,
                            user_text=text,
                            leader_text=leader_text,
                            label=label,
                            proposed_items=mentioned,
                            last_bot_msg=final_text,
                            step=step + idx + 10,
                            reply_to_role="Bas",
                            reply_to_text=final_text
                        )
                        st.session_state.pending_bot_msgs.append((corrector, correction_text))
                        generated_texts[corrector] = correction_text
                        last_bot = correction_text

                        if random.random() < 0.35 and "Leader" not in already_scheduled_roles[-2:]:
                            leader_followup = leader_reply_to_teammate(leadership, "Bas", final_text)
                            st.session_state.pending_bot_msgs.append(("Leader", leader_followup))
                            generated_texts["Leader"] = leader_followup
                            last_bot = leader_followup

            # Optional extra leader hint, but less spammy
            if st.session_state.turns >= 1:
                hints = LEADER_HINTS.get(leadership, [])
                hint_index = st.session_state.leader_hint_index % len(hints) if hints else 0
                candidate_hint = hints[hint_index] if hints else None

                strong_leader_reply = any(
                    phrase in leader_text.lower()
                    for phrase in [
                        "move on",
                        "bottom-tier",
                        "life raft",
                        "dehydrated milk",
                        "heating unit",
                        "for #",
                        "the next step",
                        "fill #",
                        "around 8",
                        "around 9",
                        "around 10",
                    ]
                )

                recent_leader_msgs = recent_role_messages("Leader", n=4)

                hint_trigger = False
                recent_conflict_turn = st.session_state.get("last_micro_conflict_turn", -999)
                if recent_conflict_turn == st.session_state.turns:
                    hint_trigger = False
                elif meta_intent in ["confused", "next_step", "boundary_check", "moon_why"]:
                    hint_trigger = False
                elif explicit_slot is not None or asking_direct_item:
                    hint_trigger = False
                elif question_type in ["why", "comparison", "rank_check"]:
                    hint_trigger = False
                elif leadership == "servant" and st.session_state.turns % 5 == 0:
                    hint_trigger = True
                elif leadership == "task_focused" and st.session_state.turns % 5 == 0:
                    hint_trigger = True
                elif leadership == "authoritarian" and st.session_state.turns % 4 == 0:
                    hint_trigger = True

                if (
                    candidate_hint
                    and hint_trigger
                    and not strong_leader_reply
                    and len(st.session_state.pending_bot_msgs) <= 3
                    and not any(candidate_hint.lower() == msg.lower() for msg in recent_leader_msgs)
                    and not any(candidate_hint.lower() in msg.lower() for msg in recent_leader_msgs)
                ):
                    st.session_state.pending_bot_msgs.append(("Leader", candidate_hint))
                    st.session_state.leader_hint_index += 1

            st.session_state.last_bot_msg = last_bot
            st.session_state.teammate_step += 1

            if st.session_state.pending_bot_msgs:
                first_role, _ = st.session_state.pending_bot_msgs[0]
                st.session_state.bot_reveal_active = True
                st.session_state.typing_role = first_role
                st.session_state.next_reveal_time = time.time() + get_typing_delay_for_role(first_role)

            st.rerun()

    # ----------------------------
    # Gate: require minimum discussion turns before ranking
    # ----------------------------
    MIN_TURNS = 2
    if st.session_state.turns < MIN_TURNS:
        st.info(f"Send at least {MIN_TURNS} messages to continue to ranking.")
        return

    # ----------------------------
    # Ranking section (shows AFTER 2 messages)
    # ----------------------------
    st.divider()
    st.subheader("Step 2 - Final ranking")

    st.write("""
Rank the 15 items from **1 (most important)** to **15 (least important)**.  
Each rank can be used **only once**.
    """)

    ranking = {}
    used_ranks = []

    for item in NASA_ITEMS:
        widget_key = f"rank_{item}"

        options = get_available_ranks_for_item(item)
        current_value = st.session_state.get(widget_key, None)

        rank = st.selectbox(
            label=item,
            options=options,
            index=options.index(current_value) if current_value in options else 0,
            format_func=lambda x: "— No rank selected —" if x is None else str(x),
            key=widget_key,
        )

        ranking[item] = rank
        if rank is not None:
            used_ranks.append(rank)

    ui_changes = detect_ui_rank_changes()
    if ui_changes:
        store_ui_rank_changes(ui_changes)
        store_pending_ui_rank_changes(ui_changes)

    if len(used_ranks) > 0 and len(set(used_ranks)) != len(used_ranks):
        st.warning("Each rank (1–15) must be used only once.")

    pending_ui_changes = get_pending_ui_rank_changes()

    current_ui_ranking = {item: st.session_state.get(f"rank_{item}", None) for item in NASA_ITEMS}
    now = time.time()

    fresh_pending_ui_changes = []
    for change in pending_ui_changes:
        item = change["item"]
        new_rank = change["new_rank"]
        created_turn = change.get("created_turn", -999)
        created_time = change.get("created_time", 0.0)

        still_matches_ui = current_ui_ranking.get(item) == new_rank
        recent_enough = (st.session_state.turns - created_turn) <= 1 and (now - created_time) <= 8.0

        if still_matches_ui and recent_enough:
            fresh_pending_ui_changes.append(change)

    latest_by_item = {}
    for change in fresh_pending_ui_changes:
        latest_by_item[change["item"]] = change

    pending_ui_changes = list(latest_by_item.values())
    pending_ui_changes.sort(key=lambda x: x.get("created_time", 0.0))
    pending_ui_changes = pending_ui_changes[-2:]

    st.session_state.pending_ui_rank_changes = pending_ui_changes

    ui_reaction_threshold = 1

    if (
        len(pending_ui_changes) >= ui_reaction_threshold
        and st.session_state.turns >= 2
        and (now - st.session_state.last_ui_reaction_time) >= 4.0
        and (now - st.session_state.get("last_user_chat_time", 0.0)) >= 6.0
        and not st.session_state.bot_reveal_active
        and len(pending_ui_changes) == 1
        and random.random() < 0.18
    ):
        latest_change = pending_ui_changes[-1]

        possible_roles = ["Leader", "Anna", "Bas", "Carlos", "David", "Emily"]

        # bias toward variety instead of always the same person
        recent_roles = [msg.get("role") for msg in st.session_state.get("chat", [])[-8:]]
        
        ranked_roles = sorted(
            possible_roles,
            key=lambda r: (
                r in recent_roles[-2:],
                r in recent_roles[-4:],
                r == "Leader"
            )
        )

        top_candidates = ranked_roles[:3] if len(ranked_roles) >= 3 else ranked_roles
        reactor = random.choice(top_candidates)

        if reactor == "Leader":
            reaction_text = ui_rank_change_reaction("Leader", leadership, latest_change)
        else:
            reaction_text = ui_rank_change_reaction(reactor, leadership, latest_change)

        if reaction_text and not st.session_state.bot_reveal_active:
            st.session_state.pending_bot_msgs.append((reactor, reaction_text))
            st.session_state.bot_reveal_active = True
            st.session_state.typing_role = reactor
            st.session_state.next_reveal_time = time.time() + get_typing_delay_for_role(reactor)
            st.session_state.last_ui_reaction_turn = st.session_state.turns
            st.session_state.last_ui_reaction_time = now
            clear_pending_ui_rank_changes()
            st.rerun()

    if st.button("Submit ranking"):
        if any(ranking[item] is None for item in NASA_ITEMS):
            st.error("Please assign a rank to every item before submitting.")
            return

        if len(set(used_ranks)) != len(used_ranks):
            st.error("Please fix duplicate ranks before submitting.")
            return
        
        nasa_score = compute_nasa_score(ranking)

        st.session_state.data["participant_id"] = st.session_state.participant_id
        st.session_state.data["nasa_ranking"] = ranking
        st.session_state.data["nasa_score"] = nasa_score
        st.session_state.data["leadership_style"] = leadership
        st.session_state.data["prime"] = prime
        st.session_state.data["discussion_log"] = format_discussion_log()

        st.session_state.saved = False
        set_survey_stage("likert")
        st.switch_page("pages/1_Likert_Survey.py")


# ----------------------------
# Router
# ----------------------------
try:
    if st.session_state.page == "consent":
        page_consent()
    elif st.session_state.page == "priming":
        page_priming()
    elif st.session_state.page == "task":
        page_task()
    else:
        st.session_state.page = "consent"
        st.rerun()
except Exception as e:
    st.error(f"App crashed: {e}")
    st.exception(e)