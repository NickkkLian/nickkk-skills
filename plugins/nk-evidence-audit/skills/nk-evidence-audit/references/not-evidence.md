# What is not evidence (each row was accepted once and turned out to be wrong)

| Presented as proof | Why it is not | What would be |
|---|---|---|
| "The process is running" | It may be running the old code | process start time vs file modification time |
| "No error" / exit 0 | A search can match nothing and exit 0; a tool can print half a file and exit 0 | run the same tool on an input that must produce a hit or a failure |
| "curl returns 200" | Browsers add cache, CORS, `Vary`; behaviour differs | reproduce from the real origin in a browser |
| "Push succeeded" | A mirror can accept a push that never deploys | fetch the live URL and find the new symbol |
| "File count unchanged" | Counts hide edits, truncation, wrong content | per-file hashes |
| "The doc / memory says so" | Documents describe the past | measure the current state |
| "Self-check green" | It only detects the failure modes someone wrote down | list the layers it checks; test one it does not |
| "Tests pass" on empty or mock data | Real data has volume, width, edge values | run with real data |
| "It looks right" (eyeballed) | A 1000px estimate measured 592px | the measured number |
| An agent's "it works" | Its conclusion is a claim, not output | its raw stdout/stderr and exit code |
| A paraphrased output | Paraphrase is selection | the original, unedited |
| A web fix with no screenshot | Nobody can see it | screenshot after `document.fonts.ready`, real click |
| Test data deleted after the run | Nothing left to inspect | leave it in place until reviewed |
| A hand-typed log block | Start and end in the same second for a 4.5 s job | logs written by the program |
| A green bundle that lives in a temp dir | It vanished overnight | evidence committed next to the change |
| "0 hits" from a wrapped `grep`/`find` | Session wrappers may honour ignore files or drop binaries | a positive control on a planted sample |
| A liveness probe that returned 200 | Soft 404s return 200 | require a second marker from the page body |

Common thread: **when the result is too clean, suspect the instrument before believing the result.**
