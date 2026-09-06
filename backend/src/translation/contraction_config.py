# Contraction (kısaltma) sistemi yapılandırması
#
# Her dilin kendine özgü kısaltma ekosistemini tanımlar.
# Plan v9 referansı: Bölüm 1.10.5 — Kısaltma Sistemi (ADR-008)
#
# Liblouis tabloları binary kısaltma (Grade 1/2) kullanır.
# Bu modül dil bazlı semantik katmanı ekler — örneğin Türkçe'nin
# 6 seviyeli kısaltma modeli, Liblouis tablolarına eşlenir.

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ContractionLevel:
    """Tek bir kısaltma düzeyi."""

    id: str  # Benzersiz tanımlayıcı (örn. "full_write", "contracted")
    label_tr: str  # Türkçe etiket
    label_en: str  # İngilizce etiket
    description_tr: str  # Türkçe açıklama
    description_en: str  # İngilizce açıklama


@dataclass
class ContractionProfile:
    """Bir dilin kısaltma profili."""

    language_code: str  # ISO 639-1
    language_name_tr: str
    language_name_en: str
    levels: list[ContractionLevel] = field(default_factory=list)
    default_level_id: str = "contracted"
    supports_contraction: bool = True
    info_message_tr: str | None = None  # Özel bilgi mesajı (örn. İspanyolca)
    info_message_en: str | None = None

    def get_level(self, level_id: str) -> ContractionLevel | None:
        """Belirtilen ID'ye sahip düzeyi döndür."""
        for level in self.levels:
            if level.id == level_id:
                return level
        return None


# ── Dil bazlı kısaltma profilleri ───────────────────────────────────────

# Dil bazlı kısaltma profilleri ──────────────────────────────────────────────────


@dataclass(frozen=True)
class ContractionCategory:
    """Tek bir kısaltma kategorisi (örn. 'Tek Harf Kısaltmaları')."""

    id: str  # Benzersiz tanımlayıcı (örn. "single_letter", "word_stem")
    label_tr: str  # Türkçe etiket
    label_en: str  # İngilizce etiket
    description_tr: str  # Türkçe açıklama
    description_en: str  # İngilizce açıklama
    sort_order: int = 0  # Sıralama


# Türkçe kısaltma kategorileri
# Kaynak: Ankara Üniversitesi ÖEZ204 Braille Okuma-Yazma ders müfredatı
# + MEB Braille Yazı Kılavuzu
TURKISH_CONTRACTION_CATEGORIES: list[ContractionCategory] = [
    ContractionCategory(
        id="single_letter",
        label_tr="Tek Harf Kısaltmaları",
        label_en="Single-Letter Contractions",
        description_tr="Her harf bir kelimeyi temsil eder. Örn: 'v' = 've', 'b' = 'bir', 'k' = 'kadar'.",
        description_en="Each letter represents a word. E.g., 'v' = 've' (and).",
        sort_order=1,
    ),
    ContractionCategory(
        id="two_letter",
        label_tr="İki Harf Kısaltmaları",
        label_en="Two-Letter Contractions",
        description_tr="İki harf bir kelimeyi veya eki temsil eder. Örn: 'ar' = '-arak', 'iy' = 'için'.",
        description_en="Two letters represent a word or suffix. E.g., 'iy' = 'için' (for).",
        sort_order=2,
    ),
    ContractionCategory(
        id="syllable",
        label_tr="Hece Kısaltmaları",
        label_en="Syllable Contractions",
        description_tr="Sık kullanılan heceler kısaltılır. Örn: 'ba', 'ma', 'la', 'en', 'er'.",
        description_en="Commonly used syllables are contracted. E.g., 'ba', 'ma', 'la'.",
        sort_order=3,
    ),
    ContractionCategory(
        id="word_stem",
        label_tr="Kelime Kökü Kısaltmaları",
        label_en="Word Stem Contractions",
        description_tr="Kelime kökleri için özel kısaltmalar. Örn: 'bugün', 'sonra', 'kendi'.",
        description_en="Special contractions for word stems. E.g., 'bugün' (today).",
        sort_order=4,
    ),
    ContractionCategory(
        id="word_part",
        label_tr="Kelime Parçası Kısaltmaları",
        label_en="Word Part Contractions",
        description_tr="Kelime içinde geçen parçalar için kısaltmalar. Örn: '-mış', '-acak', '-iyor'.",
        description_en="Contractions for word parts within words. E.g., '-mış' (past tense suffix).",
        sort_order=5,
    ),
]


