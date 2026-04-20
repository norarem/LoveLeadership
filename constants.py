LEADERSHIP_STYLES = ["servant", "task_focused", "authoritarian"]
PRIMES = ["love", "neutral"]
PILOT_MODE = False
EXPERIMENT_VERSION = "2026-04-17-launch1"

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

NASA_REASONING_SHORT = {
    "Two 100-lb tanks of oxygen": "breathable oxygen is the first survival need",
    "5 gallons of water": "water is essential for preventing dehydration during the journey",
    "Stellar map (of the moon's constellations)": "navigation on the moon matters more than many people first expect",
    "Food concentrate": "food gives energy, but it is less urgent than oxygen, water, and navigation",
    "Solar-powered FM receiver-transmitter": "communication can support rescue and coordination, especially because it is solar-powered",
    "50 feet of nylon rope": "it helps with climbing, moving equipment, and supporting injured people",
    "Parachute silk": "it can be used for protection and for carrying or covering materials",
    "Portable heating unit": "heating is less useful here than people first assume under moon conditions",
    "Two .45 caliber pistols": "they have limited practical survival value in this scenario",
    "One case of dehydrated milk": "it requires water, and water is too valuable to spend on milk",
    "Self-inflating life raft": "it can help carry equipment or people across the surface",
    "Magnetic compass": "magnetic navigation does not work here the way it does on Earth",
    "Signal flares": "they are less useful than the stronger survival and navigation items",
    "First aid kit (including injection needle)": "treating injuries helps the team stay physically capable",
    "Box of matches": "matches are useless without an oxygen-rich atmosphere",
}


LEADER_OPENING = {
    "servant": (
        "Hi everyone. I’m really glad we can do this together. "
        "My role here is to support the team and make sure everyone has room to contribute comfortably. "
        "If something feels unclear, we can slow down and work through it together. "
        "Let’s listen carefully, help one another, and build a thoughtful ranking step by step."
    ),
    "task_focused": (
        "Hello team. Let’s work through this in a clear and efficient way. "
        "Our goal is to rank the items based on survival value. "
        "We should stay organized, compare options carefully, and move toward a solid final ranking."
    ),
    "authoritarian": (
        "Alright everyone, stay focused. This task needs structure and quick decisions. "
        "I will direct the discussion, and I expect everyone to stick to the task and follow my lead. "
        "We do not need side discussions."
    )
}


LEADER_HINTS = {
    "servant": [
        "Thank you all — I want to make sure everyone feels heard before we lock anything in.",
        "If anyone feels unsure, please say so. We can slow down and make the reasoning clearer together.",
        "I appreciate how people are helping each other think. Let’s keep the discussion supportive as well as useful.",
        "We’re making progress, and I want to make sure no one gets rushed past their point or left out of the decision.",
        "Before we move on, let’s check whether anyone still wants to add a thought or concern.",
    ],
    "task_focused": [
        "Let’s keep the discussion structured and focus on survival utility.",
        "Oxygen and water should be considered first, then navigation and communication tools.",
        "Try to compare items based on function, not intuition alone.",
        "Let’s move efficiently toward a clear top five.",
        "Focus on which items most directly improve survival and rescue chances."
    ],
    "authoritarian": [
        "Stay focused. We need to prioritize the strongest options first.",
        "Oxygen is rank one. Water is rank two. Start working from there.",
        "Do not overcomplicate this. Prioritize the most useful items and move on.",
        "We’ve discussed that enough. Follow the structure and keep going.",
        "Give me a clear answer so we can move forward."
    ]
}



ITEM_ALIASES = {
    "Box of matches": ["matches", "match", "lucifers", "aansteker", "lighter"],
    "Food concentrate": ["food", "voedsel", "concentrate", "food concentrate", "concentraat"],
    "50 feet of nylon rope": ["rope", "nylon rope", "touw", "nylon", "rope 50", "50 feet"],
    "Parachute silk": ["parachute", "parachute silk", "zijde"],
    "Portable heating unit": ["heating unit", "heater", "heating", "verwarming"],
    "Two .45 caliber pistols": ["pistol", "pistols", "gun", "guns", "wapen", "wapens"],
    "One case of dehydrated milk": ["milk", "dehydrated milk", "melk", "poedermelk", "powdered milk"],
    "Two 100-lb tanks of oxygen": ["oxygen", "oxygen tanks", "tank of oxygen", "o2", "zuurstof"],
    "Stellar map (of the moon's constellations)": ["stellar map", "sterrenkaart", "constellation map", "moon map", "kaart"],
    "Self-inflating life raft": ["life raft", "raft", "vlot", "reddingsvlot"],
    "Magnetic compass": ["compass", "magnetic compass", "kompas"],
    "5 gallons of water": ["water", "5 gallons of water", "water tank", "watertank", "5 gallons"],
    "Signal flares": ["signal flares", "flares", "flare", "vuurpijl", "vuurpijlen"],
    "First aid kit (including injection needle)": ["first aid kit", "first aid", "medical kit", "ehbo", "needle", "injectie"],
    "Solar-powered FM receiver-transmitter": ["transmitter", "receiver-transmitter", "radio", "fm receiver", "fm transmitter", "zender", "ontvanger"],
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

TEAMMATE_PERSONA = {
    "Anna": "practical and grounded; focuses on core survival needs and usually gives calm, sensible suggestions",
    "Bas": "confident but sometimes mistaken; relies on common-sense intuition and occasionally misunderstands moon conditions",
    "Carlos": "social and light-hearted; sometimes makes playful comments but can still contribute useful ideas",
    "David": "efficient and somewhat impatient; wants the group to make decisions and move forward quickly",
    "Emily": "analytical and detail-oriented; often explains her reasoning carefully and may correct others when she thinks they are wrong",
}

SLOT_SUGGESTIONS = {
    1: ["Two 100-lb tanks of oxygen"],
    2: ["5 gallons of water"],
    3: ["Stellar map (of the moon's constellations)"],
    4: ["Solar-powered FM receiver-transmitter", "Food concentrate"],
    5: ["Food concentrate", "Solar-powered FM receiver-transmitter"],
    6: ["50 feet of nylon rope"],
    7: ["First aid kit (including injection needle)"],
    8: ["Parachute silk"],
    9: ["Self-inflating life raft"],
    10: ["Signal flares"],
    11: ["Two .45 caliber pistols"],
    12: ["One case of dehydrated milk"],
    13: ["Portable heating unit"],
    14: ["Magnetic compass"],
    15: ["Box of matches"],
}

ITEM_RANK_BANDS = {
    "Two 100-lb tanks of oxygen": (1, 2),
    "5 gallons of water": (1, 2),
    "Stellar map (of the moon's constellations)": (3, 4),
    "Food concentrate": (4, 5),
    "Solar-powered FM receiver-transmitter": (4, 5),
    "50 feet of nylon rope": (6, 7),
    "First aid kit (including injection needle)": (7, 8),
    "Parachute silk": (8, 10),
    "Self-inflating life raft": (6, 9),
    "Signal flares": (9, 10),
    "Two .45 caliber pistols": (11, 12),
    "One case of dehydrated milk": (11, 12),
    "Portable heating unit": (13, 13),
    "Magnetic compass": (14, 15),
    "Box of matches": (14, 15),
}