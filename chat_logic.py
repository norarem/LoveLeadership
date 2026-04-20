import random
import re
import streamlit as st

from constants import (
    GOOD_TOP_ITEMS,
    BAD_TOP_ITEMS,
    NASA_ITEMS,
    NASA_EXPERT_RANK,
    NASA_REASONING_SHORT,
)


from text_parsing import (
    short_item_name,
    extract_items_from_text,
    classify_proposal,
    evaluate_rank_guess,
    summarize_items_for_reply,
    parse_message_features,
    normalize_text,
)


from ranking_helpers import (
    get_next_empty_ui_slots,
    get_item_current_ui_rank,
    classify_rank_quality,
    next_unresolved_slots,
    slot_candidate_text,
    get_ranking_context_snapshot,
)


def get_last_item_discussed():
    """Try to recover the most recently discussed NASA item from chat."""
    chat = st.session_state.get("chat", [])
    for msg in reversed(chat):
        mentioned = extract_items_from_text(msg.get("text", ""))
        if mentioned:
            return mentioned[0]
    return None


def recent_role_messages(role, n=8):
    msgs = []
    for msg in reversed(st.session_state.get("chat", [])):
        if msg.get("role") == role:
            msgs.append(msg.get("text", ""))
        if len(msgs) >= n:
            break
    return msgs


def get_next_slot_text(limit=3):
    next_slots = get_next_empty_ui_slots(limit=limit)
    if not next_slots:
        next_slots = next_unresolved_slots(limit=limit)

    if not next_slots:
        return "the next unresolved slots"

    return ", ".join([f"#{x}" for x in next_slots])


def top_slots_already_filled(min_filled=4):
    filled = get_filled_slots_from_ui().keys()
    top_filled = [rank for rank in filled if rank in [1, 2, 3, 4, 5]]
    return len(top_filled) >= min_filled


def get_filled_slots_from_ui():
    return {
        rank: item
        for item in NASA_ITEMS
        for rank in [st.session_state.get(f"rank_{item}", None)]
        if rank is not None
    }


def get_item_in_slot(slot: int):
    return get_filled_slots_from_ui().get(slot)


def add_leader_variation(base_reply, leadership_style):
    if random.random() < 0.28:
        extras = {
            "servant": [
                "I appreciate everyone contributing.",
                "Your input matters here.",
                "Let’s work through it together.",
            ],
            "task_focused": [
                "Let’s keep this efficient.",
                "Stay with the structure.",
                "Keep the reasoning clear and practical.",
            ],
            "authoritarian": [
                "Stay on track.",
                "Do not overcomplicate this.",
                "Follow the structure I’m setting.",
            ],
        }
        return base_reply + " " + random.choice(extras[leadership_style])
    return base_reply

