<<<<<<< HEAD
import streamlit as st
import random
import uuid
import time
from streamlit_autorefresh import st_autorefresh
import gspread
import pandas as pd
import streamlit.components.v1 as components

st.set_page_config(page_title="Love in Leadership", layout="centered")

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
        "leader_perception_statement",
        "open_feedback_1",
        "open_feedback_2",
    ]

    row = [data.get(col, "") for col in column_order]
    existing_values = sheet.get_all_values()

    if not existing_values:
        sheet.append_row(column_order)

    sheet.append_row(row)

# ----------------------------
# Helpers
# ----------------------------
LEADERSHIP_STYLES = ["servant", "task_focused", "authoritarian"]
PRIMES = ["love", "neutral"]
# ----------------------------
# NASA Moon Survival Task data
# ----------------------------
NASA_ITEMS = [
    "Box of matches",
    "Food concentrate",
    "50 feet of nylon rope",
    "Parachute silk",
    "Portable heating unit",
    "Two .45 caliber pistols",
    "One case of dehydrated milk",
    "Two 100-lb tanks of oxygen",
    "Stellar map (of the moon's constellations)",
    "Self-inflating life raft",
    "Magnetic compass",
    "5 gallons of water",
    "Signal flares",
    "First aid kit (including injection needle)",
    "Solar-powered FM receiver-transmitter",
]

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

LEADER_OPENING = {
    "servant": (
        "Hi everyone. I’m really glad we can work on this together. "
        "Your perspectives matter, so please feel free to share your thoughts. "
        "Let’s support each other and reach a decision as a team."
    ),

    "task_focused": (
        "Hello team. Let’s approach this task efficiently and logically. "
        "We need to rank the items based on their usefulness for survival on the moon."
    ),

    "authoritarian": (
        "Alright, listen carefully. This task requires clear decisions. "
        "I will guide the process, and I expect you to follow my lead."
    )
}


LEADER_HINTS = {
    "servant": [
        "I appreciate everyone’s input so far. Let’s think together about what would help us survive first.",
        "That’s a good point — I want to make sure everyone feels comfortable with the top priorities.",
        "If we agree, oxygen and water seem essential. Does that feel right to everyone?",
        "Thank you all for engaging. Let’s finalize something we can stand behind as a group."
    ],

    "task_focused": [
        "From a survival standpoint, oxygen and water should be ranked highest.",
        "Navigation and communication tools are important secondary priorities.",
        "Items that depend on oxygen, such as matches, are not useful on the moon.",
        "Let’s finalize the ranking based on these functional considerations."
    ],

    "authoritarian": [
        "Oxygen is rank one. Water is rank two. That is not up for discussion.",
        "Some of these suggestions are irrelevant. Focus on what matters.",
        "Stop debating minor points and follow the structure I’m setting.",
        "I’ve decided the top priorities. Complete the remaining ranks accordingly."
    ]
}


TEAMMATE_LINES = [
    "Anna: Oxygen and water should be very high, obviously.",
    "Bas: I think the stellar map is important because there are no landmarks.",
    "Carlos: The transmitter seems crucial for communicating with the mothership.",
    "David: First aid kit and rope feel useful for injuries and movement.",
    "Emily: Matches and compass sound useless on the moon."
]
import re

ITEM_ALIASES = {
    "Box of matches": ["matches", "lucifers", "match", "aansteker", "lighter"],
    "Food concentrate": ["food", "voedsel", "concentrate", "concentraat"],
    "50 feet of nylon rope": ["rope", "touw", "nylon", "rope 50", "50 feet"],
    "Parachute silk": ["parachute", "silk", "zijde", "parachute silk"],
    "Portable heating unit": ["heating", "heater", "verwarming", "heating unit"],
    "Two .45 caliber pistols": ["pistol", "pistols", "gun", "guns", "wapen", "wapens"],
    "One case of dehydrated milk": ["milk", "dehydrated milk", "melk", "poedermelk"],
    "Two 100-lb tanks of oxygen": ["oxygen", "zuurstof", "o2"],
    "Stellar map (of the moon's constellations)": ["stellar map", "map", "kaart", "constellations", "sterrenkaart"],
    "Self-inflating life raft": ["life raft", "raft", "vlot", "reddingsvlot"],
    "Magnetic compass": ["compass", "kompas", "magnetic compass"],
    "5 gallons of water": ["water", "watertank", "water tank", "5 gallons"],
    "Signal flares": ["flares", "signal", "signaal", "vuurpijl", "vuurpijlen"],
    "First aid kit (including injection needle)": ["first aid", "ehbo", "medical", "kit", "injectie", "needle"],
    "Solar-powered FM receiver-transmitter": ["transmitter", "receiver", "radio", "fm", "zender", "ontvanger"],
}

GOOD_TOP_ITEMS = {
    "Two 100-lb tanks of oxygen",
    "5 gallons of water",
    "Stellar map (of the moon's constellations)",
    "Food concentrate",
    "Solar-powered FM receiver-transmitter",
}

BAD_TOP_ITEMS = {
    "Box of matches",
    "Magnetic compass",
    "Portable heating unit",
}

SHORT_ITEM_NAMES = {
    "Box of matches": "matches",
    "Food concentrate": "food concentrate",
    "50 feet of nylon rope": "nylon rope",
    "Parachute silk": "parachute silk",
    "Portable heating unit": "heating unit",
    "Two .45 caliber pistols": "pistols",
    "One case of dehydrated milk": "dehydrated milk",
    "Two 100-lb tanks of oxygen": "oxygen tanks",
    "Stellar map (of the moon's constellations)": "stellar map",
    "Self-inflating life raft": "life raft",
    "Magnetic compass": "compass",
    "5 gallons of water": "water",
    "Signal flares": "signal flares",
    "First aid kit (including injection needle)": "first aid kit",
    "Solar-powered FM receiver-transmitter": "transmitter",
}

def short_item_name(item: str) -> str:
    return SHORT_ITEM_NAMES.get(item, item)


