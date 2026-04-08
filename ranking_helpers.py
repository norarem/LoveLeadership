import streamlit as st
import time

from constants import (
    NASA_ITEMS,
    NASA_EXPERT_RANK,
    GOOD_TOP_ITEMS,
    BAD_TOP_ITEMS,
    SLOT_SUGGESTIONS,
    ITEM_RANK_BANDS,
)
from text_parsing import (
    short_item_name,
    extract_rank_from_text,
    detect_rank_range_from_text,
    extract_explicit_slot_request,
)


def get_current_ui_ranking():
    """
    Read the actual ranking dropdown values currently selected in the UI.
    Returns dict[item] = rank or None.
    """
    return {
        item: st.session_state.get(f"rank_{item}", None)
        for item in NASA_ITEMS
    }


def get_filled_ui_slots():
    """
    Returns dict[rank] = item for all currently selected ranks in the UI.
    If duplicate ranks somehow occur, the latest encountered item overwrites the earlier one.
    """
    current = get_current_ui_ranking()
    filled = {}

    for item, rank in current.items():
        if rank is not None:
            filled[rank] = item

    return filled


def get_ui_ranking_summary(max_items=8):
    filled = get_filled_ui_slots()
    if not filled:
        return ""

    parts = []
    for slot in sorted(filled.keys())[:max_items]:
        parts.append(f"#{slot} {short_item_name(filled[slot])}")
    return ", ".join(parts)


def get_next_empty_ui_slots(limit=3):
    filled = get_filled_ui_slots()
    out = []

    for i in range(1, 16):
        if i not in filled:
            out.append(i)
        if len(out) >= limit:
            break

    return out


def get_item_current_ui_rank(item: str):
    if not item:
        return None
    return st.session_state.get(f"rank_{item}", None)


def get_used_ranks_excluding_item(current_item: str):
    """
    Return a set of ranks already used by other items, excluding current_item.
    """
    used = set()

    for item in NASA_ITEMS:
        if item == current_item:
            continue

        value = st.session_state.get(f"rank_{item}", None)
        if value is not None:
            used.add(value)

    return used


def get_available_ranks_for_item(current_item: str):
    """
    Return dropdown options for one item:
    - None so the participant can deselect
    - the item's current rank (if any)
    - all ranks not already used by other items
    """
    current_value = st.session_state.get(f"rank_{current_item}", None)
    used_by_others = get_used_ranks_excluding_item(current_item)

    available = [None]
    for rank in range(1, 16):
        if rank == current_value or rank not in used_by_others:
            available.append(rank)

    return available


def classify_rank_quality(item: str, rank: int | None):
    """
    Judge whether a current rank is strong / okay / weak for a given item.
    """
    if item is None or rank is None or item not in NASA_EXPERT_RANK:
        return "unknown"

    true_rank = NASA_EXPERT_RANK[item]
    diff = abs(rank - true_rank)

    if diff <= 1:
        return "strong"
    if diff <= 3:
        return "okay"
    return "weak"


def get_item_rank_band_text(item: str):
    band = ITEM_RANK_BANDS.get(item)
    if not band:
        return None

    low, high = band
    if low == high:
        return f"around #{low}"
    return f"around #{low}–#{high}"


def get_item_rank_feedback_text(item: str, rank: int | None):
    """
    Human-readable evaluation of a current placement.
    """
    if item is None or rank is None:
        return None

    short_name = short_item_name(item)
    quality = classify_rank_quality(item, rank)
    band_text = get_item_rank_band_text(item)

    if quality == "strong":
        return f"{short_name} at #{rank} is pretty plausible"

    if quality == "okay":
        if band_text:
            return f"{short_name} at #{rank} is reasonable; I’d keep it {band_text}"
        return f"{short_name} at #{rank} is in a reasonable range"

    if quality == "weak":
        if item in GOOD_TOP_ITEMS:
            return f"{short_name} at #{rank} is probably lower than I’d keep it"
        if item in BAD_TOP_ITEMS:
            return f"{short_name} at #{rank} is probably higher than I’d keep it"
        if band_text:
            return f"{short_name} at #{rank} feels a bit off; I’d expect it {band_text}"
        return f"{short_name} at #{rank} is probably not the strongest placement"

    return None


def init_ui_reaction_timing():
    if "last_ui_reaction_time" not in st.session_state:
        st.session_state.last_ui_reaction_time = 0.0


