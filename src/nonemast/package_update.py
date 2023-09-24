# SPDX-FileCopyrightText: 2022 Jan Tojnar
# SPDX-License-Identifier: MIT

from gi.repository import Ggit
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from .message_utils import (
    has_changelog_reviewed_tag,
    find_changelog_link,
    linkify_html,
)
import html


def try_getting_corresponding_github_link(url: str) -> str:
    url = url.replace(
        "https://gitlab.gnome.org/GNOME/",
        "https://github.com/GNOME/",
    )
    url = url.replace("/-/", "/")

    return url


class CommitInfo(GObject.Object):
    """Wrapper around Ggit.Commit exposing properties as GObject properties."""

    __gtype_name__ = "CommitInfo"

    id_gvariant = GObject.Property(type=GObject.TYPE_VARIANT)

    def __init__(self, repo: Ggit.Repository, commit: Ggit.Commit, **kwargs):
        super().__init__(**kwargs)
        self._repo = repo
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

    @GObject.Property(type=str)
    def icon(self):
        subject = self._commit.get_subject()
        assert subject is not None, "subject cannot be empty"

        if subject.startswith("fixup! "):
            message = self._commit.get_message()
            assert message is not None, "message cannot be empty"
            message_body_is_empty = message.strip() == subject.strip()
            return "message-fixup-empty" if message_body_is_empty else "message-fixup"
        elif subject.startswith("amend! "):
            return "message-amend"
        elif subject.startswith("squash! "):
            return "message-squash"
        else:
            return "message-initial"

    @GObject.Property(type=str)
    def description(self):
        commit_parents = self._commit.get_parents()

        if commit_parents.get_size() > 0:
            parent_commit = commit_parents.get(0)
            commit_tree = self._commit.get_tree()
            parent_tree = parent_commit.get_tree()

            diff = Ggit.Diff.new_tree_to_tree(
                self._repo, parent_tree, commit_tree, None
            )

            num_deltas = diff.get_num_deltas()
            return (
                f"{num_deltas} delta in diff"
                if num_deltas == 1
                else f"{num_deltas} deltas in diff"
            )

        return ""

    def get_commit(self) -> Ggit.Commit:
        return self._commit


class CommitSquasher:
    """
    Simulates what `git rebase --autosquash` does to commit messages.
    """

    _message_lines: list[str]

    def __init__(self, commit_messages: list[str] = []):
        self._message_lines = []
        for message in commit_messages:
            self.add_commit(message)

    def add_commit(self, message: str) -> None:
        subject, *msg_lines = message.splitlines()
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

    def get_lines(self) -> str:
        """
        Returns the final commit message split into lines.

        Returns a **copy** of the list.
        """
        return list(self._message_lines)


class PackageUpdate(GObject.Object):
    __gtype_name__ = "PackageUpdate"

    subject_gvariant = GObject.Property(type=GObject.TYPE_VARIANT)
    commit_message_is_edited = GObject.Property(type=bool, default=False)
    editing_stack_page = GObject.Property(type=str, default="not-editing")
    final_commit_message_rich = GObject.Property(type=str)
    _message_squasher: CommitSquasher

    def __init__(
        self,
        repo: Ggit.Repository,
        subject: str,
        commits: list[Ggit.Commit],
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._repo = repo
        self._subject = subject
        self._commits = Gio.ListStore.new(CommitInfo)
        self._message_squasher = CommitSquasher()

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
        self._commits.append(CommitInfo(repo=self._repo, commit=commit))

        old_message_lines = self._message_squasher.get_lines()
        self._message_squasher.add_commit(commit.get_message())
        new_message_lines = self._message_squasher.get_lines()

        if old_message_lines != new_message_lines:
            self.notify("final-commit-message")

        self.props.changes_reviewed = any(
            has_changelog_reviewed_tag(line) for line in new_message_lines
        )
        url = find_changelog_link(new_message_lines)
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
        return "\n".join(self._message_squasher.get_lines())

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