def extract_items_from_text(text: str):
    """Return a list of canonical NASA item names mentioned in the user's text."""
    t = text.lower()
    found = []
    for canonical, aliases in ITEM_ALIASES.items():
        for a in aliases:
            if a in t:
                found.append(canonical)
                break
    # unique preserving order
    seen = set()
    out = []
    for x in found:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out

def classify_proposal(items):
    """Return (quality_label, details) based on whether proposed items are 'good' or 'bad' top picks."""
    if not items:
        return "none", {}

    good = [i for i in items if i in GOOD_TOP_ITEMS]
    bad = [i for i in items if i in BAD_TOP_ITEMS]

    if bad and not good:
        return "bad", {"good": good, "bad": bad}
    if good and not bad:
        return "good", {"good": good, "bad": bad}
    if good and bad:
        return "mixed", {"good": good, "bad": bad}
    return "neutral", {"good": good, "bad": bad}

def extract_rank_from_text(text: str):
    """Extract a proposed rank number from text, if present."""
    match = re.search(r"\b([1-9]|1[0-5])\b", text)
    if match:
        rank = int(match.group(1))
        if 1 <= rank <= 15:
            return rank
    return None


def detect_question_type(text: str):
    """
    Detect common participant intents.
    Returns one of:
    - item_check
    - rank_check
    - comparison
    - why
    - confirmation
    - strategy
    - agreement
    - disagreement
    - none
    """
    t = text.lower().strip()

    if any(x in t for x in ["why", "waarom", "hoezo"]):
        return "why"

    if any(x in t for x in ["what should we do", "what do we do", "where do we start", "how should we do this", "wat moeten we doen"]):
        return "strategy"

    if any(x in t for x in ["better than", "higher than", "lower than", "above", "below", "vs", "versus", "or should"]):
        return "comparison"

    if any(x in t for x in ["good number", "good at", "okay at", "ok at", "rank", "number"]):
        return "rank_check"

    if any(x in t for x in ["right?", "correct?", "is that right", "does that make sense", "should we"]):
        return "confirmation"

    if any(x in t for x in ["i agree", "agree with", "that makes sense", "true"]):
        return "agreement"

    if any(x in t for x in ["i disagree", "don’t agree", "do not agree", "no that", "not true"]):
        return "disagreement"

    # short single-item checks like "nylon rope?" or "oxygen?"
    mentioned_items = extract_items_from_text(t)
    if mentioned_items and len(t) < 35:
        return "item_check"

    return "none"


def evaluate_rank_guess(item: str, guessed_rank: int):
    """Compare guessed rank to NASA expert rank."""
    if item not in NASA_EXPERT_RANK or guessed_rank is None:
        return "unknown"

    true_rank = NASA_EXPERT_RANK[item]
    diff = abs(guessed_rank - true_rank)

    if diff <= 1:
        return "very_close"
    elif diff <= 3:
        return "reasonable"
    else:
        return "far"


def get_recent_chat_context(n=11):
    """Return the last few chat messages as a list."""
    return st.session_state.get("chat", [])[-n:]


def get_last_non_user_speaker():
    """Return the role of the most recent non-user speaker."""
    chat = st.session_state.get("chat", [])
    for msg in reversed(chat):
        if msg.get("role") != "You":
            return msg.get("role")
    return None


def get_last_item_discussed():
    """Try to recover the most recently discussed NASA item from chat."""
    chat = st.session_state.get("chat", [])
    for msg in reversed(chat):
        mentioned = extract_items_from_text(msg.get("text", ""))
        if mentioned:
            return mentioned[0]
    return None

def get_last_user_message():
    """Return the most recent user message text."""
    chat = st.session_state.get("chat", [])
    for msg in reversed(chat):
        if msg.get("role") == "You":
            return msg.get("text", "")
    return ""


def get_last_user_items():
    """Return the NASA items mentioned in the most recent user message."""
    last_user_msg = get_last_user_message()
    return extract_items_from_text(last_user_msg)

def get_recent_bot_context():
    """Return the most recent non-user message text."""
    chat = st.session_state.get("chat", [])
    for msg in reversed(chat):
        if msg.get("role") != "You":
            return msg.get("text", "")
    return ""

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

def init_discussion_state():
    if "chat" not in st.session_state:
        st.session_state.chat = []

        leader_intro = LEADER_OPENING.get(leadership)
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
    if "pending_bot_msgs" not in st.session_state:
        st.session_state.pending_bot_msgs = []
    if "bot_reveal_active" not in st.session_state:
        st.session_state.bot_reveal_active = False
    if "last_reveal_time" not in st.session_state:
        st.session_state.last_reveal_time = 0.0
    if "leader_hint_index" not in st.session_state:
        st.session_state.leader_hint_index = 0

def clear_discussion():
    st.session_state.chat = []

    leader_intro = LEADER_OPENING.get(leadership)
    if leader_intro:
        st.session_state.chat.append({
            "role": "Leader",
            "text": leader_intro
        })

    st.session_state.turns = 0
    st.session_state.suggested_items = []
    st.session_state.teammate_step = 0
    st.session_state.last_bot_msg = ""
    st.session_state.pending_bot_msgs = []
    st.session_state.leader_hint_index = 0

    if "user_message" in st.session_state:
        del st.session_state["user_message"]

def add_msg(role, text):
    st.session_state.chat.append({"role": role, "text": text})

def items_to_bullets(items):
    if not items:
        return "—"
    return ", ".join(items[:4])


