# The concept file

One JSON object is the whole input to a page. `scripts/make_explorer.py` checks it against the rules below before
it builds anything, and `scripts/explorer_check.py` checks it again when it reads the finished page. The code next
to each rule is the one a refusal prints.

A field this list does not name is refused (E01): a misspelt `tolerence` would otherwise be ignored and the question
would have no tolerance at all. A key written twice in one object is refused too, rather than the last one quietly
winning.

## Top level

| Field | Type | Rule |
|---|---|---|
| `title` | text | What the page explains, up to 90 characters. It becomes a context label and the document's `<title>` (E01, E14). |
| `question` | text | A short question in the person's words. It becomes the main heading and the page's description. |
| `result` | object | The quantity the formula gives: `name`, `label`, optional `unit`, `unit_one`, `decimals` and `unavailable`. |
| `formula` | text | One formula in the page's language (below), using only the controls' names (E02). |
| `controls` | list | One to six sliders (E01). |
| `chart` | object | `x`: the control the curve runs along (E05); `title`: its heading; optional `comparison` with `from` and `to`. |
| `notes` | list of text | One or more sentences saying what the formula leaves out (E01). They go in the footer. |
| `source` | text | Where the formula comes from, in a phrase. It goes in the footer. |
| `practice` | list | One to eight questions, each `compute` or `reach` (E01). |

## `result`

| Field | Rule |
|---|---|
| `name` | A letter, then letters, digits and `_`; not a control's name and not a function's name (E02). It is the left side of the formula line: `A = P × (1 + r ÷ 100)^n`. |
| `label` | What it is, in words: "Amount after n years". |
| `unit` | Optional. `£`, `$`, `€` and `¥` go in front of a number; `%` sticks to it; anything else follows after a space. |
| `unit_one` | Optional. The unit's form for exactly 1 or -1: `"unit": "years", "unit_one": "year"`. |
| `decimals` | Optional whole number 0–8. Fixed decimal places for the headline and result-axis ticks (ticks use the ordinary formatter if rounding would duplicate adjacent labels). Defaults to 2 for `£ $ € ¥`, otherwise the ordinary six-significant-digit formatter. At magnitude 10^21 or above, the ordinary formatter is used. Does not change the formula or grading. |
| `unavailable` | Optional sentence explaining invalid settings for this concept and how to fix them, for example "At zero speed, you cannot finish a positive distance. Choose a speed above zero." Otherwise the page explains the arithmetic error. |

Copy units from the request, including currency and physical units. A percentage result must be computed on a
0–100 scale; a `%` suffix does not multiply by 100. When no unit is implied, omit it (axes say "unitless").
Currency headlines show cents; slider readouts and substituted formula values retain their exact six-significant-digit
formatting. Fixed decimal rounding applies to the computed binary value, half away from zero. Keep a compute
question's tolerance compatible with the rounding you ask a person to use: grading still compares the full result.

## Each control

| Field | Rule |
|---|---|
| `name` | A letter, then letters, digits and `_` (so not `_x`, and not `__proto__`: the page keeps its values in plain JavaScript objects); unique; not a function's name (E04). It is how the formula refers to the control. |
| `label`, `unit`, `unit_one` | As for the result. The label is shown with the name: "Yearly rate (r)". |
| `min`, `max`, `step` | Numbers, with `min` below `max`, `step` above 0, and a whole number of steps from `min` to `max`, at most 2,000 (E04). |
| `value` | Where the slider starts: one of its positions (E04). The page opens on these values, and the formula must have a value there (E05). |

Two more rules apply to controls as a set. Every control has to be in the formula and change the result shown
somewhere along its range, with the other controls where they start (E03) — a slider that moves nothing teaches
that sliders move nothing. And every position of a slider must read exactly at six significant digits (E04): a
readout and the formula line show a value that way, so a position like 100000.4 would be shown as 100000 while the
page computed with 100000.4.

## The formula language

