# Baseline evaluation

| Scenario | Useful baseline behavior | Failure the new skill must close |
|---|---|---|
| Defensible | Compared the two supplied works and bounded certainty | Did not emit canonical audit YAML, exact status fields, evidence-reference format, or machine verdict vocabulary |
| Insufficient evidence | Resisted pressure and preserved candidate source status | Used uppercase/free-form verdict and custom metadata/status rather than the stable schema |
| Overclaim | Rejected zero results as proof | Invented “appears underexplored” despite zero evidence, used `NOT DEFENSIBLE` outside the four verdicts, and returned a nonstandard status block |

The refined skill must make negative outcomes first-class, use only four exact verdicts, link every
material difference to evidence, and avoid turning either an empty search or candidate titles into
a novelty signal.
