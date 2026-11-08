# AI usage guide

This guide explains how contributors may use AI tools while working on Gabby. AI tools can help
explore the codebase, draft changes, explain failures, and improve documentation. The contributor
remains responsible for the correctness, safety, and licensing of every submitted change.

## Use AI as an assistant

- Review generated code and explanations against the implementation, documented contracts, and
  accepted [architecture decisions](architecture/adr/README.md).
- Keep changes within the requested scope. Review the impact of broad rewrites or unrelated cleanup
  before accepting them.
- Treat generated tests as drafts. Check that they exercise the behavior and failure boundaries that
  matter, and do not merely repeat the implementation's assumptions.
- Use deterministic fakes and local clients for default tests. Do not send real credentials or call
  live model APIs from the default test suite.
- Verify factual claims, command examples, dependency details, and links before adding them to docs.

## Protect project and user data

- Never paste credentials, tokens, private keys, production data, or private vulnerability details
  into an AI service.
- Share only the minimum code or context needed for the task, and follow the AI service's privacy and
  data-handling settings.
- Do not ask an AI tool to weaken authorization, policy enforcement, sandbox boundaries, redaction,
  or resource limits to make an example pass.
- Treat model output, retrieved content, tool output, and generated code as untrusted input. Review
  commands before running them, especially commands that delete data, change Git history, publish
  artifacts, or modify cloud resources.

## Review and validate changes

Before submitting AI-assisted work:

1. Read the complete diff and remove changes you cannot explain or justify.
2. Check that the change respects Gabby's ownership boundaries: the host owns durable conversation
   state and caller identity; Gabby enforces runtime contracts and tool permissions.
3. Add or update focused regression tests for behavior changes, including relevant failure paths.
4. Run the applicable checks from the [contribution guide](../CONTRIBUTING.md) and report what was
   run, what failed, and what could not be verified.
5. Update the closest documentation and changelog when the behavior is visible to callers or
   operators.

AI-generated reviews and summaries can miss defects. They are useful input to human review, not a
replacement for it. Contributors should be able to explain the submitted change and respond to review
feedback.

## Disclose AI assistance

AI assistance does not need a special label in every commit or pull request. Describe the actual
change, its rationale, and its validation using the normal [contribution requirements](../CONTRIBUTING.md).
If an AI tool materially shaped a design or implementation and that context helps reviewers evaluate
it, mention the tool's role briefly in the pull request. Never imply that generated output was tested
or independently verified when it was not.
