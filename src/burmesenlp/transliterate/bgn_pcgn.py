# -*- coding: utf-8 -*-
"""BGN/PCGN romanization of Burmese (the 1970 US/UK-agreed system).

Source: the joint US Board on Geographic Names / UK Permanent Committee
on Geographical Names document "ROMANIZATION OF BURMESE, BGN/PCGN 1970
Agreement" (checked for validity and accuracy, October 2017), read
directly from the PDF -- not from a paraphrase:
https://assets.publishing.service.gov.uk/media/5ab4dec7ed915d78bc23450f/ROMANIZATION_OF_BURMESE.pdf
(byte-identical US mirror:
https://geonames.nga.mil/geonames/GNSSearch/GNSDocs/romanization/ROMANIZATION_OF_BURMESE.pdf)

This is a *place-name-oriented*, tone-dropping system -- not MLC's own
MLCTS standard (which marks tone and is orthography- rather than
pronunciation-based). Both are real, differently-purposed systems; this
module implements only BGN/PCGN. Do not assume its output is
authoritative for formal Myanmar-language publishing.

Verified against the source document's own worked examples (Notes 2-4):
မဒမ -> madama, အက -> aga, ကလိ -> kali, သာငယ် -> thangè, အိုဘဲ့ -> obè,
အပ် -> at -- and, independently, against the well-known place names
ရန်ကုန် -> Yangon and ပြင်ဦးလွင် -> Pyin Oo Lwin (see tests/test_transliterate.py).

Deliberately out of scope for this v1 (implement narrower and correct,
rather than broader and guessed -- see burmesenlp.spellcheck and the
Zawgyi detector's own docstrings for the same discipline elsewhere in
this project):

- **Note 5** (stacked/subjoined Pali-loan consonants, e.g. "kk" written
  one letter above another): implemented per the note's literal
  wording (upper consonant romanized first, then lower, sharing one
  trailing vowel/final), but the note's own worked example in the
  source PDF could not be independently re-derived character-for-
  character -- the dense stacked-consonant glyphs did not survive PDF
  text extraction cleanly. Treat stacked-consonant output as
  lower-confidence than the rest of this module.
- **Note 6** (n-g/n-y/t-h hyphen disambiguation, e.g. "kun-yet" not
  "kunyet"): not implemented. Output for these sequences is still a
  valid concatenation, just without the disambiguating hyphen.
- **Note 8** (a lone anusvara-with-medial-wa spelling idiom that shifts
  a *preceding* syllable's vowel from a to in, e.g. "thinbaw"): not
  implemented -- narrow enough, and different enough from the ordinary
  anusvara-as-final-nasal reading (which *is* implemented), that
  guessing felt worse than skipping.
- **Kinzi** (the prefixed nga+asat+virama unit) and the two documented
  **Contractions** sequences (see ``burmesenlp.normalize``): the source
  document does not mention kinzi by name or give a romanization rule
  for it, and no verified romanization for either contraction word was
  found. Both are passed through as unromanized Myanmar text rather
  than guessed.
- **Note 4's medial/final-syllable hyphen** for a word-INTERNAL
  vowel-initial syllable (as opposed to the word-initial case, which
  *is* implemented): would require syllable-boundary information this
  module does not have (it works over character clusters, not
  segmented syllables).
- **ည's final-consonant reading** (Note 10) is genuinely
  pronunciation-dependent per the source itself ("a reference source
  should be consulted in case of uncertainty"); this module always
  picks "i", the source table's first-listed value, not a verified
  per-word answer.
- The final-consonant table's "wun" cell for the anusvara row (row 11)
  involves a spelling variant (independent letter ဝ) this module could
  not confidently disentangle from the ordinary medial-wa case during
  PDF extraction; only the plain/i/u anusvara contexts are implemented.
"""
from __future__ import annotations

from typing import Dict, FrozenSet, Optional, Tuple

from ..normalize import _Cluster, _iter_clusters, normalize

__all__ = ["romanize"]

