---
title: "Activity Leaderboard"
weight: 30
---

# 🜂 Activity Leaderboard

The Ometeotl Activity Leaderboard distributes **1000 activity-shares** among contributors based on their recent, weighted activity. It rewards sustained, high-quality contributions while ensuring every contributor — even occasional ones — receives recognition.

The founder is excluded from share allocation and displayed out-of-competition.

**[View current standings →](live/)**

---

## How It Works

The leaderboard pipeline runs in four stages:

```
Raw Score  →  z-score  →  Adjusted Score  →  Activity-Shares
```

### Stage 1 — Raw Activity Score

Every contribution is weighted and decayed over time:

```
S(u) = Σ  weight(event) × recency(age)
```

| Event | Weight | Rationale |
|-------|--------|-----------|
| Merged PR | 10 | Core contribution — reviewed and integrated |
| Commit in merged PR | 3 | Rewards granular, iterative work |
| PR review | 4 | Code review is high-value mentorship |
| Issue opened | 2 | Surfaces bugs and proposes features |
| Comment (issue/PR) | 1 | Encourages community discussion |
| Lines changed | 0.01/line | Minor volume bonus (capped at 200 lines/PR) |

**Recency decay** uses an exponential half-life of **90 days**:

```
r(t) = 2^(−t / 90)
```

A contribution keeps 50% of its value after 3 months, 25% after 6 months, and ~6% after a year. It never reaches zero.

![Recency Decay](/ometeotl/images/leaderboard_fig4_recency_decay.png)

### Stage 2 — z-score Normalization

Raw scores are standardized across all contributors (founder included):

```
z(u) = (S(u) − mean) / std_dev
```

This removes scale dependence: `z = 0` always means "average contributor."

### Stage 3 — Adjusted Score

The standardized score is transformed through a non-linear function designed to:
- **Anchor** the average contributor at a predictable value (`f(0) = 1` always)
- **Generously reward** exceptional contributors (super-exponential growth)
- **Symbolically recognize** occasional contributors (approaches 0 but never reaches it)

```
f(z) = exp(sinh(z) / k)
```

![Adjusted Score Function](/ometeotl/images/leaderboard_fig1_adjusted_score.png)

The key mathematical properties of this function:

- **f(0) = 1 for all k** — the average contributor has a fixed, predictable score
- **Super-exponential growth for z > 0** — top contributors are rewarded aggressively
- **Approaches 0 for z < 0 but never reaches it** — no one gets zero shares
- **Monotonically increasing** — more activity always means a higher score
- **Single parameter k** controls the entire distribution shape

### Stage 4 — Adaptive Smoothing (k)

The smoothing factor k adapts to community size:

```
k = max(3, 12 − n_active)
```

Where `n_active` = number of contributors with activity in the last 180 days.

![Adaptive k](/ometeotl/images/leaderboard_fig2_dynamic_k.png)

| Phase | n_active | k range | Effect |
|-------|----------|---------|--------|
| **Protective** | 1–8 | 11 → 4 | Smooth distribution — prevents one person from dominating a small pool |
| **Mature** | 9+ | 3 (floor) | Full differentiation — exceptional contributors are generously rewarded |

This means the leaderboard automatically becomes more competitive as the community grows.

### Share Allocation

Activity-shares are proportional to adjusted scores (founder excluded), totaling 1000:

```
shares(u) = (f(z(u)) / Σ f(z(uᵢ))) × 1000
```

![Share Allocation](/ometeotl/images/leaderboard_fig3_share_allocation.png)

---

## Example

With 9 active contributors and k = 3:

| Rank | z-score | Shares | Profile |
|------|---------|--------|---------|
| 1 | +2.50 | **433** | Star contributor — generously rewarded |
| 2 | +1.94 | **179** | Strong contributor |
| 3 | +1.38 | **107** | Above average |
| 5 | +0.25 | **63** | Average — stable, predictable share |
| 7 | −0.88 | **41** | Below average — still meaningful |
| 9 | −2.00 | **17** | Occasional — symbolic but non-zero |

---

## Relationship with the Rank System

The leaderboard is **complementary** to the rank system (Path of the Serpent):

| | Rank System | Activity Leaderboard |
|-|-------------|---------------------|
| Nature | Lifetime milestone | Dynamic snapshot |
| Based on | Total merged PRs | Weighted, recency-adjusted activity |
| Direction | Only goes up | Fluctuates with activity |
| Purpose | Status and identity | Incentive and recognition |

You can be a high-ranking **Otomi** with few current shares (if inactive recently), or a new **Eagle Warrior** with a strong share from a single impactful PR.

---

## Transparency

- All parameters are in [`leaderboard/config.json`](https://github.com/kakchouch/ometeotl/blob/develop/leaderboard/config.json) — version-controlled and auditable
- Raw data is exported to `leaderboard/leaderboard-data.json` after each computation
- The formula is public and deterministic: anyone can reproduce the results
- Full mathematical specification: [`LEADERBOARD_SPEC.md`](https://github.com/kakchouch/ometeotl/blob/develop/leaderboard/LEADERBOARD_SPEC.md)