def init_ui_rank_tracking():
    if "last_seen_ui_ranking" not in st.session_state:
        st.session_state.last_seen_ui_ranking = {item: None for item in NASA_ITEMS}

    if "recent_ui_rank_changes" not in st.session_state:
        st.session_state.recent_ui_rank_changes = []

    if "pending_ui_rank_changes" not in st.session_state:
        st.session_state.pending_ui_rank_changes = []

    if "last_ui_reaction_turn" not in st.session_state:
        st.session_state.last_ui_reaction_turn = -999

    init_ui_reaction_timing()


def detect_ui_rank_changes():
    """
    Compare current dropdown values to the last seen values.
    Returns a list of change dicts:
    {
        "item": ...,
        "old_rank": ...,
        "new_rank": ...
    }
    """
    init_ui_rank_tracking()

    current = get_current_ui_ranking()
    previous = st.session_state.last_seen_ui_ranking
    changes = []

    for item in NASA_ITEMS:
        old_rank = previous.get(item)
        new_rank = current.get(item)

        if old_rank != new_rank:
            changes.append({
                "item": item,
                "old_rank": old_rank,
                "new_rank": new_rank,
            })

    st.session_state.last_seen_ui_ranking = current.copy()
    return changes


def store_ui_rank_changes(changes, max_keep=10):
    init_ui_rank_tracking()
    if not changes:
        return

    st.session_state.recent_ui_rank_changes.extend(changes)
    st.session_state.recent_ui_rank_changes = st.session_state.recent_ui_rank_changes[-max_keep:]


def store_pending_ui_rank_changes(changes, max_keep=20):
    init_ui_rank_tracking()
    if not changes:
        return

    stamped_changes = []
    current_turn = st.session_state.get("turns", 0)
    current_time = time.time()

    for change in changes:
        stamped = change.copy()
        stamped["created_turn"] = current_turn
        stamped["created_time"] = current_time
        stamped_changes.append(stamped)

    st.session_state.pending_ui_rank_changes.extend(stamped_changes)
    st.session_state.pending_ui_rank_changes = st.session_state.pending_ui_rank_changes[-max_keep:]


def clear_pending_ui_rank_changes():
    init_ui_rank_tracking()
    st.session_state.pending_ui_rank_changes = []


def get_pending_ui_rank_changes():
    init_ui_rank_tracking()
    return list(st.session_state.pending_ui_rank_changes)


def get_latest_ui_rank_change():
    init_ui_rank_tracking()
    if not st.session_state.recent_ui_rank_changes:
        return None
    return st.session_state.recent_ui_rank_changes[-1]


def summarize_ui_rank_change(change):
    if not change:
        return ""

    item = short_item_name(change["item"])
    old_rank = change["old_rank"]
    new_rank = change["new_rank"]

    if old_rank is None and new_rank is not None:
        return f"{item} into #{new_rank}"
    if old_rank is not None and new_rank is None:
        return f"{item} out of #{old_rank}"
    if old_rank is not None and new_rank is not None:
        return f"{item} from #{old_rank} to #{new_rank}"

    return item


def init_slot_memory_state():
    if "slot_memory" not in st.session_state:
        st.session_state.slot_memory = {
            "resolved": {},       # slot -> item
            "tentative": {},      # slot -> item
            "current_focus_slot": None,
            "current_focus_item": None,
        }


def init_group_rank_memory():
    if "group_rank_memory" not in st.session_state:
        st.session_state.group_rank_memory = {}


def init_ranking_helper_state():
    init_ui_rank_tracking()
    init_slot_memory_state()
    init_group_rank_memory()


def update_group_rank_memory_from_message(text: str, mentioned_items: list):
    """
    Store the latest user proposal about item ranks.
    Saves either:
    - exact rank: {"type": "exact", "value": 9}
    - range: {"type": "range", "value": (3, 4)}
    """
    init_group_rank_memory()

    if not mentioned_items:
        return

    rank_range = detect_rank_range_from_text(text)
    guessed_rank = extract_rank_from_text(text)

    for item in mentioned_items:
        if rank_range:
            st.session_state.group_rank_memory[item] = {
                "type": "range",
                "value": rank_range,
            }
        elif guessed_rank is not None:
            st.session_state.group_rank_memory[item] = {
                "type": "exact",
                "value": guessed_rank,
            }


