# History reconstruction preparation

The owner requested a new root commit based on the current local tree. The old
reachable history is retained in a repository-exclusive external audit bundle,
with the original working tree, hashes and remote-reference evidence. No claim
is made that a Git bundle preserves GitHub attachments, LFS or Actions artifacts.

The pre-reconstruction main commit is
`f54d2947080ef25fbbd23627436a55aea2b603d9` (51 reachable commits).
The remote reference inspection found only main; the Release API returned an
empty list. The previously retired dedicated verified-components package returned
404, consistent with the earlier successful deletion record; 404 alone does not
establish universal absence of registry resources.

Reconstruction changes the visible ancestry, not authorship, upstream licenses,
prior effective grants or historical distribution obligations. Third-party and
MIT-marked vendor bytes remain unchanged. Old commit IDs in provenance and review
records remain references to the preserved audit history, not ancestors of the new
root. The root commit's author is not the author of every imported file.

The public identity is explicitly designated by the owner as the individual WGY
(GitHub: wgy-wsx) <wgy@wsxdesk.com>. New source-available terms remain inactive;
publication remains blocked. This reconstruction is not a claim that commercial
use of the complete rootfs can be prohibited, or that corresponding source and
payload licensing review are complete.

A separate audit checkout prepares the proposed root commit without moving the
working repository's main branch. Exact old/new commit and tree IDs and file
changes must be reviewed before any remote rewrite. Immediately before an approved
rewrite, reread the old remote SHA and use an explicit per-reference force lease.
Never use a bare force push or update unrelated references. GitHub may retain old
commits through caches, Actions records or other references after a branch rewrite.
