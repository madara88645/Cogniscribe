import timeit
import re

text = "Bu bir test cümlesidir. Ip le mantasyon gibi kelimeler içerebilir. A B C D E F G H I J K L M N O P Q R S T U V W X Y Z a b c d e f g h i j k l m n o p q r s t u v w x y z 1 2 3 4 5 6 7 8 9 0 çğıöşüÇĞİÖŞÜ" * 10

def original_looks_fragmented(text: str) -> bool:
    if not text:
        return True
    tokens = re.findall(r"[a-zA-Z0-9çğıöşüÇĞİÖŞÜ]+", text.lower())
    if len(tokens) < 4:
        return False
    short_tokens = sum(1 for token in tokens if len(token) <= 2)
    short_ratio = short_tokens / max(1, len(tokens))
    split_hint = bool(re.search(r"\b[iı]p\s+le\s+mantasyon\b", text.lower()))
    return short_ratio >= 0.35 or split_hint

def original_fragment_ratio(text: str) -> float:
    tokens = re.findall(r"[a-zA-Z0-9çğıöşüÇĞİÖŞÜ]+", (text or "").lower())
    if not tokens:
        return 1.0
    short_tokens = sum(1 for token in tokens if len(token) <= 2)
    return short_tokens / max(1, len(tokens))

TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9çğıöşüÇĞİÖŞÜ]+")
SPLIT_HINT_PATTERN = re.compile(r"\b[iı]p\s+le\s+mantasyon\b")

def optimized_looks_fragmented(text: str) -> bool:
    if not text:
        return True
    tokens = TOKEN_PATTERN.findall(text.lower())
    if len(tokens) < 4:
        return False
    short_tokens = sum(1 for token in tokens if len(token) <= 2)
    short_ratio = short_tokens / max(1, len(tokens))
    split_hint = bool(SPLIT_HINT_PATTERN.search(text.lower()))
    return short_ratio >= 0.35 or split_hint

def optimized_fragment_ratio(text: str) -> float:
    tokens = TOKEN_PATTERN.findall((text or "").lower())
    if not tokens:
        return 1.0
    short_tokens = sum(1 for token in tokens if len(token) <= 2)
    return short_tokens / max(1, len(tokens))

if __name__ == '__main__':
    n = 10000
    t_orig_lf = timeit.timeit("original_looks_fragmented(text)", globals=globals(), number=n)
    t_opt_lf = timeit.timeit("optimized_looks_fragmented(text)", globals=globals(), number=n)

    t_orig_fr = timeit.timeit("original_fragment_ratio(text)", globals=globals(), number=n)
    t_opt_fr = timeit.timeit("optimized_fragment_ratio(text)", globals=globals(), number=n)

    print(f"Original _looks_fragmented: {t_orig_lf:.4f} s")
    print(f"Optimized _looks_fragmented: {t_opt_lf:.4f} s")
    if t_orig_lf > 0:
        print(f"Improvement: {((t_orig_lf - t_opt_lf) / t_orig_lf) * 100:.2f}%")

    print(f"Original _fragment_ratio: {t_orig_fr:.4f} s")
    print(f"Optimized _fragment_ratio: {t_opt_fr:.4f} s")
    if t_orig_fr > 0:
        print(f"Improvement: {((t_orig_fr - t_opt_fr) / t_orig_fr) * 100:.2f}%")
