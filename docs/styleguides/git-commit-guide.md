# Git Commit Guide

This document outlines conventions for writing git commit messages in the muzikki-backend project.

## Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type

The type must be one of the following:

- **feat**: A new feature
- **fix**: A bug fix
- **docs**: Documentation only changes
- **style**: Changes that don't affect code meaning (whitespace, formatting, etc.)
- **refactor**: Code change that neither fixes a bug nor adds a feature
- **perf**: Performance improvement
- **test**: Adding or updating tests
- **chore**: Changes to build process, tools, or dependencies

### Scope

The scope should be the name of the affected component or module (optional):

- `api`
- `models`
- `auth`
- `database`
- `frontend`
- etc.

### Subject

The subject line:

- Use imperative, present tense: "add" not "added" nor "adds"
- Don't capitalize first letter
- No period (.) at the end
- Maximum 50 characters

### Body

The body should include:

- Motivation for the change
- Contrast with previous behavior
- Use present tense
- Wrap at 72 characters

### Footer

The footer should contain:

- References to issues: `Closes #123, #456`
- Breaking changes: `BREAKING CHANGE: description`

## Examples

### Simple commit

```
feat(auth): add JWT token authentication

Implement JWT-based authentication for API endpoints to improve security
and enable stateless authentication.

Closes #42
```

### Bug fix

```
fix(api): resolve artist serialization error

Fix issue where artist bio field was not properly serialized when empty.
Added null check before serialization.

Closes #87
```

### Documentation

```
docs: update API documentation for artists endpoint

Add examples for filtering and pagination parameters in the artists
endpoint documentation.
```

### Breaking change

```
refactor(api): change response format for list endpoints

Change list endpoint response format to include metadata for pagination
and filtering. This provides better structure and consistency.

BREAKING CHANGE: List endpoints now return data in a 'results' field
instead of returning the array directly.

Before: GET /api/v1/artists returned [...]
After: GET /api/v1/artists returns {count: n, results: [...]}

Closes #105
```

### Multiple changes

```
chore: update dependencies and improve test coverage

- Update Django to 4.2
- Update djangorestframework to 3.14
- Add missing tests for user model
- Update requirements.txt

Closes #89, #90
```

## Best Practices

1. **Atomic commits**: Each commit should represent a single logical change
2. **Commit often**: Make small, frequent commits rather than large, infrequent ones
3. **Test before commit**: Ensure tests pass before committing
4. **Review your changes**: Use `git diff` before committing to review what you're committing
5. **Don't commit generated files**: Use `.gitignore` to exclude build artifacts and dependencies
6. **Write meaningful messages**: Future you (and your team) will thank you

## Bad Examples (to avoid)

```
fix stuff
```
Too vague, doesn't explain what was fixed.

```
WIP
```
Don't commit work in progress without description.

```
Fixed the bug with the thing in the place that wasn't working
```
Too informal and imprecise.

```
feat: Added new feature that does this and that and also fixed a bug and updated documentation
```
Too many changes in one commit, should be split into multiple commits.
