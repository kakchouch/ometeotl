from datetime import datetime, timezone
from importlib.util import (
    module_from_spec,
    spec_from_file_location,
)
from pathlib import Path

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "leaderboard"
    / "compute_leaderboard.py"
)


def load_leaderboard_module():
    spec = spec_from_file_location(
        "leaderboard_compute", MODULE_PATH
    )
    module = module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class DummyUser:
    def __init__(self, login):
        self.login = login


class DummyCommitMetadata:
    def __init__(self, date):
        self.author = type(
            "AuthorMetadata", (), {"date": date}
        )()


class DummyCommit:
    def __init__(self, login, date):
        self.author = DummyUser(login)
        self.commit = DummyCommitMetadata(date)


class DummyReview:
    def __init__(self, login, submitted_at):
        self.user = DummyUser(login)
        self.submitted_at = submitted_at


class DummyComment:
    def __init__(self, login, created_at):
        self.user = DummyUser(login)
        self.created_at = created_at


class DummyPullRequest:
    def __init__(
        self,
        login,
        merged_at,
        commits=None,
        reviews=None,
        comments=None,
    ):
        self.merged = True
        self.user = DummyUser(login)
        self.merged_at = merged_at
        self.additions = 30
        self.deletions = 10
        self._commits = commits or []
        self._reviews = reviews or []
        self._comments = comments or []

    def get_commits(self):
        return self._commits

    def get_reviews(self):
        return self._reviews

    def get_issue_comments(self):
        return self._comments


class DummyIssue:
    pull_request = None

    def __init__(self, login, created_at, comments=None):
        self.user = DummyUser(login)
        self.created_at = created_at
        self._comments = comments or []

    def get_comments(self):
        return self._comments


class DummyRepo:
    def __init__(self, pulls=None, issues=None):
        self._pulls = pulls or []
        self._issues = issues or []

    def get_pulls(self, state, sort, direction):
        return self._pulls

    def get_issues(self, state, sort, direction):
        return self._issues


def test_load_founder_identity_from_object_config():
    leaderboard = load_leaderboard_module()

    founder_identity = leaderboard._load_founder_identity(
        {
            "founder": {
                "username": "KaKChoUch",
                "aliases": ["Founder-Alt", "kakchouch"],
            }
        }
    )

    assert founder_identity.username == "kakchouch"
    assert founder_identity.aliases == frozenset(
        {"kakchouch", "founder-alt"}
    )


def test_collect_events_merges_founder_aliases_and_excludes_shares(
    monkeypatch,
):
    leaderboard = load_leaderboard_module()
    founder_identity = leaderboard.FounderIdentity(
        username="kakchouch",
        aliases=frozenset({"kakchouch", "founder-alt"}),
    )
    monkeypatch.setattr(
        leaderboard, "FOUNDER_IDENTITY", founder_identity
    )
    monkeypatch.setattr(
        leaderboard, "FOUNDER", founder_identity.username
    )
    monkeypatch.setattr(
        leaderboard,
        "NOW",
        datetime(2026, 4, 22, 12, 0, tzinfo=timezone.utc),
    )

    merged_at = datetime(2026, 4, 20, 12, 0, tzinfo=timezone.utc)
    repo = DummyRepo(
        pulls=[
            DummyPullRequest(
                login="founder-alt",
                merged_at=merged_at,
                commits=[DummyCommit("founder-alt", merged_at)],
            ),
            DummyPullRequest(
                login="alice",
                merged_at=merged_at,
                commits=[DummyCommit("alice", merged_at)],
                reviews=[DummyReview("bob", merged_at)],
            ),
        ],
        issues=[
            DummyIssue(login="kakchouch", created_at=merged_at)
        ],
    )

    events = leaderboard.collect_events(repo)

    assert set(events) == {"kakchouch", "alice", "bob"}
    assert all(user != "founder-alt" for user in events)

    raw_scores = leaderboard.compute_raw_scores(events)
    shares = leaderboard.compute_leaderboard_fallback(raw_scores)

    assert "kakchouch" not in shares
    assert set(shares) == {"alice", "bob"}
