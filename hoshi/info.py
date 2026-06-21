"""Astrological reference data — keywords and interpretive meanings."""

from pydantic import BaseModel


class Info(BaseModel, frozen=True):
    name: str
    keywords: list[str]
    meaning: str
    aliases: list[str] = []


class SignInfo(Info, frozen=True):
    element: str
    modality: str
    ruler: str


PLANETS: dict[str, Info] = {
    "Sun": Info(
        name="Sun",
        keywords=["identity", "ego", "vitality", "purpose", "will"],
        meaning=(
            "The Sun represents the core self — your fundamental identity, conscious will, and "
            "creative life force. It shows what you are becoming and where you seek to shine. "
            "The Sun's sign and house placement describe the central themes of your personality, "
            "your sense of purpose, and the kind of experiences that make you feel most alive."
        ),
    ),
    "Moon": Info(
        name="Moon",
        keywords=["emotions", "instincts", "nurturing", "memory", "comfort"],
        meaning=(
            "The Moon governs your emotional inner world — your instinctive reactions, deepest "
            "needs, and habitual patterns. It reflects how you nurture and want to be nurtured, "
            "your relationship to the past and to home, and the unconscious undercurrent that "
            "shapes your moods. Because it moves roughly 13 degrees per day, the Moon's sign "
            "is particularly sensitive to birth time accuracy."
        ),
    ),
    "Mercury": Info(
        name="Mercury",
        keywords=["communication", "intellect", "perception", "learning", "travel"],
        meaning=(
            "Mercury rules the mind's everyday machinery — how you think, speak, write, and "
            "process information. It governs short journeys, commerce, and the connective tissue "
            "between ideas. Mercury's sign colors your communication style and learning approach, "
            "while its house shows the life area where your mental energy is most engaged."
        ),
    ),
    "Venus": Info(
        name="Venus",
        keywords=["love", "beauty", "values", "pleasure", "harmony"],
        meaning=(
            "Venus describes what you find attractive and how you attract. It governs love, "
            "aesthetics, comfort, and the things you value enough to draw toward you. In a chart, "
            "Venus reveals your relationship style, artistic sensibility, and the kinds of "
            "pleasures and social connections that bring you contentment."
        ),
    ),
    "Mars": Info(
        name="Mars",
        keywords=["drive", "aggression", "energy", "desire", "courage"],
        meaning=(
            "Mars is the planet of action and assertion — your raw drive, competitive instinct, "
            "and physical energy. It shows how you pursue what you want, how you handle conflict, "
            "and where you're willing to fight. Mars' sign shapes your style of taking initiative, "
            "while its house points to the arena where you expend the most effort."
        ),
    ),
    "Jupiter": Info(
        name="Jupiter",
        keywords=["expansion", "abundance", "wisdom", "optimism", "growth"],
        meaning=(
            "Jupiter is the principle of expansion and faith. It represents where life feels "
            "generous — your capacity for growth, higher learning, philosophical outlook, and "
            "good fortune. Jupiter's placement shows where you naturally seek meaning and where "
            "excess is also a risk, since its gifts can encourage overextension."
        ),
    ),
    "Saturn": Info(
        name="Saturn",
        keywords=["structure", "discipline", "responsibility", "limits", "mastery"],
        meaning=(
            "Saturn represents structure, time, and the boundaries that give life its shape. "
            "It governs discipline, duty, and the hard-won lessons that come through persistence "
            "and limitation. Where Saturn sits in a chart marks the area of life that demands the "
            "most maturity and effort, but also promises the deepest lasting achievement."
        ),
    ),
    "Uranus": Info(
        name="Uranus",
        keywords=["rebellion", "innovation", "freedom", "disruption", "awakening"],
        meaning=(
            "Uranus is the planet of sudden change and liberation. It breaks patterns, introduces "
            "the unexpected, and drives the impulse toward individuality and reform. Its sign "
            "colors a generation's style of revolution, while its house placement shows where "
            "you personally crave freedom and resist convention."
        ),
    ),
    "Neptune": Info(
        name="Neptune",
        keywords=[
            "imagination",
            "spirituality",
            "illusion",
            "compassion",
            "transcendence",
        ],
        meaning=(
            "Neptune dissolves boundaries between the real and the imagined. It governs dreams, "
            "intuition, spirituality, and the longing for something beyond ordinary reality. "
            "Positively expressed, Neptune brings creativity, empathy, and mystical awareness; "
            "under stress, it can manifest as confusion, escapism, or deception."
        ),
    ),
    "Pluto": Info(
        name="Pluto",
        keywords=["transformation", "power", "intensity", "regeneration", "shadow"],
        meaning=(
            "Pluto governs the deep forces of transformation — death and rebirth, hidden power, "
            "and the psychological underworld. It exposes what is buried and demands that it be "
            "confronted. Pluto's house placement marks where you undergo the most profound and "
            "sometimes painful evolution, emerging fundamentally changed."
        ),
    ),
    "Chiron": Info(
        name="Chiron",
        keywords=["wound", "healing", "wisdom", "mentorship", "vulnerability"],
        meaning=(
            "Chiron, the 'wounded healer,' points to a core vulnerability that becomes a source "
            "of wisdom and compassion. Its placement reveals where you carry a deep hurt that "
            "resists easy resolution, yet through engaging with that pain, you develop the "
            "ability to guide and heal others in the same area."
        ),
    ),
}

