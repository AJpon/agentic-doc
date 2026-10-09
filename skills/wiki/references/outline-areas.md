# Step: split the repository into survey areas

Decide how to divide the repository among the surveyors. This is the first step of `outline`.

## Inputs

None.

## Procedure

1. Look at the shape of the repository:
   - The top-level directories.
   - The build and package files.
   - The tests.
   - CI.
   - The existing documentation (README, AGENTS.md, CONTRIBUTING, docs/).

   Use `git ls-files` to see only tracked files. Skip files that match `exclude` from `config show`.
2. Split the repository into 3 to 5 areas. Each area must be worth surveying separately, and together the areas must cover everything that the wiki needs to explain. The following split is common. Adapt it to the repository instead of copying it:

   | Area | Typical scope |
   | --- | --- |
   | Source code structure | The main source tree: modules, responsibilities, dependencies |
   | Tests and verification | The test suites and fixtures, and what they pin down |
   | Build, dependencies and tooling | Build files, dependency management, CI, hooks, scripts |
   | Existing documentation | READMEs and design documents, and where they disagree with the code |

   A large source tree can be split further, for example by layer or by subsystem.
3. For each area, write:
   - `scope`: the globs to read.
   - `questions`: 3 to 6 concrete questions that the surveyor must answer from the code.

Do not write any file.

## Output

Return `<SKILL_DIR>/schemas/survey-areas.schema.json`. `key` is a short lowercase identifier, such as `source`, `tests`, `build` or `docs`. `title` is a name that a person can read.
