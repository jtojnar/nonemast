# SPDX-FileCopyrightText: 2022 Jan Tojnar
# SPDX-License-Identifier: MIT

from gi.repository import Ggit
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from linkify_it import LinkifyIt
from typing import Optional
import html
import re


def has_changelog_reviewed_tag(line: str) -> bool:
    return re.match(r"^Changelog-Reviewed-By: ", line) is not None


def try_getting_corresponding_github_link(url: str) -> str:
    url = url.replace(
        "https://gitlab.gnome.org/GNOME/",
        "https://github.com/GNOME/",
    )
    url = url.replace("/-/", "/")

    return url


def find_changelog_link(lines: list[str]) -> Optional[str]:
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

    id_gvariant = GObject.Property(type=GObject.TYPE_VARIANT)

    def __init__(self, commit: Ggit.Commit, **kwargs):
        super().__init__(**kwargs)
        self._commit = commit

        self.bind_property(
            "id",
            self,
            "id-gvariant",
            GObject.BindingFlags.SYNC_CREATE,
            lambda _binding, subject: GLib.Variant.new_string(subject),
        )

    @GObject.Property(type=str)
    def id(self):
        return self._commit.get_id().to_string()

    def get_commit(self) -> Ggit.Commit:
        return self._commit


class PackageUpdate(GObject.Object):
    __gtype_name__ = "PackageUpdate"

    subject_gvariant = GObject.Property(type=GObject.TYPE_VARIANT)
    commit_message_is_edited = GObject.Property(type=bool, default=False)
    editing_stack_page = GObject.Property(type=str, default="not-editing")
    final_commit_message_rich = GObject.Property(type=str)

    def __init__(self, subject: str, commits: list[Ggit.Commit], **kwargs):
        super().__init__(**kwargs)
        self._subject = subject
        self._commits = Gio.ListStore.new(CommitInfo)
        self._message_lines: list[str] = []

        self.bind_property(
            "subject",
            self,
            "subject-gvariant",
            GObject.BindingFlags.SYNC_CREATE,
            lambda _binding, subject: GLib.Variant.new_string(subject),
        )

        for commit in commits:
            self.add_commit(commit)

        self.bind_property(
            "final-commit-message",
            self,
            "final-commit-message-rich",
            GObject.BindingFlags.SYNC_CREATE,
            lambda _binding, message: linkify_html(message),
        )

        self.bind_property(
            "commit-message-is-edited",
            self,
            "editing-stack-page",
            GObject.BindingFlags.SYNC_CREATE,
            lambda _binding, editing: "editing" if editing else "not-editing",
        )

    def add_commit(self, commit: Ggit.Commit) -> None:
        self._commits.append(CommitInfo(commit=commit))

        subject, *msg_lines = commit.get_message().splitlines()
        # Clone list so we can detect changes.
        old_message_lines = list(self._message_lines)
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
        if url is None:
            self.props.changelog_link = "No changelog detected."
        else:
            url = try_getting_corresponding_github_link(url)
            self.props.changelog_link = (
                f"<a href='{html.escape(url)}'>{html.escape(url)}</a>"
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
