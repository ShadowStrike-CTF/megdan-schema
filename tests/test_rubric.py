import itertools

import pytest
from pydantic import ValidationError

from megdan_schema.poe import DifficultyFactors
from megdan_schema.rubric import (
    TIER_POINTS,
    Assessment,
    PointsOverride,
    Tier,
    assess,
    override,
    points_for_tier,
    score_factors,
    tier_for_score,
)

EXPECTED = {
    0: (Tier.D1, 100), 1: (Tier.D1, 100), 2: (Tier.D1, 100),
    3: (Tier.D2, 200), 4: (Tier.D2, 200), 5: (Tier.D2, 200),
    6: (Tier.D3, 300), 7: (Tier.D3, 300), 8: (Tier.D3, 300),
    9: (Tier.D4, 400), 10: (Tier.D4, 400),
    11: (Tier.D5, 500), 12: (Tier.D5, 500),
}  # fmt: skip


@pytest.mark.parametrize("score,expected", sorted(EXPECTED.items()))
def test_every_score_maps_to_tier_and_points(score, expected):
    tier, points = expected
    assert tier_for_score(score) is tier
    assert points_for_tier(tier) == points


def test_all_factor_combinations():
    for combo in itertools.product(range(4), repeat=4):
        f = DifficultyFactors(tool_coverage=combo[0], hops=combo[1], obscurity=combo[2], traps=combo[3])
        a = assess(f)
        assert a.score == sum(combo) == score_factors(f)
        assert (a.tier, a.points) == EXPECTED[sum(combo)]


@pytest.mark.parametrize("score", [-1, 13, 100])
def test_tier_for_score_out_of_range(score):
    with pytest.raises(ValueError):
        tier_for_score(score)


@pytest.mark.parametrize("score", [1.0, "3", None, True])
def test_tier_for_score_wrong_type(score):
    with pytest.raises(TypeError):
        tier_for_score(score)


def test_points_for_tier_accepts_string_and_rejects_unknown():
    assert points_for_tier("D3") == 300
    with pytest.raises(ValueError):
        points_for_tier("D6")


def test_tier_points_table():
    assert TIER_POINTS == {Tier.D1: 100, Tier.D2: 200, Tier.D3: 300, Tier.D4: 400, Tier.D5: 500}


def test_assessment_model():
    a = assess(DifficultyFactors(tool_coverage=3, hops=3, obscurity=3, traps=3))
    assert a == Assessment(score=12, tier=Tier.D5, points=500)


def test_override_ok():
    o = override(250, "Hand-tuned after playtest")
    assert o == PointsOverride(points=250, reason="Hand-tuned after playtest")
    assert override(0, "x").points == 0


@pytest.mark.parametrize("reason", ["", " ", "\t\n"])
def test_override_requires_reason(reason):
    with pytest.raises(ValueError):
        override(300, reason)


@pytest.mark.parametrize("points", [-1, 2.5, "300", True])
def test_override_rejects_bad_points(points):
    with pytest.raises(ValidationError):
        override(points, "reason")


def test_override_requires_str_reason():
    with pytest.raises(ValidationError):
        override(300, None)
