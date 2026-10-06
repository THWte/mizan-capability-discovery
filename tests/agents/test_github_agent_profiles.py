"""Local structural validation for GitHub Custom Agent profiles
(``.github/agents/*.agent.md``).

**Honesty note (PART 22).** There is no official GitHub validator CLI
available in this local environment to confirm these profiles against the
live GitHub Copilot custom-agent schema. This test checks only what can be
checked locally and offline: that the expected 8 files exist, each has
well-formed YAML frontmatter with a required ``description``, that names
are unique, that declared tools are drawn from the known alias vocabulary
documented at
https://docs.github.com/en/copilot/reference/custom-agents-configuration,
and that the required 13-section body structure is present. This is a
structural sanity check, not proof the profiles are accepted by GitHub's
cloud agent runtime.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover - exercised only if PyYAML is absent
    yaml = None

_REPO_ROOT = Path(__file__).resolve().parents[2]
_AGENTS_DIR = _REPO_ROOT / ".github" / "agents"

_EXPECTED_PROFILE_NAMES = {
    "mizan-master",
    "conversation-intelligence",
    "architecture-guardian",
    "capability-discovery",
    "evidence-provenance",
    "qa-redteam",
    "git-pr-auditor",
    "evolution",
}

# Known tool aliases per the verified GitHub Custom Agents documentation
# (IDE/VS Code and github.com cloud agent). "github/*" and "playwright/*"
# style MCP-scoped entries are also valid.
_KNOWN_TOOL_ALIASES = {
    "execute",
    "shell",
    "bash",
    "powershell",
    "read",
    "edit",
    "write",
    "search",
    "grep",
    "glob",
    "agent",
    "custom-agent",
    "task",
    "web",
    "todo",
}

_REQUIRED_SECTIONS = (
    "ROLE",
    "MISSION",
    "READ-FIRST",
    "SOURCE OF TRUTH",
    "TOOLS / PERMISSIONS",
    "ALLOWED ACTIONS",
    "FORBIDDEN ACTIONS",
    "INPUT EXPECTATIONS",
    "OUTPUT FORMAT",
    "HANDOFF REQUIREMENT",
    "UNCERTAINTY RULE",
    "MEMORY RULE",
    "QUALITY GATE",
)

_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)


def _parse_frontmatter(text: str) -> dict:
    match = _FRONTMATTER_RE.match(text)
    assert match is not None, "file must start with a --- YAML frontmatter block"
    raw = match.group(1)
    if yaml is not None:
        data = yaml.safe_load(raw)
        assert isinstance(data, dict)
        return data
    # Minimal fallback parser (no PyYAML available): handles the simple
    # key: value and key: [a, b, c] forms used in these profiles only.
    data = {}
    for line in raw.splitlines():
        if not line.strip() or ":" not in line:
            continue
        key, _, value = line.partition(":")
        data[key.strip()] = value.strip()
    return data


def _profile_paths() -> list[Path]:
    assert _AGENTS_DIR.is_dir(), f"{_AGENTS_DIR} does not exist."
    return sorted(_AGENTS_DIR.glob("*.agent.md"))


def test_exactly_the_expected_eight_profiles_exist():
    paths = _profile_paths()
    names = {p.name.removesuffix(".agent.md") for p in paths}
    assert names == _EXPECTED_PROFILE_NAMES
    assert len(paths) == 8


@pytest.mark.parametrize("path", _profile_paths(), ids=lambda p: p.name)
def test_profile_has_valid_frontmatter_with_required_description(path: Path):
    text = path.read_text(encoding="utf-8")
    frontmatter = _parse_frontmatter(text)
    assert frontmatter.get("description"), f"{path.name} missing required 'description'."
    assert len(frontmatter["description"]) <= 30_000


@pytest.mark.parametrize("path", _profile_paths(), ids=lambda p: p.name)
def test_profile_tools_are_known_aliases_or_mcp_scoped(path: Path):
    text = path.read_text(encoding="utf-8")
    frontmatter = _parse_frontmatter(text)
    tools = frontmatter.get("tools")
    if tools is None:
        return
    if isinstance(tools, str):
        tools = [t.strip() for t in tools.strip("[]").split(",") if t.strip()]
    for tool in tools:
        tool = tool.strip().strip('"').strip("'")
        if "/" in tool:
            # MCP-server-scoped tool reference, e.g. "github/*".
            continue
        assert tool in _KNOWN_TOOL_ALIASES, (
            f"{path.name} declares unknown tool alias {tool!r}."
        )


@pytest.mark.parametrize("path", _profile_paths(), ids=lambda p: p.name)
def test_profile_body_has_all_required_sections(path: Path):
    text = path.read_text(encoding="utf-8")
    for section in _REQUIRED_SECTIONS:
        assert f"# {section}" in text, f"{path.name} missing required section '{section}'."


def test_no_duplicate_profile_names_across_files():
    seen = set()
    for path in _profile_paths():
        text = path.read_text(encoding="utf-8")
        frontmatter = _parse_frontmatter(text)
        name = frontmatter.get("name")
        assert name, f"{path.name} missing 'name' field."
        assert name not in seen, f"Duplicate custom agent name: {name!r}."
        seen.add(name)


def test_architecture_guardian_and_evolution_profiles_have_no_edit_tool():
    """Structural reflection of 'cannot self-approve / cannot self-adopt':
    these two profiles must not declare the edit tool."""
    for filename in ("architecture-guardian.agent.md", "evolution.agent.md"):
        path = _AGENTS_DIR / filename
        text = path.read_text(encoding="utf-8")
        frontmatter = _parse_frontmatter(text)
        tools = frontmatter.get("tools") or []
        if isinstance(tools, str):
            tools = [t.strip() for t in tools.strip("[]").split(",") if t.strip()]
        normalized = {t.strip().strip('"').strip("'") for t in tools}
        assert "edit" not in normalized and "write" not in normalized, (
            f"{filename} must not declare edit/write tools."
        )
