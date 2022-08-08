# SPDX-FileCopyrightText: 2022 Jan Tojnar
# SPDX-License-Identifier: MIT

from gi.repository import Ggit
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from typing import List, Optional
import html
import re
from .bind_property_full import bind_property_full


def has_changelog_reviewed_tag(line: str) -> bool:
    return re.match(r"^Changelog-Reviewed-By: ", line)


def find_changelog_link(lines: List[str]) -> Optional[str]:
    # Heuristics: First line starting with a URL is likely a changelog.
    for line in lines:
        line = line.strip()
        if line.startswith("https://"):
            return line
    return None


class CommitInfo(GObject.Object):
    """Wrapper around Ggit.Commit exposing properties as GObject properties."""

    __gtype_name__ = "CommitInfo"

    def __init__(self, commit: Ggit.Commit, **kwargs):
        super().__init__(**kwargs)
        self._commit = commit

    @GObject.Property(type=str)
    def id(self):
        return self._commit.get_id().to_string()


class PackageUpdate(GObject.Object):
    __gtype_name__ = "PackageUpdate"

    subject_gvariant = GObject.Property(type=GObject.TYPE_VARIANT)

    def __init__(self, subject: str, commits: List[Ggit.Commit], **kwargs):
        super().__init__(**kwargs)
        self._subject = subject
        self._commits = Gio.ListStore.new(CommitInfo)

        bind_property_full(
            source=self,
            source_property="subject",
            target=self,
            target_property="subject-gvariant",
            flags=GObject.BindingFlags.SYNC_CREATE,
            transform_to=lambda subject: GLib.Variant.new_string(subject),
        )

        self._message_lines = []
        for commit in commits:
            self.add_commit(commit)

    def add_commit(self, commit: Ggit.Commit) -> None:
        self._commits.append(CommitInfo(commit=commit))

        subject, *msg_lines = commit.get_message().splitlines()
        if subject.startswith("fixup! "):
            return
        elif subject.startswith("amend! "):
            # Starting from scratch.
            self._message_lines = []
        elif not subject.startswith("squash! "):
            # The subject from non-squash commits remains.
            self._message_lines += [subject]

        self._message_lines += msg_lines

        self.props.changes_reviewed = any(
            has_changelog_reviewed_tag(line) for line in self._message_lines
        )
        url = find_changelog_link(self._message_lines)
        self.props.changelog_link = (
            f"<a href='{html.escape(url)}'>{html.escape(url)}</a>"
            if url is not None
            else "No changelog detected."
        )

    @GObject.Property(type=str)
    def subject(self):
        return self._subject

    @GObject.Property(type=str)
    def changelog_link(self):
        return self._changelog_link

    @changelog_link.setter
    def changelog_link(self, changelog_link: str) -> None:
        self._changelog_link = changelog_link

    @GObject.Property(type=bool, default=False)
    def changes_reviewed(self):
        return self._changes_reviewed

    @changes_reviewed.setter
    def changes_reviewed(self, changes_reviewed):
        self._changes_reviewed = changes_reviewed

    @GObject.Property(type=Gio.ListStore)
    def commits(self):
        return self._commits
