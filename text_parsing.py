import re
from constants import (
    ITEM_ALIASES,
    GOOD_TOP_ITEMS,
    BAD_TOP_ITEMS,
    SHORT_ITEM_NAMES,
    NASA_EXPERT_RANK,
)


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())

def extract_reasoning_themes(text: str, already_normalized: bool = False):
    t = text if already_normalized else normalize_text(text)

    theme_rules = [
        (
            "communication",
            [
                "contact earth",
                "contact with earth",
                "contact home",
                "make contact",
                "get in contact",
                "communicate",
                "communication",
                "radio",
                "transmitter",
                "signal",
                "call for help",
            ],
        ),
        (
            "rescue",
            [
                "rescue",
                "rescued",
                "get rescued",
                "help arrives",
                "help coming",
                "reach rescue",
                "rescue base",
            ],
        ),
        (
            "navigation",
            [
                "navigation",
                "navigate",
                "find the way",
                "find our way",
                "route",
                "direction",
                "map",
                "where to go",
            ],
        ),
        (
            "ship_status",
            [
                "damage on the ship",
                "damages on the ship",
                "what damages there are on the ship",
                "state of the ship",
                "ship intact",
                "ship damaged",
                "damage to the ship",
            ],
        ),
        (
            "survival",
            [
                "survival",
                "survive",
                "stay alive",
                "breathing",
                "oxygen",
                "dehydration",
                "water",
            ],
        ),
    ]

    found = []
    for theme, cues in theme_rules:
        if any(cue in t for cue in cues):
            found.append(theme)

    return found


def short_item_name(item: str) -> str:
    return SHORT_ITEM_NAMES.get(item, item.lower())


def extract_items_from_text(text: str, already_normalized: bool = False):
    t = text if already_normalized else normalize_text(text)
    found = []

    for canonical, aliases in ITEM_ALIASES.items():
        sorted_aliases = sorted(aliases, key=len, reverse=True)
        for alias in sorted_aliases:
            alias_pattern = r"\b" + re.escape(alias.lower()) + r"\b"
            if re.search(alias_pattern, t):
                found.append(canonical)
                break

    seen = set()
    out = []
    for item in found:
        if item not in seen:
            seen.add(item)
            out.append(item)

    return out


