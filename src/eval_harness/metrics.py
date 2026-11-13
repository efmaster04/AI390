"""Statistical functions for the Week 2 evaluation harness (95% CI, McNemar, Cohen's kappa)."""

import math
import statistics


def proportion_ci95(successes, n):
    """Compute p_hat and the Handbook Section 5 95% confidence interval:
    p_hat +/- 1.96 * sqrt(p_hat * (1 - p_hat) / n), clamped to [0.0, 1.0].
    """
    if not n or n <= 0:
        return {"value": None, "ci95": None, "n": 0}
    p_hat = successes / n
    margin = 1.96 * math.sqrt(p_hat * (1.0 - p_hat) / n)
    low = max(0.0, round(p_hat - margin, 4))
    high = min(1.0, round(p_hat + margin, 4))
    return {
        "value": round(p_hat, 4),
        "ci95": [low, high],
        "n": n,
        "successes": successes,
    }


def mcnemar_test(outcomes_a, outcomes_b):
    """Paired McNemar test between two prompt versions on the same n test cases (W2.5).

    outcomes_a, outcomes_b: sequences of booleans of equal length n.
    Returns contingency counts (n11, n10, n01, n00), chi2 statistics, exact binomial p-value,
    and accuracy difference (p_b - p_a).
    """
    if len(outcomes_a) != len(outcomes_b) or not outcomes_a:
        raise ValueError("Paired outcomes must have equal non-zero length")

    n = len(outcomes_a)
    n11 = sum(1 for a, b in zip(outcomes_a, outcomes_b) if a and b)
    n10 = sum(1 for a, b in zip(outcomes_a, outcomes_b) if a and not b)
    n01 = sum(1 for a, b in zip(outcomes_a, outcomes_b) if not a and b)
    n00 = sum(1 for a, b in zip(outcomes_a, outcomes_b) if not a and not b)

    discordant = n10 + n01
    if discordant == 0:
        chi2 = 0.0
        chi2_cc = 0.0
        exact_p = 1.0
    else:
        chi2 = ((n10 - n01) ** 2) / discordant
        chi2_cc = (max(0, abs(n10 - n01) - 1) ** 2) / discordant
        k = min(n10, n01)
        tail = sum(math.comb(discordant, i) for i in range(k + 1)) / (2 ** discordant)
        exact_p = min(1.0, 2.0 * tail)

    acc_a = (n11 + n10) / n
    acc_b = (n11 + n01) / n
    return {
        "n": n,
        "n11_both_pass": n11,
        "n10_a_only": n10,
        "n01_b_only": n01,
        "n00_both_fail": n00,
        "discordant_pairs": discordant,
        "chi2": round(chi2, 4),
        "chi2_continuity_corrected": round(chi2_cc, 4),
        "exact_binomial_p": round(exact_p, 6),
        "significant_at_0_05": exact_p < 0.05,
        "accuracy_a": round(acc_a, 4),
        "accuracy_b": round(acc_b, 4),
        "delta_b_minus_a": round(acc_b - acc_a, 4),
    }


def cohens_kappa(human_labels, judge_labels):
    """Compute Cohen's kappa between binary human labels and LLM judge labels (W2.6)."""
    if len(human_labels) != len(judge_labels) or not human_labels:
        raise ValueError("Human and judge label lists must have equal non-zero length")

    n = len(human_labels)
    tp = sum(1 for h, j in zip(human_labels, judge_labels) if h and j)
    fp = sum(1 for h, j in zip(human_labels, judge_labels) if not h and j)
    fn = sum(1 for h, j in zip(human_labels, judge_labels) if h and not j)
    tn = sum(1 for h, j in zip(human_labels, judge_labels) if not h and not j)

    p_o = (tp + tn) / n
    p_human_pos = (tp + fn) / n
    p_human_neg = (fp + tn) / n
    p_judge_pos = (tp + fp) / n
    p_judge_neg = (fn + tn) / n
    p_e = (p_human_pos * p_judge_pos) + (p_human_neg * p_judge_neg)

    if math.isclose(1.0 - p_e, 0.0):
        kappa = 1.0
    else:
        kappa = (p_o - p_e) / (1.0 - p_e)

    return {
        "n": n,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "observed_agreement_po": round(p_o, 4),
        "expected_agreement_pe": round(p_e, 4),
        "cohens_kappa": round(kappa, 4),
    }


def median_p50(values):
    """Return the median (p50) of numeric values, or None if empty."""
    clean = [float(v) for v in values if v is not None]
    if not clean:
        return None
    return round(statistics.median(clean), 4)