SIGNS: dict[str, SignInfo] = {
    "Aries": SignInfo(
        name="Aries",
        element="Fire",
        modality="Cardinal",
        ruler="Mars",
        keywords=[
            "initiative",
            "courage",
            "independence",
            "impulsiveness",
            "pioneering",
        ],
        meaning=(
            "Aries is the spark of initiation — bold, direct, and eager to act. It embodies the "
            "raw drive to begin, to lead, and to assert individuality. Planets in Aries express "
            "themselves with urgency and competitive fire, thriving on challenge and novelty but "
            "sometimes struggling with patience and follow-through."
        ),
    ),
    "Taurus": SignInfo(
        name="Taurus",
        element="Earth",
        modality="Fixed",
        ruler="Venus",
        keywords=[
            "stability",
            "sensuality",
            "patience",
            "determination",
            "material security",
        ],
        meaning=(
            "Taurus grounds energy into the physical world — building, preserving, and savoring "
            "what is tangible. It brings steadiness, loyalty, and an appreciation for comfort and "
            "beauty. Planets here operate with deliberate patience and endurance, though the fixed "
            "quality can tip into stubbornness or resistance to change."
        ),
    ),
    "Gemini": SignInfo(
        name="Gemini",
        element="Air",
        modality="Mutable",
        ruler="Mercury",
        keywords=["curiosity", "adaptability", "communication", "duality", "wit"],
        meaning=(
            "Gemini is the sign of the inquiring mind — versatile, sociable, and endlessly "
            "curious. It thrives on variety, conversation, and the exchange of ideas. Planets in "
            "Gemini are mentally agile and quick to connect disparate threads, though they may "
            "scatter their energy across too many interests at once."
        ),
    ),
    "Cancer": SignInfo(
        name="Cancer",
        element="Water",
        modality="Cardinal",
        ruler="Moon",
        keywords=["nurturing", "sensitivity", "protection", "home", "emotional depth"],
        meaning=(
            "Cancer initiates through feeling — creating safety, tending bonds, and honoring "
            "roots. It is deeply protective of loved ones and carries a powerful emotional memory. "
            "Planets in Cancer operate from intuition and empathy, drawing strength from "
            "belonging, though they may struggle to release the past."
        ),
    ),
    "Leo": SignInfo(
        name="Leo",
        element="Fire",
        modality="Fixed",
        ruler="Sun",
        keywords=["creativity", "confidence", "generosity", "drama", "self-expression"],
        meaning=(
            "Leo radiates warmth, pride, and a need to be seen. It is the sign of creative "
            "self-expression, loyalty, and wholehearted engagement with life. Planets in Leo "
            "perform with flair and seek recognition, bringing leadership and generosity but "
            "sometimes an oversensitivity to perceived slights."
        ),
    ),
    "Virgo": SignInfo(
        name="Virgo",
        element="Earth",
        modality="Mutable",
        ruler="Mercury",
        keywords=["analysis", "service", "precision", "humility", "craftsmanship"],
        meaning=(
            "Virgo refines and improves — applying careful analysis, practical skill, and a deep "
            "sense of service. It notices what others miss and works to make things function "
            "better. Planets in Virgo are meticulous and health-conscious, though the drive for "
            "perfection can become self-critical or anxious."
        ),
    ),
    "Libra": SignInfo(
        name="Libra",
        element="Air",
        modality="Cardinal",
        ruler="Venus",
        keywords=["balance", "partnership", "diplomacy", "aesthetics", "justice"],
        meaning=(
            "Libra initiates through relationship — seeking harmony, fairness, and the beauty "
            "that emerges when opposing forces find equilibrium. It is the sign of partnership, "
            "negotiation, and refined taste. Planets in Libra weigh options carefully and value "
            "cooperation, sometimes at the cost of decisiveness."
        ),
    ),
    "Scorpio": SignInfo(
        name="Scorpio",
        element="Water",
        modality="Fixed",
        ruler="Pluto",
        keywords=["intensity", "depth", "secrecy", "transformation", "resilience"],
        meaning=(
            "Scorpio probes beneath the surface — seeking truth, power, and emotional honesty "
            "at any cost. It possesses extraordinary resilience and the ability to transform "
            "through crisis. Planets in Scorpio operate with penetrating focus and fierce loyalty, "
            "but can become controlling or consumed by suspicion."
        ),
    ),
    "Ophiuchus": SignInfo(
        name="Ophiuchus",
        element="Water",
        modality="Fixed",
        ruler="Chiron",
        keywords=["healing", "wisdom", "integration", "serpent-bearer", "liminality"],
        meaning=(
            "Ophiuchus, the serpent-bearer, is the thirteenth constellation along the ecliptic "
            "and appears only in real-sky astrology. Spanning just under seven degrees between "
            "Scorpio and Sagittarius, it carries themes of healing knowledge, the integration of "
            "opposites, and the boundary between death and renewal. Planets here suggest a "
            "calling toward deep transformation and the wisdom that comes from confronting "
            "what others avoid."
        ),
    ),
    "Sagittarius": SignInfo(
        name="Sagittarius",
        element="Fire",
        modality="Mutable",
        ruler="Jupiter",
        keywords=["exploration", "philosophy", "optimism", "freedom", "truth-seeking"],
        meaning=(
            "Sagittarius aims at the far horizon — pursuing meaning, adventure, and the big "
            "picture. It is the sign of philosophy, higher education, travel, and the quest for "
            "truth. Planets in Sagittarius are enthusiastic and forward-looking, bringing faith "
            "and humor but sometimes overcommitting or glossing over important details."
        ),
    ),
    "Capricorn": SignInfo(
        name="Capricorn",
        element="Earth",
        modality="Cardinal",
        ruler="Saturn",
        keywords=["ambition", "responsibility", "strategy", "endurance", "authority"],
        meaning=(
            "Capricorn builds toward lasting achievement — patient, strategic, and willing to "
            "accept the weight of responsibility. It respects tradition, hierarchies, and the "
            "value of time. Planets in Capricorn express themselves with pragmatic discipline "
            "and long-range vision, though they may struggle to relax or show vulnerability."
        ),
    ),
    "Aquarius": SignInfo(
        name="Aquarius",
        element="Air",
        modality="Fixed",
        ruler="Uranus",
        keywords=[
            "individuality",
            "humanitarianism",
            "innovation",
            "detachment",
            "idealism",
        ],
        meaning=(
            "Aquarius operates at the intersection of intellect and community — championing "
            "progress, originality, and the collective good. It values freedom of thought and "
            "resists conformity. Planets in Aquarius bring inventiveness and social awareness, "
            "but the fixed air quality can produce emotional detachment or contrarian rigidity."
        ),
    ),
    "Pisces": SignInfo(
        name="Pisces",
        element="Water",
        modality="Mutable",
        ruler="Neptune",
        keywords=[
            "intuition",
            "compassion",
            "imagination",
            "dissolution",
            "transcendence",
        ],
        meaning=(
            "Pisces dissolves boundaries — merging with the emotional and spiritual currents "
            "that flow beneath conscious awareness. It is the sign of empathy, artistic vision, "
            "and surrender. Planets in Pisces are sensitive and imaginative, capable of profound "
            "compassion but also vulnerable to confusion, escapism, and absorbing others' pain."
        ),
    ),
}

