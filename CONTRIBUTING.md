# Contributing

Bug reports, questions and patches are all welcome.

## Reporting a problem

Open an issue at
<https://github.com/syunz0531/sgotools/issues>. For anything involving the
data, please include:

- the snapshot date (the `created_utc` field in its `manifest.json`), and
- the SHA-256 of the file in question, as recorded in that manifest.

NHTSA replaces the published files in place, so a result that cannot be
reproduced is often a different release rather than a bug — the manifest is
what tells the two apart.

## Development

```bash
git clone https://github.com/syunz0531/sgotools
cd sgotools
pip install -e ".[test]"
pytest -q
```

The tests build small synthetic snapshots in `tests/conftest.py` and need no
network access or downloaded data.

## Changing how the data is handled

Decisions about the data — which rows count as incidents, how the two
reporting regimes line up, what a column means — live in
`src/sgotools/constants.py`, with the reason for each one written beside it.
If you change one, please say in the pull request which published file or
which page of NHTSA's data-element definitions supports the change, and add
a test that fails without it.

Two rules keep the package honest, and a change should not break them:

- No filter is applied that the caller did not ask for.
- Everything applied is recorded in the `Provenance` attached to the result.

## Scope

This package reads what NHTSA publishes. It does not estimate exposure,
adjudicate whether a crash was police-reportable, or make safety claims about
any company or system. Proposals in those directions are better suited to an
analysis built on top of the package.