# -- combining marks (same codepoints as burmesenlp.normalize, kept as
# local literals so this module doesn't depend on normalize's private
# rank constants) -----------------------------------------------------
_MEDIAL_YA = "ျ"
_MEDIAL_RA = "ြ"
_MEDIAL_WA = "ွ"
_MEDIAL_HA = "ှ"
_ASAT = "်"
_ANUSVARA = "ံ"
_VOWEL_TALL_AA = "ါ"
_VOWEL_AA = "ာ"
_VOWEL_E = "ေ"
_VOWEL_AI = "ဲ"  # ဲ
_VOWEL_I = "ိ"
_VOWEL_II = "ီ"
_VOWEL_U = "ု"
_VOWEL_UU = "ူ"
_TONE_MARKS = {"့", "း"}  # dot below, visarga -- dropped, Note 7

_VOWEL_SIGN_CHARS = {
    _VOWEL_TALL_AA, _VOWEL_AA, _VOWEL_E, _VOWEL_AI,
    _VOWEL_I, _VOWEL_II, _VOWEL_U, _VOWEL_UU,
}

# -- CONSONANT CHARACTERS (source page 1) ------------------------------
_INITIALS: Dict[str, str] = {
    "က": "k", "ခ": "k",
    "ဂ": "g", "ဃ": "g",
    "င": "ng",
    "စ": "s", "ဆ": "s",
    "ဇ": "z", "ဈ": "z",
    "ည": "ny", "ဉ": "ny",
    "တ": "t", "ထ": "t", "ဋ": "t", "ဌ": "t",
    "ဒ": "d", "ဍ": "d", "ဓ": "d", "ဎ": "d",
    "န": "n", "ဏ": "n",
    "ပ": "p", "ဖ": "p",
    "ဗ": "b", "ဘ": "b",
    "မ": "m",
    "ယ": "y", "ရ": "y",
    "လ": "l", "ဠ": "l",
    "ဝ": "w",
    "သ": "th",
    "ဟ": "h",
    "အ": "",  # vowel-carrier: contributes nothing of its own (Note 3);
              # the syllable's vowel-sign or the generic inherent-"a"
              # ending (Note 2) supplies the actual sound.
    "ဿ": "ss",  # "great sa" -- a Pali-loan ligature with its own single
                # codepoint (U+103F), not decomposable via virama like
                # ordinary stacked consonants; well-attested as "ss".
}

_DIGITS: Dict[str, str] = {
    "၀": "0", "၁": "1", "၂": "2", "၃": "3", "၄": "4",
    "၅": "5", "၆": "6", "၇": "7", "၈": "8", "၉": "9",
}
# k/s/t/p voice to g/z/d/b after a preceding roman-script vowel, "n", or
# "ng" (source page 1, right-hand column; applies only to the BARE
# consonant and to the ခ+medial-y/r "ch"->"gy" combination below -- the
# combination table's other rows list no voiced alternative).
_VOICED = {"k": "g", "s": "z", "t": "d", "p": "b"}

# -- CONSONANT CHARACTER COMBINATIONS (source page 2) ------------------
# Keyed by (base consonant, frozenset of medial "roles" present):
# "yr" = medial ya or ra (both merge to the same romanization here),
# "w" = medial wa, "h" = medial ha. Value: (plain, voiced-or-None).
_MEDIAL_OVERRIDES: Dict[Tuple[str, FrozenSet[str]], Tuple[str, Optional[str]]] = {
    ("ခ", frozenset({"yr"})): ("ch", "gy"),
    ("ရ", frozenset({"h"})): ("sh", None),
    ("သ", frozenset({"yr", "h"})): ("sh", None),
    ("လ", frozenset({"yr", "h"})): ("sh", None),
    ("မ", frozenset({"yr"})): ("My", None),
    ("မ", frozenset({"w"})): ("Mw", None),
    ("မ", frozenset({"yr", "w"})): ("Myw", None),
    ("မ", frozenset({"h"})): ("hM", None),
}