def classify_proposal(items):
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
    t = normalize_text(text)

    patterns = [
        r"\b(?:rank|number|nr|#)\s*([1-9]|1[0-5])\b",
        r"\b(?:at|in|to)\s+([1-9]|1[0-5])\b",
        r"\b(?:is|be)\s+([1-9]|1[0-5])\b",
        r"\b([1-9]|1[0-5])(st|nd|rd|th)\b",
        r"\b([1-9]|1[0-5])\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, t)
        if match:
            rank = int(match.group(1))
            if 1 <= rank <= 15:
                return rank

    ordinal_map = {
        "first": 1,
        "second": 2,
        "third": 3,
        "fourth": 4,
        "fifth": 5,
        "sixth": 6,
        "seventh": 7,
        "eighth": 8,
        "ninth": 9,
        "tenth": 10,
        "eleventh": 11,
        "twelfth": 12,
        "thirteenth": 13,
        "fourteenth": 14,
        "fifteenth": 15,
        "last": 15,
    }

    cardinal_map = {
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
        "eleven": 11,
        "twelve": 12,
        "thirteen": 13,
        "fourteen": 14,
        "fifteen": 15,
    }

    for word, rank in ordinal_map.items():
        if re.search(r"\b" + re.escape(word) + r"\b", t):
            return rank

    for word, rank in cardinal_map.items():
        if re.search(r"\b(?:at|in|to|is|be)\s+" + re.escape(word) + r"\b", t):
            return rank

    return None


def extract_multiple_rank_assignments(text: str):
    cleaned = text.replace("\r\n", "\n")
    cleaned = re.sub(r"(?<!\n)(#\s*(?:[1-9]|1[0-5])\b)", r"\n\1", cleaned)
    cleaned = re.sub(r"(?<!\n)((?:rank|number)\s*(?:[1-9]|1[0-5])\b)", r"\n\1", cleaned, flags=re.IGNORECASE)

    assignments = []
    seen_items = set()
    seen_ranks = set()

    for raw_line in cleaned.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        t = normalize_text(line)
        match = re.search(r"^(?:#|rank|number)?\s*([1-9]|1[0-5])\b", t)
        if not match:
            continue

        rank = int(match.group(1))
        items = extract_items_from_text(line)
        if not items:
            continue

        item = items[0]
        if item in seen_items or rank in seen_ranks:
            continue

        seen_items.add(item)
        seen_ranks.add(rank)
        assignments.append({"rank": rank, "item": item})

    assignments.sort(key=lambda x: x["rank"])
    return assignments


def detect_question_type(text: str):
    t = normalize_text(text)

    if any(x in t for x in ["why", "waarom", "hoezo"]):
        return "why"

    if any(x in t for x in [
        "what should we do", "what do we do", "where do we start",
        "how should we do this", "wat moeten we doen", "what's the plan",
        "whats the plan", "what is the plan", "how do we do this"
    ]):
        return "strategy"

    if any(x in t for x in [
        "better than", "higher than", "lower than", "above", "below",
        "vs", "versus", "or should", "more important than",
        "less important than", "before", "after"
    ]):
        return "comparison"

    if any(x in t for x in [
        "i disagree", "don't agree", "do not agree", "not true",
        "doesn't make sense", "does not make sense", "no that"
    ]):
        return "disagreement"

    if any(x in t for x in [
        "i agree",
        "agree with",
        "that makes sense",
        "sounds right",
        "sounds good",
        "that sounds good",
        "okay sounds good",
        "ok sounds good",
        "good idea",
        "fair enough",
    ]):
        return "agreement"


    if any(x in t for x in [
        "is that right", "is this right", "correct?", "right?",
        "does that make sense", "should we", "would that make sense"
    ]):
        return "confirmation"

    if extract_explicit_slot_request(t) is not None:
        return "rank_check"

    if any(x in t for x in [
        "what rank", "what number", "good number", "good at",
        "okay at", "ok at", "which rank", "which number",
        "should be rank", "should be number", "goes at", "go at",
        "somewhere at", "somewhere more like", "put it at", "place it at"
    ]):
        return "rank_check"

    mentioned_items = extract_items_from_text(t, already_normalized=True)
    if mentioned_items and len(t) < 40 and ("?" in t or len(mentioned_items) == 1):
        return "item_check"

    return "none"


def evaluate_rank_guess(item: str, guessed_rank: int):
    if item not in NASA_EXPERT_RANK or guessed_rank is None:
        return "unknown"

    true_rank = NASA_EXPERT_RANK[item]
    diff = abs(guessed_rank - true_rank)

    if diff <= 1:
        return "very_close"
    if diff <= 3:
        return "reasonable"
    return "far"


def detect_rank_range_from_text(text: str):
    t = normalize_text(text)

    match = re.search(r"\b([1-9]|1[0-5])\s*(?:or|-|to)\s*([1-9]|1[0-5])\b", t)
    if match:
        a, b = int(match.group(1)), int(match.group(2))
        return (min(a, b), max(a, b))

    match = re.search(r"\bbetween\s+([1-9]|1[0-5])\s+and\s+([1-9]|1[0-5])\b", t)
    if match:
        a, b = int(match.group(1)), int(match.group(2))
        return (min(a, b), max(a, b))

    ordinal_map = {
        "first": 1,
        "second": 2,
        "third": 3,
        "fourth": 4,
        "fifth": 5,
        "sixth": 6,
        "seventh": 7,
        "eighth": 8,
        "ninth": 9,
        "tenth": 10,
        "eleventh": 11,
        "twelfth": 12,
        "thirteenth": 13,
        "fourteenth": 14,
        "fifteenth": 15,
    }

    word_match = re.search(
        r"\b(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|eleventh|twelfth|thirteenth|fourteenth|fifteenth)\s+or\s+"
        r"(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|eleventh|twelfth|thirteenth|fourteenth|fifteenth)\b",
        t
    )
    if word_match:
        a = ordinal_map[word_match.group(1)]
        b = ordinal_map[word_match.group(2)]
        return (min(a, b), max(a, b))

    return None


def is_direct_rank_request(text: str):
    t = normalize_text(text)
    patterns = [
        "where do you think",
        "where should",
        "what rank",
        "what number",
        "how high",
        "how low",
        "where would you put",
    ]
    return any(p in t for p in patterns)


def detect_user_intent(text: str):
    t = normalize_text(text)
    rank_assignments = extract_multiple_rank_assignments(text)

    if any(x in t for x in [
        "shut up",
        "hou je bek",
        "hou je mond",
        "bek houden",
        "hou je smoel",
        "i dont like this",
        "i don't like this",
        "what are you doing",
        "stop",
        "annoying",
        "you are repeating",
        "you're repeating",
        "repeating stuff",
        "same sentence",
        "same thing over and over",
        "over and over again",
        "you are saying the same sentence",
        "this is repetitive",
        "this feels repetitive",
        "what a shit conversation",
        "shit conversation",
        "this conversation is shit",
        "this sucks",
        "this is bad",
        "this is awful",
        "this is terrible",
    ]):
        return "frustration"


    if len(rank_assignments) >= 5:
        return "full_ranking_proposal"

    if any(x in t for x in [
        "what's the plan", "whats the plan", "what is the plan",
        "how do we do this", "what should we do"
    ]):
        return "planning"

    if any(x in t for x in [
        "what about", "how about"
    ]):
        return "item_followup"

    mentioned = extract_items_from_text(t, already_normalized=True)
    if len(mentioned) >= 2:
        return "multi_item_proposal"

    return "default"


def summarize_items_for_reply(items):
    if not items:
        return "—"
    short_items = [short_item_name(i) for i in items[:4]]
    return ", ".join(short_items)


def extract_explicit_slot_request(text: str):
    t = normalize_text(text)

    patterns = [
        r"what should be number\s+([1-9]|1[0-5])\b",
        r"what is number\s+([1-9]|1[0-5])\b",
        r"number\s+([1-9]|1[0-5])\b",
        r"rank\s+([1-9]|1[0-5])\b",
        r"slot\s+([1-9]|1[0-5])\b",
        r"position\s+([1-9]|1[0-5])\b",
    ]

    for pattern in patterns:
        m = re.search(pattern, t)
        if m:
            return int(m.group(1))

    return None


def detect_meta_intent(text: str):
    t = normalize_text(text)

    if any(x in t for x in [
        "what is the next step",
        "what's the next step",
        "next step",
        "what do i do now",
        "what should i do now",
        "what now",
        "now what",
    ]):
        return "next_step"

    if any(x in t for x in [
        "i dont know what to do",
        "i don't know what to do",
        "what?",
        "i'm confused",
        "im confused",
        "confusing",
    ]):
        return "confused"

    if any(x in t for x in [
        "cannot be lower",
        "can't be lower",
        "can not be lower",
    ]):
        return "boundary_check"

    if any(x in t for x in [
        "already number",
        "already at",
        "already #",
        "is already number",
        "is already at",
        "we already locked",
        "we have already locked",
        "we already have",
        "i just said it before",
        "we already did that",
        "we have already locked in",
        "we already locked in",
        "already settled",
        "we already settled",
        "we were already settled",
        "we already agreed",
        "we already agreed on",
        "we already established",
        "we already established that",
        "leave that out",
        "leave that out of the discussion",
        "lets leave that out",
        "let's leave that out",
    ]):
        return "already_done"

    if any(x in t for x in [
        "why the moon",
        "why moon",
        "why does the moon matter",
    ]):
        return "moon_why"

    if any(x in t for x in [
        "is the ship damaged",
        "is the ship intact",
        "ship intact",
        "did we make contact",
        "made contact",
        "contact with earth",
        "contact with home",
        "are we in contact",
        "can we use the ship",
        "is rescue coming",
    ]):
        return "scenario_question"

    return "none"


def direct_item_question(text: str, mentioned_items: list):
    t = normalize_text(text)

    if not mentioned_items:
        return False

    question_cues = [
        "what about",
        "how about",
        "where should",
        "where would",
        "should be",
        "what rank",
        "what number",
        "higher",
        "lower",
        "above",
        "below",
    ]

    return "?" in t or any(cue in t for cue in question_cues)


def parse_message_features(text: str):
    t = normalize_text(text)
    mentioned_items = extract_items_from_text(t, already_normalized=True)

    return {
        "normalized_text": t,
        "mentioned_items": mentioned_items,
        "question_type": detect_question_type(text),
        "user_intent": detect_user_intent(text),
        "meta_intent": detect_meta_intent(text),
        "rank": extract_rank_from_text(text),
        "rank_range": detect_rank_range_from_text(text),
        "rank_assignments": extract_multiple_rank_assignments(text),
        "slot_request": extract_explicit_slot_request(text),
        "direct_rank_request": is_direct_rank_request(text),
        "direct_item_question": direct_item_question(text, mentioned_items),
        "reasoning_themes": extract_reasoning_themes(t, already_normalized=True),
    }
