"""Bağımlılıksız doğruluk, eşleştirilmiş test ve etiket uyumu hesapları."""

from collections import Counter
import math


def _proportion(k, n):
    if type(n) is not int or type(k) is not int or n <= 0 or not 0 <= k <= n:
        raise ValueError("Require integer counts with n > 0 and 0 <= k <= n")
    return k / n


def wald_ci(k, n):
    """95% Wald: p=k/n, bounds=p ± 1.96*sqrt(p*(1-p)/n), clipped to [0,1]."""
    p = _proportion(k, n)
    margin = 1.96 * math.sqrt(p * (1 - p) / n)
    return p, max(0.0, p - margin), min(1.0, p + margin)


def wilson_ci(k, n):
    """95% Wilson: (p+z²/(2n) ± z*sqrt(p(1-p)/n+z²/(4n²)))/(1+z²/n), z=1.96."""
    p = _proportion(k, n)
    z = 1.96
    denominator = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denominator
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return p, max(0.0, center - margin), min(1.0, center + margin)


def mcnemar(a_correct: list[bool], b_correct: list[bool]) -> dict:
    """Paired test: p_exact=min(1,2*Σ C(b+c,i)/2**(b+c)), i=0..min(b,c).

    Continuity correction: x=(abs(b-c)-1)**2/(b+c), p_chi2_cc=erfc(sqrt(x/2)).
    b=a_only, c=b_only; fewer than 25 discordant pairs recommends exact.
    """
    if len(a_correct) != len(b_correct):
        raise ValueError("Paired samples must have equal lengths")
    if any(type(value) is not bool for value in (*a_correct, *b_correct)):
        raise ValueError("Correctness values must be booleans")
    counts = Counter(zip(a_correct, b_correct))
    b, c = counts[True, False], counts[False, True]
    discordant = b + c
    # Tamsayı toplamı büyük örneklemlerde kayan noktalı kombinasyon taşmasını önler.
    tail = sum(math.comb(discordant, i) for i in range(min(b, c) + 1))
    p_exact = min(1.0, (2 * tail) / (1 << discordant))
    x = (abs(b - c) - 1) ** 2 / discordant if discordant else None
    return {
        "n": len(a_correct), "both_correct": counts[True, True],
        "a_only": b, "b_only": c, "both_wrong": counts[False, False],
        "p_exact": p_exact,
        "p_chi2_cc": math.erfc(math.sqrt(x / 2)) if x is not None else None,
        "method": "exact" if discordant < 25 else "chi2_cc",
    }


def cohen_kappa(a: list, b: list) -> dict:
    """κ=(po-pe)/(1-pe), po=agreements/n, pe=Σ count_a(l)*count_b(l)/n².

    Labels preserve first appearance; confusion[i][j] counts a=labels[i],
    b=labels[j]. Empty samples and pe=1 have undefined κ (None with a note).
    """
    if len(a) != len(b):
        raise ValueError("Paired labels must have equal lengths")
    labels = list(dict.fromkeys([*a, *b]))
    index = {label: i for i, label in enumerate(labels)}
    confusion = [[0 for _ in labels] for _ in labels]
    for left, right in zip(a, b):
        confusion[index[left]][index[right]] += 1
    n = len(a)
    result = {"kappa": None, "po": None, "pe": None, "n": n,
              "labels": labels, "confusion": confusion}
    if not n:
        result["note"] = "Kappa is undefined for empty samples."
        return result
    counts_a, counts_b = Counter(a), Counter(b)
    po = sum(left == right for left, right in zip(a, b)) / n
    pe = sum(counts_a[label] * counts_b[label] for label in labels) / (n * n)
    result.update(po=po, pe=pe)
    if pe == 1:
        result["note"] = "Kappa is undefined because expected agreement pe=1."
    else:
        result["kappa"] = (po - pe) / (1 - pe)
    return result
