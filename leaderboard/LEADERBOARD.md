# 🜂 Ometeotl Activity Leaderboard

> Last updated: 2026-04-12 16:27 UTC
> Repository: kakchouch/ometeotl
> Total activity-shares: **1000**
> Scoring: `f(z) = exp(sinh(z) / k)` — k = max(3, 12 − n_active)
> Active k: **12** (n_active = 0)

*Cold start mode: fewer than 3 active contributors. Shares allocated proportionally to raw scores.*

## Activity Shares

| Rank | Contributor | Raw Score | Shares |
|------|-------------|-----------|--------|

---

*Out-of-competition — Founder*

| Contributor | Raw Score |
|-------------|-----------|
| @kakchouch | 417.3 |

---

<details>
<summary>Methodology</summary>

The raw activity score aggregates contributions (merged PRs, reviews, issues, comments) weighted by type and by an exponential recency factor (half-life = 90 days).

The z-score is computed over all contributors (founder included).

The adjusted score uses `f(z) = exp(sinh(z) / k)` with k = max(3, 12 − n_active).

Activity-shares are proportional to adjusted scores, founder excluded. Total = 1000.

Full specification: [LEADERBOARD_SPEC.md](leaderboard/LEADERBOARD_SPEC.md)

</details>
