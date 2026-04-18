# Playbook: new-plugin-scaffold

## Trigger

A human or Claude Code has designed a new plugin contract and flagged a scaffold request. The FlaggedIssue payload names the plugin name, the artifact type, and any skeleton constraints from the contract.

## Prompt

You are running as an autonomous coding agent in an isolated VM. You have no conversation history. Read this prompt in full before acting.

Target repository: {{TARGET_REPO}}
Target branch to base work on: {{TARGET_BRANCH}}
Working branch you must create: {{BRANCH_NAME}}
Pull request title: {{PR_TITLE}}
Flagged issue id: {{ISSUE_ID}}
Playbook: {{PLAYBOOK}}

Mandatory reading before any edit:

1. AGENTS.md at the repo root. Obey every rule there.
2. STYLE.md at the repo root.
3. `plugins/README.md`. This is the authoritative contract for plugin layout.
4. At least one existing plugin directory as a shape reference, for example `plugins/audit-log-generator/`.

Payload (JSON):

```json
{{PAYLOAD_JSON}}
```

Task:

1. Create `plugins/<name>/` with the directory layout defined in `plugins/README.md`.
2. Create an empty SKILL.md containing only the section headers required by `plugins/README.md` and a single `TODO` marker in each body. Do not fill in any framework interpretation.
3. Create a stub `schema.json` that validates against the plugin-schema meta-schema. Empty properties object is acceptable.
4. Create a `tests/` directory with one placeholder test marked as skipped or pending.
5. If a plugin index exists, add an entry for the new plugin with no descriptive text beyond name and artifact type.
6. Run the repo's lint and test suite. If anything fails, stop.
7. Open a pull request with the exact title above. PR body must state "scaffold-only, no body content."

## Expected output

A single pull request that adds a new plugin directory containing only scaffold. No framework interpretation, no prose beyond section headers and TODO markers.

## Success criteria

1. Directory structure matches `plugins/README.md` exactly.
2. `schema.json` validates against the plugin-schema meta-schema.
3. Placeholder test is marked skipped or pending.
4. SKILL.md contains only section headers and TODO markers. No body content.
5. No framework interpretation, no control mappings, no risk taxonomy entries.
6. Existing tests still pass.

## Citations required

1. `plugins/README.md`, by path, as the authoritative contract.