def leader_reply(leadership_style, user_text):
    proposed = extract_items_from_text(user_text)
    label, info = classify_proposal(proposed)

    good = info.get("good", [])
    bad = info.get("bad", [])
    guessed_rank = extract_rank_from_text(user_text)
    question_type = detect_question_type(user_text)

    def items_to_short(items):
        return ", ".join(short_item_name(i) for i in items[:3]) if items else "—"

    t = user_text.lower().strip()
    first_item = proposed[0] if proposed else get_last_item_discussed()
    first_item_short = short_item_name(first_item) if first_item else None

    # Full item list question
    if ("all the items" in t) or ("all items" in t) or ("alle items" in t) or ("wat zijn alle" in t):
        if leadership_style == "servant":
            return "Of course — the full list is visible on the right. Take your time. Which 3 stand out to you as most important?"
        if leadership_style == "task_focused":
            return "The full list is shown on the right. Start with air, water, navigation, and communication."
        return "The full list is on the right. Stop stalling and state your top items."

    # Strategy question
    if question_type == "strategy":
        if leadership_style == "servant":
            return "Let’s begin with the essentials together: oxygen and water first, then communication and navigation. After that, we can place the weaker items lower."
        if leadership_style == "task_focused":
            return "Start by identifying the top 5: oxygen, water, map, transmitter, and food are strong candidates. Then place weaker items lower."
        return "Start with oxygen #1 and water #2. Then sort communication and navigation near the top. Weak items go low."

    # Very short item check: "nylon rope?" / "oxygen?" / "matches?"
    if question_type == "item_check" and first_item:
        expert_rank = NASA_EXPERT_RANK.get(first_item, None)

        if first_item in GOOD_TOP_ITEMS:
            if leadership_style == "servant":
                return f"{first_item_short.capitalize()} is definitely one of the stronger items. I’d keep it fairly high."
            if leadership_style == "task_focused":
                return f"{first_item_short.capitalize()} should be ranked relatively high."
            return f"{first_item_short.capitalize()} is important. Keep it near the top."

        if first_item in BAD_TOP_ITEMS:
            if leadership_style == "servant":
                return f"{first_item_short.capitalize()} is probably not a strong choice here. I’d place it fairly low."
            if leadership_style == "task_focused":
                return f"{first_item_short.capitalize()} has low survival utility on the moon. Rank it low."
            return f"{first_item_short.capitalize()} is a weak choice. Put it low."

        # middle items
        if leadership_style == "servant":
            return f"{first_item_short.capitalize()} has some value, but it is not one of the very strongest items. I’d place it around the middle."
        if leadership_style == "task_focused":
            return f"{first_item_short.capitalize()} is a mid-range item."
        return f"{first_item_short.capitalize()} has some value. Keep it in the middle range."

    # Rank-specific evaluation
    if question_type == "rank_check" and first_item and guessed_rank:
        rank_eval = evaluate_rank_guess(first_item, guessed_rank)
        expert_rank = NASA_EXPERT_RANK.get(first_item)
        severe_low_items = GOOD_TOP_ITEMS
        severe_high_items = BAD_TOP_ITEMS

        # item-specific severity
        if first_item in severe_low_items and guessed_rank > expert_rank + 1:
            rank_eval = "far"
        if first_item in severe_high_items and guessed_rank < 12:
            rank_eval = "far"

        if leadership_style == "servant":
            if rank_eval == "very_close":
                return f"That seems quite reasonable. {first_item_short.capitalize()} is often placed around that area."
            elif rank_eval == "reasonable":
                direction = "higher" if guessed_rank > expert_rank else "lower"
                return f"That’s not a bad suggestion. {first_item_short.capitalize()} is usually placed a little {direction} than {guessed_rank}, but you’re in the right general range."
            elif rank_eval == "far":
                direction = "higher" if expert_rank < guessed_rank else "lower"
                return f"I’d reconsider that a little. {first_item_short.capitalize()} is usually ranked quite a bit {direction} than {guessed_rank}."
            else:
                return f"That could work. Tell me your reasoning for putting {first_item_short} at rank {guessed_rank}."

        if leadership_style == "task_focused":
            if rank_eval == "very_close":
                return f"Yes, {first_item_short} at rank {guessed_rank} is a reasonable placement."
            elif rank_eval == "reasonable":
                return f"{first_item_short.capitalize()} is in the right general range, but rank {guessed_rank} may be slightly off."
            elif rank_eval == "far":
                return f"No. Rank {guessed_rank} is not an efficient placement for {first_item_short}."
            else:
                return f"State the functional reason for placing {first_item_short} at rank {guessed_rank}."

        if leadership_style == "authoritarian":
            if rank_eval == "very_close":
                return f"Acceptable. {first_item_short.capitalize()} at rank {guessed_rank} is close enough."
            elif rank_eval == "reasonable":
                return f"Not ideal. {first_item_short.capitalize()} belongs near that range, but not exactly at {guessed_rank}."
            elif rank_eval == "far":
                return f"No. {first_item_short.capitalize()} does not belong at rank {guessed_rank}. Fix it."
            else:
                return f"Decide properly. {first_item_short.capitalize()} needs a justified position."

    # Why-question
    if question_type == "why" and first_item:
        if first_item in BAD_TOP_ITEMS:
            if leadership_style == "servant":
                return f"Because {first_item_short} is less useful under moon conditions. Some items depend on atmosphere or Earth-like navigation."
            if leadership_style == "task_focused":
                return f"{first_item_short.capitalize()} has limited survival utility on the moon. Prioritize oxygen, water, navigation, and communication."
            return f"Because {first_item_short} is low utility on the moon. Move on."

        if first_item in GOOD_TOP_ITEMS:
            if leadership_style == "servant":
                return f"{first_item_short.capitalize()} supports core survival needs, which is why it tends to be ranked highly."
            if leadership_style == "task_focused":
                return f"{first_item_short.capitalize()} contributes directly to survival or rescue. That is why it should be ranked relatively high."
            return f"Because {first_item_short} is clearly more useful than low-priority items."

    # Comparison
    if question_type == "comparison" and len(proposed) >= 2:
        a, b = proposed[0], proposed[1]
        rank_a = NASA_EXPERT_RANK.get(a, 99)
        rank_b = NASA_EXPERT_RANK.get(b, 99)
        better = a if rank_a < rank_b else b
        worse = b if better == a else a

        if leadership_style == "servant":
            return f"I’d lean toward placing {short_item_name(better)} above {short_item_name(worse)}, but it’s a good comparison for the team to discuss."
        if leadership_style == "task_focused":
            return f"{short_item_name(better).capitalize()} should be ranked above {short_item_name(worse)}."
        return f"{short_item_name(better).capitalize()} goes above {short_item_name(worse)}."

    # Agreement / disagreement
    if question_type == "agreement":
        if leadership_style == "servant":
            return "I appreciate the alignment. Let’s turn that into a clearer ranking."
        if leadership_style == "task_focused":
            return "Good. Convert that agreement into an ordered placement."
        return "Fine. Then act on it."

    if question_type == "disagreement":
        if leadership_style == "servant":
            return "That’s okay — disagreement can help us think more carefully. What would you rank differently?"
        if leadership_style == "task_focused":
            return "State the alternative clearly and justify it functionally."
        return "Then give a better ranking."

    # General proposal logic
    if leadership_style == "servant":
        if label == "none":
            return "Thanks for sharing. Could you name 2–3 items you think matter most? We’ll refine together."
        if label == "good":
            return (
                f"That makes a lot of sense. You’re highlighting strong priorities ({items_to_short(good)}). "
                "Shall we agree on oxygen and water as top priorities, then discuss communication and navigation?"
            )
        if label == "bad":
            return (
                f"I like that you’re taking initiative. I’m a bit concerned about ({items_to_short(bad)}) being effective on the moon. "
                "What would you swap in instead?"
            )
        if label == "mixed":
            return (
                f"I see strong picks ({items_to_short(good)}) and some risky ones ({items_to_short(bad)}). "
                "How about we keep the strong ones and replace the risky ones together?"
            )
        return "Great — keep going. What would you place in your top 5, and why?"

    if leadership_style == "task_focused":
        if label == "none":
            return "Provide your top 3 items. Use survival utility logic: air, water, navigation, communication."
        if label == "good":
            return f"Your proposal aligns with survival utility ({items_to_short(good)}). Now specify ranks 1–5."
        if label == "bad":
            return f"Your proposal includes low-utility items ({items_to_short(bad)}). Replace them using survival logic."
        if label == "mixed":
            return f"Mixed utility. Keep ({items_to_short(good)}), replace ({items_to_short(bad)}). State your revised top 3."
        return "Translate that into a concrete ordered top 5."

    if leadership_style == "authoritarian":
        if label == "none":
            return "Stop speculating. State your top 3 items now."
        if label == "good":
            return f"Finally, something sensible ({items_to_short(good)}). I’m setting oxygen #1 and water #2. Give me your #3–#5."
        if label == "bad":
            return f"No. ({items_to_short(bad)}) are bad choices on the moon. Replace them and state your top 3 again."
        if label == "mixed":
            return f"Partly correct. Keep ({items_to_short(good)}). Drop ({items_to_short(bad)}). Try again with a clean top 3."
        return "Enough. I decide the top five. You can fill the rest."

    return "Please state your top 3 items."

