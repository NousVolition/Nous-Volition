# Smaller clones, complete original history preserved

The numerical paths already moved to Releases have also been removed from normal branch and tag history. **No numerical results were discarded.** The current main tree was identical before and after the history replacement; the follow-up documentation only explains storage and recovery. Source code, figures, reports, scientific qualifications, authors, commit messages and merge structure were preserved.

## Download and recover

- [Numerical data and full original-history backup](https://github.com/NousVolition/Nous-Volition/releases/tag/numerical-data-2026-10-11)
- [History recovery guide](https://github.com/NousVolition/Nous-Volition/releases/download/numerical-data-2026-10-11/HISTORY-BACKUP.md)
- [Original-history verification and exact refs](https://github.com/NousVolition/Nous-Volition/releases/download/numerical-data-2026-10-11/history-backup-verification.json)
- [History asset checksums](https://github.com/NousVolition/Nous-Volition/releases/download/numerical-data-2026-10-11/HISTORY-SHA256SUMS.txt)
- [Restore helper](https://github.com/NousVolition/Nous-Volition/releases/download/numerical-data-2026-10-11/restore_git_history.py)

The numerical ZIP archives and their existing links are unchanged. Continue using [the data restore instructions](DATA-RELEASES.md) for analyses in a current checkout. Restoring the complete old Git history is optional and is needed only to examine an original commit or recover an earlier revision.

For the complete original history, download the history bundle (or every numbered bundle part), `history-backup-verification.json`, and `restore_git_history.py` from the release into one folder. With Git and Python 3.10 or later, run:

```text
python restore_git_history.py --destination restored-original.git
git clone restored-original.git restored-original
```

Choose a new destination. The helper verifies all checksums, Git object integrity and the original refs. Keep this recovery clone separate; pushing its old refs back would restore the large history.

## What was verified

- All **34 original commits** are in the complete history backup, including every reachable historical file version.
- The uploaded backup was downloaded again and restored independently. Every original reference and reachable object ID matched.
- Every retained file entry across every rewritten commit matched its original Git blob and file mode. Only the preselected archived numerical paths were removed.
- Author, committer, commit messages and parent/merge relationships matched. No commits were dropped.
- The replacement was rehearsed against a disposable local mirror using an atomic update and exact old-commit leases. Fresh normal clones of the rehearsal were checked.

Measured Git object storage before cleanup was **98,746,271 bytes**; the prepared cleaned mirror was **38,301,210 bytes**, a **61.2% reduction**. The follow-up documentation adds only small text files. This is compressed Git object storage, not the size of restored scientific data or the full working folder.

## Commit IDs and historical citations

History rewriting changes affected commit IDs. Original identifiers in dated scientific manifests and publications have deliberately been preserved; they refer to the original-history backup. The [verified cleanup kit](https://github.com/NousVolition/Nous-Volition/releases/download/numerical-data-2026-10-11/verified-history-cleanup-kit.zip) contains `proposed-commit-map.txt`, which maps original commits to their rewritten counterparts, along with the exact before/after refs and verification record. Its `proposed` filenames identify the prepared artifact; the cleanup was subsequently applied using that recorded mapping.

Old GitHub commit links can depend on GitHub retaining old objects. For durable access to an original commit, restore the backup and check out its original ID. Original signed commit objects, where present, remain in that backup; rewritten commits do not retain the original signatures.

Release download URLs and uploaded numerical assets remain unchanged. GitHub's automatically generated source ZIPs follow the rewritten tags; use the numerical ZIPs plus `reports-and-source.zip` to restore the exact dated publication, or the complete history bundle for any older commit. GitHub-managed pull-request refs were backed up but were not rewritten; they can retain old objects on GitHub and are not ordinarily fetched by normal clones.

If you have an existing working clone, preserve any uncommitted work and use a fresh clone before publishing further changes. A normal pull from the old history is not the right way to synchronize after this cleanup. Local live simulation folders were not altered or restarted.