ANGLES: dict[str, Info] = {
    "Ascendant": Info(
        name="Ascendant",
        aliases=["asc", "rising", "rising sign"],
        keywords=[
            "self-image",
            "appearance",
            "first impression",
            "persona",
            "approach to life",
        ],
        meaning=(
            "The Ascendant (rising sign) is the zodiac degree on the eastern horizon at the "
            "moment of birth. It defines the lens through which you meet the world — your "
            "outward demeanor, physical presence, and instinctive approach to new situations. "
            "It is the cusp of the first house and the starting point of the entire house system."
        ),
    ),
    "Midheaven": Info(
        name="Midheaven",
        aliases=["mc", "medium coeli"],
        keywords=["career", "public image", "aspiration", "legacy", "authority"],
        meaning=(
            "The Midheaven (MC) marks the highest point of the ecliptic at birth and represents "
            "your public role, career direction, and reputation. It shows what you aspire to "
            "achieve and how the world sees your contributions. The MC is the cusp of the tenth "
            "house and reflects your relationship with ambition and social standing."
        ),
    ),
    "Imum Coeli": Info(
        name="Imum Coeli",
        aliases=["ic", "nadir"],
        keywords=["roots", "home", "inner foundation", "family", "private self"],
        meaning=(
            "The Imum Coeli (IC) is the lowest point of the chart, directly opposite the "
            "Midheaven. It represents your deepest roots — family of origin, psychological "
            "foundation, and the private inner life you return to for security. As the cusp of "
            "the fourth house, it anchors your sense of belonging and emotional bedrock."
        ),
    ),
    "Descendant": Info(
        name="Descendant",
        aliases=["dsc", "dc"],
        keywords=[
            "partnership",
            "projection",
            "other people",
            "relationships",
            "shadow",
        ],
        meaning=(
            "The Descendant sits directly opposite the Ascendant on the western horizon and "
            "marks the cusp of the seventh house. It describes the qualities you seek in close "
            "partnerships and the traits you tend to project onto others. It is the mirror of "
            "the self — what you are drawn toward and what you must integrate."
        ),
    ),
    "Vertex": Info(
        name="Vertex",
        keywords=[
            "fate",
            "encounters",
            "turning points",
            "destined meetings",
            "catalyst",
        ],
        meaning=(
            "The Vertex is a sensitive point on the western side of the chart, often called "
            "the 'point of fate.' It is associated with pivotal encounters and events that feel "
            "destined rather than chosen — moments where external forces redirect your path. "
            "Transits and synastry contacts to the Vertex often coincide with significant "
            "turning points."
        ),
    ),
    "Antivertex": Info(
        name="Antivertex",
        keywords=["personal agency", "self-directed change", "conscious choice"],
        meaning=(
            "The Antivertex is the point directly opposite the Vertex, falling on the eastern "
            "side of the chart. Where the Vertex marks fated encounters, the Antivertex suggests "
            "the role of personal will and conscious choice in shaping those same turning points. "
            "It is less commonly interpreted but carries the complementary theme of self-directed "
            "transformation."
        ),
    ),
}

