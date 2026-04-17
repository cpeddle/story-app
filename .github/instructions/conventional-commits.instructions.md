---
description: 'Conventional commit message rules for Story App. Enforces structured commit messages with Android-specific scopes.'
applyTo: '**'
---

# Conventional Commits — Story App

## Header Format

```
<type>(<scope>): <short description>
```

Keep subject imperative, specific, and concise. Scope is strongly recommended.

## Allowed Types

| Type | Purpose |
|------|---------|
| `feat` | New feature or capability |
| `fix` | Bug fix or behaviour correction |
| `refactor` | Structural change without behaviour change |
| `perf` | Performance improvement |
| `test` | Tests added or updated |
| `docs` | Documentation only |
| `build` | Build system, dependencies, tooling |
| `ci` | CI/CD pipeline changes |
| `chore` | Maintenance or housekeeping |
| `revert` | Revert a previous commit |

## Scopes (Android Domain)

| Layer | Scopes |
|-------|--------|
| **UI** | `ui`, `compose`, `navigation`, `theme` |
| **Features** | `scene`, `character-editor`, `onboarding`, `settings` |
| **Architecture** | `viewmodel`, `di`, `mvi` |
| **Domain** | `mood-engine`, `dialogue-engine`, `action-resolver`, `fixes-engine`, `wants-engine` |
| **Data** | `database`, `datastore`, `repository` |
| **Infrastructure** | `audio`, `content-filter`, `i18n`, `assets` |
| **Build** | `gradle`, `convention-plugins`, `deps` |
| **Governance** | `governance`, `skills`, `instructions` |

Omit scope only when no single area fits.

## Body

Add a body when:
- Change spans multiple files
- Rationale is non-obvious
- Behaviour changed

Use short paragraphs or flat bullets. Explain **why**, not just **what**.

## Breaking Changes

```
feat(database)!: restructure character schema

BREAKING CHANGE: CharacterEntity now uses sealed archetype variants.
Migration required from v1 schema.
```

## Traceability

- `Refs: #<issue-number>` — reference GitHub issue
- `Closes: #<issue-number>` — auto-close issue on merge

## Examples

```
feat(mood-engine): add directional mood tracking per character pair
fix(compose): correct touch target size for radial menu items
refactor(di): migrate DialogueEngine binding to SingletonComponent
test(fixes-engine): add exhaustive tests for partial-credit rejection
docs(governance): update T1.2 findings in ingestion audit trail
build(convention-plugins): add AndroidComposeConventionPlugin
chore(deps): bump Hilt to 2.51
```