Numbers (`2`, `0.5`, `.5`, `1e3`), the controls' names, `+ - * /`, `^` for powers (`**` is read as `^`), unary
minus, parentheses, and these functions: `min` and `max` (two or more arguments), `abs sqrt exp ln log10 floor ceil`
(one), `round` (the value and, optionally, a number of decimal places; halves go away from zero). `round`, `floor` and
`ceil` finish the working inside them in decimal before they round, on each number as it is written: `round(1.275, 2)`
is 1.28, `round(8.5 * 10.45, 2)` is 88.83 and `ceil(2.1 / 0.3)` is 7, as by hand, although the computer's binary
working gives a hair below 1.275, 88.825 and a hair above 7. Inside them, `+ - * /`, `min`, `max`, `abs` and whole
powers up to 400 are worked exactly; any other step (`sqrt exp ln log10`, a fractional or larger power) is taken as
the number the page computes for it, as written. Powers run right
to left (`2^3^2` is `2^9`) and bind tighter than a leading minus (`-x^2` is `-(x^2)`). Anything else is an error,
never a lookup: there is no assignment, no text, no property access and no way to call anything not on that list.

Some values have no result: division by zero, the square root of a negative number, `ln` or `log10` of a number
that is not positive, a negative number to a fractional power, zero to a negative power, and any step of the working
that is not a finite number — `1/exp(1000)` has no value even though its end would be 0, in the page and in the
checker alike. The headline says "Choose another setting" and a plain sentence explains why and what to change;
the chart leaves a gap at sampled undefined settings.

The line with numbers writes each number of the formula exactly as you typed it (`1.000137` stays `1.000137`) and a
negative value in brackets (`1 × (-3)^2 + 2 × (-3)`), so doing the sum on that line gives the result.

`python3 scripts/formula.py "P * (1 + r/100)^n" P=1000 r=5 n=10` prints the formula written back, written with the
numbers, and the result, so a formula can be tried before it goes into a concept.

## `chart`

The curve runs the `x` control from its `min` to its `max` at 201 points and keeps every other control where it is
set; the dot marks the current value. It needs at least two points with a value at the starting values (E05). A
formula with `floor`, `ceil` or `round` in it jumps, and is drawn as steps (flat, then straight up or down).

`x` also selects the principal slider shown beside the curve above 760px viewport width; at narrower widths the
curve follows the controls. Other sliders expand inside the controls panel; formula working expands below.
Choose the control that best answers the person's "what if", and open on an ordinary, meaningful grid position.
Optional `comparison` is an object with two numeric keys, `from` and `to`: distinct positions on this slider's grid
with finite results at the opening settings (E05). The page shows both answers, holding the other controls at their
current settings. Choose a useful comparison or a requested threshold. It does not calculate an optimum or steepest
point. Without it, a pair is selected once from the opening position and a position about one fifth of the range
away. Subsequent undefined endpoints are disclosed. For example, `"comparison": {"from": 100, "to": 200}`
on a sales slider shows the earnings at those two sales counts without suggesting a linear model is nonlinear.
The vertical scale follows the finite sampled values, without forcing zero into the range. If that range is over
eight interquartile spreads wide, the retained interval covers both the quartiles plus/minus three spreads and
plus/minus eight times the median's magnitude. Values beyond it are omitted from the drawing and scale; low values
on a bounded plateau are retained. A note gives the omitted count and visible bounds; an off-range current answer stays in the headline,
with its dot omitted and explained. This is a display heuristic, not a domain boundary. It may omit valid extremes
and miss narrow features between samples. Undefined samples and omitted samples both break the path.

## Practice questions

Every question has a `type` and a `prompt`. The prompt states in numerals every value the question uses (E06,
E07). The checker pairs each value with a number of its own in the prompt: `£2,000`, `3%`, `5 years`, `x = -2`. A
number can stand for a value it equals unless it visibly belongs to something else — written with another control's
unit or another currency (in "3% for 5 years", the 5 is years, so a rate of 5% is not stated), with `%` when the
value is not a percentage, or as another name's `y = 5`. A number with no unit, or with a unit word no control uses
("6 metres per second squared"), can stand for any value it equals, and one number cannot stand for two values.

A number that only says how to answer, or which question this is, stands for no value. It is recognised by where it
stands, not by a list of phrasings. When no currency sign, `%` or unit word of the concept is written with it, these
are such numbers (each a whole number):

- **a label**: a capitalised word or `#` and the number, then `:` `.` `)` `]` or "of M" / "/M", at the start of the
  prompt, of a sentence or of a bracket — "Task 2:", "Exercise 2.", "Q 2:", "#2:", "(Part 2)", "Question 3 of 4:"
  (the 4 as well);
