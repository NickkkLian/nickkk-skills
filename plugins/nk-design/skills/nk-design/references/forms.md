# Choose the first screen from the row

First write one line: **“One row is a … ; it carries … .”** Ask these four questions **in this order and stop
at the first yes**. The order is the tie-break: when two forms fit, the earlier one wins. Never build two to compare.

1. **Gap list.** Does the request name two records of the same measured amount (system and shelf, budget and actual,
   invoice and payment, plan and done) **and** ask to compare them row by row (compare, against, versus, match,
   “part by part”, “line by line”) **and** can the second be higher on some rows and lower on others?
   All three: `gaps`. Presence on two lists is not a measured amount.
   - A total checked against one outside figure (“does the money in match the bank”) is not row by row. It becomes
     one extra line under the adds-up line of whichever form is chosen.
   - If the second can only ever be less than or equal to the first (paid against billed, used against allowance),
     the second is a part of the first: answer no and go on.
2. **Step line.** Does the request name, or plainly imply, three or more stages that a row passes through one after
   another (“from inspection to dispatch”, pipeline, stages, “where each one is”), each row being at exactly one now?
   Yes: `steps`.
   - Outcomes of one decision (approved, rejected; kept, removed) are not stages.
3. **Waiting line.** Is the page's job to work through rows that each wait for a person's decision or action (queue,
   backlog, inbox, reports, requests, tickets, “work through”, “decide which”, pending, overdue) **and** does the
   request not ask for a total of money or units? Yes: `waiting`. Every row gets an arrival date.
4. **Otherwise Split.** The whole is the total of money or units if the request asks for one, otherwise the row count.

Question 4 always answers. Only two cases need a sentence in the footer's **About this demo** block:
the request names no whole (no total, no “who has and who has not”, no “how many of”); or real data lacks what
the chosen form needs (no arrival date, one source missing, free-text steps), so the page dropped to `split`.
Write `<p data-form-note>The first screen shows parts of a whole because {reason}.</p>` and record `fallback: true`.
Otherwise omit the note and record `fallback: false`. Never put this notice on the plate.
When the person names a drawing (“show me a funnel”, “I want the bar”), the person wins; record it as the reason.
Map that drawing to one of the four shipped forms; if it requires a fifth, ask before building.

Record the choice in the `nk-sources` JSON manifest:
`"form":{"name":"gaps","row_is":"one room, with predicted and measured decibels","why":"question 1: the same measured amount compared room by room; either record can be higher","also_fits":[],"fallback":false}`.

| Request | Form | Reason |
|---|---|---|
| Water allowance: used and remaining litres by household | split | q1 no: used ≤ allowance; whole = litres |
| Library purchase suggestions: decide which to accept or decline | waiting | q2 no: accept/decline are outcomes; q3 yes |
| Acoustic survey: predicted against measured decibels, room by room | gaps | q1 yes: the same measured amount can be higher or lower |
| Ceramic pieces: drying, glazing, firing; see where they pile up | steps | q2 yes |
| Commute diary: estimated against measured minutes, trip by trip | gaps | q1 yes: over or under |
| Repair tickets: waiting for parts, in repair, ready; which waited longest | steps | q2 before q3 |
| Expense claims to approve this month, with the total by category | split | q3 no: money total |
| Food bank shifts: which of the 24 are covered, which still need someone | split | “need someone” is not the page user deciding; whole = shifts |
| Last year's member list against this year's | split | q1 no: no quantity per row; both / only last / only this |
| A reading list tracker | split + footer note | names no whole |

## Editing contract (all forms)

Change `data-form` on `.plate`, the JSON-compatible `var SHAPE` between `SHAPE:start` / `SHAPE:end`, the generator,
labels and details actions, and manifest `form`. Leave all four `FORMS`, drawing CSS, dispatcher, verdict and shared
number-sources runtime in place. Do not write drawing code or bend one form to another. Use integer units or cents,
never formatted strings. `unit: {one, many}` names rows. `ui_check.py --wire-form page.html` fills the chosen fixed source
entries after you edit; their exact rows/formulas are updated by `trace()` at runtime. Keep other source entries.
Each number is clickable; repeated occurrences use one keyboard stop per id. Group labels with numeric thresholds
and the fixed page date have stated configuration sources. Runtime-created ids need the browser check in acceptance 16:
C16 cannot tell whether the page draws what it declares. Unknown is hatched, named and counted, never drawn as zero.

## Split (`split`)