ASPECTS: dict[str, Info] = {
    "Conjunction": Info(
        name="Conjunction (0°)",
        keywords=["fusion", "intensity", "new beginning", "focus"],
        meaning=(
            "A conjunction merges the energies of two bodies into a single concentrated force. "
            "The planets involved lose some of their separateness and operate as a blended unit, "
            "amplifying each other for better or worse. Conjunctions mark points of emphasis "
            "and fresh starts in the chart."
        ),
    ),
    "Opposition": Info(
        name="Opposition (180°)",
        keywords=["polarity", "awareness", "tension", "projection", "integration"],
        meaning=(
            "An opposition places two bodies across the chart from each other, creating a "
            "dynamic tension that demands awareness and balance. Each side tends to project its "
            "qualities onto the other. The challenge is integration — finding a working dialogue "
            "between two competing needs rather than swinging between extremes."
        ),
    ),
    "Trine": Info(
        name="Trine (120°)",
        keywords=["harmony", "ease", "flow", "talent", "support"],
        meaning=(
            "A trine connects bodies in signs of the same element, producing a natural flow of "
            "energy that feels easy and supportive. Trines represent innate talents and areas "
            "where life cooperates without much effort. The risk is complacency — gifts that are "
            "never developed because they never had to be."
        ),
    ),
    "Square": Info(
        name="Square (90°)",
        keywords=["friction", "challenge", "motivation", "growth", "crisis"],
        meaning=(
            "A square creates a hard angle of tension between two bodies, generating friction "
            "that demands action. Squares are the engine of growth in a chart — they provoke "
            "crises that force development. The energy is difficult but productive, pushing you "
            "to overcome obstacles that would otherwise go unaddressed."
        ),
    ),
    "Sextile": Info(
        name="Sextile (60°)",
        keywords=["opportunity", "cooperation", "communication", "stimulation"],
        meaning=(
            "A sextile links bodies in compatible elements, offering opportunities that require "
            "a modest effort to activate. It is gentler than a trine — less automatic but also "
            "less passive. Sextiles encourage dialogue, creative exchange, and productive "
            "collaboration between the energies involved."
        ),
    ),
    "Inconjunct": Info(
        name="Inconjunct (150°)",
        aliases=["quincunx"],
        keywords=["adjustment", "discomfort", "recalibration", "health", "blind spot"],
        meaning=(
            "An inconjunct (quincunx) connects signs that share neither element nor modality, "
            "producing a persistent sense of misalignment. The two energies don't oppose or "
            "support each other — they simply don't relate, requiring continuous adjustment. "
            "Inconjuncts often surface as health issues or nagging dissatisfaction that resist "
            "easy fixes."
        ),
    ),
    "Semi-sextile": Info(
        name="Semi-sextile (30°)",
        keywords=[
            "irritation",
            "subtle growth",
            "adjacent signs",
            "incremental change",
        ],
        meaning=(
            "A semi-sextile links adjacent signs, creating a mild friction between energies that "
            "are close in the zodiac but fundamentally different in element and modality. It is "
            "a quiet aspect — easy to overlook — but it drives slow, incremental development as "
            "the two sides learn to coexist."
        ),
    ),
    "Semi-square": Info(
        name="Semi-square (45°)",
        keywords=["agitation", "minor friction", "restlessness", "internal tension"],
        meaning=(
            "A semi-square is a minor hard aspect that creates low-grade irritation and "
            "restlessness. It lacks the dramatic force of a square but produces a persistent "
            "inner tension that nudges you toward action. Semi-squares often manifest as nagging "
            "dissatisfaction that motivates small but meaningful changes."
        ),
    ),
    "Sesquiquadrate": Info(
        name="Sesquiquadrate (135°)",
        aliases=["sesquisquare"],
        keywords=["frustration", "external friction", "adjustment", "agitation"],
        meaning=(
            "A sesquiquadrate (sesquisquare) is the complement of the semi-square, sitting at "
            "135 degrees. It produces frustration that tends to manifest externally — friction "
            "with circumstances or other people. Like its smaller counterpart, it drives "
            "adjustment and course correction through persistent discomfort."
        ),
    ),
    "Quintile": Info(
        name="Quintile (72°)",
        keywords=["creativity", "talent", "unique gift", "style"],
        meaning=(
            "A quintile divides the circle by five and is associated with creative talent and "
            "unique personal style. It is a minor aspect that reveals where you have a special "
            "knack or artistic gift that doesn't fit neatly into conventional categories. "
            "Quintiles suggest an ability to create something original from the energies involved."
        ),
    ),
    "Bi-quintile": Info(
        name="Bi-quintile (144°)",
        keywords=["creative mastery", "refinement", "expression", "developed talent"],
        meaning=(
            "A bi-quintile is the second harmonic of the quintile series, carrying similar themes "
            "of creative talent but with a more developed and refined quality. Where the quintile "
            "points to raw creative potential, the bi-quintile suggests a skill that has been "
            "consciously shaped and integrated into self-expression."
        ),
    ),
    "Septile": Info(
        name="Septile (51.4°)",
        keywords=["fate", "spiritual pattern", "irrational", "sacred geometry"],
        meaning=(
            "A septile divides the circle by seven and is the most esoteric of the commonly "
            "tracked aspects. It suggests a fated or spiritually patterned connection between "
            "the bodies involved — something that operates outside rational control. Septiles "
            "are associated with inspiration, compulsion, and the sense that certain experiences "
            "are part of a larger design."
        ),
    ),
}

