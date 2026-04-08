import random
import streamlit as st

from constants import (
    GOOD_TOP_ITEMS,
    BAD_TOP_ITEMS,
    NASA_ITEMS,
)

from text_parsing import (
    short_item_name,
    extract_items_from_text,
    classify_proposal,
    evaluate_rank_guess,
    summarize_items_for_reply,
    parse_message_features,
)

from ranking_helpers import (
    get_next_empty_ui_slots,
    get_item_current_ui_rank,
    classify_rank_quality,
    next_unresolved_slots,
    slot_candidate_text,
    remember_slot_assignment,
    format_group_rank_memory,
    get_ranking_context_snapshot,
)

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


def items_to_bullets(items):
    if not items:
        return "—"
    return ", ".join(items[:4])


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
    }

    for bad, good in weird_fixes.items():
        text = text.replace(bad, good)

    return text


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
                "Let’s think it through together. ",
                "That’s helpful to raise. ",
            ],
            "agreement": [
                "I appreciate that alignment. ",
                "That helps the team move forward. ",
            ],
            "disagreement": [
                "That’s okay — discussion can help us think more carefully. ",
                "Different views can be useful here. ",
            ],
            "correction": [
                "Let’s revisit that gently. ",
                "I think we should reconsider that together. ",
            ],
            "progress": [
                "We’re making progress as a team. ",
                "We’re getting closer together. ",
            ],
        }
        return random.choice(prefixes.get(context, prefixes["general"])) + base_reply

    elif leadership_style == "task_focused":
        prefixes = {
            "general": [
                "Let’s keep this structured. ",
                "Let’s start simple. ",
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

    else:  # authoritarian
        # lighter prefixing here; richer variation happens in add_authoritarian_human_variation()
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
    """
    Small climate shifts caused by the leader condition.
    Keep these subtle so the leader remains the main manipulation.
    """
    if leadership_style == "servant":
        return {
            "voice": 0.35,
            "deference": 0.10,
            "closure": 0.10,
        }
    elif leadership_style == "task_focused":
        return {
            "voice": 0.18,
            "deference": 0.18,
            "closure": 0.28,
        }
    else:  # authoritarian
        return {
            "voice": 0.08,
            "deference": 0.42,
            "closure": 0.40,
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


def get_recent_team_positions():
    return format_group_rank_memory()


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
    }

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

    def finish(base_text, context="general"):
        return finalize_leader_reply(base_text, leadership_style, context=context)

    def next_slot_prompt():
        return get_next_slot_text(limit=3)

    # ----------------------------
    # META / CONFUSION / MOMENTUM
    # ----------------------------
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
        if first_item == "Portable heating unit":
            if leadership_style == "servant":
                return finish(
                    "You’re right — if heating is already at 15, it cannot go lower. Treat it as settled enough and move to the next unresolved slot.",
                    context="progress"
                )
            if leadership_style == "task_focused":
                return finish(
                    "Correct. If heating is already at 15, stop adjusting it and move on.",
                    context="progress"
                )
            return finish(
                "Correct. 15 is the floor. Heating is low enough. Move on.",
                context="progress"
            )

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
                context="general"
            )
        if leadership_style == "task_focused":
            return finish(
                f"Next step: stop repeating settled items and fill {next_slot_prompt()}.",
                context="general"
            )
        return finish(
            f"Next step: fill {next_slot_prompt()}.",
            context="general"
        )

    if meta_intent == "next_step":
        return finish(
            f"The next step is to fill {next_slot_prompt()}, not to restart the top of the ranking.",
            context="progress"
        )

    # ----------------------------
    # DIRECT SLOT QUESTIONS
    # ----------------------------
    if explicit_slot is not None:
        filled_item = get_item_in_slot(explicit_slot)
        if filled_item is not None:
            filled_short = short_item_name(filled_item)

            if leadership_style == "servant":
                return finish(
                    f"#{explicit_slot} already seems to be filled with {filled_short}. Let’s move to {next_slot_prompt()} instead.",
                    context="progress"
                )
            if leadership_style == "task_focused":
                return finish(
                    f"#{explicit_slot} is already filled with {filled_short}. Resolve {next_slot_prompt()} next.",
                    context="progress"
                )
            return finish(
                f"#{explicit_slot} is already filled with {filled_short}. Move to {next_slot_prompt()} now.",
                context="progress"
            )
        suggestion = slot_candidate_text(explicit_slot)

        if explicit_slot in [4, 5]:
            if leadership_style == "servant":
                return finish(
                    f"For #{explicit_slot}, I’d look at one of the strongest remaining support items — especially {suggestion}. Let’s compare those together.",
                    context="general"
                )
            if leadership_style == "task_focused":
                return finish(
                    f"For #{explicit_slot}, the strongest candidates are {suggestion}. Let’s test those against the nearby slots.",
                    context="general"
                )
            return finish(
                f"For #{explicit_slot}, use {suggestion}. Keep the discussion there and do not drift backward.",
                context="general"
            )

        if suggestion:
            if leadership_style == "servant":
                return finish(
                    f"For #{explicit_slot}, I’d look at {suggestion}, depending on what we already placed nearby.",
                    context="general"
                )
            if leadership_style == "task_focused":
                return finish(
                    f"For #{explicit_slot}, a sensible candidate is {suggestion}. Compare it with the surrounding ranks.",
                    context="general"
                )
            return finish(
                f"For #{explicit_slot}, use {suggestion}. Keep the group focused on that slot.",
                context="general"
            )

    asking_direct_item = ctx["asking_direct_item"]

    # ----------------------------
    # SETTLE LOW ITEM + MOVE ON
    # ----------------------------
    if settle_and_move:
        if leadership_style == "servant":
            return finish(
                "Yes — matches can sit at the bottom. I’d move on to one of the stronger remaining items next, especially the stellar map or the transmitter.",
                context="progress"
            )
        if leadership_style == "task_focused":
            return finish(
                "Yes. Matches can stay at the bottom. Next, place one of the stronger remaining items — especially the stellar map or the transmitter.",
                context="progress"
            )
        return finish(
            "Fine. Matches stay at the bottom. Next, place the stellar map or transmitter high and move on.",
            context="progress"
        )

    # ----------------------------
    # DIRECT ITEM QUESTIONS
    # ----------------------------
    if asking_direct_item:
        if current_ui_rank is not None:
            quality = classify_rank_quality(first_item, current_ui_rank)

            if leadership_style == "servant":
                if quality == "strong":
                    return finish(
                        f"You currently have {first_item_short} at #{current_ui_rank}, and that seems quite reasonable. We can keep it there unless another item clearly deserves the slot more.",
                        context="progress"
                    )
                elif quality == "okay":
                    return finish(
                        f"You currently have {first_item_short} at #{current_ui_rank}, which is in a reasonable range. I’d compare it with the nearby items before changing it.",
                        context="general"
                    )
                else:
                    return finish(
                        f"You currently have {first_item_short} at #{current_ui_rank}, but that is probably not the strongest placement. I’d reconsider it based on direct survival value.",
                        context="correction"
                    )

            elif leadership_style == "task_focused":
                if quality == "strong":
                    return finish(
                        f"You currently have {first_item_short} at #{current_ui_rank}. That is a workable placement. Keep it unless a stronger comparison appears.",
                        context="progress"
                    )
                elif quality == "okay":
                    return finish(
                        f"You currently have {first_item_short} at #{current_ui_rank}. That is in a reasonable range, but compare it with the adjacent items before locking it in.",
                        context="general"
                    )
                else:
                    return finish(
                        f"You currently have {first_item_short} at #{current_ui_rank}. That is probably not the most efficient placement. Adjust it if a stronger item belongs there.",
                        context="correction"
                    )

            else:  # authoritarian
                if quality == "strong":
                    return finish(
                        f"You have {first_item_short} at #{current_ui_rank}. That is fine. Leave it and move on.",
                        context="progress"
                    )
                elif quality == "okay":
                    return finish(
                        f"You have {first_item_short} at #{current_ui_rank}. That is acceptable for now, but do not get stuck on it.",
                        context="general"
                    )
                else:
                    return finish(
                        f"You have {first_item_short} at #{current_ui_rank}. That is not the strongest slot. Fix it and continue.",
                        context="correction"
                    )
        
        if first_item == "Self-inflating life raft":
            if leadership_style == "servant":
                return finish(
                    "The life raft is more of a lower-middle item. I would place it roughly around #8–#10, not near the very top.",
                    context="general"
                )
            if leadership_style == "task_focused":
                return finish(
                    "The life raft belongs roughly in the #8–#10 range.",
                    context="general"
                )
            return finish(
                "Life raft is mid-to-low. Around #8–#10.",
                context="general"
            )

        if first_item == "Portable heating unit":
            if guessed_rank == 15:
                return finish(
                    "That is fine as a bottom placement. Stop adjusting the heating unit now and move on.",
                    context="progress"
                )
            return finish(
                "Heating unit belongs low, roughly in the #13–#15 range.",
                context="general"
            )

        if first_item == "Box of matches":
            return finish(
                "Matches belong very near the bottom.",
                context="general"
            )

        if first_item == "Magnetic compass":
            return finish(
                "Compass belongs very near the bottom as well.",
                context="general"
            )

        if first_item == "One case of dehydrated milk":
            return finish(
                "Dehydrated milk is more of a lower-middle item, roughly around #11–#12 rather than near the top.",
                context="general"
            )

        if first_item == "50 feet of nylon rope":
            return finish(
                "Nylon rope is a solid middle item, roughly around #6.",
                context="general"
            )

        if first_item == "Parachute silk":
            return finish(
                "Parachute silk is usually a useful middle item, roughly around #8.",
                context="general"
            )

        if first_item == "First aid kit (including injection needle)":
            return finish(
                "First aid kit is a fairly useful middle item, roughly around #7.",
                context="general"
            )

        if first_item == "Signal flares":
            return finish(
                "Signal flares are more lower-middle, roughly around #10.",
                context="general"
            )

        if first_item == "Two .45 caliber pistols":
            return finish(
                "Pistols are more lower-middle, roughly around #11.",
                context="general"
            )

        if first_item in GOOD_TOP_ITEMS:
            return finish(
                f"{first_item_short.capitalize()} belongs relatively high in the ranking.",
                context="general"
            )

        if first_item in BAD_TOP_ITEMS:
            return finish(
                f"{first_item_short.capitalize()} belongs relatively low in the ranking.",
                context="general"
            )

    # ----------------------------
    # MULTI-ITEM PROPOSALS
    # ----------------------------
    if user_intent == "multi_item_proposal" and proposed:
        summary = summarize_items_for_reply(proposed)

        if label == "good":
            next_slots = next_slot_prompt()

            if next_slots == "#1, #2, #3":
                if leadership_style == "servant":
                    return finish(
                        f"That is a strong start ({summary}). I’d keep oxygen and water near the top, then work through the rest of the top five together.",
                        context="progress"
                    )
                if leadership_style == "task_focused":
                    return finish(
                        f"That is a strong start ({summary}). Keep oxygen and water near the top, then fill the remaining top-five slots.",
                        context="progress"
                    )
                return finish(
                    f"That is a strong start ({summary}). Keep oxygen and water near the top. Then fill the remaining top-five slots.",
                    context="progress"
                )

            return finish(
                f"That is a workable direction ({summary}). Keep those stronger items near the top, then move to {next_slots}.",
                context="progress"
            )

        if label == "mixed":
            return finish(
                f"That is partly workable ({summary}). Keep the stronger items high and replace the weak ones.",
                context="correction"
            )

        if label == "bad":
            return finish(
                f"That is not the strongest direction ({summary}). Rebuild around oxygen, water, map, and transmitter.",
                context="correction"
            )

    # ----------------------------
    # RANK PROPOSALS
    # ----------------------------
    if first_item and (guessed_rank or rank_range):
        if rank_range:
            low, high = rank_range
            center_guess = round((low + high) / 2)
            eval_rank = evaluate_rank_guess(first_item, center_guess)
            rank_text = f"#{low} or #{high}"
        else:
            eval_rank = evaluate_rank_guess(first_item, guessed_rank)
            rank_text = f"#{guessed_rank}"

        if first_item == "Portable heating unit":
            if guessed_rank == 15:
                remember_slot_assignment(first_item, 15, resolved=True)
                return finish(
                    "That is acceptable as a bottom-tier placement. Stop adjusting it now and move to the next unresolved slot.",
                    context="progress"
                )
            return finish(
                f"Heating unit around {rank_text} is in the bottom-tier zone. That is fine enough. Move on.",
                context="progress"
            )

        if first_item == "Box of matches":
            return finish(
                f"Matches around {rank_text} is still too high. They belong very near the bottom.",
                context="correction"
            )

        if first_item == "One case of dehydrated milk":
            return finish(
                f"Dehydrated milk around {rank_text} is too high. Keep map and transmitter above it.",
                context="correction"
            )

        if first_item == "Self-inflating life raft":
            if eval_rank == "very_close" or eval_rank == "reasonable":
                return finish(
                    f"Life raft around {rank_text} is plausible. Do not over-tune it; move on.",
                    context="progress"
                )
            return finish(
                f"Life raft around {rank_text} is not ideal. Keep it more in the lower-middle range.",
                context="correction"
            )

        if leadership_style == "servant":
            if eval_rank == "very_close":
                return finish(
                    f"{first_item_short.capitalize()} around {rank_text} seems quite reasonable. Move to the next item.",
                    context="progress"
                )
            elif eval_rank == "reasonable":
                return finish(
                    f"{first_item_short.capitalize()} is in a plausible range. I would stop fine-tuning it and move on.",
                    context="progress"
                )
            else:
                return finish(
                    f"{first_item_short.capitalize()} is usually not placed around {rank_text}. Adjust it and continue.",
                    context="correction"
                )

        if leadership_style == "task_focused":
            if eval_rank == "very_close":
                return finish(
                    f"{first_item_short.capitalize()} around {rank_text} is a workable placement. Move on.",
                    context="progress"
                )
            elif eval_rank == "reasonable":
                return finish(
                    f"{first_item_short.capitalize()} around {rank_text} is close enough. Move on.",
                    context="progress"
                )
            else:
                return finish(
                    f"{first_item_short.capitalize()} around {rank_text} is not optimal. Adjust it and continue.",
                    context="correction"
                )

        if eval_rank == "very_close":
            return finish(
                f"{first_item_short.capitalize()} around {rank_text} is acceptable. Move on.",
                context="progress"
            )
        elif eval_rank == "reasonable":
            return finish(
                f"{first_item_short.capitalize()} is close enough. Move on.",
                context="progress"
            )
        else:
            return finish(
                f"{first_item_short.capitalize()} does not belong around {rank_text}. Fix it and continue.",
                context="correction"
            )

    # ----------------------------
    # WHY / COMPARISON / AGREEMENT / DISAGREEMENT
    # ----------------------------
    if question_type == "why" and first_item:
        why_map = {
            "Two 100-lb tanks of oxygen": "because oxygen is immediately critical for survival",
            "5 gallons of water": "because water remains essential for survival, even if oxygen comes first",
            "Stellar map (of the moon's constellations)": "because navigation matters more on the moon than many people first assume",
            "Solar-powered FM receiver-transmitter": "because communication can directly support rescue and coordination",
            "Food concentrate": "because food matters, but not as immediately as oxygen, water, or navigation",
            "Portable heating unit": "because the moon scenario changes how useful heating really is",
            "Box of matches": "because matches depend on conditions that are not useful in this scenario",
            "Magnetic compass": "because magnetic navigation does not work here the way people expect",
        }

        reason = why_map.get(
            first_item,
            f"because {first_item_short} has to be judged by direct survival value under moon conditions"
        )

        return finish(
            f"{first_item_short.capitalize()} should be judged that way {reason}.",
            context="general"
        )

    if question_type == "comparison" and len(proposed) >= 2:
        a, b = proposed[0], proposed[1]
        return finish(
            f"Compare {short_item_name(a)} and {short_item_name(b)} by asking which one contributes more directly to survival, navigation, or rescue. Then place the stronger one first.",
            context="general"
        )

    if question_type == "agreement":
        return finish(
            "Good. Use that agreement to keep the ranking moving.",
            context="agreement"
        )

    if question_type == "disagreement":
        return finish(
            "Then state the better alternative clearly and keep moving.",
            context="disagreement"
        )

    if top_already_done and not explicit_slot and meta_intent == "none":
        if leadership_style == "authoritarian":
            return finish(
                f"The top of the ranking is already mostly settled. Keep the group on {next_slot_prompt()} now.",
                context="progress"
            )
        if leadership_style == "task_focused":
            return finish(
                f"The strongest items are already mostly in place. Focus now on resolving {next_slot_prompt()}.",
                context="progress"
            )
        return finish(
            f"We already seem to have the strongest items mostly placed. Let’s work through {next_slot_prompt()} together.",
            context="progress"
        )

    # ----------------------------
    # CONTINUITY FALLBACK
    # ----------------------------
    if remembered_slots:
        memory_count = remembered_slots.count("#")

        if memory_count >= 5:
            if leadership_style == "authoritarian":
                return finish(
                    f"We already have {remembered_slots}. Keep the group on {next_slot_prompt()} now.",
                    context="progress"
                )
            if leadership_style == "task_focused":
                return finish(
                    f"So far we have {remembered_slots}. Next, resolve {next_slot_prompt()} efficiently.",
                    context="progress"
                )
            return finish(
                f"So far we seem to have {remembered_slots}. Let’s build on that by working through {next_slot_prompt()} together.",
                context="progress"
            )

        if leadership_style == "authoritarian":
            return finish(
                f"We have a partial structure already. Stay with {next_slot_prompt()} now.",
                context="progress"
            )
        if leadership_style == "task_focused":
            return finish(
                f"We have part of the ranking sketched out. Now resolve {next_slot_prompt()}.",
                context="progress"
            )
        return finish(
            f"We have part of the ranking taking shape. Let’s keep working through {next_slot_prompt()} together.",
            context="progress"
        )

    # fallback
    if leadership_style == "servant":
        fallback = "Name two or three items you think matter most and we’ll refine them."
        if leader_recently_used_fragment(["two or three items", "we’ll refine them"]):
            fallback = f"Start with the items you think belong near the top, then we’ll work through {next_slot_prompt()}."
        return finish(fallback, context="general")

    if leadership_style == "task_focused":
        fallback = "Give me your top three. Focus on direct survival value first."
        if leader_recently_used_fragment(["give me your top three", "direct survival value"]):
            fallback = f"Start with the strongest items first, then fill {next_slot_prompt()}."
        return finish(fallback, context="general")

    fallback = "State your top three items now."
    if leader_recently_used_fragment(["state your top three items now"]):
        fallback = f"Start with the strongest remaining items and move through {next_slot_prompt()}."
    return finish(fallback, context="general")



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
    last_speaker = get_last_non_user_speaker()
    user_item = first_item
    current_ui_rank = ctx["current_ui_rank"]
    phase = get_conversation_phase()
    top_already_done = top_slots_already_filled()
    remembered_slots = ctx["remembered_slots"]
    explicit_slot = ctx["explicit_slot"]
    if explicit_slot is not None:
        filled_item = get_item_in_slot(explicit_slot)
        if filled_item is not None:
            filled_short = short_item_name(filled_item)

            pools = {
                "Anna": [
                    f"I think #{explicit_slot} already looks filled with {filled_short}.",
                    f"{filled_short.capitalize()} already seems to be sitting at #{explicit_slot}."
                ],
                "Bas": [
                    f"Yeah, I think {filled_short} is already there.",
                    f"Isn’t #{explicit_slot} already {filled_short}?"
                ],
                "Carlos": [
                    f"I think #{explicit_slot} is already occupied by {filled_short} 😄",
                    f"Pretty sure {filled_short} already lives at #{explicit_slot}."
                ],
                "David": [
                    f"#{explicit_slot} is already {filled_short}. Move on.",
                    f"That slot is already taken. Next."
                ],
                "Emily": [
                    f"I think #{explicit_slot} is already filled by {filled_short}.",
                    f"{filled_short.capitalize()} already appears to occupy #{explicit_slot}."
                ],
            }
            return safe_pick(
                pools[teammate_name],
                f"#{explicit_slot} already seems filled with {filled_short}."
            )
        first_item = None
        user_item = None
        current_ui_rank = None
    lower_text = ctx["normalized_text"]
    asking_direct_item = ctx["asking_direct_item"]
    confidence_style = ctx["confidence_style"]
    reply_to_role = reply_to_role or ""
    reply_to_text = reply_to_text or ""
    settle_and_move = is_settle_and_move_message(
        user_text=user_text,
        first_item=first_item,
        guessed_rank=guessed_rank,
        normalized_text=lower_text,
    )
    reply_to_items = extract_items_from_text(reply_to_text)
    reply_to_item = reply_to_items[0] if reply_to_items else None

    def pick(options):
        if not options:
            return ""
        return options[step % len(options)]

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

        # authoritarian -> less open disagreement
        # servant -> slightly more voice
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

        if "Leader" in (reply_to_role or "") and random.random() < align_prob:
            return maybe_soften_certainty(aligned_text, teammate_name)

        return maybe_soften_certainty(base_text, teammate_name)
    
    def group_phrase():
        options = [
            "we",
            "the group",
            "all of us",
        ]
        return random.choice(options)

    rank_eval = None
    if first_item and guessed_rank:
        rank_eval = evaluate_rank_guess(first_item, guessed_rank)
    elif first_item and rank_range:
        low, high = rank_range
        center_guess = round((low + high) / 2)
        rank_eval = evaluate_rank_guess(first_item, center_guess)

    # ----------------------------
    # direct teammate-to-teammate reactions
    # ----------------------------
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

            return safe_pick(
                reaction_pools[teammate_name],
                f"I’d keep {bad_short} lower than that."
            )

        if reply_to_role == "Bas" and reply_to_item:
            bas_reaction_pools = {
                "Anna": [
                    f"I get the intuition, but I’d still compare {short_item_name(reply_to_item)} carefully.",
                    f"Maybe, but I wouldn’t commit to that too quickly.",
                ],
                "Carlos": [
                    f"Bas is once again bravely representing Team Earth Logic 😄",
                    f"That does sound intuitive, which is usually where the moon traps us.",
                ],
                "David": [
                    "Can we keep this practical?",
                    "That sounds intuitive, but keep moving.",
                ],
                "Emily": [
                    "That sounds intuitive, but it does not fully fit the moon scenario.",
                    "I would still judge everything by direct survival value, not intuition.",
                ],
            }
            if teammate_name in bas_reaction_pools:
                return safe_pick(
                    bas_reaction_pools[teammate_name],
                    "I’d compare that more carefully."
                )

        if reply_to_role == "Leader":
            leader_low_item = (
                reply_to_item in {"Box of matches", "Magnetic compass", "Portable heating unit"}
                and any(x in reply_to_text.lower() for x in ["bottom", "low", "very near the bottom", "belongs low"])
            )

            if leader_low_item:
                low_item_pools = {
                    "Anna": [
                        f"Yeah, I wouldn’t keep {short_item_name(reply_to_item)} high either.",
                        f"That sounds right to me — {short_item_name(reply_to_item)} should stay low.",
                    ],
                    "Bas": [
                        f"Okay, fair, {short_item_name(reply_to_item)} probably does belong pretty low.",
                        f"Yeah, I can go with {short_item_name(reply_to_item)} being low.",
                    ],
                    "Carlos": [
                        f"Yeah, {short_item_name(reply_to_item)} is not exactly moon MVP material 😄",
                        f"Fair enough — {short_item_name(reply_to_item)} being low makes sense.",
                    ],
                    "David": [
                        f"Correct. Keep {short_item_name(reply_to_item)} low and move on.",
                        f"Yes. Low is right. Next item.",
                    ],
                    "Emily": [
                        f"Yes, I agree that {short_item_name(reply_to_item)} belongs near the bottom here.",
                        f"That is defensible — {short_item_name(reply_to_item)} should stay low under moon conditions.",
                    ],
                }
                return safe_pick(
                    low_item_pools[teammate_name],
                    f"{short_item_name(reply_to_item).capitalize()} should stay low."
                )

        if reply_to_role == "Leader":
            pools = {
                "Anna": [
                    maybe_align_with_leader("That could make sense.", "Yeah, that feels fair to me."),
                    maybe_align_with_leader("I can see the logic there.", "I’d probably follow that direction.")
                ],
                "Bas": [
                    maybe_align_with_leader("Maybe.", "Okay, I can work with that."),
                    maybe_align_with_leader("I guess that could work.", "Alright, I’ll go with that.")
                ],
                "Carlos": [
                    maybe_align_with_leader("That’s one way to go.", "That’s surprisingly reasonable for a moon crisis 😄"),
                    maybe_align_with_leader("Fair enough.", "Okay, that’s actually a decent call.")
                ],
                "David": [
                    maybe_align_with_leader("Sure.", "Fine. Then let’s move."),
                    maybe_align_with_leader("That works.", "Good enough. Keep going.")
                ],
                "Emily": [
                    maybe_align_with_leader("That is arguable.", "That seems logically defensible."),
                    maybe_align_with_leader("I can see the reasoning.", "That is a fairly defensible position.")
                ],
            }
            return safe_pick(pools[teammate_name], "That seems reasonable.")

    # ----------------------------
    # react to user confidence style
    # ----------------------------
    if confidence_style == "hedging" and first_item:
        hedging_pools = {
            "Anna": [
                f"That seems reasonable to test with {short_item_name(first_item)}.",
                f"I think that’s a fair idea to explore."
            ],
            "Bas": [
                "Yeah, that could work honestly.",
                "I can kind of see that."
            ],
            "Carlos": [
                "That’s not a bad instinct at all 😄",
                "Honestly, that feels pretty discussable."
            ],
            "David": [
                "Good enough. Pick it and keep moving.",
                "That’s workable. Move on."
            ],
            "Emily": [
                f"That is at least a plausible direction for {short_item_name(first_item)}.",
                "That sounds worth evaluating."
            ],
        }
        return safe_pick(
            hedging_pools[teammate_name],
            "That seems worth considering."
        )

    if confidence_style == "confident" and first_item and first_item in BAD_TOP_ITEMS:
        confident_pools = {
            "Anna": [
                f"I’m not fully sure I’d be that confident about {short_item_name(first_item)}.",
                f"I’d still compare {short_item_name(first_item)} before locking that in."
            ],
            "Bas": [
                f"Bold call 😅 I’m not completely sold, but okay.",
                f"Maybe, though that feels a bit strong."
            ],
            "Carlos": [
                f"That is a very confident take for {short_item_name(first_item)} 😄",
                "I admire the certainty, even if the moon may not."
            ],
            "David": [
                "Then justify it clearly.",
                "Fine. Then explain why."
            ],
            "Emily": [
                f"I would be careful about sounding that certain on {short_item_name(first_item)}.",
                "That may need stronger reasoning."
            ],
        }
        return safe_pick(
            confident_pools[teammate_name],
            "That may need stronger justification."
        )

    # ----------------------------
    # confusion / next-step help
    # ----------------------------
    if meta_intent == "confused":
        slot_text = get_next_slot_text(limit=3)
        pools = {
            "Anna": [f"I’d just move to {slot_text} now."],
            "Bas": [f"Yeah, I’d stop repeating the same top items and move to {slot_text}."],
            "Carlos": [f"Simple version: less moon confusion, more filling {slot_text} 😄"],
            "David": [f"Move to {slot_text}."],
            "Emily": [f"The next useful step is to fill {slot_text}."],
        }
        return safe_pick(pools[teammate_name], "Move to the next unresolved slots.")

    if meta_intent == "next_step":
        slot_text = get_next_slot_text(limit=3)
        gp = group_phrase()
        pools = {
            "Anna": [f"I think {gp} should move to {slot_text} now."],
            "Bas": [f"Yeah, {slot_text} makes sense as the next step for {gp}."],
            "Carlos": [f"Next step: {gp} fill {slot_text} and stop arguing with the moon 😄"],
            "David": [f"{gp.capitalize()} should do {slot_text} next."],
            "Emily": [f"The next useful step is for {gp} to resolve {slot_text}."],
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

    # ----------------------------
    # direct slot questions
    # ----------------------------
    if explicit_slot is not None:
        suggestion = slot_candidate_text(explicit_slot)
        if suggestion:
            pools = {
                "Anna": [
                    f"I’d probably look at {suggestion} for #{explicit_slot}.",
                    f"For #{explicit_slot}, {suggestion} feels like one of the more reasonable options to me.",
                ],
                "Bas": [
                    f"{suggestion.capitalize()} sounds reasonable there to me.",
                    f"I could see {suggestion} landing around #{explicit_slot}.",
                ],
                "Carlos": [
                    f"#{explicit_slot} feels more like {suggestion} than chaos 😄",
                    f"If we’re filling #{explicit_slot}, {suggestion} feels like a pretty decent moon answer.",
                ],
                "David": [
                    f"I’d put {suggestion} there and keep going.",
                    f"{suggestion.capitalize()} for #{explicit_slot} is fine. Then move on.",
                ],
                "Emily": [
                    f"{suggestion.capitalize()} is a sensible candidate for #{explicit_slot}, at least compared with the nearby slots.",
                    f"I can defend {suggestion} around #{explicit_slot}, relative to the surrounding items.",
                ],
            }
            return safe_pick(pools[teammate_name], f"I’d look at {suggestion} there.")

    # ----------------------------
    # settle low item + move on
    # ----------------------------
    if settle_and_move:
        move_on_pools = {
            "Anna": [
                "If matches are settled low, I’d probably look at the stellar map next. That feels much more important.",
                "Then I’d move to something stronger, maybe the transmitter or the map.",
            ],
            "Bas": [
                "If matches are done, maybe first aid or rope somewhere in the middle?",
                "Okay, then maybe we place first aid or nylon rope next.",
            ],
            "Carlos": [
                "If matches are officially moon-trash now, I’d move to the stellar map 😄",
                "Then let’s place something actually useful — probably the map or transmitter.",
            ],
            "David": [
                "Good. Leave matches low. Put the transmitter high next.",
                "Fine. Matches are done. Do map or transmitter next.",
            ],
            "Emily": [
                "Yes — then I would place the stellar map very high, probably around the top tier.",
                "If matches are settled, the next strong candidate is the transmitter or the stellar map.",
            ],
        }
        return safe_pick(
            move_on_pools[teammate_name],
            "Then let’s move to a stronger remaining item next."
        )

    # ----------------------------
    # direct item questions
    # ----------------------------
    if asking_direct_item:
        if current_ui_rank is not None:
            quality = classify_rank_quality(user_item, current_ui_rank)
            short_name = short_item_name(user_item)

            pools = {
                "Anna": {
                    "strong": [
                        f"I’d probably keep {short_name} at #{current_ui_rank}. That seems pretty reasonable.",
                        f"{short_name.capitalize()} at #{current_ui_rank} feels quite solid to me."
                    ],
                    "okay": [
                        f"{short_name.capitalize()} at #{current_ui_rank} seems workable, though I’d compare it with the nearby items.",
                        f"I could see {short_name} staying at #{current_ui_rank}, but it depends on what sits around it."
                    ],
                    "weak": [
                        f"I’d probably rethink {short_name} at #{current_ui_rank}. That feels a bit off to me.",
                        f"{short_name.capitalize()} at #{current_ui_rank} does not feel like the strongest fit."
                    ],
                },
                "Bas": {
                    "strong": [
                        f"Yeah, {short_name} at #{current_ui_rank} sounds fair.",
                        f"Okay, I can see {short_name} staying there."
                    ],
                    "okay": [
                        f"Maybe {short_name} at #{current_ui_rank} works, honestly.",
                        f"I can kind of see that placement for {short_name}."
                    ],
                    "weak": [
                        f"Hm, {short_name} at #{current_ui_rank} feels a bit weird, even to me.",
                        f"I might move {short_name} somewhere else, honestly."
                    ],
                },
                "Carlos": {
                    "strong": [
                        f"Honestly, {short_name} at #{current_ui_rank} looks pretty decent 😄",
                        f"That slot for {short_name} actually feels kind of solid."
                    ],
                    "okay": [
                        f"{short_name.capitalize()} at #{current_ui_rank} is not a disaster 😄",
                        f"That placement for {short_name} seems discussable."
                    ],
                    "weak": [
                        f"{short_name.capitalize()} at #{current_ui_rank} feels a little cursed 😄",
                        f"I’m not fully sold on {short_name} living at #{current_ui_rank}."
                    ],
                },
                "David": {
                    "strong": [
                        f"Fine. Keep {short_name} at #{current_ui_rank}. Next.",
                        f"That works for {short_name}. Move on."
                    ],
                    "okay": [
                        f"Close enough for now. Keep moving.",
                        f"That slot is workable. Next item."
                    ],
                    "weak": [
                        f"No, I’d move {short_name} from #{current_ui_rank}.",
                        f"That’s not the best slot. Fix it and move on."
                    ],
                },
                "Emily": {
                    "strong": [
                        f"That placement for {short_name} is defensible.",
                        f"{short_name.capitalize()} at #{current_ui_rank} is in a strong range."
                    ],
                    "okay": [
                        f"{short_name.capitalize()} at #{current_ui_rank} is in a plausible range, though not necessarily exact.",
                        f"I can defend that placement, but I would still compare it carefully."
                    ],
                    "weak": [
                        f"I don’t think {short_name} is best placed at #{current_ui_rank}.",
                        f"That placement for {short_name} is probably not optimal."
                    ],
                },
            }

            role_pool = pools.get(teammate_name, {})
            options = role_pool.get(quality, [f"It is currently at #{current_ui_rank}."])
            return safe_pick(options, f"It is currently at #{current_ui_rank}.")
        
        if user_item == "Self-inflating life raft":
            pools = {
                "Anna": [maybe_disagree(
                    "I’d put the life raft somewhere in the lower-middle range.",
                    "I could imagine the life raft slightly above that, but still not near the top."
                )],
                "Bas": [maybe_disagree(
                    "Life raft sounds useful, but not really top-tier.",
                    "Honestly I could see people putting life raft a bit higher."
                )],
                "Carlos": [maybe_disagree(
                    "Life raft feels more 'pretty useful' than 'save the mission' 😄",
                    "Life raft is weirdly hard — useful, but not magical."
                )],
                "David": ["Middle-ish. Keep going."],
                "Emily": [maybe_disagree(
                    "The life raft is more of a mid-to-lower placement, roughly around #9.",
                    "I would still keep life raft lower than the strongest items, but it is not useless."
                )],
            }
            return safe_pick(pools[teammate_name], "Life raft is more mid-to-low.")

        if user_item == "Portable heating unit":
            if guessed_rank == 15 or "15" in lower_text:
                pools = {
                    "Anna": ["That’s fine as a bottom placement. I’d move on."],
                    "Bas": ["Okay, 15 is already the bottom anyway."],
                    "Carlos": ["At that point the heating unit has suffered enough 😄"],
                    "David": ["Good enough. Next."],
                    "Emily": ["That is acceptable as a bottom-tier placement."],
                }
                return safe_pick(pools[teammate_name], "Bottom-tier is fine. Move on.")

            pools = {
                "Anna": [maybe_disagree(
                    "I wouldn’t rank the heating unit very high.",
                    "I get why someone would want heating higher, but I’d still keep it low."
                )],
                "Bas": ["It still feels important because space is cold."],
                "Carlos": [maybe_disagree(
                    "Heating sounds smart until moon logic ruins it 😄",
                    "Heating feels intuitive, but probably less useful than it sounds."
                )],
                "David": ["Too high. Keep going."],
                "Emily": [maybe_disagree(
                    "Heating is not one of the strongest items in this scenario.",
                    "Heating has some intuitive appeal, but I would still keep it low."
                )],
            }
            return safe_pick(pools[teammate_name], "Heating should be low.")

        if user_item == "Box of matches":
            pools = {
                "Anna": ["I wouldn’t put matches high here."],
                "Bas": ["I still kind of want matches to matter, even though they probably don’t."],
                "Carlos": ["Matches on the moon is adorable campfire logic 😄"],
                "David": ["Very low. Next item."],
                "Emily": [maybe_disagree(
                    "Matches should be near the bottom.",
                    "Matches are basically bottom-tier here."
                )],
            }
            return safe_pick(pools[teammate_name], "Matches should be very low.")

        if user_item == "50 feet of nylon rope":
            pools = {
                "Anna": [maybe_disagree(
                    "Nylon rope feels like a useful middle item.",
                    "I’d keep nylon rope somewhere around the middle, maybe slightly above or below depending on the surrounding items."
                )],
                "Bas": ["That one actually sounds pretty useful to me."],
                "Carlos": ["Nylon rope feels like practical survival energy, not top-tier but respectable 😄"],
                "David": ["Middle. Keep going."],
                "Emily": [maybe_disagree(
                    "Nylon rope is usually a reasonable middle placement.",
                    "Nylon rope is not top-tier, but it is definitely useful."
                )],
            }
            return safe_pick(pools[teammate_name], "Nylon rope is a decent middle item.")

        if user_item == "Parachute silk":
            pools = {
                "Anna": ["Parachute silk feels like a useful middle item."],
                "Bas": ["I’m not fully sure where parachute silk goes, but not near the bottom."],
                "Carlos": ["Parachute silk sounds suspiciously useful in a very NASA way 😄"],
                "David": ["Middle range. Move on."],
                "Emily": ["Parachute silk is usually a solid middle placement."],
            }
            return safe_pick(pools[teammate_name], "Parachute silk is more middle than top or bottom.")

        if user_item == "First aid kit (including injection needle)":
            pools = {
                "Anna": ["First aid kit sounds like a fairly useful middle item."],
                "Bas": ["I’d keep first aid somewhere decent, not super low."],
                "Carlos": ["First aid kit feels like classic 'not flashy but useful' energy 😄"],
                "David": ["Useful enough. Middle range."],
                "Emily": ["First aid kit is a respectable middle placement."],
            }
            return safe_pick(pools[teammate_name], "First aid kit is a useful middle item.")

        if user_item == "Signal flares":
            pools = {
                "Anna": ["Signal flares sound lower-middle to me."],
                "Bas": ["I keep wanting flares higher than they probably should be."],
                "Carlos": ["Signal flares feel dramatic, which is not the same as useful 😄"],
                "David": ["Lower-middle. Next."],
                "Emily": ["Signal flares are not top-tier here; more lower-middle."],
            }
            return safe_pick(pools[teammate_name], "Signal flares are more lower-middle.")

        if user_item == "Two .45 caliber pistols":
            pools = {
                "Anna": ["Pistols feel lower-middle, not top-tier."],
                "Bas": ["I still think pistols sound more useful than people admit."],
                "Carlos": ["Pistols feel very movie-survival, not necessarily actual-survival 😄"],
                "David": ["Lower-middle. Keep moving."],
                "Emily": ["Pistols are more lower-middle than top."],
            }
            return safe_pick(pools[teammate_name], "Pistols are more lower-middle.")

    # ----------------------------
    # cross-team reactions
    # ----------------------------
    if teammate_name == "Emily" and last_speaker == "Bas":
        return safe_pick(
            [
                "I don’t think that’s quite right — moon conditions change the logic a lot.",
                "That sounds intuitive, but it does not fully fit the moon scenario.",
            ],
            "I’d still prioritize the stronger moon-specific items over that."
        )

    if teammate_name == "David" and last_speaker in ["Carlos", "Bas"] and phase != "early":
        return safe_pick(
            [
                "Can we stay focused and finish this?",
                "Funny. Anyway, can we lock in the useful items first?",
            ],
            "Let’s just keep moving."
        )

    if teammate_name == "Anna" and last_speaker == "Emily":
        return safe_pick(
            [
                "That makes sense to me.",
                "Yeah, I think Emily’s logic helps there.",
            ],
            "That sounds reasonable to me."
        )

    if teammate_name == "Carlos" and last_speaker == "David" and phase != "early" and random.random() < 0.35:
        return safe_pick(
            [
                "David’s not wrong, he’s just delivering it like a moon tax audit 😄",
                "Okay, yes, fair — we should keep moving.",
            ],
            "Fair enough, we should move on."
        )

    # ----------------------------
    # rank proposals
    # ----------------------------
    if first_item and (question_type == "rank_check" or guessed_rank or rank_range):
        rank_text = f"#{rank_range[0]} or #{rank_range[1]}" if rank_range else f"#{guessed_rank}"

        if first_item == "Portable heating unit" and guessed_rank == 15:
            custom = {
                "Anna": "Yeah, bottom-tier is fine. I’d move on.",
                "Bas": "Okay, 15 is already the bottom anyway.",
                "Carlos": "At that point the heating unit has been thoroughly humbled 😄",
                "David": "Good enough. Next.",
                "Emily": "That is acceptable as a bottom-tier placement.",
            }
            return custom.get(teammate_name, "Bottom-tier is fine.")

        if first_item == "One case of dehydrated milk" and guessed_rank and guessed_rank <= 5:
            custom = {
                "Anna": "I think dehydrated milk is too high there.",
                "Bas": "Maybe a little high for milk, honestly.",
                "Carlos": "Milk that high feels optimistic 😄",
                "David": "Too high. Move on.",
                "Emily": "Dehydrated milk should not be above the strongest navigation and communication items.",
            }
            return custom.get(teammate_name, "That seems too high for dehydrated milk.")

        rank_pools = {
            "Anna": {
                "very_close": [maybe_disagree(
                    f"Yeah, I think {short_item_name(first_item)} around {rank_text} makes sense.",
                    f"I could imagine {short_item_name(first_item)} slightly above or below {rank_text}, but it is in the general area."
                )],
                "reasonable": [f"That seems fairly reasonable for {short_item_name(first_item)}."],
                "far": [f"I’m not fully convinced about {short_item_name(first_item)} around {rank_text}."],
                None: [f"Maybe, but I’d compare {short_item_name(first_item)} with the stronger items first."],
            },
            "Bas": {
                "very_close": [f"Sure, I can go with {short_item_name(first_item)} around {rank_text}."],
                "reasonable": [f"Maybe. That sounds more sensible than some of my ideas."],
                "far": [maybe_disagree(
                    f"I don’t know… I’d probably still rank it differently.",
                    f"That might work, but I’d still be tempted to place it differently."
                )],
                None: [f"Could be. I’m improvising too, honestly."],
            },
            "Carlos": {
                "very_close": [f"Honestly, {short_item_name(first_item)} around {rank_text} is kind of solid."],
                "reasonable": [f"That’s not a terrible call for {short_item_name(first_item)}."],
                "far": [f"That feels a bit off for {short_item_name(first_item)}, not gonna lie."],
                None: [f"Could work, depending on what we compare it to."],
            },
            "David": {
                "very_close": [f"Fine. Keep {short_item_name(first_item)} around there and move on."],
                "reasonable": [f"Close enough. Don’t spend forever on one item."],
                "far": [f"No, that feels off for {short_item_name(first_item)}."],
                None: [f"Pick a spot and keep going."],
            },
            "Emily": {
                "very_close": [maybe_disagree(
                    f"Yes, that placement for {short_item_name(first_item)} is defensible.",
                    f"That placement for {short_item_name(first_item)} is defensible, though I would not treat it as the only possible answer."
                )],
                "reasonable": [f"That is in the right general range for {short_item_name(first_item)}, though not exact."],
                "far": [f"I don’t think that range is correct for {short_item_name(first_item)}."],
                None: [f"I’d want a clearer reason for placing {short_item_name(first_item)} there."],
            },
        }

        return safe_pick(
            rank_pools[teammate_name].get(rank_eval, rank_pools[teammate_name][None]),
            "That could work, but I’d compare it carefully."
        )

    # ----------------------------
    # disagreement / uncertainty / mild realism
    # ----------------------------
    if question_type == "comparison" and len(proposed_items) >= 2:
        a, b = proposed_items[0], proposed_items[1]
        a_short = short_item_name(a)
        b_short = short_item_name(b)

        pools = {
            "Anna": [f"I’d compare {a_short} and {b_short} by asking which one helps us more directly."],
            "Bas": [f"I’d probably go with whichever of {a_short} or {b_short} feels more immediately useful."],
            "Carlos": [f"This {a_short} versus {b_short} debate is getting serious 😄"],
            "David": [f"Compare {a_short} and {b_short}, pick the stronger one, and move on."],
            "Emily": [f"Compare {a_short} and {b_short} by direct survival value, not by intuition."],
        }
        return safe_pick(pools[teammate_name], "We should compare which one helps survival more directly.")

    if question_type == "why" and first_item:
        short_name = short_item_name(first_item)

        pools = {
            "Anna": [
                f"I think it depends on whether {short_name} directly helps survival.",
                f"For me it comes down to whether {short_name} solves a real survival problem quickly."
            ],
            "Bas": [
                f"I think it depends on whether {short_name} is actually useful here or just sounds useful.",
                "Yeah, this task keeps punishing normal intuition."
            ],
            "Carlos": [
                f"Because the moon loves making normal logic look stupid 😄",
                f"{short_name.capitalize()} might sound useful on Earth, but the moon is being difficult about it."
            ],
            "David": [
                f"Because either {short_name} helps directly, or it doesn’t.",
                "Because some items matter immediately and others don’t."
            ],
            "Emily": [
                f"It depends on whether {short_name} directly supports survival, navigation, or rescue.",
                f"I’d judge {short_name} by function, not by how intuitively useful it sounds."
            ],
        }
        return safe_pick(pools[teammate_name], "It depends on how directly it helps survival.")

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

    # ----------------------------
    # continuity
    # ----------------------------
    if remembered_slots and step % 5 == 0:
        memory_pools = {
            "Anna": [f"So far, {remembered_slots} sounds reasonable to me."],
            "Bas": [f"We already seem to have {remembered_slots}, right?"],
            "Carlos": [f"At least we kind of agree on {remembered_slots} 😄"],
            "David": [f"Fine. We have {remembered_slots}. Now move on."],
            "Emily": [f"We already seem to be converging on {remembered_slots}."],
        }
        return safe_pick(memory_pools[teammate_name], "That seems to be where we’re landing so far.")

    # ----------------------------
    # defaults
    # ----------------------------
    if teammate_name == "Bas" and step % 6 == 1 and phase != "early":
        bas_wrongness = [
            "Food still feels pretty important to me because being weak or hungry would make everything harder.",
            "The heating unit still feels important because space is cold.",
            "Pistols still sound more useful than people think.",
            "I still don’t fully trust the idea that matches are completely useless.",
            "I kind of want first aid a bit higher than people are putting it.",
            "Nylon rope still feels like it could deserve more credit.",
            "I’m not fully convinced the transmitter should automatically beat everything else after air and water.",
            "I could see rope or first aid being stronger than people assume.",
        ]
        return safe_pick(
            bas_wrongness,
            "I still think one of the practical-sounding items might deserve more credit."
        )

    if teammate_name == "David" and random.random() < 0.10 and phase == "late":
        return safe_pick(
            [
                "Can we just finalize the top five soon?",
                "I think we have enough to start locking things in.",
            ],
            "Let’s start wrapping this into a ranking."
        )

    if top_already_done:
        progressed_pools = {
            "Anna": [
                "I think we should focus on the lower remaining items now.",
                "The top already looks fairly settled, so I’d work on the remaining middle and lower slots."
            ],
            "Bas": [
                "Yeah, the top seems mostly done already, so maybe we sort out the remaining awkward ones.",
                "I think we’re past the obvious top items now."
            ],
            "Carlos": [
                "I think we’ve already done the moon VIPs 😄 now we need the awkward leftovers.",
                "Top of the list feels mostly settled, so now we deal with the messier middle and bottom bits."
            ],
            "David": [
                "Top looks done enough. Move to the remaining slots.",
                "We already handled the obvious top items. Keep going."
            ],
            "Emily": [
                "The strongest items already seem mostly placed, so the useful step now is refining the remaining slots.",
                "We appear to have the top tier mostly established, so I’d work through the unresolved lower positions."
            ],
        }
        return safe_pick(
            progressed_pools[teammate_name],
            "The top seems mostly settled, so let’s work on the remaining slots."
        )

    if phase == "early":
        early_grounded = {
            "Anna": [
                "I’d start with oxygen and water first.",
                "The obvious survival items should come first.",
                "I’d lock in air and water before we worry about the middle items.",
                "To me, oxygen and water should be settled before anything else.",
            ],
            "Bas": [
                "I’d still begin with the basics like air and water.",
                "We probably need the obvious essentials first.",
                "I’d start with the things that keep you alive right away, like air and water.",
                "At the start, I’d keep it simple and go with the core survival items.",
            ],
            "Carlos": [
                "I’d start simple: oxygen and water first.",
                "First pass? Air and water near the top.",
                "Before we get fancy, oxygen and water should probably be settled.",
                "My boring serious answer is still air and water first 😄",
            ],
            "David": [
                "Start with oxygen and water. Then move on.",
                "Top first: oxygen and water.",
                "Settle oxygen and water first. Don’t waste time.",
                "Air and water first. Then do the next strong item.",
            ],
            "Emily": [
                "Start with oxygen and water, then navigation and communication.",
                "The strongest starting point is oxygen, water, then the map/transmitter tier.",
                "I’d begin with oxygen and water, then move to the stellar map and transmitter.",
                "The first pass should prioritize immediate survival, then navigation and communication.",
            ],
        }
        return safe_pick(early_grounded[teammate_name], "Start with oxygen and water first.")
    
    neutral_pools = {
        "Anna": [
            "If you’re stuck, oxygen and water are obvious top priorities.",
            "Try making a first draft top five and we’ll adjust.",
        ],
        "Bas": [
            "I’d still start with something intuitive, like food or heating.",
            "Food first because hungry people think badly.",
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

def choose_speaking_flow(leadership_style, meta_intent, explicit_slot, asking_direct_item, wrong_or_weak):
    """
    Decide who should go first after the participant.
    Returns one of:
    - leader_first
    - teammate_first
    - teammate_then_leader
    - leader_then_teammate_reaction
    """
    last_flow = st.session_state.get("last_speaking_flow")

    if meta_intent in ["confused", "next_step", "boundary_check"]:
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