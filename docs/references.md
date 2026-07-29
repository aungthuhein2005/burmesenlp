# References

Credits and sources that informed BurmeseNLP.

## Thanks

Thanks to all pioneer researchers and developers for the Burmese language.
Their corpora, converters, lexicons, and papers made this toolkit possible.

## Reference GitHub

- [myPOS corpus (ver 3.0)](https://github.com/ye-kyaw-thu/myPOS/tree/master/corpus-ver-3.0/corpus)
- [Rabbit — Zawgyi ⇔ Unicode converter](https://github.com/Rabbit-Converter/Rabbit)
- [MMDT-Tokenizer](https://github.com/Myanmar-Data-Tech/mmdt-tokenizer) ([PyPI](https://pypi.org/project/mmdt-tokenizer/))

## Reference datasets

- [Myanmar idioms lexicon](https://huggingface.co/datasets/freococo/myanmar_idioms_lexicon)
- [Myanmar proverbs lexicon](https://huggingface.co/datasets/freococo/myanmar_proverbs_lexicon)
- [Myanmar–English MT pairs](https://huggingface.co/datasets/KaungHtetCho/MT-myanmar-english)
- [myPOS corpus (ver 3.0)](https://github.com/ye-kyaw-thu/myPOS/tree/master/corpus-ver-3.0/corpus)
- [ALT Burmese Corpus / Treebank](https://zenodo.org/records/3463010) (CC BY-NC-SA; ~20,000 annotated sentences)
- [MIMU place codes](https://themimu.info/place-codes)
- [Burmese names with gender (Kaggle)](https://www.kaggle.com/datasets/heinhtetahkarmg/burmese-name-with-gender)
- [Ethnic groups of Myanmar](https://www.embassyofmyanmar.be/ABOUT/ethnicgroups.htm)
- [List of universities in Myanmar](https://en.wikipedia.org/wiki/List_of_universities_in_Myanmar)
- [Public holidays in Myanmar](https://en.wikipedia.org/wiki/Public_holidays_in_Myanmar)
- [Official social and NGO organisations in Myanmar](https://en.wikipedia.org/wiki/List_of_official_social_and_NGO_organisations_in_Myanmar)
- [Buddhist temples in Myanmar](https://en.wikipedia.org/wiki/List_of_Buddhist_temples_in_Myanmar)

## Reference papers

### Phrase chunking

- Myintzu Phyo Aung & Aung Lwin Moe.
  *[New Phrase Chunking Algorithm for Myanmar Natural Language Processing](https://doi.org/10.4028/www.scientific.net/amm.695.548)*.
  Applied Mechanics and Materials, Vol. 695, pp. 548–552, 2014.
  ([Scientific.Net](https://www.scientific.net/AMM.695.548))

### Morphological analysis and hybrid systems

- Kaung Myat Thu, H. M. Devi & T. R. Singh.
  *A Hybrid Approach to Myanmar Morphological Analysis and Generation (MAG) System*.
  Nanotechnology Perceptions, Vol. 20, No. S15, pp. 2453–2465, 2024.
  Combines finite-state techniques (FSTs) for morphotactics with LSTM models for Myanmar script variation.

- Chenchen Ding, Hnin Thu Zar Aye, Win Pa Pa, Khin Thandar Nwet, Khin Mar Soe, Masao Utiyama & Eiichiro Sumita.
  *[Towards Burmese (Myanmar) Morphological Analysis: Syllable-based Tokenization and Part-of-speech Tagging](https://doi.org/10.1145/3325885)*.
  ACM Transactions on Asian and Low-Resource Language Information Processing (TALLIP), 2019.
  Annotated ALT Burmese corpus (~20,000 sentences); compares CRFs and LSTM-based RNNs.

### Grammar-driven and rule-based segmentation

- Myo Thida, Nu Wei Thet & Thein Kyaw Lwin.
  *Grammar-Driven Text Segmentation for Context Understanding of Myanmar Language*.
  Research article (Batangas State University / University of Illinois at Chicago), posted 23 January 2026.
  Rule-based NLP and lexical resource construction with tries for tokenization of formal and stylistically variable Myanmar text.

- Tin Htay Hlaing & Yoshiki Mikami.
  *Collation Weight Design for Myanmar Unicode Texts*.
  In *Proceedings of Human Language Technology for Development*, Alexandria, Egypt, May 2011.
  Technical representation of complex script forms such as consonant stacking and invisible virama signs.

### POS tagging and language modeling

- K. K. Zin & N. L. Thein.
  *Hidden Markov Model with Rule Based Approach for Part of Speech Tagging of Myanmar Language*.
  2009.
  Foundational study combining statistical HMMs with linguistic rules for Myanmar POS tagging.

- S. T. Y. Myint & M. M. Khin.
  *Lexicon Based Word Segmentation and Part of Speech Tagging for Written Myanmar Text*.
  International Journal of Computational Linguistics and Natural Language Processing, Vol. 2, Issue 6, June 2013.

## Foundational linguistic sources

- Myanmar Language Commission, Ministry of Education.
  *Myanmar Grammar* (မြန်မာသဒ္ဒါ), 2005.
  Definitive authority on Myanmar word classes, including nouns, verbs, and particle/postposition types.

- Myanmar Language Commission.
  *Myanmar Orthography*, 3rd edition, 2006.
  Standardizes spelling and visual representation of the Myanmar script.

- John Okell & Anna Allott.
  *Burmese/Myanmar Dictionary of Grammatical Forms*, 2001.
  Critical reference for morphological function of particles and suffixes in colloquial and literary Burmese.

## Computational frameworks and toolkits

- [CRF++](https://taku910.github.io/crfpp/) — Conditional Random Fields toolkit for segmenting and labeling sequential data.
- [OpenFST](https://www.openfst.org/) and [HFST](https://hfst.github.io/) — weighted finite-state transducer libraries used in morphological analyzers.
- [MMDT-Tokenizer](https://pypi.org/project/mmdt-tokenizer/) — open-source Myanmar tokenizer ([GitHub](https://github.com/Myanmar-Data-Tech/mmdt-tokenizer)).