TEAMMATE_PERSONA = {
    "Anna": "practical, grounded, focuses on survival basics",
    "Bas": "confidently wrong, misunderstands moon conditions",
    "Carlos": "jokester, makes light comments but sometimes helpful",
    "David": "impatient, wants to finish quickly, pushes for closure",
    "Emily": "nerdy know-it-all, over-explains and corrects others",
}

def teammate_reply_persona(teammate_name, user_text, leader_text, label, proposed_items, last_bot_msg, step):
    guessed_rank = extract_rank_from_text(user_text)
    question_type = detect_question_type(user_text)
    first_item = proposed_items[0] if proposed_items else get_last_item_discussed()
    last_speaker = get_last_non_user_speaker()
    last_user_items = get_last_user_items()

    def pick(options):
        return options[step % len(options)]

    user_item = last_user_items[0] if last_user_items else first_item

    recent_bot_text = get_recent_bot_context()
    recent_bot_items = extract_items_from_text(recent_bot_text)
    recent_bot_item = recent_bot_items[0] if recent_bot_items else None

    # Rank checks
    if question_type == "rank_check" and first_item and guessed_rank:
        eval_rank = evaluate_rank_guess(first_item, guessed_rank)

        rank_pools = {
            "Anna": {
                "very_close": [f"Yeah, I think you’re pretty close with {first_item} at {guessed_rank}."],
                "reasonable": [f"Your placement for {first_item} sounds roughly right, maybe just a little off."],
                "far": [f"I’m not sure about your placement of {first_item} there."],
            },
            "Bas": {
                "very_close": [f"Sure, I can go with your idea of {first_item} at {guessed_rank}."],
                "reasonable": [f"Maybe? Your rank could work, but I’m honestly improvising too 😅"],
                "far": [f"That feels a bit random to me, but I respect the confidence."],
            },
            "Carlos": {
                "very_close": [f"Honestly, your {first_item} take is kind of solid 😄"],
                "reasonable": [f"Not bad. Your rank for {first_item} is at least not chaos."],
                "far": [f"That rank for {first_item} is bold. Very bold."],
            },
            "David": {
                "very_close": [f"Fine. Keep your {first_item} there and let’s move on."],
                "reasonable": [f"Close enough. Don’t spend ages on one item."],
                "far": [f"No, your rank for {first_item} is off. Fix it."],
            },
            "Emily": {
                "very_close": [f"Yes, your placement of {first_item} is defensible."],
                "reasonable": [f"Your rank for {first_item} is in the right zone, though not exact."],
                "far": [f"That rank is too far off for {first_item}, based on standard NASA logic."],
            },
        }

        return pick(rank_pools[teammate_name].get(eval_rank, [f"I’m not fully sure about your {first_item} placement."]))

    # Why questions
    if question_type == "why" and first_item:
        why_pools = {
            "Anna": [f"I think your question about {first_item} makes sense — it depends on whether it directly helps survival."],
            "Bas": [f"Honestly, your guess is as good as mine there."],
            "Carlos": [f"Because the moon is annoying and refuses to behave like Earth 😄"],
            "David": [f"Because some items actually keep you alive, and others really don’t."],
            "Emily": [f"Your question about {first_item} comes down to whether it directly supports survival or rescue."],
        }
        return pick(why_pools[teammate_name])

    # Comparison questions
    if question_type == "comparison" and len(proposed_items) >= 2:
        a, b = proposed_items[0], proposed_items[1]
        comparison_pools = {
            "Anna": [f"I see what you mean comparing {a} and {b}. I’d probably put one slightly above the other, but both are worth discussing."],
            "Bas": [f"I’d just choose whichever one sounds cooler, honestly."],
            "Carlos": [f"Your {a} versus {b} debate is exactly how group projects become reality TV."],
            "David": [f"Pick one and move on."],
            "Emily": [f"If you compare {a} and {b}, focus on direct survival utility rather than intuition."],
        }
        return pick(comparison_pools[teammate_name])

    # Agreement / disagreement
    if question_type == "agreement":
        agree_pools = {
            "Anna": ["Yeah, I think your point makes sense."],
            "Bas": ["Nice, we agree for once. Historic moment."],
            "Carlos": ["Look at you getting consensus out of this group 😄"],
            "David": ["Good. Then lock it in."],
            "Emily": ["Agreement is useful, provided the underlying ranking is sound."],
        }
        return pick(agree_pools[teammate_name])

    if question_type == "disagreement":
        disagree_pools = {
            "Anna": ["That’s fair — what would you put instead?"],
            "Bas": ["Conflict! Finally, some energy."],
            "Carlos": ["Ah yes, democracy and mild tension."],
            "David": ["Then give a better alternative."],
            "Emily": ["Disagreement is useful if it improves the logic of the ranking."],
        }
        return pick(disagree_pools[teammate_name])

    # Direct reactions to participant's item
    if user_item and label == "good":
        direct_good_pools = {
            "Anna": [f"I think you’re right to keep {user_item} fairly high."],
            "Bas": [f"Your {user_item} pick is way less chaotic than mine would be."],
            "Carlos": [f"Your point about {user_item} actually sounds pretty smart."],
            "David": [f"Fine. Keep {user_item} high and move on."],
            "Emily": [f"Yes, your reasoning about {user_item} is broadly consistent with NASA logic."],
        }
        if step % 4 == 0:
            return pick(direct_good_pools[teammate_name])

    if user_item and label == "bad":
        direct_bad_pools = {
            "Anna": [f"I get why you mentioned {user_item}, but I don’t think it helps enough here."],
            "Bas": [f"I mean, I would probably defend {user_item} too, so maybe we’re both wrong."],
            "Carlos": [f"Your {user_item} idea has heart. Not accuracy, but heart."],
            "David": [f"No, {user_item} should not be that important."],
            "Emily": [f"I don’t think your reasoning for {user_item} holds under moon conditions."],
        }
        if step % 4 == 0:
            return pick(direct_bad_pools[teammate_name])

    # Stronger teammate-to-teammate conversational flow
    if recent_bot_item and step % 3 == 1:
        conversational_pools = {
            "Anna": [
                f"I agree with that point about {recent_bot_item}. That seems practical.",
                f"Yeah, I think keeping {recent_bot_item} in mind makes sense.",
            ],
            "Bas": [
                f"I’m not fully convinced about {recent_bot_item}, but okay.",
                f"Maybe... although I’d probably still overrate something else 😅",
            ],
            "Carlos": [
                f"Honestly, that {recent_bot_item} point was one of the smarter things said so far 😄",
                f"Yeah, fair. {recent_bot_item} does sound more useful than some of the nonsense we’ve mentioned.",
            ],
            "David": [
                f"Fine. Keep {recent_bot_item} where it belongs and move on.",
                f"Sure. We do not need a 40-minute debate about {recent_bot_item}.",
            ],
            "Emily": [
                f"That point about {recent_bot_item} is logically consistent.",
                f"Yes, {recent_bot_item} fits the survival priorities better than several alternatives.",
            ],
        }
        return pick(conversational_pools[teammate_name])

    # Direct follow-up to participant's most recent item
    if user_item and step % 3 == 2:
        followup_pools = {
            "Anna": [
                f"I think your point about {user_item} is worth keeping in the ranking.",
                f"Your idea about {user_item} seems practical to me.",
            ],
            "Bas": [
                f"I see why you mentioned {user_item}, even if I might rank it differently.",
                f"Your {user_item} idea is not the weirdest one in this chat.",
            ],
            "Carlos": [
                f"Your {user_item} take is actually kind of solid.",
                f"I’m weirdly on board with your {user_item} point.",
            ],
            "David": [
                f"Fine. Put {user_item} where it makes sense and keep going.",
                f"Your point about {user_item} is clear enough. Next item.",
            ],
            "Emily": [
                f"Your reasoning about {user_item} is at least directionally sound.",
                f"{user_item} is a reasonable item to focus on, depending on exact placement.",
            ],
        }
        return pick(followup_pools[teammate_name])

    # Cross-talk to previous teammate
    if teammate_name == "Emily" and ("matches" in last_bot_msg.lower() or "compass" in last_bot_msg.lower()):
        return pick([
            "Just to correct that: matches won’t work without oxygen. The moon has no atmosphere.",
            "Small correction: magnetic compass is of very limited use in this setting.",
        ])

    if teammate_name == "Carlos" and ("no atmosphere" in leader_text.lower() or "no atmosphere" in last_bot_msg.lower()):
        return pick([
            "So basically: no air, no fire… the moon is really killing the vibe 😄",
            "Moon survival tip: do not attempt a campfire. Worst barbecue ever.",
        ])

    if teammate_name == "David" and last_speaker in ["Carlos", "Bas"]:
        return pick([
            "Can we stay focused and finish this?",
            "Funny. Anyway, can we finalize the ranking?",
        ])

    if teammate_name == "Anna" and last_speaker == "Emily":
        return pick([
            "That makes sense to me. I’d keep the practical items high.",
            "Yeah, I think Emily’s logic is useful there.",
        ])

    if teammate_name == "Carlos" and last_speaker == "Anna" and user_item:
        return pick([
            f"Anna’s probably right about {user_item}, to be honest.",
            f"I’m with Anna there — your {user_item} point is worth keeping.",
        ])

    # General response pools
    if label == "good":
        pools = {
            "Anna": [
                "Yep, that’s sensible. Oxygen and water should be top. Then transmitter or map.",
                "Agree. After air and water, communication is huge.",
            ],
            "Bas": [
                "Yeah! Also I still think the heating unit should be #1 because space is cold.",
                "Ok but hear me out: pistols = protection. What if moon pirates show up?",
            ],
            "Carlos": [
                "Nice. This is the first time I’ve seen a group not immediately choose matches 😅",
                "Solid picks. Now let’s not fight over #7 for three hours, ok?",
            ],
            "David": [
                "Great. Lock those in and let’s finish the ranking quickly.",
                "Cool. Now decide the top 5 and we’re done.",
            ],
            "Emily": [
                "Correct direction. NASA’s standard top group includes oxygen, water, stellar map, food, transmitter.",
                "Yes. Those align with survival priorities. Next you optimize order and push low-utility items down.",
            ],
        }
        return pick(pools[teammate_name])

    if label == "bad":
        pools = {
            "Anna": [
                "I get why you said that, but matches or compass won’t help much on the moon.",
                "Try oxygen and water first. Then map or transmitter.",
            ],
            "Bas": [
                "No no, matches are genius. Fire fixes everything.",
                "Compass tells us where Earth is. So… useful.",
            ],
            "Carlos": [
                "Matches on the moon is brave. Respect. Incorrect, but respect 😂",
                "Compass on the moon feels like bringing a snorkel to a desert.",
            ],
            "David": [
                "Can we not do this… oxygen and water first, please.",
                "Guys. Stop. Oxygen and water top. Move on.",
            ],
            "Emily": [
                "Those won’t work well: matches need oxygen; compass has very limited value here. Replace them with oxygen, water, map, or transmitter.",
                "Please reconsider. The moon has no atmosphere, so combustion-based tools are ineffective.",
            ],
        }
        return pick(pools[teammate_name])

    if label == "mixed":
        pools = {
            "Anna": [
                "Some good picks in there. Keep oxygen and water high and rethink the weak ones.",
                "Half solid. Swap out the low-utility items and you’re good.",
            ],
            "Bas": [
                "Mixed is fine! It’s like a balanced diet of survival items 😌",
                "We can keep matches just in case the moon has secret oxygen?",
            ],
            "Carlos": [
                "This is like a Netflix show: some great episodes, some filler 😄",
                "Ok ok—keep the good ones, ditch the campfire-on-the-moon stuff.",
            ],
            "David": [
                "Let’s just finalize. Pick a clean top 5 and stop tweaking.",
                "Ok. Oxygen, water, transmitter, map, food. Done.",
            ],
            "Emily": [
                "You’re close. Keep the high-utility picks; drop tools that do not fit moon conditions.",
                "Mixed. Rebuild using oxygen, water, navigation, communication, then medical or mobility.",
            ],
        }
        return pick(pools[teammate_name])

    neutral_pools = {
        "Anna": [
            "If you’re stuck: oxygen and water are obvious top priorities.",
            "Try making a first draft top 5 and we’ll adjust.",
        ],
        "Bas": [
            "I’d still start with something chaotic, so maybe don’t copy me.",
            "Food first because hungry people make bad decisions.",
        ],
        "Carlos": [
            "If we mess this up, can we at least agree to blame the moon? 😄",
            "Serious-ish answer: oxygen and water should be top.",
        ],
        "David": [
            "Pick something. Any draft is better than debating forever.",
            "Let’s speedrun this: oxygen, water, transmitter, map, food.",
        ],
        "Emily": [
            "Draft top 5: oxygen, water, stellar map, food concentrate, transmitter.",
            "Start with NASA logic: air and water first, then navigation and communication.",
        ],
    }
    return pick(neutral_pools[teammate_name])

