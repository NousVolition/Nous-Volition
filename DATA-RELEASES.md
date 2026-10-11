# Numerical data downloads

**[Open the verified data release](https://github.com/NousVolition/Nous-Volition/releases/tag/numerical-data-2026-10-11)**

The 11 October 2026 storage migration moves **20 numerical files (61,321,907 bytes)** out of the current source tree. Their contents and original paths are preserved in release ZIP archives. No simulation, coefficient, numerical result or evidence level was changed by this move. Summary JSON/CSV, figures, interactive reports and numerical source remain in the repository.

## Read reports and download data

Continue using the normal report pages. Links to moved arrays now download the containing study archive. Each ZIP retains the repository folder structure; unzip into one common root, not separate folders named after the ZIPs. Some studies span several independent ZIPs: download all of that study's ZIPs for its full data.

The [file catalog](data-release/catalog.json) maps every original filename to an archive and records its size, SHA-256 and Git blob identity. [Local archive verification](data-release/archive-verification.json) records the full restore check. The release also contains a SHA256SUMS.txt list.

## Restore data into a current checkout

From the repository folder, with Python 3.10 or later:

```text
python tools/restore_numerical_data.py
python tools/restore_numerical_data.py --verify-only
```

This downloads and checks every numerical archive, restores the exact original paths, then verifies every restored file. It does not rerun simulations or overwrite files with different contents. Matching existing files are preserved. Restored paths are ignored by Git so the large files are not accidentally recommitted.

To restore one study, append its repository path, for example `--study studies/sims-recovery-entrainment`. Omit that option before running the complete repository checks. Automated checks restore their required data before validation; the original package and numerical checks remain in place.

## Keep a complete offline copy of the original publication

The release includes **every one of the 531 original files** from commit [`bfa175101743`](https://github.com/NousVolition/Nous-Volition/tree/bfa17510174326b0f9afc99d697ea5f3a94d0f61): numerical ZIPs plus `reports-and-source.zip`. That source/report archive preserves all original reports, figures, scripts, checksums and historical records exactly as they were.

Download `restore_numerical_data.py` and `catalog.json` from the release into one folder, then run:

```text
python restore_numerical_data.py --catalog catalog.json --full-snapshot --destination restored-original
```

Use a **new empty destination**. This recreates the original complete publication, including original local report links, without mixing later edited documentation into its historical checksum set. For offline use, download all ZIPs too and add `--assets-dir .`. Manual extraction of all ZIPs into one common folder also restores the original layout; the helper additionally verifies all hashes.

## Archive downloads

| Archive | Files | Bytes |
| --- | ---: | ---: |
| [sims-recovery-entrainment-numerical-001.zip](https://github.com/NousVolition/Nous-Volition/releases/download/numerical-data-2026-10-11/sims-recovery-entrainment-numerical-001.zip) | 7 | 17,034,635 |
| [social-organization-numerical-001.zip](https://github.com/NousVolition/Nous-Volition/releases/download/numerical-data-2026-10-11/social-organization-numerical-001.zip) | 13 | 44,291,492 |
| [reports-and-source.zip](https://github.com/NousVolition/Nous-Volition/releases/download/numerical-data-2026-10-11/reports-and-source.zip) | 511 | 37,461,696 |

## Preservation and limits

- Original result bytes and historical publication receipts are preserved in the release and in Git history. Where a current download link changed inside a checked package, its current delivery manifest was updated; the original manifest remains in `reports-and-source.zip`.
- This makes a fresh main-branch checkout or shallow clone smaller. A full clone still contains old large blobs in Git history; no history was rewritten.
- The archive is a dated snapshot. Later studies and completions require their own verified additions and are not implied by this release.
- Reading the kept report pages does not require restoring arrays. Running analyses or package verification that load those arrays does require restoration first.

[Published-download verification](data-release/remote-verification.json) records an independent download of every release asset, exact agreement with the locally restored archives, and validation of every archived member.
