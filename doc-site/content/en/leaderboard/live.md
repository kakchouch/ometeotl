---
title: "Current Standings"
date: 2026-04-14
weight: 1
toc: false
---

# 🜂 Current Activity Standings

<p style="color: var(--base04); font-size: 0.9em;">
Last computed: <strong>2026-04-14 07:16 UTC</strong> · 
Active contributors: <strong>1</strong> · 
Smoothing factor k: <strong>11</strong> · 
Total shares: <strong>1000</strong>
</p>

<p style="color: var(--base09); font-style: italic;">
Cold start mode: fewer than 3 active contributors. Shares allocated proportionally to raw scores.
</p>

<table>
<tr style="border-bottom: 2px solid var(--base02);"><th style="text-align:center; padding: 8px;">Rank</th><th style="padding: 8px;">Contributor</th><th style="text-align:right; padding: 8px;">Raw Score</th><th style="text-align:right; padding: 8px;">Shares</th></tr>
<tr><td style="text-align:center; padding: 6px 8px; font-weight:bold;">1</td><td style="padding: 6px 8px;"><a href="https://github.com/kamalakchouch">@kamalakchouch</a></td><td style="text-align:right; padding: 6px 8px;">6.0</td><td style="text-align:right; padding: 6px 8px;"><strong>1000.0</strong> <span style="color: var(--base04);">(100.0%)</span><div style="background: var(--base0C); height: 4px; width: 100%; border-radius: 2px; margin-top: 2px;"></div></td></tr>
</table>

---

<p style="font-style: italic; color: var(--base04);">Out-of-competition — Founder</p>

<table>
<tr style="border-bottom: 2px solid var(--base02);"><th style="padding: 8px;">Contributor</th><th style="text-align:right; padding: 8px;">Raw Score</th></tr>
<tr style="opacity: 0.7;"><td style="padding: 6px 8px;"><a href="https://github.com/kakchouch">@kakchouch</a></td><td style="text-align:right; padding: 6px 8px;">564.0</td></tr>
</table>

---

<details>
<summary>Scoring formula</summary>

```
Raw score    S(u) = Σ weight(event) × 2^(−age / 90)
z-score      z(u) = (S(u) − μ) / σ
Adjusted     f(z) = exp(sinh(clamp(z, -3.0, 4.0)) / k)
Smoothing    k    = max(3, 12 − n_active)
Shares       s(u) = f(z(u)) / Σf(z) × 1000
```

Active contributor window: 180 days (2× half-life). Founder included in normalization, excluded from share allocation.

[Full specification →](https://github.com/kakchouch/ometeotl/blob/develop/leaderboard/LEADERBOARD_SPEC.md) · [Methodology →](../)

</details>
