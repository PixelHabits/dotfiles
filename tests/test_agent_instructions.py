"""Guards for the shared agent instructions and skills.

Run: python3 tests/test_agent_instructions.py
"""

import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
AGENTS = ROOT / "dot_config" / "agents" / "AGENTS.md"
CLAUDE = ROOT / "dot_config" / "claude" / "CLAUDE.md"
SKILLS = ROOT / "dot_agents" / "skills"

# Tokens that rot: release candidates, PR numbers, ISO dates, semver, em dashes.
STALE = {
    "release candidate": re.compile(r"\brc\.\d+\b"),
    "PR number": re.compile(r"(?<![\w/])#\d{2,}\b"),
    "ISO date": re.compile(r"\b20\d\d-\d\d-\d\d\b"),
    "semver": re.compile(r"\b\d+\.\d+\.\d+\b"),
    "em dash": re.compile("—|–"),
}

# Rough budget: about four characters per token.
AGENTS_MAX_CHARS = 7_000
SKILL_MAX_CHARS = 9_000


def instruction_files():
    yield AGENTS
    yield from sorted(SKILLS.glob("*/SKILL.md"))
    yield from sorted(SKILLS.glob("*/references/*.md"))


class AgentInstructions(unittest.TestCase):
    def test_claude_imports_the_shared_core(self):
        first = CLAUDE.read_text().lstrip().splitlines()[0]
        self.assertEqual(first, "@~/.config/agents/AGENTS.md")

    def test_core_stays_small(self):
        self.assertLessEqual(len(AGENTS.read_text()), AGENTS_MAX_CHARS)

    def test_skills_stay_small(self):
        for skill in SKILLS.glob("*/SKILL.md"):
            with self.subTest(skill=skill.parent.name):
                self.assertLessEqual(len(skill.read_text()), SKILL_MAX_CHARS)

    def test_skill_frontmatter(self):
        for skill in SKILLS.glob("*/SKILL.md"):
            with self.subTest(skill=skill.parent.name):
                text = skill.read_text()
                self.assertTrue(text.startswith("---\n"))
                head = text.split("---\n", 2)[1]
                self.assertIn(f"name: {skill.parent.name}\n", head)
                self.assertIn("description:", head)

    def test_core_names_every_skill(self):
        core = AGENTS.read_text()
        for skill in SKILLS.glob("*/SKILL.md"):
            with self.subTest(skill=skill.parent.name):
                self.assertIn(f"`{skill.parent.name}`", core)

    def test_no_stale_tokens(self):
        for path in instruction_files():
            text = path.read_text()
            for label, pattern in STALE.items():
                with self.subTest(file=path.relative_to(ROOT), token=label):
                    self.assertIsNone(pattern.search(text), pattern.search(text))


if __name__ == "__main__":
    unittest.main()
