# Limitations

The default benchmark repository remains `swankystark20-group/incidentops-demo-app`. Its planted bugs, GitLab CI, issues, merge requests, and history should remain untouched.

The platform is now repository-configurable, but high-quality results still depend on the target repository exposing useful commit messages, test output, source files, runtime logs, and a valid GitLab token.

`TARGET_APP_PATH` is necessary for repositories whose application lives in a subdirectory. For root-level repositories, configure it as empty.

The benchmark validation strategies currently use pytest. Non-Python repositories can still be represented in the incident registry, but they need additional validation strategies such as npm, Maven, Gradle, Go test, or containerized validation.

The patch agent depends on LLM structured output. If the model proposes a target block that does not exactly match the source, validation fails and the retry loop runs once.

Local benchmark log triggering depends on a local checkout of the target application. In a deployed production platform, log retrieval should be replaced with a log-provider integration.

Metrics are computed from persisted incident records and agent logs. They are suitable for portfolio/evaluation dashboards, not yet for SLO-grade production observability.
