"""Closed-class grammatical word lists for Myanmar.

These sets are deliberately conservative: an entry appears in exactly the
set(s) matching its dominant grammatical function, so downstream rules do
not fight each other (the original prototype had e.g. နှင့် in both the
sentence-final-particle and conjunction lists, causing bad splits).
"""

from __future__ import annotations

# Post-positional / case markers (subject, object, locative, ...)
PPM_MARKERS = frozenset({
    "က", "ကို", "မှာ", "မှ", "၌", "တွင်", "အား", "သို့",
    "ဖြင့်", "နှင့်", "နဲ့", "ရဲ့", "၏",
})

# Clause/sentence-level conjunctions
CONJUNCTIONS = frozenset({
    "သို့မဟုတ်", "ဒါပေမယ့်", "ဒါမှမဟုတ်", "ဘာဖြစ်လို့လဲဆိုတော့",
    "ထိုနည်းတူ", "ထို့ကြောင့်", "သို့သော်", "ပြီးတော့", "လျှင်",
})

# Particles that may legitimately end a sentence (used for tagging).
FINAL_PARTICLES = frozenset({"သည်", "တယ်", "မည်", "ပြီ", "လား", "မလား", "၏"})

# Subset safe to *split sentences* on when no ။ is present.  ၏ is excluded
# because it is far more often a possessive marker mid-sentence.
SENTENCE_FINAL_PARTICLES = frozenset({"သည်", "တယ်", "မည်", "ပြီ", "လား", "မလား"})

# Words that continue the clause after a would-be final particle
# (quotatives / subordinators), so no sentence break is placed before them.
POST_FINAL_CONTINUATIONS = frozenset({"ဟု", "ဟူ", "လို့", "ဆို", "ဆိုပြီး"})

# Verbal suffixes / auxiliaries (used for POS suffix analysis)
VERB_SUFFIXES = frozenset({
    "သည်", "တယ်", "ခဲ့", "နေ", "ပေး", "ရ", "လိုက်", "ပစ်", "ထား",
    "ဖူး", "မည်", "ရန်", "စေ", "ပါ", "ကြ",
})

# Productive nominalizers / plural markers (used for POS suffix analysis)
NOUN_SUFFIXES = frozenset({"များ", "တွေ", "မှု", "ချက်", "ခြင်း", "ရေး"})

# Numeral words
NUMERAL_WORDS = frozenset({
    "တစ်", "နှစ်", "သုံး", "လေး", "ငါး", "ခြောက်", "ခုနစ်", "ရှစ်", "ကိုး",
    "ဆယ်", "ရာ", "ထောင်", "သောင်း", "သိန်း", "သန်း", "ကုဋေ",
})

# Counter classifiers (merge with a preceding numeral/digit into one word)
COUNTER_CLASSIFIERS = frozenset({
    "ယောက်", "ခု", "ကောင်", "စုံ", "အုပ်", "ခွက်", "လုံး", "ပါး",
    "ချပ်", "ထည်", "ပေါင်", "မိုင်", "ကီလို", "မီတာ", "နာရီ", "ရက်", "လ", "နှစ်",
})
