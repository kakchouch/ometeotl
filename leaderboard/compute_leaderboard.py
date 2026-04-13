#!/usr/bin/env python3
"""
Ometeotl Activity Leaderboard — Reference Implementation

Computes activity-shares for all contributors based on:
  1. Weighted raw activity scores with exponential recency decay
  2. z-score normalization
  3. Adjusted score via f(z) = exp(sinh(z) / k) with adaptive k
  4. Proportional share allocation (founder excluded)

Usage:
  GITHUB_TOKEN=<token> REPO_FULL_NAME=owner/repo python compute_leaderboard.py

Reads configuration from: leaderboard/config.json
Outputs:
  - leaderboard/LEADERBOARD.md   (human-readable)
  - leaderboard/leaderboard-data.json (machine-readable, auditable)
"""

import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# GitHub API helpers
# ---------------------------------------------------------------------------

try:
    from github import Github
except ImportError:
    sys.exit("PyGithub is required. Install with: pip install PyGithub")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "config.json"

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

FOUNDER = CONFIG["founder"].lower()
TOTAL_SHARES = CONFIG["total_shares"]
K_FLOOR = CONFIG["k_floor"]
K_OFFSET = CONFIG["k_offset"]
Z_MIN = CONFIG["z_clamp_min"]
Z_MAX = CONFIG["z_clamp_max"]
HALF_LIFE = CONFIG["half_life_days"]
ACTIVE_WINDOW = CONFIG["active_contributor_window_days"]
MIN_CONTRIBUTORS = CONFIG["min_active_contributors_for_z_score"]
WEIGHTS = CONFIG["weights"]
LINES_CAP = WEIGHTS["lines_changed_cap_per_pr"]

NOW = datetime.now(timezone.utc)


def recency_factor(event_date):
    """Exponential half-life decay: r(t) = 2^(-t/τ)."""
    age_days = (NOW - event_date).total_seconds() / 86400
    return 2 ** (-age_days / HALF_LIFE)


def is_active(last_event_date):
    """A contributor is active if their most recent event is within the window."""
    age_days = (NOW - last_event_date).total_seconds() / 86400
    return age_days <= ACTIVE_WINDOW


def compute_k(n_active):
    """Adaptive smoothing factor: k = max(k_floor, k_offset - n_active)."""
    return max(K_FLOOR, K_OFFSET - n_active)


def adjusted_score(z, k):
    """f(z) = exp(sinh(z_clamped) / k)."""
    z_clamped = max(Z_MIN, min(z, Z_MAX))
    return math.exp(math.sinh(z_clamped) / k)


# ---------------------------------------------------------------------------
# Data collection from GitHub API
# ---------------------------------------------------------------------------