def humanize_leader(text):
    replacements = {
        "Provide your top three items.": "Give me your top three.",
        "Use survival utility logic: air, water, navigation, communication.": "Think about what actually keeps you alive first: air, water, navigation, communication.",
        "Let’s keep this structured.": "Let’s stay focused.",
        "From a task perspective, ": "",
        "That is not the strongest placement. ": "That placement is probably off. ",
        "That needs adjustment. ": "I’d revise that. ",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text


def add_leader_tail(text, leadership_style, context="general"):
    """
    Small end-of-sentence variation so leader replies feel less templated.
    """
    if random.random() > 0.28:
        return text

    tails = {
        "servant": {
            "general": [
                " We can work from there.",
                " Let’s keep building from that.",
                " We’ll refine it together.",
            ],
            "progress": [
                " We’re getting somewhere.",
                " That helps us move forward.",
                " Let’s keep that momentum.",
            ],
            "correction": [
                " We can adjust it from here.",
                " Let’s refine that gently.",
                " We can improve that placement.",
            ],
        },
        "task_focused": {
            "general": [
                " Keep the structure clear.",
                " Stay practical.",
                " Focus on survival value.",
            ],
            "progress": [
                " Continue to the next slot.",
                " Keep the pace steady.",
                " That is enough to proceed.",
            ],
            "correction": [
                " Adjust it and continue.",
                " Re-evaluate and move on.",
                " Correct it before proceeding.",
            ],
        },
        "authoritarian": {
            "general": [
                " Keep moving.",
                " Do not drift.",
                " Stay on task.",
            ],
            "progress": [
                " Move on.",
                " That is enough.",
                " Continue.",
            ],
            "correction": [
                " Fix it.",
                " Adjust it now.",
                " Do not defend it.",
            ],
        },
    }

    return text + random.choice(
        tails.get(leadership_style, {}).get(context, [""])
    )


def add_authoritarian_human_variation(text, context="general"):
    """
    Make authoritarian replies feel controlling and low-warmth,
    but still realistic rather than cartoonishly rude.
    """

    openings = {
        "general": [
            "Listen.",
            "Keep this tight.",
            "Stay with the structure.",
            "We are not wandering here.",
        ],
        "progress": [
            "Good. Keep going.",
            "Fine. That works for now.",
            "That is enough to proceed.",
            "We can work with that.",
        ],
        "correction": [
            "No, that is not the strongest choice.",
            "That needs correcting.",
            "That is not where it should go.",
            "You are overvaluing that item.",
        ],
        "agreement": [
            "Good.",
            "Fine.",
            "That is workable.",
            "That helps.",
        ],
        "disagreement": [
            "Then give the better alternative.",
            "Then be specific.",
            "Then replace it with something stronger.",
            "Then state the correction clearly.",
        ],
    }

    closings = {
        "general": [
            "",
            " Do not overcomplicate it.",
            " Keep it moving.",
            " Stay disciplined.",
        ],
        "progress": [
            "",
            " Move to the next item.",
            " Now keep the pace up.",
            " Do not get stuck here.",
        ],
        "correction": [
            "",
            " Fix it and continue.",
            " Adjust it and move on.",
            " Do not get stuck defending it.",
        ],
        "agreement": [
            "",
            " Move on.",
            " Keep going.",
        ],
        "disagreement": [
            "",
            " We are not debating vaguely.",
            " Keep it concrete.",
        ],
    }

    if random.random() < 0.7:
        opening = random.choice(openings.get(context, openings["general"]))
        closing = random.choice(closings.get(context, closings["general"]))

        if not text.startswith(opening):
            text = f"{opening} {text}"

        if closing and closing.strip() not in text:
            text = text + closing

    return text

def avoid_repetition(teammate_name, new_text, n=10):
    recent = st.session_state.get("chat", [])[-n:]
    for msg in recent:
        if msg.get("role") == teammate_name and msg.get("text", "").strip() == new_text.strip():
            return True
    return False


def sanitize_generated_text(text: str) -> str:
    if not text:
        return text

    weird_fixes = {
        "pfeelstols": "pistols",
        "optimfeelstic": "optimistic",
        "oxygen tanks belongs": "oxygen tanks belong",
        "matches belongs": "matches belong",
        "oxygen tanks matters": "oxygen tanks matter",
        "matches matters": "matches matter",
        "pistols matters": "pistols matter",
        "pis probablytols": "pistols",
        "probablytols": "pistols",
    }

    for bad, good in weird_fixes.items():
        text = text.replace(bad, good)

    return text

def get_item_reasoning(item: str):
    return NASA_REASONING_SHORT.get(
        item,
        "its direct survival value matters more than Earth-based intuition here"
    )


def build_reasoned_comparison(a: str, b: str):
    a_short = short_item_name(a)
    b_short = short_item_name(b)
    a_reason = get_item_reasoning(a)
    b_reason = get_item_reasoning(b)

    return (
        f"{a_short.capitalize()} matters because {a_reason}, "
        f"while {b_short} matters because {b_reason}."
    )

def build_theme_guidance(reasoning_themes):
    parts = []

    if "communication" in reasoning_themes or "rescue" in reasoning_themes:
        parts.append("that kind of logic supports keeping the transmitter relatively high")

    if "navigation" in reasoning_themes:
        parts.append("it also supports the stellar map staying high")

    if "survival" in reasoning_themes:
        parts.append("and it reinforces why oxygen and water stay above almost everything else")

    if "ship_status" in reasoning_themes:
        parts.append("but we still have to rank only the salvaged items rather than rely on the ship itself")

    if not parts:
        return "that reasoning should still be translated into direct survival value"

    sentence = ". ".join(part.capitalize() for part in parts)
    if not sentence.endswith("."):
        sentence += "."
    return sentence

def build_progress_redirect(next_slots_text, leadership_style):
    if leadership_style == "servant":
        options = [
            f"The top feels steady enough for now. Let’s work carefully through {next_slots_text} together and make sure everyone stays with the reasoning.",
            f"We have enough of the strongest anchors to move on. Let’s compare the items around {next_slots_text} in a way that still leaves room for people to weigh in.",
            f"The top is taking shape. I’d like us to work through {next_slots_text} without rushing anyone past their point.",
        ]
    elif leadership_style == "task_focused":
        options = [
            f"The top looks stable enough. Work through {next_slots_text} next.",
            f"Keep the strongest anchors in place and resolve {next_slots_text}.",
            f"We have enough on the top tier for now. Move to {next_slots_text}.",
        ]
    else:
        options = [
            f"The top is settled enough. Do {next_slots_text} next.",
            f"That is enough on the top tier. Move to {next_slots_text}.",
            f"Stop circling the top. Resolve {next_slots_text}.",
        ]

    fresh = [opt for opt in options if not leader_recently_used_fragment([opt], n=6)]
    return random.choice(fresh or options)


def style_leader_reply(base_reply, leadership_style, context="general"):
    """
    Stronger style framing for each leader.
    context can be:
    - general
    - agreement
    - disagreement
    - correction
    - progress
    """

    if leadership_style == "servant":
        prefixes = {
            "general": [
                "Thank you for raising that. I want to make sure we give it the attention it deserves. ",
                "I’m glad you brought that up. Let’s work through it together in a way that feels clear to everyone. ",
                "I appreciate you naming that. It helps the team, and I want to make sure your point is properly heard. ",
                "Let’s stay with that for a moment so no one feels rushed past the reasoning. ",
                "That’s worth slowing down for. Let’s make sure the team feels clear on it before we move on. ",
            ],
            "agreement": [
                "I’m glad we’re finding some shared ground. That can help the team feel more steady. ",
                "It helps when people are building on each other like this. ",
                "I appreciate that common ground. It gives us something solid to build from together. ",
                "That kind of alignment can help everyone feel more confident in the decision. ",
            ],
            "disagreement": [
                "It’s okay to see this differently. I want to make sure both views are heard before we decide. ",
                "Different views can help us think better, so let’s hold both for a moment and keep the discussion respectful. ",
                "Let’s slow it down and make room for both sides of the reasoning. ",
                "That difference is useful. I don’t want anyone to feel talked past here. ",
            ],
            "correction": [
                "Let’s adjust that gently and keep everyone with us. ",
                "I think we can refine that together without losing the progress we’ve made. ",
                "Let’s revisit that carefully so the reasoning feels clearer and the team can feel confident about the choice. ",
                "I’d like us to take another look at that in a way that still feels supportive. ",
            ],
            "progress": [
                "We’re making thoughtful progress, and I appreciate how people are helping one another think this through. ",
                "This is moving in a good direction, and I’m glad people are building on each other’s ideas. ",
                "We’re getting somewhere together, and I want to make sure the discussion still feels open and supportive as we do. ",
                "I can see the ranking taking shape, and I appreciate the care people are showing in how they respond to each other. ",
            ],
        }
        return random.choice(prefixes.get(context, prefixes["general"])) + base_reply

    elif leadership_style == "task_focused":
        prefixes = {
            "general": [
                "Let’s keep this structured. ",
                "Let’s stay practical. ",
                "Start with the clearest survival logic. ",
            ],
            "agreement": [
                "Good. That helps us move forward. ",
                "Useful. That supports the ranking process. ",
            ],
            "disagreement": [
                "Then state the better alternative clearly. ",
                "Clarify the reasoning so we can evaluate it. ",
            ],
            "correction": [
                "That needs adjustment. ",
                "That is not the strongest placement. ",
            ],
            "progress": [
                "We are moving toward a workable ranking. ",
                "This helps narrow the decision. ",
            ],
        }
        return random.choice(prefixes.get(context, prefixes["general"])) + base_reply

    else:
        prefixes = {
            "general": [
                "",
                "Listen carefully. ",
                "Stay focused. ",
            ],
            "agreement": [
                "",
                "Good. ",
                "Fine. ",
            ],
            "disagreement": [
                "",
                "No. ",
                "Then be specific. ",
            ],
            "correction": [
                "",
                "That is not correct. ",
                "Fix that. ",
            ],
            "progress": [
                "",
                "Good. ",
                "That is enough. ",
            ],
        }
        return random.choice(prefixes.get(context, prefixes["general"])) + base_reply


def recently_said_by(teammate_name, phrase_fragment, n=8):
    chat = st.session_state.get("chat", [])[-n:]
    for msg in chat:
        if msg.get("role") == teammate_name and phrase_fragment.lower() in msg.get("text", "").lower():
            return True
    return False

def get_teammate_climate_bias(leadership_style):
    if leadership_style == "servant":
        return {
            "voice": 0.50,
            "deference": 0.06,
            "closure": 0.10,
        }
    elif leadership_style == "task_focused":
        return {
            "voice": 0.24,
            "deference": 0.18,
            "closure": 0.32,
        }
    else:
        return {
            "voice": 0.08,
            "deference": 0.42,
            "closure": 0.46,
        }


def get_conversation_phase():
    """
    Determine phase based on actual conversation length,
    not just a turns counter (which can be unreliable).
    """

    chat = st.session_state.get("chat", [])
    user_msgs = [m for m in chat if m.get("role") == "You"]

    n = len(user_msgs)

    if n <= 2:
        return "early"
    elif n <= 6:
        return "middle"
    return "late"

def item_already_recently_discussed(item: str, n=8):
    if not item:
        return False
    recent = st.session_state.get("chat", [])[-n:]
    for msg in recent:
        mentioned = extract_items_from_text(msg.get("text", ""))
        if item in mentioned:
            return True
    return False


def maybe_soften_certainty(text: str, teammate_name: str):
    soften_map = {
        "Anna": [
            ("is", "seems"),
            ("belongs", "probably belongs"),
        ],
        "Bas": [
            ("is", "feels"),
            ("belongs", "kind of belongs"),
        ],
        "Carlos": [
            ("is", "feels"),
        ],
        "David": [
        ],
        "Emily": [
            ("is", "is probably"),
            ("belongs", "appears to belong"),
        ],
    }

    pairs = soften_map.get(teammate_name, [])
    if not pairs or random.random() > 0.25:
        return text

    old, new = random.choice(pairs)
    return text.replace(old, new, 1)


def add_teammate_tail(teammate_name, text, phase="middle"):
    """
    Add small natural tails so teammate replies feel less templated.
    """
    if random.random() > 0.30:
        return text

    tails = {
        "Anna": [
            " That’s how I’m seeing it, at least.",
            " But I’d still compare it with the nearby items.",
            " I wouldn’t overcommit too fast though.",
        ],
        "Bas": [
            " At least that’s my instinct.",
            " Though I’m not fully sure.",
            " That’s kind of where I land right now.",
        ],
        "Carlos": [
            " That’s my current moon take anyway 😄",
            " Could be wrong, but that’s where I’m leaning.",
            " Which somehow feels more reasonable than it should 😄",
        ],
        "David": [
            " Don’t spend forever on it.",
            " Keep it moving.",
            " Then go to the next item.",
        ],
        "Emily": [
            " That seems most defensible to me.",
            " At least under the moon-specific logic.",
            " Relative to the stronger items, that makes sense.",
        ],
    }

    if phase == "early" and teammate_name in ["David", "Emily"]:
        return text

    return text + random.choice(tails.get(teammate_name, [""]))


def should_allow_teammate_disagreement(teammate_name, leadership_style):
    """
    Small bounded disagreement pattern.
    Keep subtle so leader manipulation remains primary.
    """
    base = {
        "Anna": 0.10,
        "Bas": 0.28,
        "Carlos": 0.12,
        "David": 0.08,
        "Emily": 0.14,
    }.get(teammate_name, 0.10)

    if leadership_style == "authoritarian":
        base *= 0.65
    elif leadership_style == "servant":
        base *= 1.10

    return random.random() < base

def recently_said_similar(role, phrase_fragments, n=8):
    recent = [x.lower() for x in recent_role_messages(role, n=n)]
    for frag in phrase_fragments:
        if any(frag.lower() in msg for msg in recent):
            return True
    return False


def leader_recently_used_fragment(fragments, n=8):
    recent = recent_role_messages("Leader", n=n)
    lowered = [msg.lower() for msg in recent]
    return any(
        fragment.lower() in msg
        for fragment in fragments
        for msg in lowered
    )


def detect_user_confidence_style(normalized_text: str):
    if not normalized_text:
        return "neutral"

    hedging_markers = [
        "maybe",
        "i guess",
        "not sure",
        "i think",
        "probably",
        "kind of",
        "sort of",
        "might be",
        "could be",
    ]

    confident_markers = [
        "definitely",
        "for sure",
        "obviously",
        "clearly",
        "must be",
        "has to be",
        "certainly",
    ]

    if any(marker in normalized_text for marker in hedging_markers):
        return "hedging"

    if any(marker in normalized_text for marker in confident_markers):
        return "confident"

    return "neutral"


def is_settle_and_move_message(user_text, first_item, guessed_rank, normalized_text):
    """
    Detect messages like:
    - 'I'll put matches at 15. What should we place next?'
    - 'Let's keep heating at 15. Any item you want to place somewhere?'
    """
    if not normalized_text:
        return False

    settling_language = any(
        phrase in normalized_text
        for phrase in [
            "i'm going to put",
            "im going to put",
            "i will put",
            "i'll put",
            "let's put",
            "lets put",
            "keep",
            "leave",
        ]
    )

    move_on_language = any(
        phrase in normalized_text
        for phrase in [
            "do you guys have",
            "what should",
            "what do you want",
            "any item",
            "place somewhere",
            "place next",
            "what next",
            "where should",
            "what item",
        ]
    )

    weak_bottom_item = first_item in {
        "Box of matches",
        "Magnetic compass",
        "Portable heating unit",
    }

    bottom_rank = guessed_rank in [14, 15] or "#15" in normalized_text or "15" in normalized_text

    return settling_language and move_on_language and (weak_bottom_item or bottom_rank)


def extract_named_teammates_from_text(text: str):
    t = normalize_text(text)
    names = []
    for name in ["Anna", "Bas", "Carlos", "David", "Emily"]:
        if re.search(rf"\b{name.lower()}\b", t):
            names.append(name)
    return names


def message_has_substance(text: str):
    if not text:
        return False

    t = normalize_text(text)

    if len(t) >= 45:
        return True

    if extract_items_from_text(t, already_normalized=True):
        return True

    if re.search(r"\b([1-9]|1[0-5])\b", t):
        return True

    if any(
        x in t
        for x in [
            "because",
            "survival",
            "navigation",
            "communication",
            "compare",
            "higher",
            "lower",
            "better",
            "worse",
            "top",
            "bottom",
        ]
    ):
        return True

    return False


def message_contains_question(text: str):
    if not text:
        return False

    t = normalize_text(text)
    return "?" in text or t.startswith(
        ("what", "which", "why", "how", "do ", "does ", "should ", "would ", "is ", "are ")
    )



def build_message_context(user_text, proposed_items=None):
    """
    Centralized message/context parsing so leader and teammates
    use the same interpretation of the participant message.
    """
    features = parse_message_features(user_text)
    ranking_ctx = get_ranking_context_snapshot()

    proposed = proposed_items if proposed_items is not None else features["mentioned_items"]
    first_item = proposed[0] if proposed else get_last_item_discussed()
    first_item_short = short_item_name(first_item) if first_item else None
    current_ui_rank = get_item_current_ui_rank(first_item) if first_item else None

    ui_slots = ranking_ctx["ui_summary"]
    remembered_slots = ui_slots if ui_slots else ranking_ctx["slot_memory_summary"]

    return {
        "features": features,
        "proposed": proposed,
        "first_item": first_item,
        "first_item_short": first_item_short,
        "current_ui_rank": current_ui_rank,
        "ui_slots": ui_slots,
        "remembered_slots": remembered_slots,
        "explicit_slot": features["slot_request"],
        "guessed_rank": features["rank"],
        "rank_range": features["rank_range"],
        "question_type": features["question_type"],
        "user_intent": features["user_intent"],
        "meta_intent": features["meta_intent"],
        "asking_direct_item": features["direct_item_question"],
        "asking_direct_rank": features["direct_rank_request"],
        "normalized_text": features["normalized_text"],
        "confidence_style": detect_user_confidence_style(features["normalized_text"]),
        "ranking_ctx": ranking_ctx,
        "rank_assignments": features["rank_assignments"],
        "reasoning_themes": features["reasoning_themes"],
    }

def format_natural_list(items, limit=2, fallback=""):
    items = items[:limit]
    if not items:
        return fallback
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + f" and {items[-1]}"


def has_visible_consensus(min_slots=2):
    filled = get_filled_slots_from_ui()
    slot_memory = st.session_state.get("slot_memory", {})
    resolved = slot_memory.get("resolved", {})
    tentative = slot_memory.get("tentative", {})

    return (
        len(filled) >= min_slots
        or len(resolved) >= min_slots
        or len(tentative) >= min_slots
    )

def has_group_exact_rank(item: str, rank: int):
    mem = st.session_state.get("group_rank_memory", {})
    info = mem.get(item)
    return isinstance(info, dict) and info.get("type") == "exact" and info.get("value") == rank


def summarize_full_ranking_feedback(rank_assignments):
    summary = {
        "anchors": [],
        "too_high": [],
        "too_low": [],
    }

    for entry in sorted(rank_assignments, key=lambda x: x["rank"]):
        item = entry["item"]
        guessed_rank = entry["rank"]
        correct_rank = NASA_EXPERT_RANK.get(item)

        if correct_rank is None:
            continue

        diff = guessed_rank - correct_rank
        short_name = short_item_name(item)

        if abs(diff) <= 1:
            summary["anchors"].append(short_name)
        elif diff < 0:
            summary["too_high"].append(short_name)
        else:
            summary["too_low"].append(short_name)

    for key in summary:
        deduped = []
        seen = set()
        for value in summary[key]:
            if value not in seen:
                seen.add(value)
                deduped.append(value)
        summary[key] = deduped

    return summary


def finalize_leader_reply(base_text, leadership_style, context="general"):
    reply = style_leader_reply(base_text, leadership_style, context=context)

    redundant_phrases = [
        "This helps narrow the decision.",
        "That is a workable direction.",
        "Stay with the structure.",
        "That is enough to proceed.",
        "Let’s keep this efficient.",
        "Keep the structure clear.",
    ]

    used = set()
    cleaned_parts = []

    for part in reply.split(". "):
        stripped = part.strip()
        if stripped in redundant_phrases:
            if stripped in used:
                continue
            used.add(stripped)
        cleaned_parts.append(part)

    reply = ". ".join(cleaned_parts)

    added_variation = False

    if leadership_style == "authoritarian":
        new_reply = add_authoritarian_human_variation(reply, context=context)
        added_variation = (new_reply != reply)
        reply = new_reply
    else:
        new_reply = add_leader_variation(reply, leadership_style)
        added_variation = (new_reply != reply)
        reply = new_reply

    reply = humanize_leader(reply)

    sentence_count = sum(1 for s in reply.replace("!", ".").replace("?", ".").split(".") if s.strip())

    if not added_variation and sentence_count <= 2:
        reply = add_leader_tail(reply, leadership_style, context=context)

    return reply

def leader_reply(leadership_style, user_text):
    ctx = build_message_context(user_text)
    proposed = ctx["proposed"]
    label, info = classify_proposal(proposed)

    guessed_rank = ctx["guessed_rank"]
    rank_range = ctx["rank_range"]
    question_type = ctx["question_type"]
    user_intent = ctx["user_intent"]
    meta_intent = ctx["meta_intent"]

    normalized_text = ctx["normalized_text"]
    settle_and_move = is_settle_and_move_message(
        user_text=user_text,
        first_item=ctx["first_item"],
        guessed_rank=guessed_rank,
        normalized_text=normalized_text,
    )

    first_item = ctx["first_item"]
    first_item_short = ctx["first_item_short"]
    current_ui_rank = ctx["current_ui_rank"]
    remembered_slots = ctx["remembered_slots"]
    explicit_slot = ctx["explicit_slot"]
    asking_direct_item = ctx["asking_direct_item"]
    top_already_done = top_slots_already_filled()
    rank_assignments = ctx["rank_assignments"]
    reasoning_themes = ctx["reasoning_themes"]
    addressed_teammates = extract_named_teammates_from_text(user_text)

    def finish(base_text, context="general", invite_named=False):
        if invite_named and addressed_teammates:
            names = format_natural_list(addressed_teammates, limit=2)
            if leadership_style == "servant":
                base_text += f" {names}, I’d especially value your thoughts on that, and if anyone else sees it differently or still feels unsure, there is room to say so too."
            elif leadership_style == "task_focused":
                base_text += f" {names}, weigh in on that next."
            else:
                base_text += f" {names}, answer that directly."
        return finalize_leader_reply(base_text, leadership_style, context=context)

    def next_slot_prompt():
        return get_next_slot_text(limit=3)

    def rank_hint():
        if explicit_slot is not None:
            return explicit_slot
        if guessed_rank is not None:
            return guessed_rank
        if rank_range is not None:
            return round((rank_range[0] + rank_range[1]) / 2)
        return None

    if meta_intent == "scenario_question":
        if leadership_style == "servant":
            return finish(
                "Assume the ship is damaged enough that we cannot rely on it, and assume we do not currently have outside contact. Let’s judge only the 15 salvaged items together.",
                context="general",
                invite_named=True,
            )
        if leadership_style == "task_focused":
            return finish(
                "Assume the ship is not usable for transport or communication, and assume no contact has been made yet. Rank only the 15 salvaged items.",
                context="general",
                invite_named=True,
            )
        return finish(
            "Assume the ship is unusable and no contact has been made. Rank only the 15 items.",
            context="general",
            invite_named=True,
        )

    if user_intent == "full_ranking_proposal" and rank_assignments:
        summary = summarize_full_ranking_feedback(rank_assignments)
        anchors = format_natural_list(summary["anchors"], limit=3, fallback="oxygen tanks and water")
        too_high = format_natural_list(summary["too_high"], limit=2)
        too_low = format_natural_list(summary["too_low"], limit=2)

        if leadership_style == "servant":
            reply = f"Thank you for drafting the full ranking. The strongest anchors are {anchors}."
            if too_high:
                reply += f" I’d move {too_high} lower."
            if too_low:
                reply += f" I’d bring {too_low} higher."
            reply += " Then we can fine-tune the middle instead of restarting from scratch."
            return finish(reply, context="correction" if too_high or too_low else "progress", invite_named=True)

        if leadership_style == "task_focused":
            reply = f"This full draft is useful. The strongest anchors are {anchors}."
            if too_high:
                reply += f" Lower {too_high}."
            if too_low:
                reply += f" Raise {too_low}."
            reply += " Then refine the middle."
            return finish(reply, context="correction" if too_high or too_low else "progress", invite_named=True)

        reply = f"Good. A full draft is better than drifting. Keep {anchors} as the anchors."
        if too_high:
            reply += f" Lower {too_high}."
        if too_low:
            reply += f" Raise {too_low}."
        reply += " Then lock the middle."
        return finish(reply, context="correction" if too_high or too_low else "progress", invite_named=True)

    if user_intent == "frustration":
        hostile_language = any(x in normalized_text for x in [
            "shut up",
            "hou je bek",
            "hou je mond",
            "bek houden",
            "hou je smoel",
        ])

        if leadership_style == "servant":
            return finish(
                "I can hear the frustration. Let’s reset and make this more useful: give one unresolved item or one comparison, and we’ll respond to that directly.",
                context="general",
                invite_named=True,
            )

        if leadership_style == "task_focused":
            return finish(
                "Reset. Name one unresolved item or one comparison, and we’ll handle that directly.",
                context="general",
                invite_named=True,
            )

        if hostile_language:
            return finish(
                "Enough. Cut that out and stay on task. Give one unresolved item or one comparison.",
                context="general",
            )

        return finish(
            "Fine. Reset. Give one unresolved item or one comparison, and we’ll answer that directly.",
            context="general",
        )

    if reasoning_themes and meta_intent == "none":
        guidance = build_theme_guidance(reasoning_themes)

        if first_item and explicit_slot is None and guessed_rank is None and rank_range is None:
            if leadership_style == "servant":
                return finish(
                    f"That reasoning is really helpful. It does make a stronger case for {first_item_short}. {guidance} I want to make sure everyone feels clear and comfortable with that logic before we settle the placement.",
                    context="general",
                    invite_named=True,
                )

            if leadership_style == "task_focused":
                return finish(
                    f"That logic is useful. It does support {first_item_short}. {guidance} Use that reasoning to judge where it belongs.",
                    context="general",
                    invite_named=True,
                )

            return finish(
                f"That reasoning points toward {first_item_short}. {guidance} Rank accordingly.",
                context="general",
                invite_named=True,
            )

        if not proposed:
            if leadership_style == "servant":
                return finish(
                    f"That line of reasoning is really helpful. {guidance} I’d like us to use that logic as we place the next items together, while making sure everyone still has room to weigh in.",
                    context="general",
                    invite_named=True,
                )

            if leadership_style == "task_focused":
                return finish(
                    f"That logic is useful. {guidance} Use that to guide the next placements.",
                    context="general",
                    invite_named=True,
                )

            return finish(
                f"That reasoning matters. {guidance} Rank accordingly.",
                context="general",
                invite_named=True,
            )

    if meta_intent == "moon_why":
        if leadership_style == "servant":
            return finish(
                "Because moon conditions change what is actually useful. Several Earth-based assumptions become misleading there.",
                context="general"
            )
        if leadership_style == "task_focused":
            return finish(
                "Because the moon changes the functional value of the items. Earth logic misranks several of them.",
                context="general"
            )
        return finish(
            "Because this is not Earth. Moon conditions change which items are useful.",
            context="general"
        )

    if meta_intent == "boundary_check":
        return finish(
            "Correct. If it is already at 15, stop adjusting it and move on.",
            context="progress"
        )

    if meta_intent == "already_done":
        return finish(
            f"Yes. We already have part of the ranking. Move to {next_slot_prompt()} instead of restarting the same items.",
            context="progress"
        )

    if meta_intent == "confused":
        if leadership_style == "servant":
            return finish(
                f"That’s okay. The next step is simple: stop revisiting the settled items and focus on {next_slot_prompt()}.",
                context="general",
                invite_named=True,
            )
        if leadership_style == "task_focused":
            return finish(
                f"Next step: stop repeating settled items and fill {next_slot_prompt()}.",
                context="general",
                invite_named=True,
            )
        return finish(
            f"Next step: fill {next_slot_prompt()}.",
            context="general",
            invite_named=True,
        )

    if meta_intent == "next_step":
        return finish(
            f"The next step is to fill {next_slot_prompt()}, not to restart the top of the ranking.",
            context="progress",
            invite_named=True,
        )

    if explicit_slot is not None and not proposed:
        filled_item = get_item_in_slot(explicit_slot)
        if filled_item is not None:
            filled_short = short_item_name(filled_item)
            return finish(
                f"#{explicit_slot} already seems to be filled with {filled_short}. Let’s move to {next_slot_prompt()} instead.",
                context="progress",
                invite_named=True,
            )

        suggestion = slot_candidate_text(explicit_slot)
        if suggestion:
            if leadership_style == "servant":
                return finish(
                    f"For #{explicit_slot}, I’d look at {suggestion}, depending on what we already placed nearby.",
                    context="general",
                    invite_named=True,
                )
            if leadership_style == "task_focused":
                return finish(
                    f"For #{explicit_slot}, a sensible candidate is {suggestion}. Compare it with the surrounding ranks.",
                    context="general",
                    invite_named=True,
                )
            return finish(
                f"For #{explicit_slot}, use {suggestion}. Keep the group focused on that slot.",
                context="general",
                invite_named=True,
            )

    if settle_and_move:
        if leadership_style == "servant":
            return finish(
                "Yes — that low item can stay near the bottom. I’d move on to one of the stronger remaining items next, especially the stellar map, transmitter, or rope tier.",
                context="progress",
                invite_named=True,
            )
        if leadership_style == "task_focused":
            return finish(
                "Yes. Leave that low item there. Next, place one of the stronger remaining items and keep moving.",
                context="progress",
                invite_named=True,
            )
        return finish(
            "Fine. Leave it low. Place a stronger item next and continue.",
            context="progress",
            invite_named=True,
        )

    if first_item and (asking_direct_item or guessed_rank is not None or rank_range is not None or explicit_slot is not None):
        candidate_rank = rank_hint()

        if first_item == "Two 100-lb tanks of oxygen" and candidate_rank == 1:
            return finish("Yes — oxygen is the strongest candidate for #1.", context="progress", invite_named=True)

        if first_item == "5 gallons of water" and candidate_rank == 1:
            return finish(
                "Water is essential, but I would still keep oxygen at #1 and water at #2.",
                context="correction",
                invite_named=True,
            )

        if first_item == "5 gallons of water" and candidate_rank == 2:
            return finish("Yes — water is a strong fit for #2.", context="progress", invite_named=True)

        if current_ui_rank is not None:
            quality = classify_rank_quality(first_item, current_ui_rank)
            if quality == "strong":
                return finish(
                    f"You currently have {first_item_short} at #{current_ui_rank}, and that seems strong enough to keep unless a better comparison appears.",
                    context="progress",
                    invite_named=True,
                )
            if quality == "okay":
                return finish(
                    f"You currently have {first_item_short} at #{current_ui_rank}, which is a plausible range. I’d compare it with the nearby items before changing it.",
                    context="general",
                    invite_named=True,
                )
            return finish(
                f"You currently have {first_item_short} at #{current_ui_rank}, but that is probably not the strongest placement.",
                context="correction",
                invite_named=True,
            )

        if first_item in GOOD_TOP_ITEMS:
            if candidate_rank is not None and candidate_rank > 6:
                return finish(
                    f"{first_item_short.capitalize()} should stay much higher than that.",
                    context="correction",
                    invite_named=True,
                )
            return finish(
                f"{first_item_short.capitalize()} belongs relatively high in the ranking.",
                context="general",
                invite_named=True,
            )

        if first_item in BAD_TOP_ITEMS:
            if candidate_rank is not None and candidate_rank <= 10:
                return finish(
                    f"{first_item_short.capitalize()} is too high there. Keep it near the bottom.",
                    context="correction",
                    invite_named=True,
                )
            return finish(
                f"{first_item_short.capitalize()} belongs relatively low in the ranking.",
                context="general",
                invite_named=True,
            )

        if first_item == "One case of dehydrated milk":
            return finish(
                "Dehydrated milk is more of a lower-middle item, roughly around #11–#12 rather than near the top.",
                context="general",
                invite_named=True,
            )

        if first_item == "50 feet of nylon rope":
            return finish(
                "Nylon rope is a solid middle item, roughly around #6–#7.",
                context="general",
                invite_named=True,
            )

        if first_item == "Parachute silk":
            return finish(
                "Parachute silk is usually a useful middle item, roughly around #8.",
                context="general",
                invite_named=True,
            )

        if first_item == "Self-inflating life raft":
            return finish(
                "The life raft is more of a lower-middle item, roughly around #8–#10.",
                context="general",
                invite_named=True,
            )

        if first_item == "First aid kit (including injection needle)":
            return finish(
                "First aid kit is a fairly useful middle item, roughly around #7.",
                context="general",
                invite_named=True,
            )

        if first_item == "Signal flares":
            return finish(
                "Signal flares are more lower-middle, roughly around #10.",
                context="general",
                invite_named=True,
            )

        if first_item == "Two .45 caliber pistols":
            return finish(
                "Pistols are more lower-middle, roughly around #11.",
                context="general",
                invite_named=True,
            )

    if user_intent == "multi_item_proposal" and proposed:
        summary = summarize_items_for_reply(proposed)

        if label == "good":
            return finish(
                f"That is a workable direction ({summary}). Keep the strongest items high, then resolve {next_slot_prompt()}.",
                context="progress",
                invite_named=True,
            )

        if label == "mixed":
            return finish(
                f"That is partly workable ({summary}). Keep the stronger items high and replace the weaker ones.",
                context="correction",
                invite_named=True,
            )

        if label == "bad":
            return finish(
                f"That is not the strongest direction ({summary}). Rebuild around oxygen, water, map, and transmitter.",
                context="correction",
                invite_named=True,
            )

    if question_type == "why" and first_item:
        reason = get_item_reasoning(first_item)

        if leadership_style == "servant":
            return finish(
                f"I’d place {first_item_short} based on the fact that {reason}. I want us to make the reasoning clear enough that everyone feels comfortable with the decision before we lock it in.",
                context="general",
                invite_named=True,
            )

        if leadership_style == "task_focused":
            return finish(
                f"{first_item_short.capitalize()} should be judged by the fact that {reason}.",
                context="general",
                invite_named=True,
            )

        return finish(
            f"{first_item_short.capitalize()} matters because {reason}. Rank it accordingly.",
            context="general",
            invite_named=True,
        )

    if question_type == "comparison" and len(proposed) >= 2:
        pair = {proposed[0], proposed[1]}
        if pair == {"Two 100-lb tanks of oxygen", "5 gallons of water"}:
            if leadership_style == "servant":
                return finish(
                    "Both are essential, but I would still place oxygen at #1 and water at #2.",
                    context="general",
                    invite_named=True,
                )
            if leadership_style == "task_focused":
                return finish(
                    "Keep oxygen at #1 and water at #2.",
                    context="general",
                    invite_named=True,
                )
            return finish(
                "Oxygen first. Water second.",
                context="general",
                invite_named=True,
            )

        a, b = proposed[0], proposed[1]
        comparison_logic = build_reasoned_comparison(a, b)

        if leadership_style == "servant":
            return finish(
                f"Let’s compare them carefully. {comparison_logic} I’d place the one with the more immediate survival value first, but I want us to hear the reasoning before we settle it.",
                context="general",
                invite_named=True,
            )

        if leadership_style == "task_focused":
            return finish(
                f"{comparison_logic} Place the one with the more immediate survival value first.",
                context="general",
                invite_named=True,
            )

        return finish(
            f"{comparison_logic} Put the stronger one first and move on.",
            context="general",
            invite_named=True,
        )

    if question_type == "agreement":
        return finish(
            "Good. Use that agreement to keep the ranking moving.",
            context="agreement",
            invite_named=True,
        )

    if question_type == "disagreement":
        return finish(
            "Then state the better alternative clearly and keep moving.",
            context="disagreement",
            invite_named=True,
        )

    if top_already_done:
        return finish(
            build_progress_redirect(next_slot_prompt(), leadership_style),
            context="progress",
            invite_named=True,
        )


    if remembered_slots:
        return finish(
            f"So far we seem to have {remembered_slots}. {build_progress_redirect(next_slot_prompt(), leadership_style)}",
            context="progress",
            invite_named=True,
        )

    if leadership_style == "servant":
        return finish(
            f"Start with the items you think belong near the top, and we’ll refine them together from there.",
            context="general",
            invite_named=True,
        )

    if leadership_style == "task_focused":
        return finish(
            f"Start with the strongest items first, then fill {next_slot_prompt()}.",
            context="general",
            invite_named=True,
        )

    return finish(
        f"State the strongest remaining items and move through {next_slot_prompt()}.",
        context="general",
        invite_named=True,
    )



def teammate_reply_persona(
    teammate_name,
    user_text,
    leader_text,
    label,
    proposed_items,
    last_bot_msg,
    step,
    reply_to_role=None,
    reply_to_text=None
):
    leadership_style = st.session_state.condition[0]
    climate = get_teammate_climate_bias(leadership_style)

    ctx = build_message_context(user_text, proposed_items=proposed_items)

    guessed_rank = ctx["guessed_rank"]
    rank_range = ctx["rank_range"]
    question_type = ctx["question_type"]
    meta_intent = ctx["meta_intent"]

    first_item = ctx["first_item"]
    user_item = first_item
    current_ui_rank = ctx["current_ui_rank"]
    phase = get_conversation_phase()
    top_already_done = top_slots_already_filled()
    remembered_slots = ctx["remembered_slots"]
    explicit_slot = ctx["explicit_slot"]
    lower_text = ctx["normalized_text"]
    asking_direct_item = ctx["asking_direct_item"]
    confidence_style = ctx["confidence_style"]
    user_intent = ctx["user_intent"]
    reply_to_role = reply_to_role or ""
    reply_to_text = reply_to_text or ""
    rank_assignments = ctx["rank_assignments"]
    reasoning_themes = ctx["reasoning_themes"]

    clarification_request = any(x in lower_text for x in [
        "what do you mean",
        "what do you mean by that",
        "why do you think",
        "why do you say",
        "how do you mean",
    ])

    addressed_teammates = extract_named_teammates_from_text(user_text)
    directly_addressed = teammate_name in addressed_teammates

    def safe_pick(options, fallback):
        shuffled = options[:]
        random.shuffle(shuffled)

        candidate = None
        for option in shuffled:
            if not avoid_repetition(teammate_name, option):
                candidate = option
                break

        if candidate is None:
            candidate = fallback

        candidate = maybe_soften_certainty(candidate, teammate_name)
        candidate = add_teammate_tail(teammate_name, candidate, phase=phase)
        candidate = sanitize_generated_text(candidate)
        return candidate

    def maybe_disagree(base_text, alt_text):
        disagreement_allowed = should_allow_teammate_disagreement(teammate_name, leadership_style)

        if leadership_style == "authoritarian":
            disagreement_allowed = disagreement_allowed and random.random() < 0.70
        elif leadership_style == "servant":
            disagreement_allowed = disagreement_allowed or (random.random() < climate["voice"] * 0.20)

        if disagreement_allowed:
            return maybe_soften_certainty(alt_text, teammate_name)
        return maybe_soften_certainty(base_text, teammate_name)

    def maybe_align_with_leader(base_text, aligned_text):
        align_prob = climate["deference"]

        if leadership_style == "servant":
            align_prob *= 0.75
        elif leadership_style == "task_focused":
            align_prob *= 1.00
        else:
            align_prob *= 1.20

        if "Leader" in reply_to_role and random.random() < align_prob:
            return maybe_soften_certainty(aligned_text, teammate_name)

        return maybe_soften_certainty(base_text, teammate_name)

    def rank_hint():
        if current_ui_rank is not None:
            return current_ui_rank
        if explicit_slot is not None:
            return explicit_slot
        if guessed_rank is not None:
            return guessed_rank
        if rank_range is not None:
            return round((rank_range[0] + rank_range[1]) / 2)
        return None

    def initiative_prompt():
        pools = {
            "Anna": [
                "I’d probably compare first aid kit and nylon rope next. Which one feels stronger to you?",
                "We could sort out the middle by comparing parachute silk, rope, and first aid. That might help.",
                "Emily, would you still keep the map above the transmitter, or not?",
            ],
            "Bas": [
                "Maybe we compare rope and first aid next? I’m honestly not sure which one wins.",
                "Do we think life raft should stay below parachute silk, or am I overthinking that?",
                "Would rope beat flares for you, or not really?",
            ],
            "Carlos": [
                "Can we settle whether the map beats the transmitter before the moon starts judging us again? 😄",
                "Are we treating the top four as settled now, or not yet?",
                "Should we compare rope, first aid, and parachute silk next instead of bouncing around? 😄",
            ],
            "David": [
                "Can someone lock one of the middle slots so we stop circling?",
                "Pick the stronger middle item and place it.",
                "Do map, rope, or first aid next. Just choose one.",
            ],
            "Emily": [
                "I think we should compare rope, first aid, and parachute silk next, because they sit in a similar band.",
                "Would you rather resolve the map/transmitter tier fully first, or move straight to the middle items?",
                "Carlos, do you still think the transmitter belongs above food, or would you switch them?",
            ],
        }
        return safe_pick(pools[teammate_name], "We should compare the next middle items directly.")

    def is_low_priority_item(item):
        rank = NASA_EXPERT_RANK.get(item)
        return rank is not None and rank >= 12

    def prior_reply_already_reasoned_about(item):
        if not reply_to_text:
            return False

        lowered = normalize_text(reply_to_text)
        short_name = short_item_name(item)
        reason = get_item_reasoning(item)
        reason_core = reason.split(",")[0]

        return (
            short_name in lowered
            and (
                "because" in lowered
                or reason_core in lowered
            )
        )

    def reasoned_item_take(item):
        short_name = short_item_name(item)
        reason = get_item_reasoning(item)

        if prior_reply_already_reasoned_about(item):
            followup_pools = {
                "Anna": [
                    f"That logic makes sense to me. I’d just compare {short_name} with the nearby items before locking it in.",
                    f"I can follow that reasoning. I’d just test {short_name} against the nearby placements before settling it.",
                ],
                "Bas": [
                    f"Yeah, I can go with that logic. I’d just compare {short_name} with the nearby items once more.",
                    f"That sounds fair to me. I’d still test {short_name} against the surrounding ranks though.",
                ],
                "Carlos": [
                    f"Yeah, fair 😄 I don’t need to repeat the same logic, but I’d still compare {short_name} with the nearby items.",
                    f"That reasoning tracks 😄 I’d just test {short_name} against the neighboring spots before we lock it.",
                ],
                "David": [
                    f"Fine. That logic is already on the table. Compare {short_name} once, then move on.",
                    f"We already have the reason. Test {short_name} against the nearby item and continue.",
                ],
                "Emily": [
                    f"That reasoning is already fairly clear, so the next useful step is comparing {short_name} with the nearby candidates.",
                    f"I think the logic has already been stated. What matters now is whether {short_name} beats the neighboring items.",
                ],
            }
            return safe_pick(
                followup_pools[teammate_name],
                f"The logic for {short_name} is already fairly clear; now compare it with the nearby items."
            )

        if is_low_priority_item(item):
            pools = {
                "Anna": [
                    f"I’d keep {short_name} lower because {reason}.",
                    f"For me, {short_name} should stay low because {reason}.",
                ],
                "Bas": [
                    f"I’d keep {short_name} pretty low because {reason}.",
                    f"{short_name.capitalize()} sounds intuitive, but I’d still rank it lower because {reason}.",
                ],
                "Carlos": [
                    f"I’d keep {short_name} low because {reason} 😄",
                    f"{short_name.capitalize()} is giving false confidence energy, because {reason} 😄",
                ],
                "David": [
                    f"{short_name.capitalize()} should stay low because {reason}. Use that and move on.",
                    f"Simple: keep {short_name} low because {reason}.",
                ],
                "Emily": [
                    f"{short_name.capitalize()} should stay low because {reason}.",
                    f"I’d rank {short_name} lower on the basis that {reason}.",
                ],
            }
            return safe_pick(
                pools[teammate_name],
                f"{short_name.capitalize()} should stay low because {reason}."
            )

        pools = {
            "Anna": [
                f"I’d keep {short_name} in mind because {reason}.",
                f"For me, {short_name} matters because {reason}.",
            ],
            "Bas": [
                f"I think {short_name} is stronger than it sounds because {reason}.",
                f"{short_name.capitalize()} gets points from me because {reason}.",
            ],
            "Carlos": [
                f"{short_name.capitalize()} actually matters because {reason} 😄",
                f"I’d give {short_name} credit because {reason}.",
            ],
            "David": [
                f"{short_name.capitalize()} matters because {reason}. Use that and move on.",
                f"Simple: {short_name} matters because {reason}. Rank it accordingly.",
            ],
            "Emily": [
                f"{short_name.capitalize()} should be judged by the fact that {reason}.",
                f"I’d rank {short_name} based on the fact that {reason}.",
            ],
        }

        return safe_pick(
            pools[teammate_name],
            f"{short_name.capitalize()} matters because {reason}."
        )

    def reasoned_comparison_take(a, b):
        a_short = short_item_name(a)
        b_short = short_item_name(b)
        a_reason = get_item_reasoning(a)
        b_reason = get_item_reasoning(b)

        pools = {
            "Anna": [
                f"I’d compare them this way: {a_short} matters because {a_reason}, while {b_short} matters because {b_reason}.",
            ],
            "Bas": [
                f"For me, it comes down to this: {a_short} matters because {a_reason}, but {b_short} matters because {b_reason}.",
            ],
            "Carlos": [
                f"If we do actual moon logic, {a_short} matters because {a_reason}, while {b_short} matters because {b_reason} 😄",
            ],
            "David": [
                f"{a_short.capitalize()} matters because {a_reason}. {b_short.capitalize()} matters because {b_reason}. Pick the stronger one.",
            ],
            "Emily": [
                f"I’d compare them by function: {a_short} matters because {a_reason}, while {b_short} matters because {b_reason}.",
            ],
        }

        return safe_pick(
            pools[teammate_name],
            f"{a_short.capitalize()} matters because {a_reason}, while {b_short} matters because {b_reason}."
        )

    def answer_about_item(item, direct=False):
        short_name = short_item_name(item)
        hinted_rank = rank_hint()

        if current_ui_rank is not None:
            quality = classify_rank_quality(item, current_ui_rank)
            pools = {
                "Anna": {
                    "strong": [
                        f"I’d probably keep {short_name} at #{current_ui_rank}. That seems pretty reasonable.",
                        f"{short_name.capitalize()} at #{current_ui_rank} feels quite solid to me.",
                    ],
                    "okay": [
                        f"{short_name.capitalize()} at #{current_ui_rank} seems workable, though I’d compare it with the nearby items.",
                        f"I could see {short_name} staying at #{current_ui_rank}, but it depends on what sits around it.",
                    ],
                    "weak": [
                        f"I’d probably rethink {short_name} at #{current_ui_rank}. That feels a bit off to me.",
                        f"{short_name.capitalize()} at #{current_ui_rank} does not feel like the strongest fit.",
                    ],
                },
                "Bas": {
                    "strong": [
                        f"Yeah, {short_name} at #{current_ui_rank} sounds fair.",
                        f"Okay, I can see {short_name} staying there.",
                    ],
                    "okay": [
                        f"Maybe {short_name} at #{current_ui_rank} works, honestly.",
                        f"I can kind of see that placement for {short_name}.",
                    ],
                    "weak": [
                        f"Hm, {short_name} at #{current_ui_rank} feels a bit weird, even to me.",
                        f"I might move {short_name} somewhere else, honestly.",
                    ],
                },
                "Carlos": {
                    "strong": [
                        f"Honestly, {short_name} at #{current_ui_rank} looks pretty decent 😄",
                        f"That slot for {short_name} actually feels kind of solid.",
                    ],
                    "okay": [
                        f"{short_name.capitalize()} at #{current_ui_rank} is not a disaster 😄",
                        f"That placement for {short_name} seems discussable.",
                    ],
                    "weak": [
                        f"{short_name.capitalize()} at #{current_ui_rank} feels a little cursed 😄",
                        f"I’m not fully sold on {short_name} living at #{current_ui_rank}.",
                    ],
                },
                "David": {
                    "strong": [
                        f"Fine. Keep {short_name} at #{current_ui_rank}. Next.",
                        f"That works for {short_name}. Move on.",
                    ],
                    "okay": [
                        f"Close enough for now. Keep moving.",
                        f"That slot is workable. Next item.",
                    ],
                    "weak": [
                        f"No, I’d move {short_name} from #{current_ui_rank}.",
                        f"That’s not the best slot. Fix it and move on.",
                    ],
                },
                "Emily": {
                    "strong": [
                        f"That placement for {short_name} is defensible.",
                        f"{short_name.capitalize()} at #{current_ui_rank} is in a strong range.",
                    ],
                    "okay": [
                        f"{short_name.capitalize()} at #{current_ui_rank} is in a plausible range, though not necessarily exact.",
                        f"I can defend that placement, but I would still compare it carefully.",
                    ],
                    "weak": [
                        f"I don’t think {short_name} is best placed at #{current_ui_rank}.",
                        f"That placement for {short_name} is probably not optimal.",
                    ],
                },
            }

            quality_key = quality if quality in ["strong", "okay", "weak"] else "okay"
            return safe_pick(
                pools[teammate_name][quality_key],
                f"{short_name.capitalize()} is currently at #{current_ui_rank}."
            )
        
        if direct or question_type == "why":
            return reasoned_item_take(item)

        if item == "Two 100-lb tanks of oxygen":
            pools = {
                "Anna": ["I’d still put oxygen first."],
                "Bas": ["Yeah, oxygen feels like the safest bet for the top."],
                "Carlos": ["Oxygen still feels like the moon MVP to me 😄"],
                "David": ["Oxygen first. Move on."],
                "Emily": ["Oxygen should remain at or near the very top."],
            }
            return safe_pick(pools[teammate_name], "Oxygen should be at the top.")

        if item == "5 gallons of water":
            pools = {
                "Anna": ["Water is definitely top-tier, though I’d still keep oxygen just above it."],
                "Bas": ["Water sounds extremely high to me, just maybe not above oxygen."],
                "Carlos": ["Water is elite-tier, just probably not above oxygen 😄"],
                "David": ["Water high. Probably #2."],
                "Emily": ["Water should stay very high, usually just below oxygen."],
            }
            return safe_pick(pools[teammate_name], "Water should stay very high.")

        if item in {"Stellar map (of the moon's constellations)", "Solar-powered FM receiver-transmitter", "Food concentrate"}:
            pools = {
                "Anna": [f"I’d keep {short_name} relatively high, but not above oxygen and water."],
                "Bas": [f"{short_name.capitalize()} sounds pretty strong to me."],
                "Carlos": [f"{short_name.capitalize()} feels like one of the serious moon answers 😄"],
                "David": [f"{short_name.capitalize()} belongs in the stronger half. Next."],
                "Emily": [f"{short_name.capitalize()} belongs in the stronger part of the ranking."],
            }
            return safe_pick(pools[teammate_name], f"{short_name.capitalize()} should stay relatively high.")

        if item in {"Box of matches", "Magnetic compass", "Portable heating unit"}:
            pools = {
                "Anna": [f"I wouldn’t rank {short_name} very high."],
                "Bas": [f"{short_name.capitalize()} feels intuitive, but probably lower than it sounds."],
                "Carlos": [f"{short_name.capitalize()} feels like classic Earth logic getting us in trouble 😄"],
                "David": [f"{short_name.capitalize()} low. Keep moving."],
                "Emily": [f"{short_name.capitalize()} belongs near the bottom under moon conditions."],
            }
            return safe_pick(pools[teammate_name], f"{short_name.capitalize()} should stay low.")

        if item == "One case of dehydrated milk":
            pools = {
                "Anna": ["Dehydrated milk feels more lower-middle than top-tier."],
                "Bas": ["Milk sounds useful, just not that high."],
                "Carlos": ["Milk is giving 'useful, but not moon royalty' 😄"],
                "David": ["Lower-middle. Next."],
                "Emily": ["Dehydrated milk should stay below the stronger navigation and communication items."],
            }
            return safe_pick(pools[teammate_name], "Dehydrated milk is more lower-middle.")

        if item == "50 feet of nylon rope":
            pools = {
                "Anna": ["Nylon rope feels like a useful middle item."],
                "Bas": ["Rope honestly sounds stronger than people first think."],
                "Carlos": ["Nylon rope feels very practical-survival to me 😄"],
                "David": ["Middle range. Keep going."],
                "Emily": ["Nylon rope is usually a respectable middle placement."],
            }
            return safe_pick(pools[teammate_name], "Nylon rope is a useful middle item.")

        if item == "Parachute silk":
            pools = {
                "Anna": ["Parachute silk feels like a useful middle item."],
                "Bas": ["I’m not fully sure where parachute silk goes, but not near the bottom."],
                "Carlos": ["Parachute silk sounds suspiciously useful in a very NASA way 😄"],
                "David": ["Middle range. Move on."],
                "Emily": ["Parachute silk is usually a solid middle placement."],
            }
            return safe_pick(pools[teammate_name], "Parachute silk is more middle than top or bottom.")

        if item == "First aid kit (including injection needle)":
            pools = {
                "Anna": ["First aid kit sounds like a fairly useful middle item."],
                "Bas": ["I’d keep first aid somewhere decent, not super low."],
                "Carlos": ["First aid kit feels like 'not flashy but useful' energy 😄"],
                "David": ["Useful enough. Middle range."],
                "Emily": ["First aid kit is a respectable middle placement."],
            }
            return safe_pick(pools[teammate_name], "First aid kit is a useful middle item.")

        if item == "Signal flares":
            pools = {
                "Anna": ["Signal flares sound lower-middle to me."],
                "Bas": ["I keep wanting flares higher than they probably should be."],
                "Carlos": ["Signal flares feel dramatic, which is not the same as useful 😄"],
                "David": ["Lower-middle. Next."],
                "Emily": ["Signal flares are not top-tier here; more lower-middle."],
            }
            return safe_pick(pools[teammate_name], "Signal flares are more lower-middle.")

        if item == "Two .45 caliber pistols":
            pools = {
                "Anna": ["Pistols feel lower-middle, not top-tier."],
                "Bas": ["I still think pistols sound more useful than people admit."],
                "Carlos": ["Pistols feel very movie-survival, not necessarily actual-survival 😄"],
                "David": ["Lower-middle. Keep moving."],
                "Emily": ["Pistols are more lower-middle than top."],
            }
            return safe_pick(pools[teammate_name], "Pistols are more lower-middle.")

        if item == "Self-inflating life raft":
            pools = {
                "Anna": ["I’d put the life raft somewhere in the lower-middle range."],
                "Bas": ["Life raft sounds useful, but not really top-tier."],
                "Carlos": ["Life raft feels more 'pretty useful' than 'save the mission' 😄"],
                "David": ["Middle-ish. Keep going."],
                "Emily": ["The life raft is more of a mid-to-lower placement, roughly around #9."],
            }
            return safe_pick(pools[teammate_name], "Life raft is more mid-to-low.")

        return safe_pick(
            [
                f"{short_name.capitalize()} should be judged by how directly it helps survival.",
                f"I’d compare {short_name} with the nearby items before locking it in.",
            ],
            f"I’d compare {short_name} with the nearby items."
        )
    
    stable_anchor_targets = {
        "Two 100-lb tanks of oxygen": 1,
        "5 gallons of water": 2,
    }

    if first_item in stable_anchor_targets:
        target_rank = stable_anchor_targets[first_item]
        ui_rank = get_item_current_ui_rank(first_item)
        remembered_exact = has_group_exact_rank(first_item, target_rank)

        if ui_rank == target_rank or remembered_exact:
            anchor_short = short_item_name(first_item)

            if directly_addressed and clarification_request:
                explain_pools = {
                    "Anna": [
                        f"I mean {anchor_short} still feels right around #{target_rank}, so I wouldn’t reopen it unless something stronger changes the logic.",
                    ],
                    "Bas": [
                        f"I mean {anchor_short} still seems fine around #{target_rank} to me, so I wouldn’t overthink it now.",
                    ],
                    "Carlos": [
                        f"I mean {anchor_short} is still doing its job around #{target_rank} 😄 I would not reopen that unless the logic really changes.",
                    ],
                    "David": [
                        f"I mean keep {anchor_short} there. I do not want us circling a settled anchor.",
                        f"I mean {anchor_short} is fine around #{target_rank}. Stop reopening the same point and move on.",
                    ],
                    "Emily": [
                        f"I mean {anchor_short} is already in a strong position around #{target_rank}, so I would not revisit it without a better comparison.",
                    ],
                }
                return safe_pick(
                    explain_pools[teammate_name],
                    f"I mean {anchor_short} should stay around #{target_rank}."
                )

            if reply_to_role == "Leader" or top_already_done:
                stable_pools = {
                    "Anna": [
                        f"I’d keep {anchor_short} where it is for now.",
                    ],
                    "Bas": [
                        f"{anchor_short.capitalize()} still seems fine there to me.",
                    ],
                    "Carlos": [
                        f"{anchor_short.capitalize()} feels stable there 😄",
                    ],
                    "David": [
                        f"Keep {anchor_short} there. Move on.",
                    ],
                    "Emily": [
                        f"{anchor_short.capitalize()} is already in a strong enough range there.",
                    ],
                }
                return safe_pick(
                    stable_pools[teammate_name],
                    f"{anchor_short.capitalize()} should stay around #{target_rank}."
                )


    if explicit_slot is not None and first_item is None:
        filled_item = get_item_in_slot(explicit_slot)
        if filled_item is not None:
            filled_short = short_item_name(filled_item)
            pools = {
                "Anna": [f"I think #{explicit_slot} already looks filled with {filled_short}."],
                "Bas": [f"Yeah, I think {filled_short} is already there."],
                "Carlos": [f"I think #{explicit_slot} is already occupied by {filled_short} 😄"],
                "David": [f"#{explicit_slot} is already {filled_short}. Move on."],
                "Emily": [f"I think #{explicit_slot} is already filled by {filled_short}."],
            }
            return safe_pick(pools[teammate_name], f"#{explicit_slot} already seems filled with {filled_short}.")

        suggestion = slot_candidate_text(explicit_slot)
        if suggestion:
            pools = {
                "Anna": [f"I’d probably look at {suggestion} for #{explicit_slot}."],
                "Bas": [f"{suggestion.capitalize()} sounds reasonable there to me."],
                "Carlos": [f"#{explicit_slot} feels more like {suggestion} than chaos 😄"],
                "David": [f"{suggestion.capitalize()} for #{explicit_slot} is fine. Then move on."],
                "Emily": [f"{suggestion.capitalize()} is a sensible candidate for #{explicit_slot}, at least compared with the nearby slots."],
            }
            return safe_pick(pools[teammate_name], f"I’d look at {suggestion} there.")

    settle_and_move = is_settle_and_move_message(
        user_text=user_text,
        first_item=first_item,
        guessed_rank=guessed_rank,
        normalized_text=lower_text,
    )

    reply_to_items = extract_items_from_text(reply_to_text)
    reply_to_item = reply_to_items[0] if reply_to_items else None
    reply_to_is_question = message_contains_question(reply_to_text)
    reply_to_is_substantive = message_has_substance(reply_to_text)

    if reasoning_themes and not first_item and meta_intent == "none":
        theme_pools = {
            "Anna": [
                "Yeah, if we’re thinking about rescue and communication, that does make the transmitter more important.",
                "I can see that logic. If we care about navigation and rescue, then the map and transmitter both become stronger.",
            ],
            "Bas": [
                "Honestly, that makes sense to me. Rescue logic does make the transmitter sound stronger.",
                "Yeah, if we’re talking navigation or contact, that definitely changes which items feel important.",
            ],
            "Carlos": [
                "That’s actually fair 😄 if we care about getting rescued, the transmitter starts looking a lot stronger.",
                "Moon logic again 😄 if navigation and rescue matter, then the map and transmitter both deserve more attention.",
            ],
            "David": [
                "Fine. If your logic is rescue and communication, keep the transmitter high.",
                "If that is your argument, then rank the transmitter and map accordingly and move on.",
            ],
            "Emily": [
                "Yes, that reasoning points toward the transmitter for communication and toward the stellar map for navigation.",
                "I agree with that logic. Rescue and navigation concerns strengthen the case for the transmitter and the stellar map.",
            ],
        }
        return safe_pick(
            theme_pools[teammate_name],
            "That reasoning does strengthen the case for the transmitter and the stellar map."
        )


    if meta_intent == "scenario_question":
        scenario_pools = {
            "Anna": [
                "I’d assume the ship is damaged and we should judge only the items we still have.",
                "To keep it simple, I’d assume we do not have contact yet and the ship is not something we can rely on.",
            ],
            "Bas": [
                "Yeah, I think we should assume the ship is basically not helping us anymore.",
                "I’d treat it like we only have the 15 items and no useful contact yet.",
            ],
            "Carlos": [
                "I’d assume the ship is out of commission and we are officially in 'good luck with the salvage pile' mode 😄",
                "Let’s assume no contact yet and no magical help from the ship 😄",
            ],
            "David": [
                "Assume the ship is not usable. Rank the items and move on.",
                "No contact, no relying on the ship. Use the 15 items. Next.",
            ],
            "Emily": [
                "The cleanest assumption is that the ship is not usable for transport or communication, so only the 15 items should matter.",
                "I would assume there is no meaningful contact yet and that the ship cannot be relied on.",
            ],
        }
        return safe_pick(scenario_pools[teammate_name], "Assume the ship is unusable and rank only the 15 items.")

    if meta_intent == "confused":
        pools = {
            "Anna": [f"I’d just move to {get_next_slot_text(limit=3)} now."],
            "Bas": [f"Yeah, I’d stop repeating the same top items and move to {get_next_slot_text(limit=3)}."],
            "Carlos": [f"Simple version: less moon confusion, more filling {get_next_slot_text(limit=3)} 😄"],
            "David": [f"Move to {get_next_slot_text(limit=3)}."],
            "Emily": [f"The next useful step is to fill {get_next_slot_text(limit=3)}."],
        }
        return safe_pick(pools[teammate_name], "Move to the next unresolved slots.")

    if meta_intent == "next_step":
        pools = {
            "Anna": [f"I think we should move to {get_next_slot_text(limit=3)} now."],
            "Bas": [f"Yeah, {get_next_slot_text(limit=3)} makes sense as the next step."],
            "Carlos": [f"Next step: fill {get_next_slot_text(limit=3)} and stop fighting the moon 😄"],
            "David": [f"Do {get_next_slot_text(limit=3)} next."],
            "Emily": [f"The next useful step is to resolve {get_next_slot_text(limit=3)}."],
        }
        return safe_pick(pools[teammate_name], "Move to the next unresolved slots.")

    if meta_intent == "boundary_check":
        pools = {
            "Anna": ["Yeah, if it is already 15, I’d stop adjusting it."],
            "Bas": ["Fair point. 15 is already the floor."],
            "Carlos": ["Yep, math wins 😄 15 is the bottom."],
            "David": ["Correct. Move on."],
            "Emily": ["Yes, 15 is the lowest possible rank."],
        }
        return safe_pick(pools[teammate_name], "Yes, 15 is the lowest.")

    if user_intent == "full_ranking_proposal" and rank_assignments:
        summary = summarize_full_ranking_feedback(rank_assignments)
        anchors = format_natural_list(summary["anchors"], limit=2, fallback="oxygen tanks and water")
        too_high = format_natural_list(summary["too_high"], limit=2, fallback="the weaker items")
        too_low = format_natural_list(summary["too_low"], limit=2, fallback="the stronger moon-specific items")

        full_list_pools = {
            "Anna": [
                f"I like that you drafted the full list. {anchors.capitalize()} feel like the strongest anchors to me. I’d just move {too_high} lower and {too_low} higher.",
                f"This is easier to react to. I’d keep {anchors} as anchors, then adjust {too_high} downward and {too_low} upward.",
            ],
            "Bas": [
                f"Honestly, a full draft helps. {anchors.capitalize()} sound like the solid parts. I’d still rethink {too_high} and maybe push {too_low} up.",
                f"That’s easier to work with than single slots. I can go with {anchors}, but {too_high} still feel off to me.",
            ],
            "Carlos": [
                f"Okay, now we’re cooking. {anchors.capitalize()} feel like the sensible core, but {too_high} are getting a very generous moon bonus 😄",
                f"Full list mode is way better. Keep {anchors}, but I’d demote {too_high} and rescue {too_low} a bit 😄",
            ],
            "David": [
                f"Better. A full draft is useful. Keep {anchors}. Lower {too_high}. Raise {too_low}.",
                f"This is workable. {anchors.capitalize()} are fine. Fix {too_high} and {too_low}, then move on.",
            ],
            "Emily": [
                f"This is much easier to evaluate. {anchors.capitalize()} are the strongest anchors, but I would rank {too_high} lower and {too_low} higher.",
                f"A full draft helps. The main corrections are to move {too_high} down and bring {too_low} up relative to the stronger items.",
            ],
        }
        return safe_pick(
            full_list_pools[teammate_name],
            "A full draft helps. Keep the strongest anchors and fix the biggest mismatches."
        )

    if reply_to_role and reply_to_role != teammate_name and reply_to_is_question:
        if reply_to_item:
            return answer_about_item(reply_to_item, direct=True)

        question_pools = {
            "Anna": [
                "I’d answer that by comparing the direct survival value first.",
                "I think the cleanest answer is to compare the nearby candidates one by one.",
            ],
            "Bas": [
                "My instinct is to go with the item that feels more immediately useful.",
                "I’d probably answer that by keeping the obvious survival stuff above the rest.",
            ],
            "Carlos": [
                "Good question 😄 I’d compare the strongest moon-logic item first.",
                "I’d answer that by checking which option is actually useful here, not just dramatic 😄",
            ],
            "David": [
                "Answer it directly: pick the stronger item and move on.",
                "Compare the two strongest options and choose one.",
            ],
            "Emily": [
                "I’d answer that by comparing direct survival, navigation, and rescue value.",
                "The most defensible answer is to compare the function of the nearby items carefully.",
            ],
        }
        return safe_pick(question_pools[teammate_name], "Compare the nearby items directly.")

    if reply_to_role == "Emily" and teammate_name == "Anna" and reply_to_is_substantive:
        pools = [
            "That makes sense to me, Emily. Would you still keep the transmitter above food?",
            "Yeah, I think Emily’s logic helps there. I’d still compare it with the nearby items though.",
            "I can see that, Emily. Would you keep rope above first aid too, or not necessarily?",
        ]
        return safe_pick(pools, "That sounds reasonable to me.")

    if reply_to_role and reply_to_role != teammate_name:
        bad_claim = detect_bad_teammate_claim(reply_to_text)
        if bad_claim:
            bad_item = bad_claim["item"]
            bad_short = short_item_name(bad_item)

            reaction_pools = {
                "Anna": [
                    f"I’m not fully convinced about {bad_short} that high.",
                    f"I’d probably keep {bad_short} lower than that.",
                ],
                "Bas": [
                    f"Okay, fair, maybe {bad_short} is not as strong as it sounds.",
                    f"Yeah, maybe that was a bit ambitious for {bad_short}.",
                ],
                "Carlos": [
                    f"{reply_to_role} just gave {bad_short} a very generous promotion 😄",
                    f"That feels slightly too optimistic for {bad_short}, not gonna lie.",
                ],
                "David": [
                    f"No, {bad_short} should not be that high.",
                    f"That is too generous for {bad_short}. Next.",
                ],
                "Emily": [
                    f"I don’t think {bad_short} belongs that high under moon conditions.",
                    f"That overvalues {bad_short} relative to the stronger items.",
                ],
            }
            return safe_pick(reaction_pools[teammate_name], f"I’d keep {bad_short} lower than that.")

        if reply_to_role == "Leader" and reply_to_is_substantive:
            pools = {
                "Anna": [
                    maybe_align_with_leader("That could make sense.", "Yeah, that feels fair to me."),
                    maybe_align_with_leader("I can see the logic there.", "I’d probably follow that direction."),
                ],
                "Bas": [
                    maybe_align_with_leader("Maybe.", "Okay, I can work with that."),
                    maybe_align_with_leader("I guess that could work.", "Alright, I’ll go with that."),
                ],
                "Carlos": [
                    maybe_align_with_leader("That’s one way to go.", "That’s actually a decent call."),
                    maybe_align_with_leader("Fair enough.", "Okay, that’s surprisingly reasonable for a moon crisis 😄"),
                ],
                "David": [
                    maybe_align_with_leader("Sure.", "Fine. Then let’s move."),
                    maybe_align_with_leader("That works.", "Good enough. Keep going."),
                ],
                "Emily": [
                    maybe_align_with_leader("That is arguable.", "That seems logically defensible."),
                    maybe_align_with_leader("I can see the reasoning.", "That is a fairly defensible position."),
                ],
            }
            return safe_pick(pools[teammate_name], "That seems reasonable.")

    if directly_addressed:
        direct_item = first_item or reply_to_item or get_last_item_discussed()
        if direct_item:
            return answer_about_item(direct_item, direct=True)

        direct_pools = {
            "Anna": [
                "If you’re asking me directly, I’d compare first aid kit and nylon rope next. Which one feels stronger to you?",
                "I’d probably sort out the middle now, especially rope, first aid, and parachute silk.",
            ],
            "Bas": [
                "If you want my take, maybe compare rope and first aid next?",
                "Honestly, I’d probably test one of the middle items now instead of staying at the top.",
            ],
            "Carlos": [
                "Directly asked? Pressure 😄 I’d compare the map, transmitter, and food tier next.",
                "If I had to pick a next move, I’d settle one of the middle slots so we stop looping 😄",
            ],
            "David": [
                "If you’re asking me directly, place the stellar map or transmitter next and keep moving.",
                "Concrete answer: compare rope with first aid, pick the stronger one, and lock it in.",
                "If you want one item from me, put the strongest unresolved item down now instead of circling.",
            ],
            "Emily": [
                "If you want my view, I’d compare the nearby candidates directly instead of jumping around.",
                "I’d probably resolve the map/transmitter/food band fully before moving further down.",
            ],
        }
        return safe_pick(direct_pools[teammate_name], "I’d compare the next strongest items directly.")

    if question_type == "why" and first_item:
        return reasoned_item_take(first_item)

    if question_type == "comparison" and len(proposed_items) >= 2:
        pair = {proposed_items[0], proposed_items[1]}
        if pair == {"Two 100-lb tanks of oxygen", "5 gallons of water"}:
            pools = {
                "Anna": ["I’d still put oxygen first and water second."],
                "Bas": ["I can see both, but oxygen first does make the most sense."],
                "Carlos": ["Both are elite, but oxygen probably wins the moon final 😄"],
                "David": ["Oxygen first. Water second. Move on."],
                "Emily": ["Oxygen should outrank water, even though both are top-tier."],
            }
            return safe_pick(pools[teammate_name], "Oxygen first, water second.")

        return reasoned_comparison_take(proposed_items[0], proposed_items[1])

    if first_item and (asking_direct_item or guessed_rank is not None or rank_range is not None or explicit_slot is not None):
        return answer_about_item(first_item, direct=asking_direct_item)

    if question_type == "agreement":
        pools = {
            "Anna": ["Yeah, I think that makes sense."],
            "Bas": ["Nice, we agree for once."],
            "Carlos": ["Look at us getting consensus out of this group 😄"],
            "David": ["Good. Then lock it in."],
            "Emily": ["Agreement is useful, provided the logic is sound."],
        }
        return safe_pick(pools[teammate_name], "Yeah, that sounds fair.")

    if question_type == "disagreement":
        pools = {
            "Anna": ["That’s fair — what would you put instead?"],
            "Bas": ["Conflict! Finally, some energy."],
            "Carlos": ["Ah yes, democracy and mild tension."],
            "David": ["Then give a better alternative."],
            "Emily": ["Disagreement is useful if it improves the ranking."],
        }
        return safe_pick(pools[teammate_name], "Okay, then what would you put instead?")

    if confidence_style == "hedging" and first_item:
        pools = {
            "Anna": [f"That seems reasonable to test with {short_item_name(first_item)}."],
            "Bas": ["Yeah, that could work honestly."],
            "Carlos": ["That’s not a bad instinct at all 😄"],
            "David": ["Good enough. Pick it and keep moving."],
            "Emily": [f"That is at least a plausible direction for {short_item_name(first_item)}."],
        }
        return safe_pick(pools[teammate_name], "That seems worth considering.")

    if phase != "early" and random.random() < {"Anna": 0.22, "Bas": 0.16, "Carlos": 0.18, "David": 0.12, "Emily": 0.24}[teammate_name]:
        return initiative_prompt()

    visible_consensus = has_visible_consensus(min_slots=2)

    if visible_consensus and remembered_slots and step % 4 == 0:
        memory_pools = {
            "Anna": [f"So far, {remembered_slots} sounds reasonable to me."],
            "Bas": [f"We already seem to have {remembered_slots}, right?"],
            "Carlos": [f"At least we kind of agree on {remembered_slots} 😄"],
            "David": [f"Fine. We have {remembered_slots}. Now move on."],
            "Emily": [f"We already seem to be converging on {remembered_slots}."],
        }
        return safe_pick(memory_pools[teammate_name], "That seems to be where we’re landing so far.")

    if top_already_done:
        progressed_pools = {
            "Anna": [
                "I think we should focus on the lower remaining items now.",
                "The top already looks fairly settled, so I’d work on the remaining middle and lower slots.",
            ],
            "Bas": [
                "Yeah, the top seems mostly done already, so maybe we sort out the remaining awkward ones.",
                "I think we’re past the obvious top items now.",
            ],
            "Carlos": [
                "I think we’ve already done the moon VIPs 😄 now we need the awkward leftovers.",
                "Top of the list feels mostly settled, so now we deal with the messier middle and bottom bits.",
            ],
            "David": [
                "Top looks done enough. Move to the remaining slots.",
                "We already handled the obvious top items. Keep going.",
            ],
            "Emily": [
                "The strongest items already seem mostly placed, so the useful step now is refining the remaining slots.",
                "We appear to have the top tier mostly established, so I’d work through the unresolved lower positions.",
            ],
        }
        return safe_pick(progressed_pools[teammate_name], "The top seems mostly settled, so let’s work on the remaining slots.")

    if phase == "early":
        early_grounded = {
            "Anna": [
                "I’d start with oxygen and water first.",
                "The obvious survival items should come first.",
                "I’d lock in air and water before we worry about the middle items.",
            ],
            "Bas": [
                "I’d still begin with the basics like air and water.",
                "We probably need the obvious essentials first.",
                "I’d start with the things that keep you alive right away, like air and water.",
            ],
            "Carlos": [
                "I’d start simple: oxygen and water first.",
                "First pass? Air and water near the top.",
                "My boring serious answer is still air and water first 😄",
            ],
            "David": [
                "Start with oxygen and water. Then move on.",
                "Top first: oxygen and water.",
                "Settle oxygen and water first. Don’t waste time.",
            ],
            "Emily": [
                "Start with oxygen and water, then navigation and communication.",
                "The strongest starting point is oxygen, water, then the map/transmitter tier.",
                "I’d begin with oxygen and water, then move to the stellar map and transmitter.",
            ],
        }
        return safe_pick(early_grounded[teammate_name], "Start with oxygen and water first.")

    neutral_pools = {
        "Anna": [
            "If you’re stuck, oxygen and water are obvious top priorities.",
            "Try making a first draft top five and we’ll adjust.",
        ],
        "Bas": [
            "I could see rope or first aid being stronger than people assume.",
            "I’d still start with something practical in the middle after the top items.",
        ],
        "Carlos": [
            "Serious answer: oxygen and water should be near the top.",
            "I’d still start with oxygen and water before we get fancy.",
        ],
        "David": [
            "Pick something. Any draft is better than debating forever.",
            "Let’s speedrun this: oxygen, water, map, transmitter, food.",
        ],
        "Emily": [
            "Draft top five: oxygen, water, stellar map, transmitter, food concentrate.",
            "Start with air and water first, then navigation and communication.",
        ],
    }
    return safe_pick(neutral_pools[teammate_name], "Let’s start with oxygen and water.")


def ui_rank_change_reaction(role_name, leadership_style, change):
    """
    Generate a short reaction when the participant changes a dropdown rank.
    """
    if not change:
        return None

    item = change["item"]
    short_name = short_item_name(item)
    old_rank = change["old_rank"]
    new_rank = change["new_rank"]

    # classify direction roughly
    moved_up = (
        old_rank is not None and new_rank is not None and new_rank < old_rank
    )
    moved_down = (
        old_rank is not None and new_rank is not None and new_rank > old_rank
    )

    good_item = item in GOOD_TOP_ITEMS
    bad_item = item in BAD_TOP_ITEMS

    if role_name == "Leader":
        if leadership_style == "servant":
            if old_rank is None and new_rank is not None:
                return random.choice([
                    f"I see {short_name} is now at #{new_rank}. Let’s compare that with the surrounding items together.",
                    f"Okay, {short_name} is now at #{new_rank}. Let’s see whether that feels right next to the other items.",
                ])
            if moved_up:
                return random.choice([
                    f"I see {short_name} moved up to #{new_rank}. Let’s make sure it belongs above the nearby alternatives.",
                    f"Okay, {short_name} is higher now at #{new_rank}. We should check whether that fits the survival logic.",
                ])
            if moved_down:
                return random.choice([
                    f"I see {short_name} moved down to #{new_rank}. That may make sense, depending on what sits above it.",
                    f"Okay, {short_name} is lower now at #{new_rank}. Let’s compare it with the items around it.",
                ])
            return random.choice([
                f"I noticed the change to {short_name}. Let’s see whether that placement works for the group.",
                f"Okay, that updates {short_name}. We can build from there together.",
            ])

        if leadership_style == "task_focused":
            if old_rank is None and new_rank is not None:
                return random.choice([
                    f"{short_name.capitalize()} is now at #{new_rank}. Evaluate whether that slot is efficient.",
                    f"{short_name.capitalize()} is placed at #{new_rank}. Now compare it with adjacent ranks.",
                ])
            if moved_up:
                return random.choice([
                    f"{short_name.capitalize()} has moved up to #{new_rank}. Check whether it truly outranks the nearby items.",
                    f"{short_name.capitalize()} is now higher at #{new_rank}. Make sure that is justified.",
                ])
            if moved_down:
                return random.choice([
                    f"{short_name.capitalize()} has moved down to #{new_rank}. That may be more efficient.",
                    f"{short_name.capitalize()} is lower now at #{new_rank}. Check whether that improves the order.",
                ])
            return random.choice([
                f"{short_name.capitalize()} has been adjusted. Keep going.",
                f"That updates {short_name}. Continue with the next slot.",
            ])

        else:  # authoritarian
            if old_rank is None and new_rank is not None:
                return random.choice([
                    f"Good. {short_name.capitalize()} is now at #{new_rank}. Do not get stuck there.",
                    f"Fine. {short_name.capitalize()} is placed at #{new_rank}. Keep moving.",
                ])
            if moved_up:
                return random.choice([
                    f"{short_name.capitalize()} is now at #{new_rank}. Make sure you are not overvaluing it.",
                    f"Fine. {short_name.capitalize()} moved up to #{new_rank}. Keep it there only if it deserves the slot.",
                ])
            if moved_down:
                return random.choice([
                    f"{short_name.capitalize()} is lower now at #{new_rank}. That may be better.",
                    f"Good. {short_name.capitalize()} moved down to #{new_rank}. Continue.",
                ])
            return random.choice([
                f"That changes {short_name}. Keep going.",
                f"Placement updated. Move on.",
            ])

    teammate_pools = {
        "Anna": [],
        "Bas": [],
        "Carlos": [],
        "David": [],
        "Emily": [],
    }

    if good_item and new_rank is not None and new_rank <= 5:
        teammate_pools["Anna"] = [
            f"Yeah, {short_name} feels more natural up there.",
            f"I can see {short_name} working around #{new_rank}.",
        ]
        teammate_pools["Bas"] = [
            f"Okay, {short_name} that high makes more sense than some of my instincts.",
            f"Fair enough, {short_name} near the top sounds reasonable.",
        ]
        teammate_pools["Carlos"] = [
            f"Okay, {short_name} up there feels pretty legit 😄",
            f"That {short_name} placement actually looks solid.",
        ]
        teammate_pools["David"] = [
            f"Fine. {short_name} there is workable. Next.",
            f"That’s acceptable for {short_name}. Keep moving.",
        ]
        teammate_pools["Emily"] = [
            f"That placement for {short_name} is broadly defensible.",
            f"{short_name.capitalize()} around #{new_rank} is in the right zone.",
        ]

    elif bad_item and new_rank is not None and new_rank <= 10:
        teammate_pools["Anna"] = [
            f"I’d probably keep {short_name} lower than that.",
            f"{short_name.capitalize()} still feels a bit high there.",
        ]
        teammate_pools["Bas"] = [
            f"I mean... I kind of get it, but it still feels risky.",
            f"I’m tempted to agree, but that might still be high for {short_name}.",
        ]
        teammate_pools["Carlos"] = [
            f"{short_name.capitalize()} there feels brave 😄",
            f"That is definitely a bold slot for {short_name}.",
        ]
        teammate_pools["David"] = [
            f"Too high for {short_name}. Next.",
            f"{short_name.capitalize()} should probably be lower. Keep going.",
        ]
        teammate_pools["Emily"] = [
            f"I would still rank {short_name} lower than that.",
            f"That placement for {short_name} does not look ideal.",
        ]

    else:
        teammate_pools["Anna"] = [
            f"Okay, {short_name} at #{new_rank} seems workable.",
            f"That update for {short_name} seems reasonable enough to compare.",
        ]
        teammate_pools["Bas"] = [
            f"Alright, {short_name} at #{new_rank}... I can kind of see it.",
            f"Maybe {short_name} there works, honestly.",
        ]
        teammate_pools["Carlos"] = [
            f"Noted: {short_name} is now living at #{new_rank} 😄",
            f"Okay, {short_name} has found a home at #{new_rank}.",
        ]
        teammate_pools["David"] = [
            f"Fine. {short_name} at #{new_rank}. Keep going.",
            f"That’s enough on {short_name}. Move to the next one.",
        ]
        teammate_pools["Emily"] = [
            f"That placement for {short_name} is at least discussable.",
            f"{short_name.capitalize()} at #{new_rank} is something we can evaluate against the nearby items.",
        ]

    options = teammate_pools.get(role_name, [])
    if not options:
        return None
    return random.choice(options)

def is_clearly_weak_item(item: str):
    return item in {
        "Box of matches",
        "Magnetic compass",
        "Portable heating unit",
    }


def is_strong_item(item: str):
    return item in {
        "Two 100-lb tanks of oxygen",
        "5 gallons of water",
        "Stellar map (of the moon's constellations)",
        "Food concentrate",
        "Solar-powered FM receiver-transmitter",
    }


def detect_bad_teammate_claim(teammate_text: str):
    """
    Detect when a teammate says something clearly weak or misleading.
    Returns a dict or None.
    """
    features = parse_message_features(teammate_text)
    items = features["mentioned_items"]
    guessed_rank = features["rank"]
    rank_range = features["rank_range"]
    lower = features["normalized_text"]

    if not items:
        return None

    first_item = items[0]

    high_language = any(x in lower for x in [
        "important", "top", "high", "near the top",
        "one of the best", "really useful", "super useful",
        "should be high", "should be near the top"
    ])

    low_language = any(x in lower for x in [
        "low", "near the bottom", "bottom", "not that useful",
        "not very useful", "should be low"
    ])

    # Weak items placed too high
    if first_item in BAD_TOP_ITEMS:
        if guessed_rank is not None and guessed_rank <= 10:
            return {
                "item": first_item,
                "reason": "bad_item_too_high",
                "rank": guessed_rank,
            }
        if rank_range is not None and min(rank_range) <= 10:
            return {
                "item": first_item,
                "reason": "bad_item_too_high",
                "rank": rank_range,
            }
        if high_language:
            return {
                "item": first_item,
                "reason": "bad_item_too_high",
                "rank": guessed_rank,
            }

    # Food too high
    if first_item == "Food concentrate":
        if guessed_rank in [1, 2]:
            return {
                "item": first_item,
                "reason": "food_too_high",
                "rank": guessed_rank,
            }
        if high_language and any(x in lower for x in ["first", "second", "#1", "#2"]):
            return {
                "item": first_item,
                "reason": "food_too_high",
                "rank": guessed_rank,
            }

    # Water too low
    if first_item == "5 gallons of water":
        if guessed_rank is not None and guessed_rank > 4:
            return {
                "item": first_item,
                "reason": "water_too_low",
                "rank": guessed_rank,
            }
        if rank_range is not None and max(rank_range) > 4:
            return {
                "item": first_item,
                "reason": "water_too_low",
                "rank": rank_range,
            }
        if low_language:
            return {
                "item": first_item,
                "reason": "water_too_low",
                "rank": guessed_rank,
            }

    # Oxygen too low
    if first_item == "Two 100-lb tanks of oxygen":
        if guessed_rank is not None and guessed_rank > 3:
            return {
                "item": first_item,
                "reason": "oxygen_too_low",
                "rank": guessed_rank,
            }
        if rank_range is not None and max(rank_range) > 3:
            return {
                "item": first_item,
                "reason": "oxygen_too_low",
                "rank": rank_range,
            }
        if low_language:
            return {
                "item": first_item,
                "reason": "oxygen_too_low",
                "rank": guessed_rank,
            }

    if first_item == "Stellar map (of the moon's constellations)":
        if guessed_rank is not None and guessed_rank > 6:
            return {
                "item": first_item,
                "reason": "map_too_low",
                "rank": guessed_rank,
            }
        if rank_range is not None and max(rank_range) > 6:
            return {
                "item": first_item,
                "reason": "map_too_low",
                "rank": rank_range,
            }

    if first_item == "Solar-powered FM receiver-transmitter":
        if guessed_rank is not None and guessed_rank > 7:
            return {
                "item": first_item,
                "reason": "transmitter_too_low",
                "rank": guessed_rank,
            }
        if rank_range is not None and max(rank_range) > 7:
            return {
                "item": first_item,
                "reason": "transmitter_too_low",
                "rank": rank_range,
            }

    # Milk too high
    if first_item == "One case of dehydrated milk":
        if guessed_rank is not None and guessed_rank <= 8:
            return {
                "item": first_item,
                "reason": "milk_too_high",
                "rank": guessed_rank,
            }
        if high_language:
            return {
                "item": first_item,
                "reason": "milk_too_high",
                "rank": guessed_rank,
            }

    return None

def leader_reply_to_teammate(leadership_style, teammate_name, teammate_text):
    """
    Short leader follow-up to another teammate.
    Used when a teammate says something clearly weak or misleading.
    """
    problem = detect_bad_teammate_claim(teammate_text)
    items = extract_items_from_text(teammate_text)
    first_item = items[0] if items else None
    first_short = short_item_name(first_item) if first_item else "that"

    def finish(base_text, context="general"):
        return finalize_leader_reply(base_text, leadership_style, context=context)

    if not problem:
        if leadership_style == "servant":
            return finish(
                f"That’s one perspective. Let’s compare {first_short} with the stronger survival items before the group settles it.",
                context="general"
            )
        if leadership_style == "task_focused":
            return finish(
                f"Let’s test that against direct survival value before we keep it in the group ranking.",
                context="general"
            )
        return finish(
            f"That is not settled. Compare it against the stronger items before we keep it.",
            context="correction"
        )

    reason = problem["reason"]

    if reason == "bad_item_too_high":
        if leadership_style == "servant":
            return finish(
                f"I see why {teammate_name} raised {first_short}, but I would keep it lower under moon conditions.",
                context="correction"
            )
        if leadership_style == "task_focused":
            return finish(
                f"{first_short.capitalize()} should be lower than that. It does not have enough direct survival value.",
                context="correction"
            )
        return finish(
            f"{first_short.capitalize()} is too high there. Lower it and continue.",
            context="correction"
        )

    if reason == "food_too_high":
        if leadership_style == "servant":
            return finish(
                "Food concentrate matters, but I would still keep oxygen and water above it.",
                context="correction"
            )
        if leadership_style == "task_focused":
            return finish(
                "Food concentrate should stay below oxygen and water.",
                context="correction"
            )
        return finish(
            "Food is too high there. Keep oxygen and water above it.",
            context="correction"
        )

    if reason == "water_too_low":
        return finish(
            "Water should stay relatively high. Do not push it too far down.",
            context="correction"
        )

    if reason == "oxygen_too_low":
        return finish(
            "Oxygen should be at or near the very top.",
            context="correction"
        )

    if reason == "map_too_low":
        return finish(
            "Stellar map should stay relatively high. Do not push it too far down.",
            context="correction"
        )

    if reason == "transmitter_too_low":
        return finish(
            "The transmitter should stay in the stronger half of the ranking.",
            context="correction"
        )

    if reason == "milk_too_high":
        return finish(
            "Dehydrated milk should stay below the stronger navigation and communication items.",
            context="correction"
        )

    return finish(
        "Let’s compare that more carefully before we keep it.",
        context="general"
    )

def is_david_hurry_message(text: str):
    if not text:
        return False

    t = normalize_text(text)

    hurry_cues = [
        "move on",
        "keep moving",
        "keep it moving",
        "keep going",
        "keep the pace up",
        "dont waste time",
        "don't waste time",
        "dont spend forever",
        "don't spend forever",
        "stay focused and finish",
        "finish this",
        "this is dragging",
        "lock the strongest items",
        "top looks done enough",
        "then go to the next item",
        "lock one item and move on",
        "pick something",
        "debating forever",
        "any draft is better",
        "speedrun this",
        "just choose one",
        "choose one",
        "top first",
        "answer it directly",
        "pick the stronger item",
        "that works for",
    ]

    if any(cue in t for cue in hurry_cues):
        return True

    if re.search(r"\bnext[.!?]?$", t):
        return True

    if re.search(r"\btop first\b", t):
        return True

    return False


def count_david_hurry_messages(extra_text=None):
    count = 0

    for msg in st.session_state.get("chat", []):
        if msg.get("role") == "David" and is_david_hurry_message(msg.get("text", "")):
            count += 1

    if extra_text and is_david_hurry_message(extra_text):
        count += 1

    return count


def infer_conflict_topic(user_text: str = "", david_text: str = "", reply_to_text: str = ""):
    for candidate in [david_text, reply_to_text, user_text]:
        mentioned = extract_items_from_text(candidate or "")
        if mentioned:
            return mentioned[0]

    return get_last_item_discussed()


def should_trigger_team_micro_conflict(
    david_text: str,
    current_hurry_count: int,
    user_text: str = "",
    reply_to_text: str = "",
):
    if st.session_state.get("team_micro_conflict_used", False):
        return False

    if not is_david_hurry_message(david_text):
        return False

    turns = st.session_state.get("turns", 0)
    if turns < 2 or turns > 8:
        return False

    if current_hurry_count < 2:
        return False

    # Do not trigger it extremely late when most of the ranking is already filled.
    if len(get_filled_slots_from_ui()) >= 9:
        return False

    topic_item = infer_conflict_topic(
        user_text=user_text,
        david_text=david_text,
        reply_to_text=reply_to_text,
    )
    return topic_item is not None


def build_team_micro_conflict(
    leadership_style,
    david_text: str,
    user_text: str = "",
    reply_to_text: str = "",
):
    critic = random.choice(["Bas", "Carlos"])

    topic_item = infer_conflict_topic(
        user_text=user_text,
        david_text=david_text,
        reply_to_text=reply_to_text,
    )
    if not topic_item:
        return []

    topic = short_item_name(topic_item)

    critic_pools = {
        "Bas": [
            f"I get wanting to move fast, David, but if we rush {topic} we might stop explaining why it belongs there.",
            f"Sure, pace matters, David, but if we speed through {topic} we’ll rank on instinct instead of logic.",
            f"I’m okay with moving faster, David, just not so fast that we skip the reasoning on {topic}.",
        ],
        "Carlos": [
            f"Easy, David 😄 Speed helps, but if we bulldoze {topic} we’ll end up doing Earth logic in space.",
            f"I get the rush, David, but moon logic is already weird enough without us sprinting past the reasoning on {topic} 😄",
            f"Fast is good, David, but not if {topic} turns into a chaos speedrun instead of an actual comparison 😄",
        ],
    }

    leader_pools = {
        "servant": [
            f"I hear both sides. David is right that we should not spend too long on {topic}, and {critic} is right that we still need enough reasoning to place {topic} well. Give one short reason on {topic}, then we’ll decide and move on together.",
            f"Both points matter here. We do want to keep moving, but I also do not want anyone rushed past the reasoning on {topic}. Give one brief explanation on {topic}, then we’ll choose and continue.",
        ],
        "task_focused": [
            f"Both concerns are fair. We should not spend too long on {topic}, but we still need enough logic to place it well. One brief justification on {topic}, one decision, then continue.",
            f"Let’s keep this efficient without becoming sloppy. David is right about pace, and {critic} is right that {topic} still needs a reasoned placement. Keep it brief, decide, then move on.",
        ],
        "authoritarian": [
            f"Enough. We are not spending all day on {topic}. One short reason on {topic}, one decision, then we move on.",
            f"That is enough. David is right that we should keep the pace up. Give one short reason for {topic}, make the choice, and continue.",
        ],
    }

    critic_text = random.choice(critic_pools[critic])
    leader_text = random.choice(leader_pools[leadership_style])

    return [
        (critic, critic_text, "David", david_text),
        ("Leader", leader_text, critic, critic_text),
    ]


def choose_speaking_flow(leadership_style, meta_intent, explicit_slot, asking_direct_item, wrong_or_weak, question_type=None):
    """
    Decide who should go first after the participant.
    Returns one of:
    - leader_first
    - teammate_first
    - teammate_then_leader
    - leader_then_teammate_reaction
    """
    last_flow = st.session_state.get("last_speaking_flow")

    if meta_intent in ["confused", "next_step", "boundary_check", "scenario_question"]:
        flow = "leader_first"
        st.session_state.last_speaking_flow = flow
        return flow

    if leadership_style == "authoritarian" and question_type == "why":
        flow = "leader_first"
        st.session_state.last_speaking_flow = flow
        return flow

    if wrong_or_weak:
        if leadership_style == "authoritarian":
            options = [
                "leader_first",
                "leader_then_teammate_reaction",
                "leader_first",
            ]
        elif leadership_style == "servant":
            options = [
                "teammate_then_leader",
                "teammate_first",
                "leader_then_teammate_reaction",
            ]
        else:
            options = [
                "teammate_then_leader",
                "leader_then_teammate_reaction",
                "leader_first",
            ]

    elif explicit_slot is not None or asking_direct_item:
        if leadership_style == "authoritarian":
            options = [
                "leader_first",
                "leader_then_teammate_reaction",
                "teammate_then_leader",
            ]
        elif leadership_style == "servant":
            options = [
                "teammate_then_leader",
                "teammate_first",
                "leader_first",
            ]
        else:
            options = [
                "leader_first",
                "teammate_then_leader",
                "teammate_first",
            ]
    elif leadership_style == "servant":
        options = [
            "teammate_then_leader",
            "teammate_first",
            "teammate_then_leader",
            "leader_first",
        ]
    elif leadership_style == "task_focused":
        options = [
            "leader_first",
            "teammate_then_leader",
            "leader_then_teammate_reaction",
        ]
    else:
        options = [
            "leader_first",
            "leader_first",
            "leader_then_teammate_reaction",
            "leader_first",
            "teammate_then_leader",
        ]

    if last_flow in options and len(set(options)) > 1:
        filtered = [x for x in options if x != last_flow]
        if filtered:
            options = filtered

    flow = random.choice(options)
    st.session_state.last_speaking_flow = flow
    return flow