def compute_nasa_score(participant_ranking: dict) -> int:
    score = 0
    for item in NASA_ITEMS:
        score += abs(int(participant_ranking[item]) - int(NASA_EXPERT_RANK[item]))
    return score

def scroll_to_top():
    components.html(
        """
        <script>
            window.parent.scrollTo(0, 0);
        </script>
        """,
        height=0,
    )

def assign_condition():
    """Randomly assign one of the 3x2 conditions."""
    leadership = random.choice(LEADERSHIP_STYLES)
    prime = random.choice(PRIMES)
    return leadership, prime

def init_session():
    if "participant_id" not in st.session_state:
        st.session_state.participant_id = str(uuid.uuid4())
    if "page" not in st.session_state:
        st.session_state.page = "consent"
    if "condition" not in st.session_state:
        st.session_state.condition = assign_condition()
    if "data" not in st.session_state:
        st.session_state.data = {}

init_session()

leadership, prime = st.session_state.condition

# ----------------------------
# Pages
# ----------------------------
def page_consent():
    scroll_to_top()
    st.title("Love in Leadership — Study")

    st.write("""
 Dear respondent, 
Thank you in advance for filling in this survey, and therefore participating in this research conducted by a master student at Erasmus University Rotterdam. This research aims to investigate the relationship between love in leadership and team performance and experience. 

First, some general information is needed, afterwards you will complete a short writing tasks and a group decision-making task. You will be matched with a team including a leader and other team members. Lastly, a short survey is presented in which you can talk about your experience of the experiment. Your participation in this research is highly valued. 
             
The entire experiment will take about 15 to 20 minutes, and the data will be used for research purposes only. The experiment is done anonymously. The responses will be kept confidential and will not be shared with any third parties. Moreover, there are no right or wrong answers, and you are free to stop the experiment at any moment.  

For further information or questions, feel free to send an email to Nora Remijnse at 569443gr@eur.nl. 
 
Please select the “I consent to participate in this study” box below if you: 

Are above 18 years old
Have read the information above and agree to this 

    """)

    st.subheader("Consent")
    consent = st.checkbox("I consent to participate in this study.")

    st.subheader("Demographics (optional)")

    age_category = st.selectbox(
        "Age",
        [
            "18–24",
            "25–34",
            "35–44",
            "45–54",
            "55–64",
            "65+",
        ],
    )

    gender = st.selectbox(
        "Gender",
        [
            "Male",
            "Female",
            "Non-binary",
            "Prefer not to say",
        ],
    )

    country = st.text_input("Which country are you from?")

    if st.button("Next"):
        if not consent:
            st.error("Please provide consent to continue.")
            return

        st.session_state.data["consent"] = True
        st.session_state.data["age_category"] = age_category
        st.session_state.data["gender"] = gender
        st.session_state.data["country"] = country.strip()

        st.session_state.page = "priming"
        st.rerun()