def collect_events(repo):
    """
    Collect all scored events for each contributor.
    Returns: dict[username] -> list of (event_type, datetime)
    """
    events = {}  # username -> [(event_type, date, extra)]

    def add_event(user, event_type, date, extra=None):
        if user is None:
            return
        username = user.lower()
        # Exclude bots
        if username.endswith("[bot]") or username == "github-actions":
            return
        if username not in events:
            events[username] = []
        events[username].append((event_type, date, extra))

    # --- Merged PRs ---
    print("Fetching merged pull requests...")
    pulls = repo.get_pulls(state="closed", sort="updated", direction="desc")
    for pr in pulls:
        if not pr.merged:
            continue
        author = pr.user.login if pr.user else None
        merged_at = pr.merged_at
        if merged_at is None:
            continue
        if merged_at.tzinfo is None:
            merged_at = merged_at.replace(tzinfo=timezone.utc)

        add_event(author, "merged_pr", merged_at)

        # Lines changed (capped)
        lines = min(pr.additions + pr.deletions, LINES_CAP)
        add_event(author, "lines_changed", merged_at, extra=lines)

        # Commits in the PR
        try:
            commits = pr.get_commits()
            for commit in commits:
                c_author = commit.author
                if c_author:
                    c_date = commit.commit.author.date
                    if c_date and c_date.tzinfo is None:
                        c_date = c_date.replace(tzinfo=timezone.utc)
                    if c_date:
                        add_event(c_author.login, "commit_in_merged_pr", c_date)
        except Exception:
            pass  # Some PRs may not have accessible commits

        # PR reviews
        try:
            reviews = pr.get_reviews()
            for review in reviews:
                reviewer = review.user
                if reviewer and reviewer.login.lower() != (author or "").lower():
                    r_date = review.submitted_at
                    if r_date and r_date.tzinfo is None:
                        r_date = r_date.replace(tzinfo=timezone.utc)
                    if r_date:
                        add_event(reviewer.login, "pr_review", r_date)
        except Exception:
            pass

        # PR comments
        try:
            comments = pr.get_issue_comments()
            for comment in comments:
                commenter = comment.user
                if commenter:
                    c_date = comment.created_at
                    if c_date and c_date.tzinfo is None:
                        c_date = c_date.replace(tzinfo=timezone.utc)
                    if c_date:
                        add_event(commenter.login, "pr_comment", c_date)
        except Exception:
            pass

    # --- Issues ---
    print("Fetching issues...")
    issues = repo.get_issues(state="all", sort="updated", direction="desc")
    for issue in issues:
        if issue.pull_request is not None:
            continue  # Skip PRs (they appear as issues too)
        author = issue.user.login if issue.user else None
        created = issue.created_at
        if created and created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if created:
            add_event(author, "issue_opened", created)

        # Issue comments
        try:
            comments = issue.get_comments()
            for comment in comments:
                commenter = comment.user
                if commenter:
                    c_date = comment.created_at
                    if c_date and c_date.tzinfo is None:
                        c_date = c_date.replace(tzinfo=timezone.utc)
                    if c_date:
                        add_event(commenter.login, "issue_comment", c_date)
        except Exception:
            pass

    return events


# ---------------------------------------------------------------------------
# Score computation
# ---------------------------------------------------------------------------


def compute_raw_scores(events):
    """Compute weighted, recency-adjusted raw scores."""
    scores = {}
    for username, user_events in events.items():
        total = 0.0
        for event_type, date, extra in user_events:
            r = recency_factor(date)
            if event_type == "lines_changed" and extra is not None:
                total += WEIGHTS["lines_changed_per_unit"] * extra * r
            elif event_type in WEIGHTS:
                total += WEIGHTS[event_type] * r
        scores[username] = round(total, 4)
    return scores


def compute_z_scores(raw_scores):
    """Compute z-scores (centered, reduced) over all contributors."""
    values = list(raw_scores.values())
    n = len(values)

    if n < 2:
        return {u: 0.0 for u in raw_scores}

    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / (n - 1)  # Bessel
    std = math.sqrt(variance)

    if std == 0:
        return {u: 0.0 for u in raw_scores}

    return {u: round((s - mean) / std, 6) for u, s in raw_scores.items()}


def compute_leaderboard(raw_scores, z_scores, n_active):
    """Compute adjusted scores and allocate shares."""
    k = compute_k(n_active)

    # Adjusted scores for everyone
    adjusted = {u: adjusted_score(z, k) for u, z in z_scores.items()}

    # Share allocation (founder excluded)
    contributors = {u: s for u, s in adjusted.items() if u != FOUNDER}

    if not contributors:
        return k, adjusted, {}

    total_adj = sum(contributors.values())

    if total_adj == 0:
        equal_share = round(TOTAL_SHARES / len(contributors), 1)
        return k, adjusted, {u: equal_share for u in contributors}

    shares = {
        u: round((s / total_adj) * TOTAL_SHARES, 1) for u, s in contributors.items()
    }

    # Fix rounding residual
    residual = round(TOTAL_SHARES - sum(shares.values()), 1)
    if residual != 0 and shares:
        top_user = max(shares, key=shares.get)
        shares[top_user] = round(shares[top_user] + residual, 1)

    return k, adjusted, shares


