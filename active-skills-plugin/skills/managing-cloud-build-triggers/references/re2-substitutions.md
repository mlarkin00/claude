# Cloud Build Triggers: RE2 & Substitutions Reference

## RE2 Syntax for Branch/Tag Patterns

Cloud Build uses RE2 regular expression syntax.

| Goal                                          | RE2 Pattern   |
| --------------------------------------------- | ------------- | ---------- |
| Exact match 'main'                            | `^main$`      |
| Any branch starting with 'feature/'           | `^feature/.*` |
| Any branch ending in '-release'               | `.*-release$` |
| Branch 'dev' or 'staging'                     | `^(dev        | staging)$` |
| Any tag starting with 'v' followed by a digit | `^v\d.*`      |

## Default Substitution Variables

These variables are automatically available in every build:

- `$PROJECT_ID`: Project ID of the build.
- `$BUILD_ID`: Unique ID of the build.
- `$REPO_NAME`: Name of your repository.
- `$BRANCH_NAME`: Branch name of your source.
- `$TAG_NAME`: Tag name of your source.
- `$REVISION_ID`: Commit SHA of your source.
- `$SHORT_SHA`: First seven characters of `$REVISION_ID`.

## Custom Substitution Rules

- Custom variables MUST start with an underscore (e.g., `_ENV`, `_TARGET_CLUSTER`).
- Only uppercase letters, numbers, and underscores are allowed.
- You can override default values at the trigger level using the `--substitutions` flag.

**Example Command Syntax:**
`--substitutions="_ENV=prod,_REGION=us-central1"`
