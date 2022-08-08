# SPDX-FileCopyrightText: 2022 Jan Tojnar
# SPDX-License-Identifier: MIT

from gi.repository import Ggit
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from linkify_it import LinkifyIt
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


def linkify_html(text: str) -> str:
    linkify = LinkifyIt()

    if not linkify.test(text):
        return ""

    result = ""
    last_index = 0
    for match in linkify.match(text):
        link = f"<a href='{html.escape(match.url)}'>{html.escape(match.text)}</a>"
        result += html.escape(text[last_index : match.index]) + link
        last_index = match.last_index

    result += text[last_index:]

    return result


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
    final_commit_message_rich = GObject.Property(type=str)

    def __init__(self, subject: str, commits: List[Ggit.Commit], **kwargs):
        super().__init__(**kwargs)
        self._subject = subject
        self._commits = Gio.ListStore.new(CommitInfo)
        self._message_lines = []

        bind_property_full(
            source=self,
            source_property="subject",
            target=self,
            target_property="subject-gvariant",
            flags=GObject.BindingFlags.SYNC_CREATE,
            transform_to=lambda subject: GLib.Variant.new_string(subject),
        )

        for commit in commits:
            self.add_commit(commit)

        bind_property_full(
            source=self,
            source_property="final-commit-message",
            target=self,
            target_property="final-commit-message-rich",
            flags=GObject.BindingFlags.SYNC_CREATE,
            transform_to=lambda message: linkify_html(message),
        )

    def add_commit(self, commit: Ggit.Commit) -> None:
        self._commits.append(CommitInfo(commit=commit))

        subject, *msg_lines = commit.get_message().splitlines()
        old_message_lines = self._message_lines
        if subject.startswith("fixup! "):
            return
        elif subject.startswith("amend! "):
            # Starting from scratch.
            self._message_lines = []
            # Drop empty line after subject.
            match msg_lines:
                case ["", *rest]:
                    msg_lines = rest
        elif not subject.startswith("squash! "):
            # The subject from non-squash commits remains.
            self._message_lines += [subject]

        self._message_lines += msg_lines
        if old_message_lines != self._message_lines:
            self.notify("final-commit-message")

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
    def final_commit_message(self):
        return "\n".join(self._message_lines)

    @final_commit_message.setter
    def final_commit_message(self, message):
        self._message_lines = message.splitlines()

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