def compute_leaderboard_fallback(raw_scores):
    """Fallback: proportional allocation when n_active < min threshold."""
    contributors = {u: s for u, s in raw_scores.items() if u != FOUNDER}
    total = sum(contributors.values())

    if total == 0:
        if not contributors:
            return {}
        equal = round(TOTAL_SHARES / len(contributors), 1)
        return {u: equal for u in contributors}

    shares = {u: round((s / total) * TOTAL_SHARES, 1) for u, s in contributors.items()}
    residual = round(TOTAL_SHARES - sum(shares.values()), 1)
    if residual != 0 and shares:
        top_user = max(shares, key=shares.get)
        shares[top_user] = round(shares[top_user] + residual, 1)

    return shares


# ---------------------------------------------------------------------------
# Output generation
# ---------------------------------------------------------------------------


def generate_markdown(data, repo_name):
    """Generate LEADERBOARD.md content."""
    lines = [
        "# 🜂 Ometeotl Activity Leaderboard",
        "",
        f"> Last updated: {NOW.strftime('%Y-%m-%d %H:%M')} UTC",
        f"> Repository: {repo_name}",
        f"> Total activity-shares: **{TOTAL_SHARES}**",
        f"> Scoring: `f(z) = exp(sinh(z) / k)` — k = max({K_FLOOR}, {K_OFFSET} − n_active)",
        f"> Active k: **{data['k']}** (n_active = {data['n_active']})",
        "",
    ]

    if data.get("fallback"):
        lines.append(
            "*Cold start mode: fewer than "
            f"{MIN_CONTRIBUTORS} active contributors. "
            "Shares allocated proportionally to raw scores.*"
        )
        lines.append("")

    # Main leaderboard
    lines.append("## Activity Shares")
    lines.append("")

    if data.get("fallback"):
        lines.append("| Rank | Contributor | Raw Score | Shares |")
        lines.append("|------|-------------|-----------|--------|")
        ranked = sorted(data["shares"].items(), key=lambda x: -x[1])
        for rank, (user, share) in enumerate(ranked, 1):
            raw = data["raw_scores"].get(user, 0)
            lines.append(f"| {rank} | @{user} | {raw:.1f} | {share:.1f} |")
    else:
        lines.append(
            "| Rank | Contributor | Raw Score | z-Score | Adj. Score | Shares |"
        )
        lines.append(
            "|------|-------------|-----------|---------|------------|--------|"
        )
        ranked = sorted(data["shares"].items(), key=lambda x: -x[1])
        for rank, (user, share) in enumerate(ranked, 1):
            raw = data["raw_scores"].get(user, 0)
            z = data["z_scores"].get(user, 0)
            adj = data["adjusted_scores"].get(user, 0)
            lines.append(
                f"| {rank} | @{user} | {raw:.1f} | {z:+.2f} | {adj:.4f} | {share:.1f} |"
            )

    # Founder section
    if FOUNDER in data["raw_scores"]:
        lines.extend(
            [
                "",
                "---",
                "",
                "*Out-of-competition — Founder*",
                "",
            ]
        )
        raw = data["raw_scores"][FOUNDER]
        z = data["z_scores"].get(FOUNDER, 0)
        adj = data["adjusted_scores"].get(FOUNDER, 0)
        if data.get("fallback"):
            lines.append("| Contributor | Raw Score |")
            lines.append("|-------------|-----------|")
            lines.append(f"| @{FOUNDER} | {raw:.1f} |")
        else:
            lines.append("| Contributor | Raw Score | z-Score | Adj. Score |")
            lines.append("|-------------|-----------|---------|------------|")
            lines.append(f"| @{FOUNDER} | {raw:.1f} | {z:+.2f} | {adj:.4f} |")

    # Methodology
    lines.extend(
        [
            "",
            "---",
            "",
            "<details>",
            "<summary>Methodology</summary>",
            "",
            "The raw activity score aggregates contributions "
            "(merged PRs, reviews, issues, comments) weighted by type "
            f"and by an exponential recency factor (half-life = {HALF_LIFE} days).",
            "",
            "The z-score is computed over all contributors (founder included).",
            "",
            f"The adjusted score uses `f(z) = exp(sinh(z) / k)` with "
            f"k = max({K_FLOOR}, {K_OFFSET} − n_active).",
            "",
            "Activity-shares are proportional to adjusted scores, "
            "founder excluded. Total = 1000.",
            "",
            "Full specification: "
            "[LEADERBOARD_SPEC.md](leaderboard/LEADERBOARD_SPEC.md)",
            "",
            "</details>",
            "",
        ]
    )

    return "\n".join(lines)