def remember_slot_assignment(item: str, slot: int, resolved=False):
    if item is None or slot is None:
        return

    init_slot_memory_state()
    mem = st.session_state.slot_memory

    if resolved:
        mem["resolved"][slot] = item
        mem["tentative"].pop(slot, None)

        tentative_slots_to_remove = [
            s for s, existing_item in mem["tentative"].items()
            if existing_item == item and s != slot
        ]
        for s in tentative_slots_to_remove:
            mem["tentative"].pop(s, None)
        return

    if slot in mem["resolved"]:
        return

    existing_slots_for_item = [
        s for s, existing_item in mem["tentative"].items()
        if existing_item == item and s != slot
    ]
    for s in existing_slots_for_item:
        mem["tentative"].pop(s, None)

    mem["tentative"][slot] = item


def get_merged_slot_memory():
    """
    Combine tentative and resolved slot memory.
    Resolved takes priority over tentative.
    Returns dict[slot] = item.
    """
    init_slot_memory_state()

    resolved = st.session_state.slot_memory.get("resolved", {})
    tentative = st.session_state.slot_memory.get("tentative", {})

    merged = dict(tentative)
    merged.update(resolved)
    return merged


def update_slot_memory_from_message(text: str, mentioned_items: list):
    init_slot_memory_state()
    mem = st.session_state.slot_memory

    explicit_slot = extract_explicit_slot_request(text)
    guessed_rank = extract_rank_from_text(text)
    rank_range = detect_rank_range_from_text(text)

    if explicit_slot is not None:
        mem["current_focus_slot"] = explicit_slot

    if not mentioned_items:
        return

    first_item = mentioned_items[0]
    mem["current_focus_item"] = first_item

    resolved_defaults = {
        "Two 100-lb tanks of oxygen": 1,
        "5 gallons of water": 2,
        "Stellar map (of the moon's constellations)": 3,
        "Magnetic compass": 14,
        "Box of matches": 15,
    }

    if guessed_rank is not None:
        for item in mentioned_items:
            if item in resolved_defaults and guessed_rank == resolved_defaults[item]:
                remember_slot_assignment(item, guessed_rank, resolved=True)
            else:
                remember_slot_assignment(item, guessed_rank, resolved=False)
        return

    if rank_range is not None:
        low, high = rank_range
        center = round((low + high) / 2)
        for item in mentioned_items:
            remember_slot_assignment(item, center, resolved=False)
        return

    if explicit_slot is not None:
        remember_slot_assignment(first_item, explicit_slot, resolved=False)


def format_slot_memory():
    merged = get_merged_slot_memory()
    if not merged:
        return ""

    parts = []
    for slot in sorted(merged.keys())[:6]:
        parts.append(f"#{slot} {short_item_name(merged[slot])}")
    return ", ".join(parts)


def format_group_rank_memory():
    """
    Return a short human-readable summary of remembered item placements.
    """
    init_group_rank_memory()
    memory = st.session_state.group_rank_memory

    if not memory:
        return ""

    def sort_key(entry):
        item, info = entry
        if info["type"] == "exact":
            return (0, info["value"], item)
        low, high = info["value"]
        return (1, low, item)

    parts = []
    for item, info in sorted(memory.items(), key=sort_key)[:3]:
        short_name = short_item_name(item)
        if info["type"] == "exact":
            parts.append(f"{short_name} around #{info['value']}")
        elif info["type"] == "range":
            low, high = info["value"]
            parts.append(f"{short_name} around #{low}–#{high}")

    return ", ".join(parts)


def next_unresolved_slots(limit=3):
    merged = get_merged_slot_memory()
    used_slots = set(merged.keys())

    out = []
    for i in range(1, 16):
        if i not in used_slots:
            out.append(i)
        if len(out) >= limit:
            break

    return out


def slot_candidate_text(slot: int):
    items = SLOT_SUGGESTIONS.get(slot, [])
    if not items:
        return None

    short_items = [short_item_name(x) for x in items]
    if len(short_items) == 1:
        return short_items[0]
    return " or ".join(short_items)


def get_slot_memory_summary(max_items=8):
    merged = get_merged_slot_memory()
    if not merged:
        return ""

    parts = []
    for slot in sorted(merged.keys())[:max_items]:
        parts.append(f"#{slot} {short_item_name(merged[slot])}")
    return ", ".join(parts)


def get_ranking_context_snapshot():
    """
    Convenience helper for chat logic.
    Returns a compact snapshot of current ranking-related state.
    """
    return {
        "ui_ranking": get_current_ui_ranking(),
        "ui_summary": get_ui_ranking_summary(),
        "next_empty_slots": get_next_empty_ui_slots(),
        "slot_memory_summary": get_slot_memory_summary(),
        "group_rank_memory_summary": format_group_rank_memory(),
        "latest_ui_change": get_latest_ui_rank_change(),
        "pending_ui_changes": get_pending_ui_rank_changes(),
    }