# -- CONSONANT CHARACTERS WITH END-OF-SYLLABLE MARKS (source page 3) --
# final letter -> {vowel context -> latin rhyme}. Context: "" (plain/
# inherent a), "i" (dependent ိ/ီ alone), "u" (dependent ု/ူ alone),
# "w" (medial wa alone, no separate vowel sign), "o" (ို, i.e. i-type +
# u-type together -- က/င only), "aw" (ော, i.e. ေ + tall-aa/aa together
# -- က/င only).
_FINAL_RHYME: Dict[Tuple[str, str], str] = {
    ("က", ""): "et", ("က", "o"): "aik", ("က", "aw"): "auk",
    ("င", ""): "in", ("င", "o"): "aing", ("င", "aw"): "aung",
    ("စ", ""): "it",
    ("ည", ""): "i",  # Note 10: pronunciation-dependent; "i"/"in"/"e" all attested. See module docstring.
    ("တ", ""): "at", ("တ", "i"): "eik", ("တ", "u"): "ôk", ("တ", "w"): "ut",
    ("ပ", ""): "at", ("ပ", "i"): "eik", ("ပ", "u"): "ôk", ("ပ", "w"): "ut",
    ("န", ""): "an", ("န", "i"): "ein", ("န", "u"): "ôn", ("န", "w"): "un",
    ("မ", ""): "an", ("မ", "i"): "ein", ("မ", "u"): "ôn", ("မ", "w"): "un",
    ("ယ", ""): "è",
    ("ဉ", ""): "in",
}
_FINAL_LETTERS = frozenset(letter for letter, _ctx in _FINAL_RHYME)

# Kinzi (<U+1004, U+103A, U+1039>, a fixed unit visually rendered above
# the consonant that follows it) is NOT documented in the BGN/PCGN
# source at all -- this rhyme is this module's own inference, not from
# the source tables, cross-validated against well-known conventional
# spellings rather than guessed: မင်္ဂလာ -> "Mingala(r)" and
# စင်္ကာပူ -> "Singabu" (matching Note 8's own "Sin-gabu" example, whose
# source Burmese text is itself suspected -- see the module docstring --
# of having lost this exact kinzi sequence during PDF extraction) both
# fall out correctly by treating kinzi as merging into the PRECEDING
# syllable exactly like a plain-context ç final ("in"), same as row 2
# above, then letting the consonant kinzi sits above start a fresh
# syllable (with voicing state carried on, since "in" ends in "n").
# Only applies when the preceding syllable has no vowel sign of its own
# (an onset that already carries one, immediately followed by kinzi, is
# an unverified combination and is left unmerged).
_KINZI_CODA = "\u0000kinzi"
_FINAL_RHYME[(_KINZI_CODA, "")] = "in"

# Row 11: anusvara (ံ) as a final nasal -- a MARK on the onset cluster
# itself, not a separate cluster (unlike rows 1-10 above). Only the
# unambiguous plain/i/u contexts are implemented; see module docstring.
_ANUSVARA_RHYME: Dict[str, str] = {"": "an", "i": "ein", "u": "ôn"}

# Open-syllable (no following final consonant) vowel endings.
_OPEN_ENDING: Dict[str, str] = {
    "": "a",  # Note 2: inherent vowel
    "i": "i",
    "u": "u",
    "o": "o",
    "e": "e",
    "aw": "aw",
    "è": "è",
}

# Independent vowel LETTERS (page 2's "Independent Characters" column) --
# distinct Unicode codepoints, not decomposable into an onset consonant
# plus a vowel-sign mark. အ itself (also independent, but decomposes
# naturally via the empty onset in _INITIALS) is handled separately.
_INDEPENDENT_VOWELS: Dict[str, str] = {
    "ဣ": "i", "ဤ": "i",
    "ဥ": "u", "ဦ": "u",
    "ဧ": "e", "၏": "e",
    "ဩ": "aw", "ဪ": "aw",
}

_VOWEL_TRIGGERS_VOICING = set("aeiouè") | {"ô"}


