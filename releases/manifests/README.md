# Release Manifests

This directory is reserved for versioned dataset manifests.

Intended contents:

- one `manifest.json` per published dataset version
- source refresh metadata
- table row counts and quality-check summaries

`manifest.template.json` is the starting structure for each release manifest,
matching the manifest contract in `V1-DATASET-SPEC.md`. Copy it to
`manifest-<dataset_version>.json` and fill in real values when publishing a
release.