- **a bracket** holding only the number and words — "(2 marks)", "(4 s.f.)", "[3 points]";
- **a precision**: the number after "to" or "in" with a word after it — "to 2 decimals", "correct to 4 s.f.", "to
  2-decimal-place accuracy", "answer in 2 lines".

And, whatever is written with it, any number after "nearest", "question", "part" or "step", or followed by a word for
decimal places or significant figures ("to the nearest 10", "Give 2 decimals", "3 sig figs"). A number with a
decimal point is never a label, bracket count or precision: in "within 0.02 of 0.5", both are values. The rule can
refuse a number that is a value written the same way ("grows to 3000 pounds" when the concept's unit is `£`): write
it with the concept's unit or as `name = value`.

### `compute`: work out the result

| Field | Rule |
|---|---|
| `set` | A value for every control and nothing else, each one of its slider's positions (E06). "Show it on the controls" puts these on the sliders. |
| `tolerance` | Above 0, and smaller than the nearest other answer any one slider gives (E06): every position of each slider is tried, the others at the question's values. A far position can be the nearest — a ball thrown up at 20 m/s is at 18.975 m after 1.5 s and at 18.876 m after 2.6 s, coming down — and a staircase gives the same answer for several positions in a row (25 items at 10 to a box need 3 boxes, and so do 21 to 30). A tolerance that also passes another answer cannot tell a right reading from a misread slider. |

The answer is graded on the number: `2318.55`, `2,318.548` and `£2318.55` are all the same answer. Commas may only
separate groups of three digits; `23,18.55`, `2318,55` and `0x90F` are not read as numbers.

### `reach`: set the free controls to meet a goal

| Field | Rule |
|---|---|
| `fixed` | Values for all but one or two controls, each one of its slider's positions (E07). Pressing Try it or Check puts these on the sliders and locks them. |
| `goal` | `"at least"`, `"at most"` or `"within"` (E07). |
| `target` | The number the goal is about. |
| `tolerance` | Only with `"within"`, and required there (E07). |
| `lowest` or `highest` | Optional: the name of one free control. The answer must meet the goal, and no position of that control further toward that end may meet it, the other controls as they are — every position, not only the next one, since a curve can turn back: a ball thrown up is within 1 m of 15 m at 0.9 s going up and again at 3 s coming down, and the earliest is 0.9 s (E07). |

A reach question's prompt states its fixed values, its target and, for a within goal, its tolerance, paired as for
a compute question. It must not already be passed at the page's starting values, and at least one setting of the
free controls must pass it (E07). The free controls together may have at most 200,000 settings, because the checker walks
all of them.

A goal counts as met within a billionth of its target, and a typed answer within a billionth of the right answer:
0.52 is 0.020000000000000018 away from 0.5 in floating point, and a question should not turn on the last bit.

## A whole concept

```json
{
  "title": "How compound interest grows",
  "question": "Money left to grow at a fixed yearly rate earns interest on its interest. How much is there after a number of years?",
  "result": {"name": "A", "label": "Amount after n years", "unit": "£"},
  "formula": "P * (1 + r/100)^n",
  "controls": [
    {"name": "P", "label": "Starting amount", "unit": "£", "min": 100, "max": 10000, "step": 100, "value": 1000},
    {"name": "r", "label": "Yearly rate", "unit": "%", "min": 0, "max": 15, "step": 0.5, "value": 5},
    {"name": "n", "label": "Years", "unit": "years", "unit_one": "year", "min": 0, "max": 40, "step": 1, "value": 10}
  ],
  "chart": {"x": "n", "title": "The amount, year by year"},
  "notes": ["Interest is added once a year.", "Nothing is paid in or taken out along the way.", "The rate never changes."],
  "source": "the standard compound interest formula, compounded once a year.",
  "practice": [
    {"type": "compute", "prompt": "£2,000 at 3% a year for 5 years. What is the amount?", "set": {"P": 2000, "r": 3, "n": 5}, "tolerance": 0.5},
    {"type": "reach", "prompt": "£1,000 at 7% a year: after how many whole years is there £2,000 or more for the first time?", "fixed": {"P": 1000, "r": 7}, "goal": "at least", "target": 2000, "lowest": "n"}
  ]
}
```

`python3 scripts/make_explorer.py --concept-of page.html` prints the concept of a page that is already built, to
edit and build again.