def page_priming():
    scroll_to_top()
    st.title("Writing task")

    if prime == "love":
        prompt = "Please write about a past experience in which you felt loved."
    else:
        prompt = "Please write directions to the supermarket nearest to your home."

    st.write(prompt)
    text = st.text_area("Your response", height=200)

    st.caption("Minimum 100 characters to continue.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Back"):
            st.session_state.page = "consent"
            st.rerun()

    with col2:
        if st.button("Next"):
            if len(text.strip()) < 100:
                st.error("Please write a bit more (at least 100 characters).")
                return
            st.session_state.data["priming_text"] = text.strip()
            st.session_state.page = "task"
            st.rerun()


def page_task():
    scroll_to_top()
    st.title("NASA Moon Survival Task")

    # --- Initialize discussion state ---
    init_discussion_state()

    # --- Sidebar controls (always visible) ---
    st.sidebar.header("Controls")

    st.sidebar.caption(f"Messages sent: {st.session_state.turns} / 2")

    if st.sidebar.button("🧹 Clear discussion", key="clear_discussion_btn"):
        clear_discussion()
        st.rerun()

    # Optional: put instructions in an expander to reduce overload
    with st.expander("Instructions (click to open)", expanded=True):
        st.write("""
**Scenario**: Imagine that your spacecraft has crash-landed on the moon. You must decide which items are most important for survival until rescue arrives.

**Your task**: You will work with a team to decide how important each of the 15 items is.

**Step 1 – Team discussion**

Use the chat to discuss the items with your team.  
Please send **at least 2 messages** in the discussion.

**Step 2 – Final ranking**

After the discussion, rank the **15 items** from:

**1 = most important for survival**  
**15 = least important for survival**

Each number can be used **only once**.

**Step 3 – Submit your ranking**

When you are finished ranking all items, click **Submit ranking** to continue.
""")

    # --- Layout: chat left, items right ---
    left, right = st.columns([2, 1], gap="large")

    # ----------------------------
    # RIGHT COLUMN: items reference + controls
    # ----------------------------
    with right:
        st.subheader("Items (reference)")
        st.caption("Keep this list open while chatting.")

        with st.container(height=420):
            for i, item in enumerate(NASA_ITEMS, start=1):
                st.write(f"{i}. {item}")

        st.divider()

        # Progress indicator
        st.caption(f"Messages sent: **{st.session_state.turns} / 2**")

    # ----------------------------
    # LEFT COLUMN: chat
    # ----------------------------
    with left:
        st.subheader("Team chat")

        # --- Reveal bot messages one-by-one using autorefresh (no freezing) ---
        DELAY_SECONDS = 1.2  # change to 5 if you really want, but 1–2 feels best

        # Start autorefresh loop if we have queued messages
        if st.session_state.pending_bot_msgs:
            st.session_state.bot_reveal_active = True

        if st.session_state.bot_reveal_active:
            # refresh every 300ms while revealing
            st_autorefresh(interval=300, key="bot_reveal_refresh")

            now = time.time()
            if st.session_state.pending_bot_msgs and (now - st.session_state.last_reveal_time) >= DELAY_SECONDS:
                role, msg_text = st.session_state.pending_bot_msgs.pop(0)
                add_msg(role, msg_text)
                st.session_state.last_reveal_time = now

            # stop refreshing when queue empty
            if not st.session_state.pending_bot_msgs:
                st.session_state.bot_reveal_active = False


        # Show chat as chat bubbles
        for m in st.session_state.chat:
            role = m["role"]
            chat_role = "user" if role == "You" else "assistant"
            with st.chat_message(chat_role):
                st.markdown(f"**{role}:** {m['text']}")

        # Chat input
        user_text = st.chat_input(
             "Type your message…",
             disabled=st.session_state.bot_reveal_active
         )


        if user_text:
            text = user_text.strip()

            # store participant message
            add_msg("You", text)
            st.session_state.turns += 1

            # extract items mentioned
            mentioned = extract_items_from_text(text)
            for it in mentioned:
                if it not in st.session_state.suggested_items:
                    st.session_state.suggested_items.append(it)

            # classify
            label, info = classify_proposal(mentioned)

           # --- Build bot response queue ---
            leader_text = leader_reply(leadership, text)
            st.session_state.pending_bot_msgs.append(("Leader", leader_text))

            # Occasionally add an extra leader intervention / hint
            if st.session_state.turns >= 1:
                hints = LEADER_HINTS.get(leadership, [])
                hint_index = st.session_state.leader_hint_index % len(hints) if hints else 0

                if hints and st.session_state.turns % 2 == 0:
                    candidate_hint = hints[hint_index]

                    # avoid adding a hint that is too similar to the main leader reply
                    if candidate_hint.lower() not in leader_text.lower() and leader_text.lower() not in candidate_hint.lower():
                        st.session_state.pending_bot_msgs.append(("Leader", candidate_hint))

                    st.session_state.leader_hint_index += 1

            st.session_state.last_reveal_time = 0.0

            step = st.session_state.teammate_step
            last_bot = st.session_state.last_bot_msg

            teammates = ["Anna", "Bas", "Carlos", "David", "Emily"]
            start = st.session_state.teammate_step % len(teammates)

            question_type = detect_question_type(text)
            short_simple_input = (
                len(text.strip()) < 28 and
                len(mentioned) <= 1 and
                question_type in ["item_check", "confirmation", "none"]
            )

            num_teammates = 2 if short_simple_input else 3
            selected_teammates = [teammates[(start + i) % len(teammates)] for i in range(num_teammates)]

            for idx, tm in enumerate(selected_teammates):
                reply = teammate_reply_persona(
                    teammate_name=tm,
                    user_text=text,
                    leader_text=leader_text,
                    label=label,
                    proposed_items=mentioned,
                    last_bot_msg=last_bot,
                    step=step + idx
                )
                st.session_state.pending_bot_msgs.append((tm, reply))
                last_bot = reply

            st.session_state.last_bot_msg = last_bot
            st.session_state.teammate_step += 1

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
    st.subheader("Final ranking")

    st.write("""
Rank the 15 items from **1 (most important)** to **15 (least important)**.  
Each rank can be used **only once**.
    """)

    if "nasa_ranking" not in st.session_state:
        st.session_state.nasa_ranking = {item: i + 1 for i, item in enumerate(NASA_ITEMS)}

    ranking = {}
    used_ranks = []

    for item in NASA_ITEMS:
        rank = st.selectbox(
            label=item,
            options=list(range(1, 16)),
            index=st.session_state.nasa_ranking[item] - 1,
            key=f"rank_{item}",
        )
        ranking[item] = rank
        used_ranks.append(rank)

    if len(set(used_ranks)) != len(used_ranks):
        st.warning("Each rank (1–15) must be used exactly once.")

    if st.button("Submit ranking"):
        if len(set(used_ranks)) != len(used_ranks):
            st.error("Please fix duplicate ranks before submitting.")
            return

        st.session_state.data["nasa_ranking"] = ranking
        st.session_state.data["nasa_score"] = compute_nasa_score(ranking)
        st.session_state.data["leadership_style"] = leadership
        st.session_state.data["prime"] = prime

        st.session_state.page = "post_survey_likert"
        st.rerun()