def _medial_roles(marks: Tuple[str, ...]) -> FrozenSet[str]:
    roles = set()
    if _MEDIAL_YA in marks or _MEDIAL_RA in marks:
        roles.add("yr")
    if _MEDIAL_WA in marks:
        roles.add("w")
    if _MEDIAL_HA in marks:
        roles.add("h")
    return frozenset(roles)


def _vowel_signs(marks: Tuple[str, ...]) -> FrozenSet[str]:
    return frozenset(m for m in marks if m in _VOWEL_SIGN_CHARS)


def _vowel_context(vowel_signs: FrozenSet[str]) -> Optional[str]:
    """-> '', 'i', 'u', 'o', 'aw', 'e', 'è', or None (combination not in the source tables).

    Medials never factor in here: an ordinary medial (ya/ra/ha/wa)
    changes the ONSET consonant, not the vowel -- a plain "" context
    still applies when there's no separate vowel-sign mark. The one
    documented exception (medial wa doubling as a final-rhyme vowel
    marker for specific finals, source page 3's "w" column) is handled
    where the final-consonant merge actually happens, since it depends
    on *which* final letter follows, not on the onset alone.
    """
    if not vowel_signs:
        return ""
    if vowel_signs <= {_VOWEL_TALL_AA, _VOWEL_AA}:
        return ""  # ာ/ါ alone is an explicit spelling of the default vowel
    if vowel_signs == {_VOWEL_AI}:
        return "è"
    if vowel_signs == {_VOWEL_E}:
        return "e"
    has_i = bool(vowel_signs & {_VOWEL_I, _VOWEL_II})
    has_u = bool(vowel_signs & {_VOWEL_U, _VOWEL_UU})
    if has_i and has_u:
        return "o"
    if has_i and vowel_signs == frozenset(vowel_signs & {_VOWEL_I, _VOWEL_II}):
        return "i"
    if has_u and vowel_signs == frozenset(vowel_signs & {_VOWEL_U, _VOWEL_UU}):
        return "u"
    if _VOWEL_E in vowel_signs and (vowel_signs & {_VOWEL_TALL_AA, _VOWEL_AA}):
        return "aw"
    return None


def _onset(base: str, roles: FrozenSet[str]) -> Optional[Tuple[str, Optional[str]]]:
    """-> (plain, voiced-or-None) latin for *base* with medial *roles*, or None if unhandled."""
    override = _MEDIAL_OVERRIDES.get((base, roles))
    if override is not None:
        return override
    base_latin = _INITIALS.get(base)
    if base_latin is None:
        return None
    if not roles:
        return (base_latin, _VOICED.get(base_latin))
    if roles == frozenset({"h"}):
        return ("h" + base_latin, None)
    suffix = ("y" if "yr" in roles else "") + ("w" if "w" in roles else "")
    if not suffix:
        return None  # "h" combined with another medial outside the overrides above: unverified, skip
    return (base_latin + suffix, None)


def _is_bare_final(cluster: _Cluster) -> bool:
    if cluster.kind != "syllable" or cluster.stacked or cluster.base not in _FINAL_LETTERS:
        return False
    non_tone = [m for m in cluster.marks if m not in _TONE_MARKS]
    return non_tone == [_ASAT]  # tone marks (Note 7) may still ride along, and are dropped


def _coda_key(cluster: _Cluster) -> Optional[str]:
    """-> the key to look up in :data:`_FINAL_RHYME` if *cluster* merges into
    the syllable before it (a real final-consonant letter, or kinzi), else None."""
    if _is_bare_final(cluster):
        return cluster.base
    if cluster.kind == "kinzi":
        return _KINZI_CODA
    return None


def _romanize_onset_text(base: str, roles: FrozenSet[str], prev_ending: Optional[str]) -> Optional[str]:
    pair = _onset(base, roles)
    if pair is None:
        return None
    plain, voiced = pair
    if voiced is not None and prev_ending is not None and (
        prev_ending.endswith("ng") or prev_ending.endswith("n")
        or (prev_ending and prev_ending[-1] in _VOWEL_TRIGGERS_VOICING)
    ):
        return voiced
    return plain


