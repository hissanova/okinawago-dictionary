"""
日本語（沖縄語）の音節（モーラ？）のスキーム
mora::=[g]([P]|[C][v]V[V])
word::=mora+...
- g:glottal stop ["'", "?"]
- P:pseudo-consonant ["Q", "N"]
- C:consonant
- v:semi-vowel
- V:vowel
"""
from typing import Dict, List, NamedTuple, Tuple
from enum import Enum
import json
from itertools import product

vowels = {'a', 'i', 'u', 'e', 'o'}
consonants = {
    'C', 'S', 'Z', 'b', 'c', 'd', 'g', 'h', 'k', 'l', 'm', 'n', 'p', 'q', 'r',
    's', 't', 'z'
}
semi_vowels = {'j', 'w'}
sokuon = {'Q'}
hatsuon = {'N'}
glottal_stops = {"'", '?'}
others = {' ', '(', ')', ',', '-', '=', ']'}

exceptions = ["hNN"]  # 発音記号の例外

with open("resources/kana-table.json", 'r') as kana_list_file:
    pronunc_kana_dict = json.load(kana_list_file)

long_vowel_dict = {}
for pronunc, kana_list in pronunc_kana_dict.items():
    if any(pronunc.endswith(vowel) for vowel in vowels):
        pronunc += pronunc[-1]
        kana_list = [kana + "ー" for kana in kana_list]
        long_vowel_dict[pronunc] = kana_list

pronunc_kana_dict.update(long_vowel_dict)

with open("resources/phonetics-table.json", 'r') as table:
    phonetics_dict = json.load(table)

roman_to_kana_n_ipa = {}
for entry in phonetics_dict:
    romans = entry["roman"]
    entry.pop("roman")
    for roman in romans:
        roman_to_kana_n_ipa[roman] = entry


def _delete_others(pronunciation: str) -> str:
    """発音記号の文字列から、子音、半母音、母音以外の文字を消去します。"""
    for other_chr in others:
        pronunciation = str(pronunciation).replace(other_chr, '')
    return pronunciation


def _check_glottal_stop(ch_list: List[str]) -> Tuple[str, List[str]]:
    char = ch_list[0]
    if char in glottal_stops:
        return _check_consonant(char, ch_list[1:])
    return _check_consonant('', ch_list)


def _check_consonant(mora: str, ch_list: List[str]) -> Tuple[str, List[str]]:
    char = ch_list[0]
    if char in sokuon.union(hatsuon):
        return char, ch_list[1:]
    if char in consonants:
        return _check_semi_vowels(mora + char, ch_list[1:])
    return _check_semi_vowels(mora, ch_list)


def _check_semi_vowels(mora: str, ch_list: List[str]) -> Tuple[str, List[str]]:
    char = ch_list[0]
    if char in semi_vowels:
        return _check_vowel(mora + char, ch_list[1:])
    return _check_vowel(mora, ch_list)


def _check_vowel(mora: str, ch_list: List[str]) -> Tuple[str, List[str]]:
    char = ch_list[0]
    if char in vowels:
        return _check_ending(mora + char, ch_list[1:])
    raise Exception(f"{mora}の次は、母音{{aeiou}}が続きます。")


def _check_ending(mora: str, ch_list: List[str]) -> Tuple[str, List[str]]:
    if len(ch_list) == 0:
        return mora, ch_list
    char = ch_list[0]
    if char in vowels and mora[-1] == char:
        return mora + char, ch_list[1:]
    return mora, ch_list


def split_into_moras(pronunciation: str) -> List[str]:
    """発音記号の文字列をモーラに分解します。"""
    word = _delete_others(pronunciation)
    chr_list = list(word)
    moras: List[str] = []
    while chr_list:
        mora, chr_list = _check_glottal_stop(chr_list)
        moras.append(mora)
    return moras


class PhonemeSymols(NamedTuple):
    simplified: str
    original: str

    def to_dict(self):
        return {"simplified": self.simplified, "original": self.original}


class Pronunciation(NamedTuple):
    ipa: str
    kana: List[str]

    def to_dict(self):
        return {"IPA": self.ipa, "kana": self.kana}


class SocialClass(Enum):
    HEIMIN = "HEIMIN"
    SHIZOKU = "SHIZOKU"


class WordPhonetics(NamedTuple):
    phonemes: PhonemeSymols
    pronunciations: Dict[SocialClass, Pronunciation]

    def to_dict(self):
        return {
            "phonemes": self.phonemes.to_dict(),
            "pronunciation": {
                s_class.value: pronunc.to_dict()
                for s_class, pronunc in self.pronunciations.items()
            }
        }


excel2Original_dict = {
    "?": "ʔ",
    "C": "ç",
    "Z": "ʐ",
    "S": "ş",
}


def get_original_phonemes(phoneme_symbols_in_excel: str) -> str:
    return phoneme_symbols_in_excel.translate({
        ord(k): ord(v)
        for k, v in excel2Original_dict.items()
    }).replace("]", "<sup>¬</sup>")


def _contain_long_vowel(mora: str) -> bool:
    return any(mora.count(v) > 1 for v in vowels)


def _add_char_to_all(word_list: List[str], char: str) -> List[str]:
    return [word + char for word in word_list]


def mora2kana_n_IPA(mora: str) -> Tuple[List[List[str]], List[str]]:
    long_vowel_sym = ["", ""]
    if _contain_long_vowel(mora):
        mora = mora[:-1]
        long_vowel_sym = ["ー", "ː"]
    kana_n_ipa = roman_to_kana_n_ipa[mora]
    return (
        [
            _add_char_to_all(k, long_vowel_sym[0])
            for k in kana_n_ipa["kana"].values()
        ],
        [ipa + long_vowel_sym[1] for ipa in kana_n_ipa["IPA"].values()],
    )


def get_ipa_n_kana(
        phoneme_symbols_in_excel: str) -> Dict[SocialClass, Pronunciation]:
    if phoneme_symbols_in_excel == "hNN":
        return {
            SocialClass.HEIMIN: Pronunciation(
                "hnː",
                ["フンー"],
            )
        }

    moras = split_into_moras(phoneme_symbols_in_excel)
    converted_moras = [mora2kana_n_IPA(m) for m in moras]
    # print(converted_moras)
    kanas = [m[0] for m in converted_moras]
    ipas = [m[1] for m in converted_moras]
    # print(kanas)
    # print(ipas)
    ret_dict = {
        SocialClass.HEIMIN:
        Pronunciation(
            "".join(ipa[0] for ipa in ipas),
            ["".join(w) for w in product(*[k[0] for k in kanas])],
        )
    }
    if any(len(ipa) > 1 for ipa in ipas):
        ret_dict.update({
            SocialClass.SHIZOKU:
            Pronunciation(
                "".join(ipa[-1] for ipa in ipas),
                ["".join(w) for w in product(*[k[-1] for k in kanas])],
            )
        })
    return ret_dict


def generate_phonetics(phoneme_symbols_in_excel: str) -> WordPhonetics:
    return WordPhonetics(
        PhonemeSymols(
            phoneme_symbols_in_excel,
            get_original_phonemes(phoneme_symbols_in_excel),
        ),
        get_ipa_n_kana(phoneme_symbols_in_excel),
    )


def convert2kana(pronunciation: str) -> List[str]:
    """発音記号をかな表記に変換します。"""

    kana_list = []
    for mora in split_into_moras(pronunciation):
        kana_list.append(pronunc_kana_dict[mora])
    converted = []
    for kana in product(*kana_list):
        converted.append("".join(kana))
    return converted