HOUSES: dict[int, Info] = {
    1: Info(
        name="1st House",
        keywords=["self", "identity", "body", "appearance", "beginnings"],
        meaning=(
            "The first house is the house of self — your physical body, personal identity, and "
            "the way you initiate contact with the world. Planets here strongly color your "
            "personality and are immediately visible to others. It is the most personal house, "
            "setting the tone for the entire chart."
        ),
    ),
    2: Info(
        name="2nd House",
        keywords=["resources", "money", "values", "self-worth", "possessions"],
        meaning=(
            "The second house governs personal resources — money, possessions, and what you "
            "value enough to hold onto. It also reflects your sense of self-worth and the "
            "relationship between material security and inner stability. Planets here shape "
            "your earning style and your attachment to the tangible."
        ),
    ),
    3: Info(
        name="3rd House",
        keywords=[
            "communication",
            "siblings",
            "local travel",
            "learning",
            "perception",
        ],
        meaning=(
            "The third house rules everyday communication, short journeys, and the immediate "
            "environment — siblings, neighbors, and early education. It describes how your mind "
            "works at the practical level: how you gather information, articulate ideas, and "
            "navigate your local world."
        ),
    ),
    4: Info(
        name="4th House",
        keywords=["home", "family", "roots", "foundation", "inner life"],
        meaning=(
            "The fourth house is the foundation of the chart — home, family of origin, and your "
            "deepest private self. It represents where you come from and the psychological "
            "ground you stand on. Planets here speak to your relationship with ancestry, "
            "domestic life, and the emotional security you need to function."
        ),
    ),
    5: Info(
        name="5th House",
        keywords=["creativity", "romance", "children", "play", "self-expression"],
        meaning=(
            "The fifth house is the house of creative joy — romance, children, artistic "
            "expression, and anything you do for the pleasure of doing it. It governs risk-taking "
            "in the name of self-expression and the things you create that carry your personal "
            "stamp. Planets here amplify your need for play and recognition."
        ),
    ),
    6: Info(
        name="6th House",
        keywords=["work", "health", "routine", "service", "craftsmanship"],
        meaning=(
            "The sixth house governs daily work, health habits, and acts of service. It is less "
            "about career ambition (that's the tenth) and more about the discipline of showing "
            "up — the routines, skills, and maintenance tasks that keep life functioning. Planets "
            "here shape your work ethic, relationship to your body, and attitude toward duty."
        ),
    ),
    7: Info(
        name="7th House",
        keywords=["partnership", "marriage", "contracts", "open enemies", "the other"],
        meaning=(
            "The seventh house sits opposite the first and governs one-to-one partnerships — "
            "romantic, business, and legal. It describes what you seek in a partner and the "
            "qualities you project onto others. Traditionally it also rules open adversaries: "
            "anyone you meet face to face as an equal, whether in alliance or opposition."
        ),
    ),
    8: Info(
        name="8th House",
        keywords=[
            "transformation",
            "shared resources",
            "intimacy",
            "death",
            "the occult",
        ],
        meaning=(
            "The eighth house plunges into shared power — joint finances, inheritance, sexuality, "
            "and psychological transformation. It governs what is hidden and what must be "
            "surrendered. Planets here encounter themes of trust, control, loss, and the "
            "regeneration that follows. It is one of the most intense houses in the chart."
        ),
    ),
    9: Info(
        name="9th House",
        keywords=["philosophy", "higher education", "travel", "law", "meaning"],
        meaning=(
            "The ninth house expands the mind beyond the local and the familiar — higher "
            "education, long-distance travel, religion, philosophy, and the search for meaning. "
            "It governs your worldview and your relationship to belief systems. Planets here "
            "drive the need to explore, teach, publish, or find a guiding truth."
        ),
    ),
    10: Info(
        name="10th House",
        keywords=["career", "reputation", "public role", "achievement", "authority"],
        meaning=(
            "The tenth house crowns the chart and represents your public life — career, "
            "reputation, and the legacy you build in the world. It describes your relationship "
            "to authority (both wielding it and answering to it) and the kind of achievement "
            "that matters most to you. Planets here are visible and consequential."
        ),
    ),
    11: Info(
        name="11th House",
        keywords=["community", "friends", "ideals", "groups", "future vision"],
        meaning=(
            "The eleventh house governs your wider social circle — friends, groups, networks, "
            "and shared ideals. It represents the communities you belong to and the hopes and "
            "wishes that connect you to something larger than yourself. Planets here shape your "
            "social style and your vision of the future you want to help create."
        ),
    ),
    12: Info(
        name="12th House",
        keywords=[
            "solitude",
            "the unconscious",
            "hidden enemies",
            "spirituality",
            "surrender",
        ],
        meaning=(
            "The twelfth house is the most hidden part of the chart — the realm of the "
            "unconscious, solitude, and experiences that dissolve the ego. It governs "
            "confinement, secrets, self-undoing, and spiritual transcendence. Planets here "
            "operate behind the scenes, often manifesting as blind spots, hidden strengths, or "
            "a pull toward retreat and inner work."
        ),
    ),
}

