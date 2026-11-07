# Remote retirement execution record

The user explicitly authorized deleting all wsx-rootfs Releases and attachments
and its dedicated verified-components GHCR package. During execution the user
waived further backup and requested immediate deletion. That later instruction
superseded the earlier requirement to finish recoverable backups; no further
scope confirmation was required.

## Result

Deletion and subsequent API verification succeeded. The repository now has zero
Releases, and GET of the previously accessible dedicated package returns HTTP 404
after a successful DELETE. Repository identity and private visibility were
rechecked successfully. The exact verification time is in remote-retirement.json.

| Deleted Release ID | Tag | Deleted attachments |
| --- | --- | ---: |
| 430347773 | wsx-cachyos-plasma-2026.11.1-r2 | 6 |
| 430329519 | wsx-cachyos-plasma-2026.11.1-r1 | 6 |
| 429946009 | wsx-omarchy-4.0.6-r7 | 6 |
| 429927434 | component-import-6dd87b7082bd93a330e397c8aa315b18c6f06428405be7760da930fdd6318206 | 1 |

All four Releases were Drafts; their 19 attachments were removed with them.
The dedicated private package was `wsx-rootfs/verified-components`, package ID
16440856, with one version (1478930273), digest
`sha256:fbf7a09de32f616c1198191af8346f071f13c4e530580eff4289bb668fea84e9`.
Its repository association and exact version were revalidated before deletion.
No other package or repository was touched.

## Boundaries preserved

Git refs before and after are identical: main remains at
`ed7a9827ade026e828f4f0124c5261b46cdb2103`; no tag, branch or commit was deleted
or rewritten. Actions runs/artifacts and workflow activation states were not
changed. No commit, push, build dispatch, replacement package or new release was
created. The working-tree source migration has not been pushed; remote main
still contains the old recipe. Its scheduled builds can fail when attempting to
fetch the now-retired package. This operation did not disable that schedule.

The license review remains unresolved. Remote retirement is not a new license
grant, corresponding-source package, ownership determination or revocation of
previously effective permissions. See RECHECK.md for the remaining source,
notice, grantor and image-content work before replacement distribution.

## Local retained evidence, not a complete release backup

`/tmp/wsx-rootfs-remote-retirement-20261103T154204/` contains the exact pre-delete
metadata, deletion-plan.json, deletion-journal.json and deletion-result.json.
It also retains the local working-tree snapshot and verified Git bundle.

Seventeen release attachments were fully downloaded and individually checked
against the API SHA-256 digests before the instruction to stop. The Omarchy r7
rootfs download was incomplete and remains a `.partial` file; do not treat it as
restorable. The component staging Release archive was not downloaded through
that route. The dedicated OCI manifest/config/layer were separately backed up
and hash-verified; its embedded component archive hash matches the historical
pin. These are retained files, not a claim that all deleted Releases can be fully
restored from this directory. Git bundles do not include release attachments.

The user reported existing latest attachments under /mnt/wsl/u/wsx/. A bounded
lookup did not establish their exact location or hashes before the user waived
further backup. Their existence or recoverability is not asserted by this report.
No other repository was entered to search for them. The task-owned downloader
and its child were stopped; no desktop, service, device owner or other process
was stopped. Existing local files were not deleted.

These files reside under /tmp; retain the needed evidence outside temporary
storage before routine cleanup. Any later restoration would need separate
instructions and would not recreate the original GitHub asset IDs/timestamps.
