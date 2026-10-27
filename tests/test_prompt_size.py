"""Keep the skill's routinely loaded text within its declared product budget."""
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1] / 'skill/physicsguard'


def test_skill_and_route_text_stay_within_budget():
    entry = (SKILL / 'SKILL.md').read_text(encoding='utf-8')
    debugging = (SKILL / 'references/routes/ai-debugging.md').read_text(encoding='utf-8')
    assert len(entry) <= 6000
    assert len(debugging) <= 5000
    assert len(debugging.encode('utf-8')) <= 5000
    assert len(entry) + len(debugging) <= 10000
    for path in (SKILL / 'references').rglob('*.md'):
        assert len(path.read_text(encoding='utf-8')) <= 12000, path.relative_to(SKILL)
