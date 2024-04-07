# SPDX-FileCopyrightText: 2023 Jan Tojnar
# SPDX-License-Identifier: MIT

from gi.repository import Ggit
from .helpers import unwrap


def signature_to_string(signature: Ggit.Signature) -> str:
    return f"{signature.get_name()} <{signature.get_email()}>"


def is_commit_empty(commit: Ggit.Commit) -> bool:
    repo: Ggit.Repository = unwrap(commit.get_owner())
    commit_tree: Ggit.Tree = unwrap(commit.get_tree())
    commit_parents: Ggit.CommitParents = unwrap(commit.get_parents())

    if commit_parents.get_size() > 0:
        parent_commit: Ggit.Commit = unwrap(commit_parents.get(0))
        parent_tree: Ggit.Tree = unwrap(parent_commit.get_tree())

        diff: Ggit.Diff = unwrap(
            Ggit.Diff.new_tree_to_tree(
                repo,
                parent_tree,
                commit_tree,
                None,
            )
        )

        return diff.get_num_deltas() == 0
    else:
        # Root commit has no parent so we do not need to compare it.
        return commit_tree.size() == 0
