import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from entry_score_engine import label_from_score


def test_entry_score_85_creates_entry():
    assert label_from_score(85, "SAFE") == "ENTRY"


def test_entry_score_97_creates_ss_plus():
    assert label_from_score(97, "SAFE") == "SS_PLUS"


def test_near_entry_generated_at_70_to_84():
    assert label_from_score(70, "SAFE") == "NEAR_ENTRY"
    assert label_from_score(84, "SAFE") == "NEAR_ENTRY"