POINTS: dict[str, Info] = {
    "N.Node": Info(
        name="North Node",
        aliases=["n.node", "north node", "rahu", "dragon's head"],
        keywords=[
            "destiny",
            "growth direction",
            "soul purpose",
            "unfamiliar territory",
        ],
        meaning=(
            "The North Node of the Moon points toward the qualities and experiences you are "
            "growing into in this lifetime. It represents your evolutionary direction — the "
            "unfamiliar territory that challenges you but ultimately fulfills your potential. "
            "Its sign and house describe the themes you are meant to develop."
        ),
    ),
    "S.Node": Info(
        name="South Node",
        aliases=["s.node", "south node", "ketu", "dragon's tail"],
        keywords=["past patterns", "comfort zone", "innate skills", "release"],
        meaning=(
            "The South Node sits opposite the North Node and represents the qualities you "
            "arrive with — talents, habits, and default patterns from the past. It is your "
            "comfort zone, and while its gifts are real, over-reliance on them can stall growth. "
            "The South Node shows what you are learning to release or rebalance."
        ),
    ),
    "Lilith": Info(
        name="Black Moon Lilith",
        aliases=["lilith", "bml", "black moon"],
        keywords=["raw instinct", "exile", "taboo", "autonomy", "primal feminine"],
        meaning=(
            "Black Moon Lilith is the lunar apogee — the point where the Moon is farthest from "
            "Earth. It represents the wild, undomesticated part of the psyche: instincts that "
            "refuse to conform, desires that have been shamed or exiled, and the fierce autonomy "
            "that emerges when you stop seeking approval. Its sign and house show where you "
            "confront taboo and reclaim what was denied."
        ),
    ),
    "Fortune": Info(
        name="Lot of Fortune",
        aliases=["fortune", "part of fortune", "lot of fortune"],
        keywords=["luck", "material well-being", "body", "flow", "circumstances"],
        meaning=(
            "The Lot of Fortune (Part of Fortune) synthesizes the Sun, Moon, and Ascendant "
            "into a single point that indicates where worldly luck and material well-being "
            "flow most naturally. It is traditionally associated with the body, health, and "
            "the circumstances that arise without deliberate effort."
        ),
    ),
    "Spirit": Info(
        name="Lot of Spirit",
        aliases=["spirit", "part of spirit", "lot of spirit"],
        keywords=["will", "intellect", "purpose", "conscious action", "soul"],
        meaning=(
            "The Lot of Spirit is the complement of the Lot of Fortune, reversing the Sun–Moon "
            "arc. Where Fortune reflects what happens to you, Spirit reflects what you choose "
            "to do — your conscious will, intellectual engagement, and sense of purpose. It "
            "points to the area of life where deliberate action is most rewarding."
        ),
    ),
    "Eros": Info(
        name="Lot of Eros",
        aliases=["eros", "lot of eros", "part of eros", "lot of love"],
        keywords=["desire", "attraction", "passion", "longing"],
        meaning=(
            "The Lot of Eros, derived from Venus, represents desire and attraction at their "
            "most personal — what pulls you toward another person or experience with magnetic "
            "intensity. Its placement highlights where erotic and aesthetic longing concentrate "
            "in the chart."
        ),
    ),
    "Necessity": Info(
        name="Lot of Necessity",
        aliases=["necessity", "lot of necessity", "part of necessity"],
        keywords=["constraint", "fate", "obligation", "unavoidable circumstances"],
        meaning=(
            "The Lot of Necessity, derived from Mercury, points to where life imposes "
            "constraints you cannot easily escape. It represents the unavoidable obligations "
            "and fated circumstances that shape your path regardless of personal preference — "
            "the things you must deal with rather than choose."
        ),
    ),
    "Courage": Info(
        name="Lot of Courage",
        aliases=["courage", "lot of courage", "part of courage", "lot of boldness"],
        keywords=["bravery", "daring", "assertion", "confrontation"],
        meaning=(
            "The Lot of Courage, derived from Mars, shows where boldness and confrontation "
            "are called for in your life. It highlights the arena where you must take risks, "
            "assert yourself, and face opposition directly in order to move forward."
        ),
    ),
    "Victory": Info(
        name="Lot of Victory",
        aliases=["victory", "lot of victory", "part of victory"],
        keywords=["success", "achievement", "recognition", "triumph"],
        meaning=(
            "The Lot of Victory, derived from Jupiter, indicates where success, public "
            "recognition, and triumph are most available. It points to the life area where "
            "sustained effort is most likely to be rewarded with lasting achievement and "
            "the respect of others."
        ),
    ),
    "Nemesis": Info(
        name="Lot of Nemesis",
        aliases=[
            "nemesis",
            "lot of nemesis",
            "part of nemesis",
            "discipline",
            "lot of discipline",
        ],
        keywords=["downfall", "reckoning", "enemies", "karmic consequence"],
        meaning=(
            "The Lot of Nemesis, derived from Saturn, warns of the area where overreach invites "
            "a reckoning. It represents the karmic consequence of hubris — the enemies, setbacks, "
            "and hard lessons that arise when boundaries are ignored. Understanding its placement "
            "helps you recognize where caution and humility are essential."
        ),
    ),
}
