# ContribScout — Scoring Engine Specification

ContribScout uses a transparent, explainable 0–10 scoring engine. Every recommendation includes its final score out of 10, an itemized breakdown across six weighted criteria, evidence justification, confidence level, and negative signals.

## Evaluation Criteria and Default Weights

| Criterion | Default Weight | Description |
| :--- | :---: | :--- |
| **Practical Usefulness & Impact** | **25% (0.25)** | Measures the functional importance of resolving the issue (e.g., core bug fix vs. cosmetic edit). |
| **Feasibility for Developer** | **20% (0.20)** | Evaluates language match proficiency, familiar frameworks, and weekly time budget compatibility. |
| **Technical Depth & Engineering Value**| **20% (0.20)** | Rewards non-trivial engineering tasks (logic errors, concurrency, performance, tests) over trivial tasks. |
| **Maintainer Responsiveness** | **15% (0.15)** | Evaluates historical maintainer activity, open PR reviews, and recent commit velocity. |
| **Learning & Portfolio Value** | **10% (0.10)** | Measures alignment with stated learning goals and portfolio visibility in established repositories. |
| **Repository Health & Readiness** | **10% (0.10)** | Assesses community adoption, commit recency, open issue ratio, and OSI-compliant licensing. |

Total: `100% (1.00)`

Weights can be customized in `config/scoring.yaml`. If custom weights do not sum to 1.0, ContribScout automatically normalizes them proportionally:
$$w_i^{\text{normalized}} = \frac{w_i}{\sum_{j} w_j}$$

---

## Confidence Adjustment

To prevent poorly documented, unverified, or ambiguous issues from receiving artificially inflated scores, ContribScout computes an evidence density score $\text{Conf} \in [0.2, 1.0]$:

- **High Confidence ($\ge 0.75$)**: Detailed issue description ($\ge 200$ chars), verified repository metadata, clear reproduction context.
- **Medium Confidence ($0.50 - 0.74$)**: Standard issue description, verified repository metadata.
- **Low Confidence ($< 0.50$)**: Sparse description ($< 50$ chars) or unretrievable repository metadata.

The final score applies a confidence dampening factor:
$$\text{Final Score} = \text{Raw Score} \times (0.70 + 0.30 \times \text{Conf})$$

---

## Worked Example: Real Engineering Work vs. Typo Fix

A critical design requirement of ContribScout is that **an easy typo fix must not outrank a substantial, feasible engineering improvement**.

### Scenario A: Well-specified Python Bug Fix
- **Issue**: `acme/fast-nlp#42` — TypeError in tokenizer under empty inputs.
- **Metadata**: Detailed traceback provided, repository has 1,850 stars, active within 24 hours.
- **Criteria Scores**:
  - Practical Usefulness: `8.0 / 10` (Core functional bug impacting users)
  - Feasibility: `8.0 / 10` (Python advanced match, pytest familiar)
  - Technical Depth: `6.5 / 10` (Debugging, regression test required)
  - Maintainer Responsiveness: `7.5 / 10` (Active maintainers, existing issue discussion)
  - Learning & Portfolio: `8.0 / 10` (1,850 stars, high portfolio value)
  - Repository Health: `10.0 / 10` (Recent commits, Apache-2.0 license)
- **Raw Score**:
  $$(8.0 \times 0.25) + (8.0 \times 0.20) + (6.5 \times 0.20) + (7.5 \times 0.15) + (8.0 \times 0.10) + (10.0 \times 0.10) = 7.825$$
- **Confidence**: `0.95` (High)
- **Final Score**: **`7.8 / 10.0`**

### Scenario B: 1-Character Typo in Documentation
- **Issue**: `acme/fast-nlp#88` — Fix typo in README link.
- **Metadata**: 1 line description.
- **Criteria Scores**:
  - Practical Usefulness: `2.0 / 10` (Minor typo; low functional impact)
  - Feasibility: `10.0 / 10` (Extremely easy)
  - Technical Depth: `1.5 / 10` (Trivial edit; minimal engineering depth)
  - Maintainer Responsiveness: `6.0 / 10` (Standard)
  - Learning & Portfolio: `3.0 / 10` (Negligible engineering portfolio value)
  - Repository Health: `10.0 / 10` (Same repo)
- **Raw Score**:
  $$(2.0 \times 0.25) + (10.0 \times 0.20) + (1.5 \times 0.20) + (6.0 \times 0.15) + (3.0 \times 0.10) + (10.0 \times 0.10) = 5.00$$
- **Confidence**: `0.70` (Medium due to sparse context)
- **Final Score**: **`4.6 / 10.0`**

**Result**: The genuine engineering bug (`7.8`) decisively outranks the trivial typo fix (`4.6`).
