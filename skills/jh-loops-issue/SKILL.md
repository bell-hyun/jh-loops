---
name: jh-loops-issue
description: Author a GitHub issue that conforms to the jh-loops contract (목적 / 상세 / Depends-on / Acceptance Criteria, agent-verifiable AC) and create it with the `agent` label. Use when the user wants to file an issue for the autonomous loop, create an agent-workable issue, or "make a jh-loops issue".
user-invocable: true
---

# Author a jh-loops issue

Produce a GitHub issue that the jh-loops autonomous loop can pick up and finish
unattended. The loop's reliability rests entirely on issue quality: the
**Acceptance Criteria are the single source of truth for "done"** — there is no
separate gates file. Your job is to enforce that contract before the issue is
created.

Conduct a short interview, **one question at a time**, recommending an answer
each time. Explore the repo for answers before asking the user.

## The contract (must hold, or do not create the issue)

- **목적 (Why)** — required. A user story: *As <role>, I want <what>, so that <why>.*
- **상세 (What / Context)** — optional. Scope, non-scope, links, constraints.
- **Depends-on** — optional. `#<n>` references; the loop won't start until they
  all close. Omit the section if there are none.
- **Acceptance Criteria** — required, and **every item must be decidable by an
  autonomous agent with no human judgment**. Each item is checked by running a
  command or observing a deterministic result. Because AC is the source of
  truth, **each item must name its own check** (e.g. `` `npm test` passes ``).

## Interview

1. **Target repo.** Confirm `owner/name` (infer via `gh repo view --json nameWithOwner`).
2. **Goal.** Get a real user story. If the user gives only a title, push until you
   have *As X, I want Y, so that Z*.
3. **Context.** Background, scope, non-scope, links, constraints. Optional.
4. **Dependencies.** "Does this need another open issue done first?" Collect
   `#numbers`. Optionally check each with `gh issue view <n> --json state`.
5. **Acceptance Criteria** — the important part. Draft criteria, then test EACH
   against this bar:
   - Can an agent decide pass/fail by running something or observing a
     deterministic result? If yes, keep it and make the check explicit.
   - If it's subjective ("looks clean", "is intuitive", "feels fast"), either
     reframe it into something measurable or move it to 상세 — **do not** leave it
     in AC.
   - Prefer at least one objective gate (build / test / lint) where the repo has one.
   - If you cannot form any agent-verifiable AC, **stop**: this is a
     `needs-spec` or human-only task and should not be an `agent` issue. Tell the
     user instead of creating it.

## Assemble

Build the body with these EXACT headings (the parser matches `## Depends-on` and
`## Acceptance Criteria` verbatim; 목적/상세 are free text). Write the issue
content in the user's language.

```markdown
## 목적 (Why)
As <role>, I want <what>, so that <why>.

## 상세 (What / Context)
<context, or omit this section>

## Depends-on
- #12

## Acceptance Criteria
- [ ] <agent-verifiable statement>
- [ ] `<command>` passes
```

**Optional self-check.** If the `jh_loops` package is importable (e.g. run from
the jh-loops repo with `src` on the path, or pip-installed), confirm the draft
parses the way the loop will read it:

```bash
python3 - <<'PY'
import sys; sys.path.insert(0, "src")
from jh_loops.issues import Issue, parse
body = open("/tmp/jh-issue-body.md").read()
p = parse(Issue(number=0, title="", body=body, labels=[]))
assert p.has_ac_section and p.acceptance_criteria, "no usable AC"
print("depends_on:", p.depends_on)
print("acceptance_criteria:", p.acceptance_criteria)
PY
```

## Create

Show the full draft and the target repo, and **get explicit confirmation** before
creating anything (this is an outward action).

On approval, write the body to a temp file and create the issue with the `agent`
opt-in label:

```bash
gh issue create --repo <owner/name> \
  --title "<concise title>" \
  --body-file /tmp/jh-issue-body.md \
  --label agent
```

Do **not** add `in-progress`, `in-review`, `needs-spec`, or `needs-human` — those
belong to the loop's lifecycle, not to a freshly authored issue.

Report the created issue URL.
