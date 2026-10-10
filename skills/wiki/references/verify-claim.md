# Step: verify the claims of one page

You are a sceptical verifier. Try to prove the technical claims on the page wrong.

## Inputs

- `page`: the catalogue entry of the page (`id`, `path`, `audience`, `brief`, `sources`, ...).

## Procedure

1. Read the page at `<wiki_dir>/<page.path>`. List its definite statements: "X does Y", "Y happens when Z", and so on.
2. For each statement, read the sources (`page.sources`, expanded with `git ls-files`) and try to disprove it. Use `major` or higher for:
   - A statement that is true only under a condition the page does not state.
   - A statement that describes an older implementation.
   - A cause and effect that are reversed.
3. Check every Mermaid diagram against the real structure and call order. A diagram that disagrees with the code is `major`.
4. If an important fact is missing, so that the page does not answer `page.brief`, that is `major`.
5. Broken sentences in the configured language, and terms that change within the page, are `minor`.
6. The last check depends on the page:
   - On a no-code page (see `writing-rules.md`), source code is `major`: snippets, function names, type names and file paths. Relative links to other wiki pages are not code. Do not report them, because the related-pages section is required on every page.
   - On other pages, an identifier or path that is not spelled exactly as in the code is `major`.

When you are unsure whether something is an issue, report it. A missed error costs more than an extra fix. The exception in step 6 is not a case for doubt: never report wiki links.

You are a verifier, not a writer. Do not change any file.

## Output

Return `<SKILL_DIR>/schemas/verdict.schema.json` with `lens: "claim"`. Set `pass` to `true` only if `issues` is empty. Give each issue a concrete `location`, and a `fix` that says what to change.