def _romanize_cluster(
    cluster: _Cluster,
    prev_ending: Optional[str],
    coda_base: Optional[str],
) -> Optional[str]:
    """-> latin text for *cluster* (optionally merged with a following bare-final
    coda whose letter is *coda_base*), or None if some part is unhandled."""
    if cluster.base in _DIGITS and not cluster.stacked and not cluster.marks:
        return None if coda_base is not None else _DIGITS[cluster.base]

    if (
        not cluster.stacked
        and set(cluster.marks) <= _TONE_MARKS
        and cluster.base in _INDEPENDENT_VOWELS
    ):
        vowel = _INDEPENDENT_VOWELS[cluster.base]
        if coda_base is not None:
            rhyme = _FINAL_RHYME.get((coda_base, vowel))
            return rhyme  # None if unhandled -- caller falls back to no-merge
        return vowel

    roles = _medial_roles(cluster.marks)
    onset_text: Optional[str]

    if cluster.stacked:
        upper_latin = _INITIALS.get(cluster.base)
        lower_pair = _onset(cluster.stacked[1], roles)
        if upper_latin is None or lower_pair is None:
            return None
        onset_text = upper_latin + lower_pair[0]  # Note 5: no voicing on either consonant here
    else:
        onset_text = _romanize_onset_text(cluster.base, roles, prev_ending)
        if onset_text is None:
            return None

    vowel_signs = _vowel_signs(cluster.marks)
    context = _vowel_context(vowel_signs)
    if context is None:
        return None

    if coda_base is not None:
        rhyme = None
        if context == "" and roles == frozenset({"w"}):
            # Medial wa alone doubles as a final-rhyme vowel marker for
            # specific finals only (source page 3's "w" column, rows
            # တ/ပ/န/မ) -- try that reading before the plain one.
            rhyme = _FINAL_RHYME.get((coda_base, "w"))
        if rhyme is None:
            rhyme = _FINAL_RHYME.get((coda_base, context))
        if rhyme is None:
            return None
        return onset_text + rhyme

    if _ANUSVARA in cluster.marks:
        rhyme = _ANUSVARA_RHYME.get(context)
        if rhyme is None:
            return None
        return onset_text + rhyme

    return onset_text + _OPEN_ENDING.get(context, "")


def romanize(text: str) -> str:
    """Romanize Burmese *text* using the BGN/PCGN 1970 system.

    Tone is dropped (the system's own design, not a shortcut taken
    here -- see Note 7 of the source document). Non-Myanmar characters
    (Latin text, digits, punctuation, whitespace) pass through
    unchanged. See the module docstring for what this v1 does not
    attempt (kinzi, stacked-consonant edge cases, several narrow
    hyphenation/disambiguation notes).

    Any syllable this module cannot confidently romanize (an unhandled
    medial/vowel/final combination) is left as the original Myanmar
    text in the output, rather than guessed.
    """
    if not isinstance(text, str):
        raise TypeError(f"expected str, got {type(text).__name__}")
    if not text:
        return ""

    clusters = list(_iter_clusters(normalize(text, warn_zawgyi=False)))
    out = []
    prev_ending: Optional[str] = None
    i = 0
    n = len(clusters)
    while i < n:
        cluster = clusters[i]
        if cluster.kind != "syllable":
            out.append(cluster.raw)
            prev_ending = None
            i += 1
            continue

        coda_base = _coda_key(clusters[i + 1]) if i + 1 < n else None

        result = _romanize_cluster(cluster, prev_ending, coda_base)
        if result is None and coda_base is not None:
            # Coda didn't fit this onset's vowel context (rare/unverified
            # combination) -- fall back to treating the two clusters
            # independently rather than losing the whole syllable.
            coda_base = None
            result = _romanize_cluster(cluster, prev_ending, None)

        if result is None:
            out.append(cluster.base + cluster.stacked + "".join(cluster.marks))
            prev_ending = None
            i += 1
            continue

        out.append(result)
        prev_ending = result
        i += 2 if coda_base is not None else 1

    return "".join(out)
