"""Offline unit tests for derived metrics. Run: python tests/test_metrics.py"""

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from aquarius.metrics import basis_bps, funding_apr, wrapper_spread_bps  # noqa: E402


def test_funding_apr():
    # 6.25e-6 per hour -> 24*365 hours
    assert math.isclose(funding_apr(6.25e-6), 6.25e-6 * 8760, rel_tol=1e-12)
    assert funding_apr(0.0) == 0.0


def test_wrapper_spread_bps():
    # a 0.1% richer than b -> ~10 bps
    assert math.isclose(wrapper_spread_bps(100.1, 100.0), 9.995, rel_tol=1e-3)
    assert wrapper_spread_bps(100.0, 100.0) == 0.0
    # antisymmetric
    assert math.isclose(wrapper_spread_bps(100.0, 100.1), -9.995, rel_tol=1e-3)


def test_basis_bps():
    # spot 1 bp above perp
    assert math.isclose(basis_bps(4472.0 * 1.0001, 4472.0), 1.0, rel_tol=1e-6)
    assert basis_bps(4472.0, 4472.0) == 0.0


if __name__ == "__main__":
    fns = [test_funding_apr, test_wrapper_spread_bps, test_basis_bps]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\nALL {len(fns)} METRIC TESTS PASSED")
