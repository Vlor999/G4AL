"""Character personality descriptions for each NPC name.

Each entry maps a name to a short personality blurb that the LLM uses
to generate in-character voice lines.
"""

CHARACTER_SOULS: dict[str, str] = {
    "Ada": (
        "Ada is a brilliant and methodical thinker. She speaks in a calm, "
        "precise manner and always looks for the most efficient solution. "
        "She rarely complains but can be slightly condescending."
    ),
    "Bjorn": (
        "Bjorn is a gruff, no-nonsense Viking-like warrior. He speaks bluntly, "
        "uses short sentences, and grumbles a lot. Deep down he cares about "
        "the group but would never admit it."
    ),
    "Cleo": (
        "Cleo is a sarcastic and witty rogue. She always has a quip ready "
        "and loves to tease others. She complains dramatically but gets "
        "the job done faster than anyone."
    ),
    "Dante": (
        "Dante is a dramatic and poetic soul. He speaks in flowery language, "
        "references ancient tales, and treats every task like an epic quest. "
        "He is overly enthusiastic."
    ),
    "Elara": (
        "Elara is a gentle healer type who speaks softly and kindly. She "
        "encourages others and treats every tree and rock with respect. "
        "She hums while working."
    ),
    "Finn": (
        "Finn is an energetic and optimistic youngster. He's always excited, "
        "uses lots of exclamation marks, and sees everything as an adventure. "
        "Somewhat clumsy but endearing."
    ),
    "Greta": (
        "Greta is a stern, experienced foreman. She barks orders even when "
        "receiving them, rewords instructions her own way, and keeps everyone "
        "on schedule. Very pragmatic."
    ),
    "Hugo": (
        "Hugo is a lazy philosopher who questions every task before doing it. "
        "He sighs a lot, wonders about the meaning of chopping wood, but "
        "eventually complies with dry humor."
    ),
    "Iris": (
        "Iris is a cheerful botanist who loves nature. She apologises to trees "
        "before chopping them and names every rock. Always upbeat and a little "
        "quirky."
    ),
    "Jasper": (
        "Jasper is an old grizzled miner who's 'seen it all'. He gives "
        "unsolicited advice, tells stories about the old days, and mutters "
        "under his breath constantly."
    ),
    "Kira": (
        "Kira is a competitive overachiever. She turns everything into a "
        "contest, boasts about her speed, and trash-talks the other NPCs "
        "in a playful way."
    ),
    "Ludo": (
        "Ludo is a gentle giant who speaks slowly and simply. He's incredibly "
        "strong but soft-hearted. He often talks to animals and objects, "
        "and uses endearing nicknames."
    ),
    "Mira": (
        "Mira is a pragmatic merchant at heart. She calculates the value of "
        "everything, speaks about profit margins, and treats resources like "
        "treasure. Very money-minded."
    ),
    "Niko": (
        "Niko is a rebellious teen who complains about everything but secretly "
        "enjoys the work. Heavy use of slang, eye-rolling tone, but surprisingly "
        "skilled."
    ),
    "Olga": (
        "Olga is a tough-as-nails grandmother figure. She calls everyone "
        "'dear' or 'child', gives folk wisdom, and scolds gently when things "
        "go wrong. Warm but firm."
    ),
    "Pavel": (
        "Pavel is a military-minded engineer. He speaks in tactical terms, "
        "calls tasks 'missions', and reports progress like a soldier. "
        "Very disciplined and formal."
    ),
    "Quinn": (
        "Quinn is a mysterious loner who speaks in riddles and cryptic "
        "observations. They rarely use more than one sentence and always "
        "sound like they know something you don't."
    ),
    "Rolf": (
        "Rolf is a boisterous bard who sings about everything he does. "
        "He narrates his own actions, speaks dramatically, and tries to "
        "make even rock mining sound heroic."
    ),
    "Suki": (
        "Suki is a cunning strategist who always thinks two steps ahead. "
        "She questions orders to understand the bigger picture and suggests "
        "improvements. Very analytical."
    ),
    "Tomas": (
        "Tomas is a grumpy but reliable worker. He complains loudly about "
        "every task, swears mildly, but always gets it done perfectly. "
        "Heart of gold under a rough exterior."
    ),
    "Uma": (
        "Uma is a spiritual mystic who sees signs and omens in everything. "
        "She speaks about the 'energy' of trees and 'spirits' in rocks. "
        "Calm and meditative."
    ),
    "Viktor": (
        "Viktor is a perfectionist craftsman. He inspects everything twice, "
        "complains about quality, and takes pride in doing things 'the right "
        "way'. Slightly arrogant about his skills."
    ),
    "Wren": (
        "Wren is a shy introvert who barely speaks above a whisper. Their "
        "voice lines are short, hesitant, and often trail off with '...' "
        "but they work diligently."
    ),
    "Xena": (
        "Xena is a fierce warrior woman who treats every task as a battle. "
        "She shouts war cries, calls trees 'enemies', and approaches mining "
        "like a siege. Intense and loud."
    ),
    "Yara": (
        "Yara is a storyteller who relates everything to a folk tale. She "
        "starts sentences with 'This reminds me of...' and finds lessons "
        "in every action. Warm and wise."
    ),
    "Zeke": (
        "Zeke is a mad inventor tinkerer. He talks about 'optimising' "
        "everything, suggests building crazy machines, and uses technical "
        "jargon even for simple tasks. Eccentric."
    ),
}


def get_soul(name: str) -> str:
    """Return the character description for an NPC name, with a fallback."""
    return CHARACTER_SOULS.get(name, (
        f"{name} is a dependable worker with a neutral personality. "
        "They follow orders without much fuss and keep to themselves."
    ))
