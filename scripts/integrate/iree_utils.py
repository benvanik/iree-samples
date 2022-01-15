# Copyright 2022 The IREE Authors
#
# Licensed under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import os
import shlex
import shutil
import subprocess
from typing import Tuple

_repo_root = None


def get_repo_root() -> str:
    global _repo_root
    if _repo_root is None:
        _repo_root = os.getcwd()
        _validate_repo_root()
    return _repo_root


def get_submodule_root(submodule) -> str:
    path = os.path.join(get_repo_root(), "third_party", "llvm-project")
    if not os.path.isdir(path):
        raise SystemExit(f"Could not find submodule: {path}")
    return path


def _validate_repo_root():
    # Look for something we know is there.
    known_dir = os.path.join(_repo_root, "iree/compiler")
    if not os.path.isdir(known_dir):
        raise SystemExit(f"ERROR: Must run from the iree repository root. "
                         f"Actually in: {_repo_root}")


def git_setup_remote(remote_alias, url, *, repo_dir=None):
    needs_create = False
    try:
        existing_url = git_exec(["remote", "get-url", remote_alias],
                                capture_output=True,
                                repo_dir=repo_dir,
                                quiet=True)
        existing_url = existing_url.strip()
        if existing_url == url:
            return
    except subprocess.CalledProcessError:
        # Does not exist.
        needs_create = True

    if needs_create:
        git_exec(["remote", "add", "--no-tags", remote_alias, url])
    else:
        git_exec(["remote", "set-url", remote_alias, url])


def git_check_porcelain(*, repo_dir=None):
    output = git_exec(["status", "--porcelain", "--untracked-files=no"],
                      capture_output=True,
                      quiet=True,
                      repo_dir=repo_dir)
    if output:
        raise SystemExit(
            f"ERROR: git directory {get_repo_root()} is not clean. "
            f"Please stash changes:\n{output}")


def git_fetch(*, repository=None, repo_dir=None):
    args = ["fetch"]
    if repository:
        args.append(repository)
    git_exec(args, repo_dir=repo_dir)


def git_checkout(ref, *, repo_dir=None):
    git_exec(["checkout", ref], repo_dir=repo_dir)


def git_create_branch(branch_name,
                      *,
                      checkout=True,
                      ref=None,
                      force=False,
                      repo_dir=None):
    branch_args = ["branch"]
    if force:
        branch_args.append("-f")
    branch_args.append(branch_name)
    if ref is not None:
        branch_args.append(ref)
    git_exec(branch_args, repo_dir=repo_dir)

    if checkout:
        git_exec(["checkout", branch_name], repo_dir=repo_dir)


def git_push_branch(repository, branch_name, *, force=False, repo_dir=None):
    push_args = ["push", "--set-upstream"]
    if force:
        push_args.append("-f")
    push_args.append(repository)
    push_args.append(f"{branch_name}:{branch_name}")
    git_exec(push_args, repo_dir=repo_dir)


def git_submodule_set_origin(path, *, url=None, branch=None, repo_dir=None):
    if url is not None:
        git_exec(["submodule", "set-url", "--", path, url], repo_dir=repo_dir)

    if branch is not None:
        try:
            if branch == "--default":
                git_exec(["submodule", "set-branch", "--default", "--", path],
                         repo_dir=repo_dir)
            else:
                git_exec([
                    "submodule", "set-branch", "--branch", branch, "--", path
                ],
                         repo_dir=repo_dir)
        except subprocess.CalledProcessError:
            # The set-branch command returns 0 on change and !0 on no change.
            # This is a bit unfortunate.
            ...


def git_reset(ref, *, hard=True, repo_dir=None):
    args = ["reset"]
    if hard:
        args.append("--hard")
    args.append(ref)
    git_exec(args, repo_dir=repo_dir)


def git_current_commit(*, repo_dir=None) -> Tuple[str, str]:
    output = git_exec(["log", "-n", "1", "--pretty=format:%H (%ci): %s"],
                      capture_output=True,
                      repo_dir=repo_dir,
                      quiet=True)
    output = output.strip()
    parts = output.split(" ")
    # Return commit, full_summary
    return parts[0], output


def git_create_commit(*, message, add_all=False, repo_dir=None):
    if add_all:
        git_exec(["add", "-A"], repo_dir=repo_dir)
    git_exec(["commit", "-m", message])


def git_exec(args, *, repo_dir=None, quiet=False, capture_output=False):
    full_args = ["git"] + args
    full_args_quoted = [shlex.quote(a) for a in full_args]
    if not repo_dir:
        repo_dir = get_repo_root()
    if not quiet:
        print(f"++ EXEC: (cd {repo_dir} && {' '.join(full_args_quoted)})")
    if capture_output:
        return subprocess.check_output(full_args, cwd=repo_dir).decode("utf-8")
    else:
        subprocess.check_call(full_args, cwd=repo_dir)