# Dil bazlı kısaltma kategorileri haritası
# Şimdilik yalnızca Türkçe'de checkbox sistemi var.
CONTRACTION_CATEGORIES: dict[str, list[ContractionCategory]] = {
    "tr": TURKISH_CONTRACTION_CATEGORIES,

    # ── İngilizce (UEB — Unified English Braille) ──────────────────
    # Kaynak: BANA (Braille Authority of North America) — "The ABCs of UEB"
    # + ICEB (International Council on English Braille) UEB Rulebook
    # UEB Grade 2'de ~180 kısaltma vardır, 6 ana kategoriye ayrılır:
    "en": [
        ContractionCategory(
            id="alphabetic_wordsigns",
            label_tr="Tek Harf Kelime İşaretleri",
            label_en="Alphabetic Wordsigns",
            description_tr="Bir Braille harfi tam bir kelimeyi temsil eder. Örn: 'b' = 'but', 'c' = 'can', 'd' = 'do', 'p' = 'people'.",
            description_en="One braille letter represents a full word. E.g., 'b' = 'but', 'c' = 'can', 'd' = 'do'.",
            sort_order=1,
        ),
        ContractionCategory(
            id="strong_wordsigns",
            label_tr="Güçlü Kelime İşaretleri",
            label_en="Strong Wordsigns",
            description_tr="En sık kullanılan kelimeler için özel işaretler: 'and', 'for', 'of', 'the', 'with', 'child', 'shall', 'this', 'which', 'out', 'still'.",
            description_en="Special signs for most common words: 'and', 'for', 'of', 'the', 'with', 'child', 'shall', etc.",
            sort_order=2,
        ),
        ContractionCategory(
            id="strong_groupsigns",
            label_tr="Güçlü Grup İşaretleri",
            label_en="Strong Groupsigns",
            description_tr="Sık kullanılan harf grupları: 'ch', 'sh', 'th', 'wh', 'ou', 'st', 'ar', 'ed', 'er', 'gh', 'ow', 'ing'. Kelimenin her yerinde kullanılır.",
            description_en="Common letter groups: 'ch', 'sh', 'th', 'wh', 'ou', 'st', 'ar', 'ed', 'er', 'gh', 'ow', 'ing'. Used anywhere in a word.",
            sort_order=3,
        ),
        ContractionCategory(
            id="lower_groupsigns",
            label_tr="Alt Grup İşaretleri",
            label_en="Lower Groupsigns",
            description_tr="Alt noktalı grup işaretleri: 'ea', 'bb', 'cc', 'ff', 'gg', 'en', 'in'. 'be', 'con', 'dis' ön ekleri.",
            description_en="Lower-dot group signs: 'ea', 'bb', 'cc', 'ff', 'gg', 'en', 'in'. Prefixes 'be', 'con', 'dis'.",
            sort_order=4,
        ),
        ContractionCategory(
            id="initial_letter",
            label_tr="Baş Harf Kısaltmaları",
            label_en="Initial-Letter Contractions",
            description_tr="Dot 5 + harf ile oluşturulan kısaltmalar. Örn: 'day', 'ever', 'father', 'here', 'know', 'mother', 'name', 'under', 'work'.",
            description_en="Dot 5 + letter contractions. E.g., 'day', 'ever', 'father', 'here', 'know', 'mother', 'name', 'under', 'work'.",
            sort_order=5,
        ),
        ContractionCategory(
            id="final_groupsigns",
            label_tr="Son Ek Grup İşaretleri",
            label_en="Final-Letter Groupsigns",
            description_tr="Dot 46/56 + harf ile kelime sonu kısaltmaları. Örn: '-ound', '-ance', '-sion', '-less', '-ment', '-tion', '-ness', '-ful', '-ity'.",
            description_en="Dot 46/56 + letter word endings. E.g., '-ound', '-ance', '-sion', '-less', '-ment', '-tion', '-ness', '-ful', '-ity'.",
            sort_order=6,
        ),
    ],

    # ── Almanca ────────────────────────────────────────────────────
    # Kaynak: braille.ch - "Elements of the German Braille Code"
    # + Wikipedia German Braille + Brailleschriftkommission der
    # deutschsprachigen Länder (BSKDL)
    # Alman Braille'i 3 seviyede tanımlanır (1998 standardı):
    #   Basisschrift (Grade 1), Vollschrift (Grade 1½), Kurzschrift (Grade 2)
    "de": [
        ContractionCategory(
            id="vollschrift_groups",
            label_tr="Vollschrift Harf Grupları",
            label_en="Vollschrift Letter Groups",
            description_tr="8 temel harf grubu kısaltması: 'au', 'eu', 'ei', 'ch', 'sch', 'st', 'äu', 'ie'. Yalnızca aynı hecede kullanılır.",
            description_en="8 basic letter group contractions: 'au', 'eu', 'ei', 'ch', 'sch', 'st', 'äu', 'ie'. Only used within same syllable.",
            sort_order=1,
        ),
        ContractionCategory(
            id="kurzschrift_single_cell",
            label_tr="Kurzschrift Tek Hücre Kısaltmaları",
            label_en="Kurzschrift Single-Cell Contractions",
            description_tr="Tek Braille hücresinde hece/ses kısaltmaları: 'ge', 'es', 'em', 'ein', 'er', 'in'. Tüm pozisyonlarda kullanılabilir.",
            description_en="Single-cell syllable/sound contractions: 'ge', 'es', 'em', 'ein', 'er', 'in'. Can be used in all positions.",
            sort_order=2,
        ),
        ContractionCategory(
            id="kurzschrift_upper_words",
            label_tr="Kurzschrift Üst Kelime İşaretleri",
            label_en="Kurzschrift Upper Wordsigns",
            description_tr="Üst noktalı tam kelime kısaltmaları: 'aber', 'bei', 'sich', 'das', 'den', 'für', 'gegen', 'jetzt', 'kann', 'man', 'nicht', 'oder', 'so', 'voll', 'der'.",
            description_en="Upper-dot whole-word contractions: 'aber' (but), 'das' (the), 'für' (for), 'nicht' (not), 'oder' (or), 'der' (the).",
            sort_order=3,
        ),
        ContractionCategory(
            id="kurzschrift_suffixes",
            label_tr="Kurzschrift Son Ek Kısaltmaları",
            label_en="Kurzschrift Suffix Contractions",
            description_tr="Kelime sonu kısaltmaları: '-ig', '-lich', '-ach', 'ck', 'tt'. Alman Braille'ine özgü ek kısaltmaları.",
            description_en="Word ending contractions: '-ig', '-lich', '-ach', 'ck', 'tt'. German-specific suffix contractions.",
            sort_order=4,
        ),
    ],

    # ── Fransızca ──────────────────────────────────────────────────
    # Kaynak: Association Valentin Haüy (AVH) — "Abrégé Orthographique
    # Étendu" + Duxbury Systems Fransızca tablo dokümantasyonu
    # Fransızca CBFU (Code Braille Français Uniformisé) 2006 standardı
    # Grade 2'de harf grubu ve kelime kısaltmalarının yanı sıra
    # kendine özgü "abréviation" sistemi vardır.
    "fr": [
        ContractionCategory(
            id="letter_groups",
            label_tr="Harf Grubu Kısaltmaları",
            label_en="Letter Group Contractions",
            description_tr="Sık kullanılan harf grupları için tek hücreli kısaltmalar: 'ch', 'au', 'eu', 'ou', 'an', 'in', 'on', 'ai', 'ei', 'oi', 'gn', 'ill', 'elle', 'ment', 'tion'.",
            description_en="Single-cell contractions for common letter groups: 'ch', 'au', 'eu', 'ou', 'an', 'in', 'on', 'ai', 'ei', 'oi', 'gn', 'ill', 'elle', 'ment', 'tion'.",
            sort_order=1,
        ),
        ContractionCategory(
            id="word_contractions",
            label_tr="Kelime Kısaltmaları",
            label_en="Word Contractions",
            description_tr="Tek hücre ile tam kelime kısaltmaları: 'de', 'du', 'des', 'la', 'le', 'les', 'que', 'qui', 'par', 'pour', 'plus', 'dans', 'avec', 'tout'.",
            description_en="Single-cell whole word contractions: 'de', 'du', 'des', 'la', 'le', 'les', 'que', 'qui', 'par', 'pour', 'plus', 'dans', 'avec', 'tout'.",
            sort_order=2,
        ),
        ContractionCategory(
            id="prefixes",
            label_tr="Ön Ek Kısaltmaları",
            label_en="Prefix Contractions",
            description_tr="Yaygın Fransızca ön ekleri: 're-', 'com-', 'con-', 'trans-', 'pro-', 'pré-', 'dé-', 'in-', 'inter-', 'anti-', 'super-'.",
            description_en="Common French prefixes: 're-', 'com-', 'con-', 'trans-', 'pro-', 'pré-', 'dé-', 'in-', 'inter-', 'anti-', 'super-'.",
            sort_order=3,
        ),
        ContractionCategory(
            id="suffixes",
            label_tr="Son Ek Kısaltmaları",
            label_en="Suffix Contractions",
            description_tr="Yaygın Fransızca son ekleri: '-ment', '-tion', '-able', '-ible', '-ité', '-eur', '-euse', '-ique', '-logie', '-graphie'.",
            description_en="Common French suffixes: '-ment', '-tion', '-able', '-ible', '-ité', '-eur', '-euse', '-ique', '-logie', '-graphie'.",
            sort_order=4,
        ),
    ],

    # ── Portekizce ─────────────────────────────────────────────────
    # Kaynak: Duxbury Systems Portekizce tablo dokümantasyonu +
    # Wikipedia Portuguese Braille
    # Fransız Braille sistemine çok yakındır. Grade 2 kısaltmaları
    # harf grubu ve kelime kısaltmalarını içerir.
    "pt": [
        ContractionCategory(
            id="letter_groups",
            label_tr="Harf Grubu Kısaltmaları",
            label_en="Letter Group Contractions",
            description_tr="Sık kullanılan harf grupları: 'ch', 'lh', 'nh', 'ou', 'ão', 'õe', 'am', 'em', 'im', 'om', 'um', 'an', 'en', 'in', 'on', 'un'.",
            description_en="Common letter groups: 'ch', 'lh', 'nh', 'ou', 'ão', 'õe', 'am', 'em', 'im', 'om', 'um', 'an', 'en', 'in', 'on', 'un'.",
            sort_order=1,
        ),
        ContractionCategory(
            id="word_contractions",
            label_tr="Kelime Kısaltmaları",
            label_en="Word Contractions",
            description_tr="Tek hücreli tam kelime kısaltmaları: 'de', 'do', 'da', 'que', 'não', 'com', 'para', 'por', 'mais', 'como', 'entre', 'sobre'.",
            description_en="Single-cell whole word contractions: 'de' (of), 'que' (that), 'não' (not), 'com' (with), 'para' (for), 'por' (by).",
            sort_order=2,
        ),
        ContractionCategory(
            id="suffixes",
            label_tr="Son Ek Kısaltmaları",
            label_en="Suffix Contractions",
            description_tr="Yaygın Portekizce son ekleri: '-ção', '-mento', '-dade', '-mente', '-ável', '-ível', '-ismo', '-ista', '-eiro', '-eira'.",
            description_en="Common Portuguese suffixes: '-ção', '-mento', '-dade', '-mente', '-ável', '-ível', '-ismo', '-ista', '-eiro'.",
            sort_order=3,
        ),
    ],

    # ── Arapça ────────────────────────────────────────────────────
    # Kaynak: Liblouis ar-ar-g2.ctb + Wikipedia Arabic Braille
    # Arapça Braille Grade 2 kısaltma sistemi sınırlıdır.
    # Temel olarak sık kullanılan kelimelerin ve harf gruplarının
    # kısaltmalarını içerir.
    "ar": [
        ContractionCategory(
            id="common_words",
            label_tr="Sık Kullanılan Kelime Kısaltmaları",
            label_en="Common Word Contractions",
            description_tr="En sık kullanılan Arapça kelimeler: 'في' (fî), 'من' (min), 'على' (alâ), 'إلى' (ilâ), 'كان' (kâne), 'هذا' (hâzâ), 'مع' (maa), 'عن' (an).",
            description_en="Most common Arabic words: 'fî' (in), 'min' (from), 'alâ' (on), 'ilâ' (to), 'kâne' (was), 'hâzâ' (this).",
            sort_order=1,
        ),
        ContractionCategory(
            id="grammatical_prefixes",
            label_tr="Dilbilgisel Ön Ek Kısaltmaları",
            label_en="Grammatical Prefix Contractions",
            description_tr="Arapça dilbilgisel ön ekleri: 'الـ' (el-), 'بـ' (bi-), 'لـ' (li-), 'كـ' (ke-), 'فـ' (fe-), 'و' (ve), 'سـ' (se-).",
            description_en="Arabic grammatical prefixes: 'el-' (the), 'bi-' (with/by), 'li-' (for/to), 'ke-' (as/like), 'fe-' (then/so), 've' (and), 'se-' (will).",
            sort_order=2,
        ),
        ContractionCategory(
            id="common_endings",
            label_tr="Yaygın Kelime Sonu Kısaltmaları",
            label_en="Common Ending Contractions",
            description_tr="Arapça kelime sonları: '-ية' (iyye), '-ون' (ûn), '-ين' (în), '-ات' (ât), '-ان' (ân), '-ة' (te/et).",
            description_en="Arabic word endings: '-iyye' (noun ending), '-ûn' (masculine plural), '-în' (plural/genitive), '-ât' (feminine plural).",
            sort_order=3,
        ),
    ],

    # ── Rusça ─────────────────────────────────────────────────────
    # Kaynak: Liblouis ru-ru-g1.ctb, ru-litbrl.ctb
    # Rusça Braille'de sınırlı bir kısaltma sistemi vardır.
    # Grade 1 temel, litbrl ise edebî Braille içindir.
    "ru": [
        ContractionCategory(
            id="common_pronouns",
            label_tr="Sık Zamir ve Edat Kısaltmaları",
            label_en="Common Pronoun & Preposition Contractions",
            description_tr="Sık kullanılan zamir ve edatlar: 'я' (ya), 'мы' (mı), 'вы' (vı), 'он' (on), 'она' (ona), 'они' (oni), 'в' (v), 'на' (na), 'с' (s), 'по' (po), 'из' (iz).",
            description_en="Common pronouns and prepositions: 'ya' (I), 'mı' (we), 'vı' (you), 'on' (he), 'ona' (she), 'oni' (they), 'v' (in), 'na' (on).",
            sort_order=1,
        ),
        ContractionCategory(
            id="common_endings",
            label_tr="Yaygın Kelime Sonu Kısaltmaları",
            label_en="Common Ending Contractions",
            description_tr="Rusça yaygın kelime sonları: '-ого'/-его', '-тся'/-ться', '-ство', '-ский', '-ение', '-ание', '-овать', '-ивать'.",
            description_en="Common Russian word endings: '-ogo/-ego', '-tsya/-t'sya', '-stvo', '-skiy', '-enie', '-anie', '-ovat', '-ivat'.",
            sort_order=2,
        ),
    ],

    # İspanyolca: kısaltma sistemi yok (ONCE standartlarına göre Grade 1 yalnızca)
    "es": [],
}


