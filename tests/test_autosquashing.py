# SPDX-FileCopyrightText: 2022 Jan Tojnar
# SPDX-License-Identifier: MIT

import gi

gi.require_version("Ggit", "1.0")

from gi.repository import Ggit
from typing import List
import subprocess
import tempfile

try:
    from ..src.package_update import PackageUpdate
except:
    # For some reason, the above fails with the following inside nix-build:
    #     ImportError: attempted relative import beyond top-level package
    from src.package_update import PackageUpdate


class FakeCommit(Ggit.Commit):
    """docstring for FakeCommit"""

    def __init__(self, message):
        self._message = message

    def get_id(self) -> Ggit.OId:
        return Ggit.OId.new_from_string("deadbeefdeadbeefdeadbeefdeadbeefdeadbeef")

    def get_message(self) -> str:
        return self._message


def autosquash_commits_with_git(commit_messages: List[str]) -> List[str]:
    """Initializes a Git repository, fills it with a sequence of commits, autosquashes them, and then returns the new sequence of commit messages."""
    with tempfile.TemporaryDirectory() as repo_path:

        def git(*args, **kwargs):
            return subprocess.check_output(
                ["git", *args],
                encoding="utf-8",
                cwd=repo_path,
            )

        git("init")
        # Set up commit author identity.
        git("config", "user.name", "Tester")
        git("config", "user.email", "test@example.com")
        # Set up fake editor that will keep rebase todo as is.
        git("config", "sequence.editor", "cat")
        # Set up fake editor that will keep commit messages when squashing as is.
        git("config", "core.editor", "cat")

        for message in commit_messages:
            git("commit", "--allow-empty", "-m", message)

        git("rebase", "--interactive", "--autosquash", "--root")

        commits = git("log", "--format=%H", "--reverse").splitlines()

        return [git("log", "--format=%B", "-n", "1", commit) for commit in commits]


def check_autosquashing(commit_messages: List[str]) -> None:
    commits = [
        FakeCommit(
            message=message,
        )
        for message in commit_messages
    ]
    update = PackageUpdate(
        subject="Foo",
        commits=commits,
    )

    expected = autosquash_commits_with_git(commit_messages)
    # Git forces two line breaks at the end.
    expected = [message.rstrip("\n") for message in expected]
    assert [update.props.final_commit_message] == expected


def test_autosquashing_fixup():
    check_autosquashing(
        [
            "Hello",
            "fixup! Hello",
        ]
    )


def test_autosquashing_fixup_with_body():
    check_autosquashing(
        [
            "Hello",
            "fixup! Hello\n\nfoo",
        ]
    )


def test_autosquashing_squash():
    check_autosquashing(
        [
            "Hello",
            "squash! Hello\n\nfoo",
        ]
    )


def test_autosquashing_double_squash():
    check_autosquashing(
        [
            "Hello",
            "squash! Hello\n\nfoo",
            "squash! Hello\n\nfoo",
        ]
    )
