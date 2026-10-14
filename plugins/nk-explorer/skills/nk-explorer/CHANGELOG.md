# Changes

## 0.1.7 — 2026-10-13

Ship `output/loan.html` so the README's example link resolves. The opening now gives a request to type, the existing
page picture, graded practice, offline use and the recorded Python re-check with the loan's real numbers. The
longer explanation and historical evidence remain below; the picture and Chrome records are labelled 0.1.6.

The page template formats axes with locale-aware grouping and precision based on tick spacing, independently
of headline decimals. Optional `chart.locale` selects the number/currency style and is schema-checked. The loan
declares `en-GB`. Sparse extremes use three-interquartile-spread fences extended to include zero, exposing the
ordinary loan curve while preserving low plateaus. Omitted samples and off-range dots remain disclosed; formula
results and grading are unchanged.

Offline checks pass: concept 32/32, explorer_check 105/105, formula 44/44, make_explorer 12/12, numsrc 50/50,
and Node chart regressions 14/14 (6/14 on the old template, including failing currency-label and scale cases).
All three example concepts build with 0 file findings. Chrome and human layout checks were not rerun.

## 0.1.6 — 2026-10-11

A first-time user's run found correct answers presented without useful units, a running-time curve flattened by
near-zero speed, and unclear scratch-file instructions. A second first-time user's run found that the chart was
below the controls despite the README saying it was beside them, and that straight-line examples offered little
reason to explore.

Results and axes now carry units, currency uses cents, unavailable answers explain the setting, and the chart
discloses omitted extremes. The opening screen puts controls beside the curve above 760px, with other settings
in the controls panel and formula working below. Optional comparison endpoints show a meaningful change without
inventing curvature. Concept validation and self-tests cover the new fields; scratch/profile writes and the
limits of browser and numerical evidence are documented. The README uses the builder's replacement text with
fresh command recordings and an explicit account of the two user trials.

Integration also makes printed next-step paths relative so command recordings carry no local account path. The
description explicitly states when to use the skill; compatibility wording is preserved inside metadata for
frontmatter validators.

The browser recordings now include a 6/6 loan-page check and 47/47 self-tests on Python 3.13.9 and 3.9.6,
with one earlier 45/47 run and its unknown cause disclosed. Keyboard/focus, phone-size appearance, other browsers,
Windows and Linux remain unchecked. The README and acceptance wording distinguish these tested cases from
a broader browser audit.

An outsider's README-first review found the result buried below specifications and browser promises broader
than the evidence. This text-only fix names the teaching audience, shows the loan's checked numbers, generates
before verifying, qualifies policy/compatibility claims, and separates original examples from reconstructions.
Unchecked human acceptance remains explicit; warning order may vary. Scripts and assets are unchanged.
