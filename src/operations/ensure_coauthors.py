# SPDX-FileCopyrightText: 2023 Jan Tojnar
# SPDX-License-Identifier: MIT

import re
from gi.repository import Ggit
from gi.repository import Gio
from typing import Generator
from ..package_update import PackageUpdate
from ..git_utils import is_commit_empty, signature_to_string

CO_AUTHORED_BY_REGEX = re.compile(
    r"^Co-authored-by: *(.+) *$",
    re.IGNORECASE | re.MULTILINE,
)


def get_coauthors(commit_message: str) -> list[str]:
    return re.findall(CO_AUTHORED_BY_REGEX, commit_message)


def get_missing_coauthors(
    # Should be Gio.ListStore[PackageUpdate] but pygobject does not implement Generic.
    updates: Gio.ListStore,
) -> Generator[tuple[Ggit.Commit, set[str]], None, None]:
    for update in updates:
        authors: set[str] = set()
        acknowledged_authors: set[str] = set(
            get_coauthors(update.props.final_commit_message)
        )

        assert (
            len(update.props.commits) > 0
        ), "Update does not consist of any commits, should not happen"
        first_commit = update.props.commits[0].get_commit()
        acknowledged_authors.add(signature_to_string(first_commit.get_author()))

        for commit_info in update.props.commits:
            commit = commit_info.get_commit()
            if not is_commit_empty(commit):
                authors.add(signature_to_string(commit.get_author()))

        missing_authors = authors - acknowledged_authors
        if len(missing_authors) > 0:
            yield first_commit, missing_authors
