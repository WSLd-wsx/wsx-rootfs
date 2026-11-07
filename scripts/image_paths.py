"""Resolve image symlinks against the image root, never the build host root."""
from collections import deque
from pathlib import Path, PurePosixPath


def resolve(root, relative):
    pending=deque(PurePosixPath(relative).parts)
    parts=[]; followed=0
    while pending:
        name=pending.popleft()
        if name in ('','/','.'):
            if name=='/':parts=[]
            continue
        if name=='..':
            if parts:parts.pop()
            continue
        path=root.joinpath(*parts,name)
        if path.is_symlink():
            followed+=1
            if followed>40:raise ValueError('Image symlink cycle: '+str(relative))
            target=path.readlink().as_posix()
            if target.startswith(('/output/','/workspace/','/mnt/')):
                raise ValueError('Build/host path in image link: '+str(relative))
            pending.extendleft(reversed(PurePosixPath(target).parts))
        else:
            parts.append(name)
    return root.joinpath(*parts)