def generate_hugo_page(data, repo_name):
    """Generate a Hugo content page for the doc-site with live leaderboard data."""
    date_str = NOW.strftime("%Y-%m-%d")
    time_str = NOW.strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        "---",
        'title: "Current Standings"',
        f"date: {date_str}",
        "weight: 1",
        "toc: false",
        "---",
        "",
        "# 🜂 Current Activity Standings",
        "",
        '<p style="color: var(--base04); font-size: 0.9em;">',
        f"Last computed: <strong>{time_str}</strong> · ",
        f"Active contributors: <strong>{data['n_active']}</strong> · ",
        f"Smoothing factor k: <strong>{data['k']}</strong> · ",
        f"Total shares: <strong>{TOTAL_SHARES}</strong>",
        "</p>",
        "",
    ]

    if data.get("fallback"):
        lines.extend(
            [
                '<p style="color: var(--base09); font-style: italic;">',
                f"Cold start mode: fewer than {MIN_CONTRIBUTORS} active contributors. "
                "Shares allocated proportionally to raw scores.",
                "</p>",
                "",
            ]
        )

    # --- Main leaderboard table ---
    ranked = sorted(data["shares"].items(), key=lambda x: -x[1])

    if not ranked:
        lines.extend(
            [
                "*No active contributors yet. "
                "[Start your first PR and become an Eagle Warrior!]"
                "(https://github.com/kakchouch/ometeotl)*",
                "",
            ]
        )
    else:
        # Build HTML table for better styling in Hugo
        lines.append("<table>")
        if data.get("fallback"):
            lines.append(
                '<tr style="border-bottom: 2px solid var(--base02);">'
                '<th style="text-align:center; padding: 8px;">Rank</th>'
                '<th style="padding: 8px;">Contributor</th>'
                '<th style="text-align:right; padding: 8px;">Raw Score</th>'
                '<th style="text-align:right; padding: 8px;">Shares</th>'
                "</tr>"
            )
            for rank, (user, share) in enumerate(ranked, 1):
                raw = data["raw_scores"].get(user, 0)
                pct = share / 10
                # Visual bar
                bar_width = max(2, int(share / 10))  # max 100px width
                lines.append(
                    f"<tr>"
                    f'<td style="text-align:center; padding: 6px 8px; font-weight:bold;">{rank}</td>'
                    f'<td style="padding: 6px 8px;">'
                    f'<a href="https://github.com/{user}">@{user}</a></td>'
                    f'<td style="text-align:right; padding: 6px 8px;">{raw:.1f}</td>'
                    f'<td style="text-align:right; padding: 6px 8px;">'
                    f"<strong>{share:.1f}</strong>"
                    f' <span style="color: var(--base04);">({pct:.1f}%)</span>'
                    f'<div style="background: var(--base0C); height: 4px; '
                    f'width: {bar_width}%; border-radius: 2px; margin-top: 2px;"></div>'
                    f"</td></tr>"
                )
        else:
            lines.append(
                '<tr style="border-bottom: 2px solid var(--base02);">'
                '<th style="text-align:center; padding: 8px;">Rank</th>'
                '<th style="padding: 8px;">Contributor</th>'
                '<th style="text-align:right; padding: 8px;">Raw Score</th>'
                '<th style="text-align:right; padding: 8px;">z-Score</th>'
                '<th style="text-align:right; padding: 8px;">Adj. Score</th>'
                '<th style="text-align:right; padding: 8px;">Shares</th>'
                "</tr>"
            )
            for rank, (user, share) in enumerate(ranked, 1):
                raw = data["raw_scores"].get(user, 0)
                z = data["z_scores"].get(user, 0)
                adj = data["adjusted_scores"].get(user, 0)
                pct = share / 10
                bar_width = max(2, int(share / 10))
                # Color z-score
                z_color = "var(--base0C)" if z >= 0 else "var(--base09)"
                lines.append(
                    f"<tr>"
                    f'<td style="text-align:center; padding: 6px 8px; font-weight:bold;">{rank}</td>'
                    f'<td style="padding: 6px 8px;">'
                    f'<a href="https://github.com/{user}">@{user}</a></td>'
                    f'<td style="text-align:right; padding: 6px 8px;">{raw:.1f}</td>'
                    f'<td style="text-align:right; padding: 6px 8px; color: {z_color};">{z:+.2f}</td>'
                    f'<td style="text-align:right; padding: 6px 8px;">{adj:.4f}</td>'
                    f'<td style="text-align:right; padding: 6px 8px;">'
                    f"<strong>{share:.1f}</strong>"
                    f' <span style="color: var(--base04);">({pct:.1f}%)</span>'
                    f'<div style="background: var(--base0C); height: 4px; '
                    f'width: {bar_width}%; border-radius: 2px; margin-top: 2px;"></div>'
                    f"</td></tr>"
                )
        lines.append("</table>")
        lines.append("")

    # --- Founder section ---
    if FOUNDER in data["raw_scores"]:
        raw = data["raw_scores"][FOUNDER]
        z = data["z_scores"].get(FOUNDER, 0)
        adj = data["adjusted_scores"].get(FOUNDER, 0)

        lines.extend(
            [
                "---",
                "",
                '<p style="font-style: italic; color: var(--base04);">'
                "Out-of-competition — Founder</p>",
                "",
                "<table>",
            ]
        )

        if data.get("fallback"):
            lines.append(
                '<tr style="border-bottom: 2px solid var(--base02);">'
                '<th style="padding: 8px;">Contributor</th>'
                '<th style="text-align:right; padding: 8px;">Raw Score</th>'
                "</tr>"
            )
            lines.append(
                f'<tr style="opacity: 0.7;">'
                f'<td style="padding: 6px 8px;">'
                f'<a href="https://github.com/{FOUNDER}">@{FOUNDER}</a></td>'
                f'<td style="text-align:right; padding: 6px 8px;">{raw:.1f}</td>'
                f"</tr>"
            )
        else:
            lines.append(
                '<tr style="border-bottom: 2px solid var(--base02);">'
                '<th style="padding: 8px;">Contributor</th>'
                '<th style="text-align:right; padding: 8px;">Raw Score</th>'
                '<th style="text-align:right; padding: 8px;">z-Score</th>'
                '<th style="text-align:right; padding: 8px;">Adj. Score</th>'
                "</tr>"
            )
            z_color = "var(--base0C)" if z >= 0 else "var(--base09)"
            lines.append(
                f'<tr style="opacity: 0.7;">'
                f'<td style="padding: 6px 8px;">'
                f'<a href="https://github.com/{FOUNDER}">@{FOUNDER}</a></td>'
                f'<td style="text-align:right; padding: 6px 8px;">{raw:.1f}</td>'
                f'<td style="text-align:right; padding: 6px 8px; color: {z_color};">{z:+.2f}</td>'
                f'<td style="text-align:right; padding: 6px 8px;">{adj:.4f}</td>'
                f"</tr>"
            )

        lines.extend(["</table>", ""])

    # --- Formula summary ---
    lines.extend(
        [
            "---",
            "",
            "<details>",
            "<summary>Scoring formula</summary>",
            "",
            "```",
            "Raw score    S(u) = Σ weight(event) × 2^(−age / 90)",
            "z-score      z(u) = (S(u) − μ) / σ",
            f"Adjusted     f(z) = exp(sinh(clamp(z, {Z_MIN}, {Z_MAX})) / k)",
            f"Smoothing    k    = max({K_FLOOR}, {K_OFFSET} − n_active)",
            f"Shares       s(u) = f(z(u)) / Σf(z) × {TOTAL_SHARES}",
            "```",
            "",
            f"Active contributor window: {ACTIVE_WINDOW} days (2× half-life). "
            "Founder included in normalization, excluded from share allocation.",
            "",
            "[Full specification →]"
            "(https://github.com/kakchouch/ometeotl/blob/develop/leaderboard/LEADERBOARD_SPEC.md) · "
            "[Methodology →](../)",
            "",
            "</details>",
            "",
        ]
    )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    token = os.environ.get("GITHUB_TOKEN")
    repo_name = os.environ.get("REPO_FULL_NAME")

    if not token or not repo_name:
        sys.exit("GITHUB_TOKEN and REPO_FULL_NAME environment variables required.")

    g = Github(token)
    repo = g.get_repo(repo_name)

    print(f"Computing leaderboard for {repo_name}...")

    # Collect events
    events = collect_events(repo)
    print(f"Collected events for {len(events)} contributors.")

    # Raw scores
    raw_scores = compute_raw_scores(events)

    # Determine active contributors (excluding founder for the count)
    last_events = {}
    for username, user_events in events.items():
        dates = [d for _, d, _ in user_events]
        if dates:
            last_events[username] = max(dates)

    active_users = {u for u, d in last_events.items() if is_active(d) and u != FOUNDER}
    n_active = len(active_users)
    k = compute_k(n_active)

    print(f"Active contributors (excl. founder): {n_active}")
    print(f"Computed k = max({K_FLOOR}, {K_OFFSET} - {n_active}) = {k}")

    # Decide: z-score path or fallback
    use_fallback = n_active < MIN_CONTRIBUTORS

    if use_fallback:
        print(
            f"Cold start: n_active ({n_active}) < {MIN_CONTRIBUTORS}. "
            "Using proportional fallback."
        )
        z_scores = {u: 0.0 for u in raw_scores}
        adjusted_scores_dict = {u: 0.0 for u in raw_scores}
        shares = compute_leaderboard_fallback(raw_scores)
    else:
        z_scores = compute_z_scores(raw_scores)
        k, adjusted_scores_dict, shares = compute_leaderboard(
            raw_scores, z_scores, n_active
        )

    # Assemble output data
    output_data = {
        "timestamp": NOW.isoformat(),
        "repository": repo_name,
        "n_active": n_active,
        "k": k,
        "fallback": use_fallback,
        "total_shares": TOTAL_SHARES,
        "config": CONFIG,
        "raw_scores": raw_scores,
        "z_scores": z_scores,
        "adjusted_scores": adjusted_scores_dict,
        "shares": shares,
        "ranked": sorted(shares.items(), key=lambda x: -x[1]),
    }

    # Write JSON
    json_path = SCRIPT_DIR / "leaderboard-data.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False, default=str)
    print(f"Wrote {json_path}")

    # Write Markdown (repo root)
    md_content = generate_markdown(output_data, repo_name)
    md_path = SCRIPT_DIR / "LEADERBOARD.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"Wrote {md_path}")

    # Write Hugo page (doc-site)
    hugo_content = generate_hugo_page(output_data, repo_name)
    hugo_dir = SCRIPT_DIR.parent / "doc-site" / "content" / "en" / "leaderboard"
    hugo_dir.mkdir(parents=True, exist_ok=True)
    hugo_path = hugo_dir / "live.md"
    with open(hugo_path, "w", encoding="utf-8") as f:
        f.write(hugo_content)
    print(f"Wrote {hugo_path}")

    # Summary
    print("\n--- Leaderboard ---")
    for user, share in sorted(shares.items(), key=lambda x: -x[1]):
        flag = " (founder, out-of-competition)" if user == FOUNDER else ""
        print(f"  @{user}: {share:.1f} shares{flag}")


if __name__ == "__main__":
    main()