CONTRACTION_PROFILES: dict[str, ContractionProfile] = {
    # ── Türkçe: 6 seviyeli sistem ────────────────────────────────────
    # Liblouis Türkçe tabloları:
    #   tr.tbl     → Grade 0 (bilgisayar Braille'i, 8 nokta)
    #   tr-g1.ctb  → Grade 1 (kısaltmasız, 6 nokta)
    #   tr-g2.tbl  → Grade 2 (kısaltmalı, 6 nokta)
    # Türkçe G2 tablosu içinde çok seviyeli kısaltma bulunur:
    # tek harf, iki harf, hece, kelime kökü
    "tr": ContractionProfile(
        language_code="tr",
        language_name_tr="Türkçe",
        language_name_en="Turkish",
        supports_contraction=True,
        default_level_id="contracted_full",
        levels=[
            ContractionLevel(
                id="computer",
                label_tr="Bilgisayar Braille'i",
                label_en="Computer Braille",
                description_tr="8 noktalı birebir Braille. Her karakter doğrudan eşleşir. Braille ekranlar ve programlama için idealdir.",
                description_en="8-dot one-to-one braille. Each character maps directly. Ideal for braille displays and programming.",
            ),
            ContractionLevel(
                id="full_write",
                label_tr="Tam Yazım",
                label_en="Full Writing",
                description_tr="6 noktalı kısaltmasız Braille. Her harf tek tek yazılır. Öğrenme ve resmî belgeler için uygundur.",
                description_en="6-dot uncontracted braille. Each letter is written individually. Suitable for learning and official documents.",
            ),
            ContractionLevel(
                id="single_letter",
                label_tr="Tek Harf Kısaltmaları",
                label_en="Single Letter Contractions",
                description_tr="Yalnızca tek harf kısaltmaları kullanılır. Her harf bir kelimeyi temsil edebilir. Giriş seviyesi kısaltmalı okuma.",
                description_en="Only single-letter contractions. Each letter can represent a word. Entry-level contracted reading.",
            ),
            ContractionLevel(
                id="two_letter",
                label_tr="Tek + İki Harf Kısaltmaları",
                label_en="Single + Two-Letter Contractions",
                description_tr="Tek harf ve iki harf kısaltmaları. Sık kullanılan hece ve ekler kısaltılır.",
                description_en="Single and two-letter contractions. Common syllables and suffixes are contracted.",
            ),
            ContractionLevel(
                id="syllable",
                label_tr="Tek + İki + Hece Kısaltmaları",
                label_en="Single, Two-Letter + Syllable Contractions",
                description_tr="Tek harf, iki harf ve hece kısaltmaları. Orta düzey kısaltmalı Braille.",
                description_en="Single, two-letter, and syllable contractions. Intermediate contracted braille.",
            ),
            ContractionLevel(
                id="contracted",
                label_tr="Kelime Kökü Dahil Kısaltmalı",
                label_en="Contracted with Word Stems",
                description_tr="Tek harf, iki harf, hece ve kelime kökü kısaltmaları. İleri düzey kısaltmalı Braille.",
                description_en="Single, two-letter, syllable, and word stem contractions. Advanced contracted braille.",
            ),
            ContractionLevel(
                id="contracted_full",
                label_tr="Tam Kısaltmalı (Tümü)",
                label_en="Fully Contracted (All)",
                description_tr="Tüm kısaltmalar: tek harf, iki harf, hece, kelime kökü ve kelime parçası. En sıkıştırılmış Braille. MEB müfredatına uygun.",
                description_en="All contractions: single-letter, two-letter, syllable, word stem, and word part. Most compact braille. Aligned with Turkish national curriculum.",
            ),
        ],
    ),

    # ── İngilizce (UEB) ─────────────────────────────────────────────
    "en": ContractionProfile(
        language_code="en",
        language_name_tr="İngilizce",
        language_name_en="English",
        supports_contraction=True,
        default_level_id="contracted",
        levels=[
            ContractionLevel(
                id="computer",
                label_tr="Bilgisayar Braille'i",
                label_en="Computer Braille",
                description_tr="8 noktalı birebir Braille.",
                description_en="8-dot one-to-one braille.",
            ),
            ContractionLevel(
                id="full_write",
                label_tr="Kısaltmasız (Uncontracted)",
                label_en="Uncontracted (Grade 1)",
                description_tr="UEB Grade 1. Her harf tek tek yazılır, kısaltma kullanılmaz. Öğrenme ve başlangıç seviyesi için.",
                description_en="UEB Grade 1. Each letter written individually, no contractions. For learning and beginner level.",
            ),
            ContractionLevel(
                id="contracted",
                label_tr="Kısaltmalı (Contracted)",
                label_en="Contracted (Grade 2)",
                description_tr="UEB Grade 2. Yaklaşık 180 kısaltma kullanılır. Standart İngilizce Braille.",
                description_en="UEB Grade 2. Approximately 180 contractions. Standard English braille.",
            ),
        ],
    ),

    # ── Almanca: 3 kademeli ─────────────────────────────────────────
    "de": ContractionProfile(
        language_code="de",
        language_name_tr="Almanca",
        language_name_en="German",
        supports_contraction=True,
        default_level_id="vollschrift",
        levels=[
            ContractionLevel(
                id="computer",
                label_tr="Bilgisayar Braille'i",
                label_en="Computer Braille",
                description_tr="8 noktalı birebir Braille.",
                description_en="8-dot one-to-one braille.",
            ),
            ContractionLevel(
                id="basisschrift",
                label_tr="Basisschrift (Temel Yazım)",
                label_en="Basisschrift (Basic Writing)",
                description_tr="Alman Braille'i temel seviye. Büyük harf işaretleri kullanılır, kısaltma yok.",
                description_en="German braille basic level. Capital letter signs used, no contractions.",
            ),
            ContractionLevel(
                id="vollschrift",
                label_tr="Vollschrift (Tam Yazım)",
                label_en="Vollschrift (Full Writing)",
                description_tr="Standart Alman Braille'i. Temel kısaltmalar ve biçimlendirme işaretleri kullanılır.",
                description_en="Standard German braille. Basic contractions and formatting signs.",
            ),
            ContractionLevel(
                id="kurzschrift",
                label_tr="Kurzschrift (Kısa Yazım)",
                label_en="Kurzschrift (Short Writing)",
                description_tr="Gelişmiş Alman Braille'i. Kapsamlı kısaltma sistemi. İleri düzey kullanıcılar için.",
                description_en="Advanced German braille. Extensive contraction system. For advanced users.",
            ),
        ],
    ),

    # ── Fransızca ───────────────────────────────────────────────────
    "fr": ContractionProfile(
        language_code="fr",
        language_name_tr="Fransızca",
        language_name_en="French",
        supports_contraction=True,
        default_level_id="abrégé",
        levels=[
            ContractionLevel(
                id="computer",
                label_tr="Bilgisayar Braille'i",
                label_en="Computer Braille",
                description_tr="8 noktalı birebir Braille.",
                description_en="8-dot one-to-one braille.",
            ),
            ContractionLevel(
                id="intégral",
                label_tr="Intégral (Tam Yazım)",
                label_en="Intégral (Full Writing)",
                description_tr="Fransızca kısaltmasız Braille. Her kelime tam yazılır.",
                description_en="French uncontracted braille. Every word written in full.",
            ),
            ContractionLevel(
                id="abrégé",
                label_tr="Abrégé (Kısaltmalı)",
                label_en="Abrégé (Contracted)",
                description_tr="Fransızca kısaltmalı Braille. Standart Fransızca Braille yazımı.",
                description_en="French contracted braille. Standard French braille writing.",
            ),
        ],
    ),

    # ── İspanyolca: Kısaltma sistemi yok ────────────────────────────
    "es": ContractionProfile(
        language_code="es",
        language_name_tr="İspanyolca",
        language_name_en="Spanish",
        supports_contraction=False,
        default_level_id="full_write",
        info_message_tr="İspanyolca Braille'de kısaltma sistemi bulunmamaktadır. Yalnızca tam yazım (Grade 1) kullanılır.",
        info_message_en="Spanish braille does not have a contraction system. Only full writing (Grade 1) is available.",
        levels=[
            ContractionLevel(
                id="computer",
                label_tr="Bilgisayar Braille'i",
                label_en="Computer Braille",
                description_tr="8 noktalı birebir Braille.",
                description_en="8-dot one-to-one braille.",
            ),
            ContractionLevel(
                id="full_write",
                label_tr="Tam Yazım (Grade 1)",
                label_en="Full Writing (Grade 1)",
                description_tr="İspanyolca Grade 1. Kısaltma kullanılmaz. Tüm İspanyolca Braille için standart.",
                description_en="Spanish Grade 1. No contractions. Standard for all Spanish braille.",
            ),
        ],
    ),

    # ── Arapça ──────────────────────────────────────────────────────
    "ar": ContractionProfile(
        language_code="ar",
        language_name_tr="Arapça",
        language_name_en="Arabic",
        supports_contraction=True,
        default_level_id="full_write",
        levels=[
            ContractionLevel(
                id="computer",
                label_tr="Bilgisayar Braille'i",
                label_en="Computer Braille",
                description_tr="8 noktalı birebir Braille.",
                description_en="8-dot one-to-one braille.",
            ),
            ContractionLevel(
                id="full_write",
                label_tr="Tam Yazım (Grade 1)",
                label_en="Full Writing (Grade 1)",
                description_tr="Arapça kısaltmasız Braille.",
                description_en="Arabic uncontracted braille.",
            ),
            ContractionLevel(
                id="contracted",
                label_tr="Kısaltmalı (Grade 2)",
                label_en="Contracted (Grade 2)",
                description_tr="Arapça kısaltmalı Braille.",
                description_en="Arabic contracted braille.",
            ),
        ],
    ),

    # ── Rusça ───────────────────────────────────────────────────────
    "ru": ContractionProfile(
        language_code="ru",
        language_name_tr="Rusça",
        language_name_en="Russian",
        supports_contraction=True,
        default_level_id="full_write",
        levels=[
            ContractionLevel(
                id="computer",
                label_tr="Bilgisayar Braille'i",
                label_en="Computer Braille",
                description_tr="8 noktalı birebir Braille.",
                description_en="8-dot one-to-one braille.",
            ),
            ContractionLevel(
                id="full_write",
                label_tr="Tam Yazım (Grade 1)",
                label_en="Full Writing (Grade 1)",
                description_tr="Rusça kısaltmasız Braille.",
                description_en="Russian uncontracted braille.",
            ),
            ContractionLevel(
                id="contracted",
                label_tr="Kısaltmalı (Grade 2)",
                label_en="Contracted (Grade 2)",
                description_tr="Rusça kısaltmalı Braille.",
                description_en="Russian contracted braille.",
            ),
        ],
    ),

    # ── Portekizce ──────────────────────────────────────────────────
    "pt": ContractionProfile(
        language_code="pt",
        language_name_tr="Portekizce",
        language_name_en="Portuguese",
        supports_contraction=True,
        default_level_id="full_write",
        levels=[
            ContractionLevel(
                id="computer",
                label_tr="Bilgisayar Braille'i",
                label_en="Computer Braille",
                description_tr="8 noktalı birebir Braille.",
                description_en="8-dot one-to-one braille.",
            ),
            ContractionLevel(
                id="full_write",
                label_tr="Tam Yazım (Grade 1)",
                label_en="Full Writing (Grade 1)",
                description_tr="Portekizce kısaltmasız Braille.",
                description_en="Portuguese uncontracted braille.",
            ),
            ContractionLevel(
                id="contracted",
                label_tr="Kısaltmalı (Grade 2)",
                label_en="Contracted (Grade 2)",
                description_tr="Portekizce kısaltmalı Braille.",
                description_en="Portuguese contracted braille.",
            ),
        ],
    ),
}


def get_contraction_profile(language_code: str) -> ContractionProfile | None:
    """Dil kodu için kısaltma profilini döndür."""
    return CONTRACTION_PROFILES.get(language_code)


def get_all_contraction_profiles() -> dict[str, ContractionProfile]:
    """Tüm kısaltma profillerini döndür."""
    return dict(CONTRACTION_PROFILES)