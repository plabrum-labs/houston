# ToolJet

**What it is:** Open-source low-code internal-tools builder (drag-drop UI, 50+ data source connectors, JS/Python transforms), self-hostable.
**Axis:** app-builder, deploy/migration.
**Depth:** thin — docs and GitHub only.

## Products & surfaces

| Product | What it is |
|---|---|
| **ToolJet** | Core app builder: canvas, queries, workflows. |
| **GitSync** | Push/pull an app's definition to/from a git repository for version control and promotion between environments. |
| **GitSync API** | Programmatic commit/push of app versions, for CI/CD pipelines. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| GitSync app-as-folder | Each app becomes a folder (`.meta/meta.json` + app JSON) in the repo | no (cautionary) |
| Whole-file replacement on commit | Every push overwrites the entire app JSON file, not a structural diff | no (cautionary) |

## Worth avoiding

**GitSync stores an app as one JSON file, replaced wholesale on every commit.** Per ToolJet's own docs, pushing a new app version replaces the app's JSON file in its folder outright and updates `.meta/meta.json` with the new version id/name. There is no structural serialization — the diff a reviewer sees in git is the entire file, because JSON key ordering and nested object churn touch most of the file on almost any change. That diff is **100% of the file: unreviewable by a human, unmergeable by git, and useless as input to an LLM** trying to understand what changed.

This is precisely the format Retool *abandoned* — Retool's YAML-based source control had the same "whole-app serialization" shape before being replaced by Toolscript specifically to make diffs reviewable (see `retool.md`). ToolJet's GitSync is git-shaped (it uses git, has push/pull, has an API) but not git-*useful* in the way that matters for review or for AI-assisted editing.

**The general lesson:** "we store our app in git" and "our app is code" are different claims. GitSync satisfies the first (there's a repo, there's a commit history) without satisfying the second (a change is legible as a diff). Retool's Toolscript satisfies both. The gap between them is the gap this file exists to mark.

## Facts & figures

- GitSync ships from ToolJet 2.50.0-LTS onward per version-scoped docs; folder/JSON structure confirmed across 2.50.0-LTS and 3.0.0-LTS doc trees.

## Sources

- [GitSync overview (2.50.0-LTS)](https://docs.tooljet.com/docs/2.50.0-lts/gitsync/)
- [Push Changes to Git Repo](https://docs.tooljet.com/docs/development-lifecycle/gitsync/push/)
- [Pushing Changes to Git Repo (3.0.0-LTS)](https://docs.tooljet.com/docs/3.0.0-lts/release-management/gitsync/git-push/)
- [GitSync API](https://docs.tooljet.com/docs/development-lifecycle/cicd/gitsync-api/)
- [ToolJet GitHub — versioned GitSync docs source](https://github.com/ToolJet/Tooljet/blob/develop/docs/versioned_docs/version-3.16.0-LTS/development-lifecycle/gitsync/overview.md)
- **Not directly verified:** whether newer ToolJet versions (post 3.16) have moved toward a more structural/per-resource serialization; this file reflects the folder+single-JSON model documented as of research date.
