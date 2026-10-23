"""American spelling, as a fact about the repository rather than a review note.

This lives in the engine and not in the test suite because a test can only
refuse a British spelling. The importer, which brings prose in from elsewhere,
is where one can actually be fixed -- and it cannot reach a word list that
lives in `tests/`.

Caught three times by a person before it was caught once by a machine: the
`-ise` family, then the identifier forms that `\\b` boundaries miss because `_`
is a word character, then `instalment`, which belongs to a different family
altogether (doubled consonant, not a suffix swap). A fourth time in AAC-03:
`Parameterise` and `misspelt`. Neither was in the list, which held whole
words, so every inflection had to be written out by hand and the ones nobody
wrote out went through; and `misspelt` is `spelt` behind a prefix, which `\\b`
reads as one word. The list is built from stems and endings now, and a word is
read through its prefix.
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

#: Stems that take `-ise` where American takes `-ize`, in every ending either
#: form has: `parameterise` is `parameter` and `ise`.
_ISE_STEMS = (
    "anonym", "apolog", "author", "capital", "categor", "central", "character",
    "civil", "colon", "commercial", "commodit", "computer", "conceptual",
    "container", "contextual", "critic", "custom", "democrat", "digit", "dramat",
    "econom", "emphas", "energ", "equal", "external", "familiar", "final",
    "formal", "general", "global", "harmon", "hospital", "hypothes", "ideal",
    "industrial", "initial", "institutional", "internal", "item", "legitim",
    "local", "magnet", "maxim", "mechan", "memor", "minim", "mobil", "modern",
    "monet", "monopol", "motor", "natural", "neutral", "normal", "operational",
    "optim", "organ", "parameter", "parametr", "penal", "personal", "polar",
    "popular", "pressur", "privat", "priorit", "product", "pseudonym", "public",
    "radical", "random", "rational", "real", "recogn", "sanit", "sensit",
    "serial", "social", "special", "stabil", "standard", "steril", "subsid",
    "summar", "symbol", "synchron", "synthes", "systemat", "theor", "token",
    "trivial", "util", "vapor", "virtual", "visual",
)
_ISE_ENDINGS = (
    "ise", "ised", "ises", "ising", "iser", "isers", "isable",
    "isation", "isations", "isational",
)

#: `-yse` for `-yze`. Not `-yses`: `analyses` is the plural of `analysis` in
#: both.
_YSE_STEMS = ("anal", "paral", "catal", "electrol", "dial", "hydrol")
_YSE_ENDINGS = ("yse", "ysed", "ysing", "yser", "ysers")

#: `-our` for `-or`. Not `glamour`, which American keeps.
_OUR_STEMS = (
    "ard", "arm", "behavi", "cand", "clam", "col", "endeav", "fav", "ferv",
    "flav", "harb", "hon", "hum", "lab", "neighb", "od", "parl", "rig", "rum",
    "sav", "splend", "tum", "val", "vap", "vig",
)
_OUR_ENDINGS = (
    "our", "ours", "oured", "ouring", "ourful", "ourless", "ourable",
    "ourably", "ourite", "ourites", "ourhood", "ourhoods", "oural", "ourally",
    "ourer", "ourers", "oury",
)

#: `-re` for `-er`.
_RE_STEMS = (
    "calib", "cent", "centimet", "fib", "kilomet", "lit", "lust", "meag", "met",
    "millimet", "mit", "sab", "somb", "spect", "theat",
)
_RE_ENDINGS = ("re", "res", "red", "ring")

#: The final `l` doubled where the stress is not on it. Not `control` or
#: `compel`, which American doubles too, and not `-lation`: `cancellation`
#: is American.
_LL_STEMS = (
    "bevel", "cancel", "channel", "counsel", "dial", "duel", "enamel", "equal",
    "fuel", "funnel", "grovel", "initial", "jewel", "label", "level", "libel",
    "marvel", "model", "panel", "pencil", "quarrel", "ravel", "rival", "shovel",
    "signal", "swivel", "total", "towel", "travel", "tunnel", "yodel",
)
_LL_ENDINGS = ("led", "ling", "lings", "ler", "lers", "lor", "lors")


def _families() -> Dict[str, str]:
    words = {}
    for stem in _ISE_STEMS:
        for ending in _ISE_ENDINGS:
            words[stem + ending] = stem + ending.replace("is", "iz", 1)
    for stem in _YSE_STEMS:
        for ending in _YSE_ENDINGS:
            words[stem + ending] = stem + ending.replace("ys", "yz", 1)
    for stem in _OUR_STEMS:
        for ending in _OUR_ENDINGS:
            words[stem + ending] = stem + ending.replace("our", "or", 1)
    for stem in _RE_STEMS:
        for ending in _RE_ENDINGS:
            words[stem + ending] = stem + {"re": "er", "res": "ers", "red": "ered", "ring": "ering"}[ending]
    for stem in _LL_STEMS:
        for ending in _LL_ENDINGS:
            words[stem + ending] = stem + ending[1:]
    return words


#: British forms and their American equivalents. Words that are spelled the
#: same in both (advise, precise, franchise, otherwise, analysis) are
#: deliberately absent.
BRITISH = _families()
BRITISH.update({
    # -ce nouns
    "defence": "defense", "defences": "defenses", "offence": "offense",
    "offences": "offenses", "licence": "license", "licences": "licenses",
    "pretence": "pretense", "pretences": "pretenses",
    "practise": "practice", "practised": "practiced", "practises": "practices",
    "practising": "practicing",
    # -ogue
    "catalogue": "catalog", "catalogues": "catalogs", "catalogued": "cataloged",
    "cataloguing": "cataloging", "analogue": "analog", "analogues": "analogs",
    "dialogue": "dialog", "dialogues": "dialogs",
    # a single consonant where American doubles it
    "instalment": "installment", "instalments": "installments",
    "enrolment": "enrollment", "enrolments": "enrollments",
    "fulfilment": "fulfillment", "fulfil": "fulfill", "fulfils": "fulfills",
    "enrol": "enroll", "enrols": "enrolls", "skilful": "skillful",
    "wilful": "willful", "distil": "distill", "distils": "distills",
    "instil": "instill", "instils": "instills",
    "marvellous": "marvelous", "jewellery": "jewelry", "woollen": "woolen",
    # -ae- and -oe-
    "anaemia": "anemia", "anaemic": "anemic", "anaesthesia": "anesthesia",
    "anaesthetic": "anesthetic", "anaesthetics": "anesthetics",
    "anaesthetist": "anesthetist", "anaesthetists": "anesthetists",
    "diarrhoea": "diarrhea", "encyclopaedia": "encyclopedia",
    "foetal": "fetal", "foetus": "fetus", "gynaecology": "gynecology",
    "gynaecologist": "gynecologist", "haematology": "hematology",
    "haematologist": "hematologist", "haemodialysis": "hemodialysis",
    "haemoglobin": "hemoglobin", "haemorrhage": "hemorrhage",
    "leukaemia": "leukemia", "oedema": "edema", "oesophagus": "esophagus",
    "oesophageal": "esophageal", "oestrogen": "estrogen",
    "orthopaedic": "orthopedic", "orthopaedics": "orthopedics",
    "paediatric": "pediatric", "paediatrics": "pediatrics",
    "paediatrician": "pediatrician", "paediatricians": "pediatricians",
    "manoeuvre": "maneuver", "manoeuvres": "maneuvers",
    "manoeuvred": "maneuvered", "manoeuvring": "maneuvering",
    # irregulars
    "artefact": "artifact", "artefacts": "artifacts",
    "programme": "program", "programmes": "programs",
    "storey": "story", "storeys": "stories", "cheque": "check", "cheques": "checks",
    "judgement": "judgment", "judgements": "judgments",
    "acknowledgement": "acknowledgment", "acknowledgements": "acknowledgments",
    "ageing": "aging", "sceptic": "skeptic", "sceptics": "skeptics",
    "sceptical": "skeptical", "scepticism": "skepticism",
    "grey": "gray", "greys": "grays", "greyed": "grayed", "greying": "graying",
    "greyish": "grayish", "greyscale": "grayscale",
    "speciality": "specialty", "specialities": "specialties", "aluminium": "aluminum",
    "aeroplane": "airplane", "aeroplanes": "airplanes", "cosy": "cozy",
    "kerb": "curb", "mould": "mold", "moulds": "molds", "moulded": "molded",
    "plough": "plow", "pyjamas": "pajamas", "smoulder": "smolder",
    "sulphur": "sulfur", "sulphate": "sulfate", "tyre": "tire", "tyres": "tires",
    "enquiry": "inquiry", "enquiries": "inquiries",
    "whilst": "while", "amongst": "among", "amidst": "amid",
    "afterwards": "afterward", "learnt": "learned", "burnt": "burned",
    "spelt": "spelled", "dreamt": "dreamed", "leant": "leaned",
    "spilt": "spilled", "spoilt": "spoiled",
})

#: A prefix leaves a British word British: `misspelt` is `spelt`,
#: `unrecognised` is `recognised`, `remodelled` is `modelled`.
PREFIXES = ("un", "re", "de", "dis", "mis", "pre", "non", "co", "sub", "over", "under", "inter", "multi")

#: Letters only, so `_` and digits end a word: `normalise_name` is read as
#: `normalise` and `name`, which `\\b` never did.
_WORD = re.compile(r"[A-Za-z]+")


def american(word: str) -> str:
    """The American spelling of one word, or "" when it is not British."""
    lower = word.lower()
    if lower in BRITISH:
        return BRITISH[lower]
    for prefix in PREFIXES:
        if lower.startswith(prefix) and lower[len(prefix):] in BRITISH:
            return prefix + BRITISH[lower[len(prefix):]]
    return ""


def _match_case(source: str, replacement: str) -> str:
    """Keep the shape of the word being replaced.

    `Organisation` at the start of a sentence must not come back lower case,
    and an all-caps heading must not come back mixed.
    """
    if source.isupper():
        return replacement.upper()
    if source[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


def americanize(text: str) -> str:
    """Rewrite British spellings in a piece of prose."""

    def swap(match):
        found = american(match.group(0))
        return _match_case(match.group(0), found) if found else match.group(0)

    return _WORD.sub(swap, str(text or ""))


def offences(text: str) -> List[Tuple[str, str]]:
    """Every British spelling in a piece of text, lower-cased, with its
    replacement."""
    found = {}
    for word in {w.lower() for w in _WORD.findall(text)}:
        replacement = american(word)
        if replacement:
            found[word] = replacement
    return sorted(found.items())
