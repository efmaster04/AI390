import math

import pytest

from eval.stats import cohen_kappa, mcnemar, wald_ci, wilson_ci


def test_wald_known_value():
    assert wald_ci(8, 10) == pytest.approx((0.8, 0.552, 1.0), abs=0.0005)


def test_wilson_known_value_and_boundaries():
    assert wilson_ci(8, 10) == pytest.approx((0.8, 0.490, 0.943), abs=0.0005)
    assert wald_ci(0, 10) == (0, 0, 0)
    assert wald_ci(10, 10) == (1, 1, 1)
    assert wilson_ci(0, 10)[2] > 0
    assert wilson_ci(10, 10)[1] < 1


@pytest.mark.parametrize("function", [wald_ci, wilson_ci])
@pytest.mark.parametrize("k,n", [(0, 0), (-1, 10), (11, 10), (1, -1)])
def test_invalid_counts(function, k, n):
    with pytest.raises(ValueError):
        function(k, n)


def test_mcnemar_exact_and_table():
    result = mcnemar([True, True] + [False] * 7, [True, False] + [True] * 6 + [False])
    assert result == {
        "n": 9, "both_correct": 1, "a_only": 1, "b_only": 6,
        "both_wrong": 1, "p_exact": 0.125,
        "p_chi2_cc": math.erfc(math.sqrt((16 / 7) / 2)), "method": "exact",
    }


def test_mcnemar_no_discordance():
    result = mcnemar([True, False], [True, False])
    assert result["p_exact"] == 1.0
    assert result["p_chi2_cc"] is None
    assert mcnemar([], [])["n"] == 0


def test_mcnemar_chi_square_recommendation():
    result = mcnemar([True] * 25, [False] * 25)
    assert result["method"] == "chi2_cc"
    assert result["p_exact"] == 2 / 2**25
    assert result["p_chi2_cc"] == pytest.approx(math.erfc(math.sqrt(24**2 / 50)))
    assert mcnemar([True, False], [False, True])["p_chi2_cc"] == pytest.approx(math.erfc(0.5))


def test_mcnemar_unequal_lengths():
    with pytest.raises(ValueError):
        mcnemar([True], [])


def test_kappa_perfect_agreement():
    result = cohen_kappa([1, 1, 0, 0], [1, 1, 0, 0])
    assert result["kappa"] == 1.0
    assert result["labels"] == [1, 0]
    assert result["confusion"] == [[2, 0], [0, 2]]


def test_kappa_hand_calculated():
    a = [1] * 25 + [0] * 25
    b = [1] * 20 + [0] * 5 + [1] * 10 + [0] * 15
    result = cohen_kappa(a, b)
    po = (20 + 15) / 50
    pe = (25 / 50) * (30 / 50) + (25 / 50) * (20 / 50)
    assert result["po"] == po
    assert result["pe"] == pe
    assert result["kappa"] == pytest.approx((po - pe) / (1 - pe))
    assert result["confusion"] == [[20, 5], [10, 15]]


def test_kappa_undefined_empty_and_mismatched():
    result = cohen_kappa(["pass"] * 4, ["pass"] * 4)
    assert result["pe"] == 1
    assert result["kappa"] is None
    assert "note" in result
    assert cohen_kappa([], [])["kappa"] is None
    with pytest.raises(ValueError):
        cohen_kappa([1], [])