def page_post_survey_likert():
    scroll_to_top()
    st.title("Final questions - Part 1")

    st.write(
        "You have completed the task. Please answer a few final questions about your experience during the task."
    )

    st.caption("For the statements below, use the scale from 1 = strongly disagree to 7 = strongly agree.")

    likert_options = list(range(1, 8))

    with st.form("post_survey_likert_form"):
        st.subheader("Section 1: Statements")

        q1 = st.radio("1. I felt a positive connection with the other members of my team.", likert_options, horizontal=True)
        q2 = st.radio("2. I felt motivated to work together with my team to successfully complete the task.", likert_options, horizontal=True)
        q3 = st.radio("3. I felt proud to be part of this team.", likert_options, horizontal=True)
        q4 = st.radio("4. If you make a mistake on this team, it is often held against you.", likert_options, horizontal=True)
        q5 = st.radio("5. Members of this team are able to bring up problems and tough issues.", likert_options, horizontal=True)
        q6 = st.radio("6. People on this team sometimes reject others for being different.", likert_options, horizontal=True)
        q7 = st.radio("7. It is safe to take a risk on this team.", likert_options, horizontal=True)
        q8 = st.radio("8. It is difficult to ask other members of this team for help.", likert_options, horizontal=True)
        q9 = st.radio("9. No one on this team would deliberately act in a way that undermines my efforts.", likert_options, horizontal=True)
        q10 = st.radio("10. Working with members of this team, my unique skills and talents are valued and utilized.", likert_options, horizontal=True)
        q11 = st.radio("11. Communication within the team was clear and effective during the task.", likert_options, horizontal=True)
        q12 = st.radio("12. Team members listened to and considered each other’s input.", likert_options, horizontal=True)
        q13 = st.radio("13. The team coordinated well while working on the task.", likert_options, horizontal=True)
        q14 = st.radio("14. I felt that collaboration within the team was smooth and constructive.", likert_options, horizontal=True)
        q15 = st.radio("15. Overall, I am satisfied with how the team worked together.", likert_options, horizontal=True)

        submitted = st.form_submit_button("Continue")

        if submitted:
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

            st.session_state.page = "post_survey_open"
            st.rerun()