Answers where the whole went. An 8 px bar, 2 px gaps, two to five ordered parts; first (“good”) part uses point.
Legend order equals bar order and gives words and numbers. For amounts, legend and identity put money/units first,
then row counts. Known widths are proportional to amounts; an unknown hatch reserves the unknown share of rows
(its width never estimates missing money). Zero parts stay in the legend but have no segment.
SHAPE: `amount: {field, label, kind: "money"|"int"}` or `null` for counts; `parts: [{label, statuses}]`;
`unknownLabel`. Statuses must cover every row exactly once.
For paid/owing money on the same row, an amount part can set `field` (e.g. paid/owing/waived cents).
Add `countParts: [{label,statuses}]` to partition rows exactly once (paid / part paid / unpaid / waived),
while amount parts may overlap. `amount.field` remains the independently summed whole (billed cents).
The table automatically exposes those component fields beside the whole so a person can re-add them.
Identity: sum of each part's integer amount = whole from a separate pass; sum of status counts = all rows.
Cross: uncovered/overlapping status, lost cent, invalid typed amount or unsafe integer sum. Missing amounts are
counted in words and excluded from amount sums. Title: “Where the {total} {whole word} went”. Phone: legend wraps.
Generator pattern (keep the starter's common row fields and history):
```js
for (var i=0; i<COUNT; i++) {
  var r = {id:i+1, src:"A:"+(i+2), name:"Invented booking "+(i+1), cat:"Rooms", rule:"fixture",
    cents:10000, status:i%3 ? "Approved" : "Needs review", reason:"Invented", history:["fixture"]};
  rows.push(r);
}
```

## Gap list (`gaps`)

Answers where two sources disagree. At most `show` nonzero differences (default/cap 6), descending absolute
difference. Shared scale = largest drawn difference; B below A runs left, B above A right, signs and lower/higher
words repeat the direction. `point` names the direction to act on. Rest row names its count and both directional
sums with a third-token swatch; no aggregate bar that could exceed the shared scale. Missing pairs stay out of BOTH
totals and are counted. Phone: name and signed value share a line; the bar is full width beneath; names wrap.
SHAPE: `a: {field,label}`, `b: {field,label}`, `kind: "int"|"money"`, `words: {lower,higher,match,compared}`,
`point: "lower"|"higher"` (use lower by default), `show: 6`; optional `quantity: "units"` for title words.
Identity: A total − lower differences + higher differences = independent B total; match + lower + higher = compared.
Cross: three passes disagree, text quantity, duplicate row id, unsafe sum. Title also states compared/all row counts.
```js
for (var i=0; i<COUNT; i++) {
  var r = {id:i+1, src:"A:"+(i+2), name:"Invented room "+(i+1), cat:"Survey", rule:"fixture",
    cents:0, status:"Needs review", predicted:50, measured:50+(i%5-2), reason:"Invented", history:["fixture"]};
  rows.push(r);
}
```

## Waiting line (`waiting`)

Answers how many wait and the oldest age. One square per waiting row, oldest band at left; labelled exclusive bands.
Missing arrivals have their own hatched group. Outcomes follow a divider as hollow squares with words/counts.
Point = at or past `limitDays`; without a limit use `null`, point = oldest band. Align a stated limit to a band boundary
so its whole group label can say “past the {n}-day limit”. If a limit cuts a band, the point cells still follow row ages.
Over 120 waiting rows merge a group's squares into continuous blocks. All lanes have equal available width;
width = count / largest merged group × lane width, including unknown dates and any merged decided group.
Blocks fit without clipping or panning; counts remain explicit. Decided squares wrap, even above 120 waiting rows.
Every group of squares uses the available width; there is no separate fixed lane cap for waiting or decided groups.
Decided groups over 120 also merge hollow cells on the same scale. Returning to 120 waiting rows restores squares.
SHAPE: `since: {field}`, `today: "YYYY-MM-DD"`, `waitingStatuses`, `bands: [{label,minDays}]` descending to zero,
`limitDays` (7 by default), `outcomes: [{label,statuses}]`. Default bands: ≥7, 3–6, 1–2, today.
Identity: band counts + unknown dates = independently counted waiting; waiting + each outcome = all rows.
Cross: future/invalid date, date falls in no band, unknown/overlapping status. Empty dated set says oldest unknown.
Caption states the fixed date and whole UTC calendar days elapsed (today = zero). Explain the block scale only when
blocks are drawn; caption digits must use sourced markup or be written as words. C16g checks static text and
caption-function literals; dynamic values and actual visibility still need the browser check. Phone: one band per line,
cells left, label right; outcomes under a rule. Title: “{waiting} {things} waiting, the oldest for {n} days”.
```js
for (var i=0; i<COUNT; i++) {
  var d = new Date(Date.parse(SHAPE.today+"T00:00:00Z")-(i%15)*86400000);
  rows.push({id:i+1, src:"A:"+(i+2), name:"Invented request "+(i+1), cat:"Workshop", rule:"fixture",
    cents:0, status:i%4 ? "Needs review":"Approved", arrived:d.toISOString().slice(0,10),
    reason:"Invented", history:["fixture"]});
}
```

## Step line (`steps`)

Answers counts per ordered stage, where they pile up. Three to seven boxes, name/count and 6 px fill scaled to fullest
step; line SVG chevrons join stages. Point box also says “most {things} are here”; first wins a tie. Dashed exit boxes
after a divider say “left the line”, with no chevron between exits. Phone: boxes stack, chevrons point down.
SHAPE: `step: {field}`, `steps: [names]` in work order, `exits: [{label,values}]`.
Identity: step counts = in progress (independent non-exit pass); in progress + exits = all rows.
Cross: unknown step, overlapping step/exit, unsafe count. Title names in-progress count and fullest stage/count.
Decisions must change the step field too; default starter approve → first exit, reject → last exit, send back → first step.
```js
for (var i=0; i<COUNT; i++) {
  rows.push({id:i+1, src:"A:"+(i+2), name:"Invented repair "+(i+1), cat:"Repairs", rule:"fixture",
    cents:0, status:"Needs review", stage:SHAPE.steps[i%SHAPE.steps.length],
    reason:"Invented", history:["fixture"]});
}
```
