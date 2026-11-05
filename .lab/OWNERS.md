# File ownership (one owner per path; others read only)
| Path | Owner |
|---|---|
| PROTOCOL.md | protocol-architect (append-only after G1) |
| lit/, paper/refs.bib | literature-scout |
| experiments/, results/ | experiment-lead |
| theory/ | theory-lead |
| hardware/ | hardware-lead |
| analysis/, paper/numbers.tex | statistician |
| figures/ | figure-designer |
| paper/*.tex (except numbers.tex) | paper-writer |
| audit/ | reproducibility-auditor, red-team-reviewer, citation-verifier |
| release/, CITATION.cff | release-manager |
| .lab/STATE.md, TASKS.md, BUDGET.md | project-coordinator |
| .lab/gates.json | human only, via /lab-gate |
