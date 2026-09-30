# Finding format — three things or it is not finished

```
FINDING: <one sentence>
where measured: <files, scope, tool; e.g. "same-line matches only", "remotes enumerable from this machine">
confidence: proven | supported, other causes not excluded | neither confirmed nor refuted
reproduce: <exact command>
```

- "I could not prove it is wrong" is not "it is right"; it is the third tier.
- A measurement taken with a broken instrument (a truncated line, a grep on a path that did not exist)
  is not a finding. Two real cases: a conclusion drawn from a line cut off at 118 characters; a "said 0
  times" drawn from grepping a file that was never there.
- Numeric acceptance criteria state the sampling region, the statistic (mean / median / p95 / share) and
  the conditions (which renderer, which background, which colour space). A threshold error gets corrected
  by the next measurement; a sampling error produces true numbers about the wrong thing and never fails.