def page_post_survey_open():
    scroll_to_top()
    st.title("Final questions - Part 2")

    st.write(
        "Thank you. You may now answer a few final questions about the task and the experiment."
    )

    with st.form("post_survey_open_form"):
        st.subheader("Section 2: Final questions")

        leader_perception = st.radio(
            "Which statement felt most applicable to the team leader?",
            [
                "The team leader showed genuine concern for the well-being of team members.",
                "The team leader focused strongly on completing the task efficiently.",
                "The team leader made decisions in a controlling or directive manner.",
            ],
        )

        feedback_1 = st.text_area(
            "What did you think of the experiment?",
            height=150
        )

        feedback_2 = st.text_area(
            "Do you have any final thoughts or comments you would like to share?",
            height=150
        )

        submitted = st.form_submit_button("Submit final answers")

        if submitted:
            st.session_state.data["post_survey_open"] = {
                "leader_perception_statement": leader_perception,
                "open_feedback_1": feedback_1.strip(),
                "open_feedback_2": feedback_2.strip(),
            }

            st.session_state.page = "post_task"
            st.rerun()

def page_post_task():
    scroll_to_top()
    if "saved" not in st.session_state:

        participant_data = {
            "participant_id": st.session_state.participant_id,
            "leadership_style": st.session_state.data.get("leadership_style"),
            "prime": st.session_state.data.get("prime"),
            "priming_text": st.session_state.data.get("priming_text"),
            "age_category": st.session_state.data.get("age_category"),
            "gender": st.session_state.data.get("gender"),
            "country": st.session_state.data.get("country"),
            "nasa_score": st.session_state.data.get("nasa_score"),
            "discussion_log": format_discussion_log(),
            **st.session_state.data.get("post_survey_likert", {}),
            **st.session_state.data.get("post_survey_open", {}),
        }

        save_to_gsheet(participant_data)
        st.session_state.saved = True

    st.title("Thank you for participating ✅")
    st.write("Thank you for participating in this study. Your responses have been recorded successfully.")

    st.subheader("Performance")
    st.write(f"Your NASA score: **{st.session_state.data.get('nasa_score')}** (lower = better)")

# ----------------------------
# Router
# ----------------------------
if st.session_state.page == "consent":
    page_consent()
elif st.session_state.page == "priming":
    page_priming()
elif st.session_state.page == "task":
    page_task()
elif st.session_state.page == "post_survey_likert":
    page_post_survey_likert()
elif st.session_state.page == "post_survey_open":
    page_post_survey_open()
elif st.session_state.page == "post_task":
    page_post_task()
else:
    # fallback (in case something weird happens)
    st.session_state.page = "consent"
    st.rerun()
=======

>>>>>>> 93071376ba90fd20b632f78c235ac03ae20b6f6d
