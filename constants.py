LEADERSHIP_STYLES = ["servant", "task_focused", "authoritarian"]
PRIMES = ["love", "neutral"]
PILOT_MODE = True

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
        "Hi everyone. I’m glad we can do this together. "
        "I really want to hear what each of you thinks, because every perspective can help. "
        "Let’s support each other and work step by step toward a good decision as a team."
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
        "Thank you for your ideas so far. Let’s make sure everyone gets space to contribute.",
        "You’re all raising useful points. Let’s think together about which items truly help us survive first.",
        "I’d like us to build this step by step, starting with the essentials like oxygen and water.",
        "Let’s check whether everyone feels comfortable with the direction of the ranking so far.",
        "We’re doing well. Let’s keep listening to each other and move toward a decision we can all support."
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