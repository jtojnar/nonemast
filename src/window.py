# SPDX-FileCopyrightText: 2022 Jan Tojnar
# SPDX-License-Identifier: MIT

from gi.repository import Adw
from gi.repository import Ggit
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk
from collections import OrderedDict
from pathlib import Path
from typing import List, Optional
import re
import shutil
import subprocess
import tempfile
import threading
from .package_update import PackageUpdate


def make_error_dialog(parent, text, **kwargs):
    dialog = Gtk.MessageDialog(
        text=text,
        message_type=Gtk.MessageType.ERROR,
        buttons=Gtk.ButtonsType.CLOSE,
        transient_for=parent,
        modal=True,
        **kwargs,
    )
    dialog.connect("response", lambda dialog, response_id: Gtk.Window.destroy(dialog))
    return dialog


def open_commit_message_in_editor(parent: Gtk.Window, path: Path):
    """Open path in a text editor and wait for it to quit."""
    editor = None
    if shutil.which("re.sonny.Commit") is not None:
        editor = ["re.sonny.Commit", path]
    elif shutil.which("subl") is not None:
        editor = ["subl", "--wait", path]
    elif shutil.which("gedit") is not None:
        editor = ["gedit", "--wait", path]
    elif shutil.which("gnome-text-editor") is not None:
        editor = ["gnome-text-editor", "--standalone", path]

    if editor is None:

        def show_error():
            make_error_dialog(
                parent, "Unable to find a text editor for editing commit messages."
            ).show()

        GLib.idle_add(show_error)
    else:
        subprocess.check_call(editor)


NIXPKGS_REMOTE_URL = "git@github.com:NixOS/nixpkgs.git"


def view_commit_in_vcs_tool(
    parent: Gtk.Window,
    commit_id: str,
    repo_path: Gio.File,
) -> None:
    """Open commit details in a VCS management tool."""
    viewer = None
    if shutil.which("sublime_merge") is not None:
        viewer = ["sublime_merge", "search", f"commit:{commit_id}"]

    if viewer is None:
        make_error_dialog(
            parent, "Unable to find a tool for viewing Git commits."
        ).show()
    else:
        subprocess.run(viewer, cwd=repo_path.get_path())


def find_nixpkgs_remote_name(repo: Ggit.Repository) -> Optional[str]:
    for remote_name in repo.list_remotes():
        remote = repo.lookup_remote(remote_name)
        if remote is not None:
            if remote.get_url() == NIXPKGS_REMOTE_URL:
                return remote_name
    return None


def get_merge_base(
    repo: Ggit.Repository,
    oid_one: Ggit.OId,
    oid_two: Optional[Ggit.OId],
) -> Optional[Ggit.OId]:
    if oid_two is None:
        return None
    try:
        return repo.merge_base(oid_one, oid_two)
    except GLib.Error as e:
        return None


def get_base_commit_subject(subject: str) -> str:
    return re.sub(r"^(fixup! |squash! |amend! )+", "", subject)


def signature_to_string(signature: Ggit.Signature) -> str:
    return f"{signature.get_name()} <{signature.get_email()}>"


@Gtk.Template(resource_path="/cz/ogion/Nonemast/update-details.ui")
class UpdateDetails(Gtk.Box):
    __gtype_name__ = "UpdateDetails"

    _update = None

    _binding = None
    changes_not_reviewed = GObject.Property(type=bool, default=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @GObject.Property(type=PackageUpdate)
    def update(self):
        return self._update

    @update.setter
    def update(self, update):
        self._update = update
        if self._binding is not None:
            self._binding.unbind()
        if self._update is not None:
            self._binding = self._update.bind_property(
                "changes-reviewed",
                self,
                "changes-not-reviewed",
                GObject.BindingFlags.INVERT_BOOLEAN | GObject.BindingFlags.SYNC_CREATE,
            )


@Gtk.Template(resource_path="/cz/ogion/Nonemast/window.ui")
class NonemastWindow(Adw.ApplicationWindow):
    __gtype_name__ = "NonemastWindow"

    updates_list_stack = Gtk.Template.Child()
    updates_list_error = Gtk.Template.Child()
    updates_list_view = Gtk.Template.Child()

    # Mapping between updates’ commit subjects and their indices in updates_store.
    _updates_subject_indices = {}

    updates = GObject.Property(type=Gio.ListStore)
    updates_search_filter = Gtk.Template.Child()

    details_stack = Gtk.Template.Child()
    update_details = Gtk.Template.Child()

    _repo: Ggit.Repository

    def __init__(self, repo_path: Gio.File, **kwargs):
        super().__init__(**kwargs)

        self._repo_path = repo_path

        self._search_query = None
        self._filter_reviewed = None

        self.props.updates = Gio.ListStore.new(PackageUpdate)

        action = Gio.SimpleAction.new("mark-as-reviewed", GLib.VariantType.new("s"))
        action.connect("activate", self.mark_as_reviewed)
        self.add_action(action)

        action = Gio.SimpleAction.new("edit-commit-message", GLib.VariantType.new("s"))
        action.connect("activate", self.edit_commit_message)
        self.add_action(action)

        action = Gio.SimpleAction.new("view-commit", GLib.VariantType.new("s"))
        action.connect("activate", self.view_commit)
        self.add_action(action)

        action = Gio.SimpleAction.new_stateful(
            name="filter",
            parameter_type=GLib.VariantType.new("s"),
            state=GLib.Variant.new_string("all"),
        )
        action.connect("change-state", self.on_toggle_filter)
        self.add_action(action)

        thread = threading.Thread(
            target=self.load_commit_history,
            daemon=True,
        )
        thread.start()

    def on_toggle_filter(self, action, variant):
        match variant.get_string():
            case "reviewed":
                self._filter_reviewed = True
            case "unreviewed":
                self._filter_reviewed = False
            case other:
                self._filter_reviewed = None
        action.set_state(variant)
        self.updates_search_filter.set_filter_func(self.filter_func)

    def filter_func(self, update: PackageUpdate):
        search_matches = (
            self._search_query is None or self._search_query in update.props.subject
        )
        filter_matches = (
            self._filter_reviewed is None
            or self._filter_reviewed == update.props.changes_reviewed
        )

        return search_matches and filter_matches

    @Gtk.Template.Callback()
    def clear_search(self, _object, _pspec):
        self._search_query = None
        self.updates_search_filter.set_filter_func(self.filter_func)

    @Gtk.Template.Callback()
    def on_search_changed(self, entry):
        text = entry.get_text().strip()
        if text == "":
            self._search_query = None
        else:
            self._search_query = text

        self.updates_search_filter.set_filter_func(self.filter_func)

    def mark_as_reviewed(self, action, parameter) -> None:
        original_commit_subject = parameter.get_string()
        signature = self.make_git_signature()
        commit_message = f"squash! {original_commit_subject}\n\nChangelog-Reviewed-By: {signature_to_string(signature)}"
        self.create_empty_commit(
            target_subject=original_commit_subject,
            message=commit_message,
            author=signature,
        )

    def edit_commit_message(self, action, parameter) -> None:
        original_commit_subject = parameter.get_string()

        def editing_thread():
            update = self.props.updates.get_item(
                self._updates_subject_indices[original_commit_subject]
            )
            update.props.commit_message_is_edited = True
            try:
                old_commit_message = update.props.final_commit_message.strip()
                with tempfile.TemporaryDirectory() as temp_dir:
                    commit_file_path = Path(temp_dir) / "COMMIT_EDITMSG"
                    with open(commit_file_path, "w") as commit_file:
                        commit_file.write(old_commit_message)

                    # Blocks the thread until editing finishes.
                    open_commit_message_in_editor(self, commit_file_path)

                    with open(commit_file_path) as commit_file:
                        new_commit_message = commit_file.read().strip()

                if new_commit_message == "":
                    return

                if new_commit_message == old_commit_message:
                    return

                commit_message = (
                    f"amend! {original_commit_subject}\n\n{new_commit_message}"
                )
                signature = self.make_git_signature()
                self.create_empty_commit(
                    target_subject=original_commit_subject,
                    message=commit_message,
                    author=signature,
                )
            finally:
                update.props.commit_message_is_edited = False

        thread = threading.Thread(
            target=editing_thread,
        )
        thread.start()

    def view_commit(self, action, parameter) -> None:
        commit_id = parameter.get_string()
        view_commit_in_vcs_tool(self, commit_id, self._repo_path)

    def make_git_signature(self) -> Optional[Ggit.Signature]:
        try:
            config: Ggit.Config = self._repo.get_config().snapshot()
            author_name = config.get_string("user.name")
            author_email = config.get_string("user.email")

            return Ggit.Signature.new_now(
                name=author_name,
                email=author_email,
            )
        except:
            make_error_dialog(
                parent=self,
                text="Missing Git Identity",
                secondary_text="Please <a href='https://www.git-scm.com/book/en/v2/Getting-Started-First-Time-Git-Setup#_your_identity'>configure Git with your name and e-mail address</a> for commit authorship.",
                secondary_use_markup=True,
            ).show()

        return None

    def create_empty_commit(
        self,
        target_subject: str,
        message: str,
        author: Ggit.Signature,
    ) -> None:
        head: Ggit.OId = self._repo.get_head().get_target()
        current_commit: Ggit.Commit = self._repo.lookup(head, Ggit.Commit)
        try:
            # Create an empty squash commit adding Changelog-Reviewed-By tag to the commit message.
            new_commit_oid: Ggit.OId = self._repo.create_commit(
                update_ref="HEAD",
                author=author,
                committer=author,
                message_encoding="UTF-8",
                message=message,
                tree=current_commit.get_tree(),
                parents=[current_commit],
            )
        except GLib.Error as error:
            make_error_dialog(
                parent=self,
                text="Error Creating a Commit",
                secondary_text=error.message,
            ).show()

        new_commit: Ggit.Commit = self._repo.lookup(new_commit_oid, Ggit.Commit)
        update = self.props.updates.get_item(
            self._updates_subject_indices[target_subject]
        )
        update.add_commit(new_commit)

    @Gtk.Template.Callback()
    def on_selected_item_changed(self, selection, prop_name):
        self.do_select_update(selection.get_selected_item())

    def do_select_update(self, update: PackageUpdate):
        self.update_details.props.update = update

    def populate_updates(self, updates: OrderedDict[str, List[Ggit.Commit]]):
        index = 0
        for subject, commits in updates.items():
            self._updates_subject_indices[subject] = index
            update = PackageUpdate(
                subject=subject,
                commits=commits,
            )
            self.props.updates.append(update)
            index += 1
        self.updates_list_stack.set_visible_child_name("list")
        self.details_stack.set_visible_child_name("details")

        return GLib.SOURCE_REMOVE

    def show_error(self, error: GLib.Error):
        self.updates_list_stack.set_visible_child_name("error")
        self.updates_list_error.set_description(error.message)

        return GLib.SOURCE_REMOVE

    def load_commit_history(self):
        updates = OrderedDict()
        try:
            self._repo = Ggit.Repository.open(self._repo_path)
            mailmap: Ggit.Mailmap = Ggit.Mailmap.new_from_repository(self._repo)
            head = self._repo.get_head()

            # Find the remote corresponding to upstream Nixpkgs
            nixpkgs_remote_name = find_nixpkgs_remote_name(self._repo)
            if nixpkgs_remote_name is None:
                error = GLib.Error(
                    f"Could not find a Git remote with URL “{NIXPKGS_REMOTE_URL}”.",
                    "nonemast",
                    1,
                )
                GLib.idle_add(self.show_error, error)
                return

            # Determine merge bases between the current branch and master and staging branches.
            merge_base_staging = get_merge_base(
                self._repo,
                head.get_target(),
                self._repo.lookup_branch(
                    f"{nixpkgs_remote_name}/staging",
                    Ggit.BranchType.REMOTE,
                ).get_target(),
            )
            merge_base_master = get_merge_base(
                self._repo,
                head.get_target(),
                self._repo.lookup_branch(
                    f"{nixpkgs_remote_name}/master",
                    Ggit.BranchType.REMOTE,
                ).get_target(),
            )

            # Traverse the commit list until one of the merge bases or a limit is reached.
            n_revisions = 500
            revwalker: Ggit.RevisionWalker = Ggit.RevisionWalker.new(self._repo)
            revwalker.set_sort_mode(
                Ggit.SortMode.TIME | Ggit.SortMode.TOPOLOGICAL | Ggit.SortMode.REVERSE
            )
            if merge_base_master is not None:
                revwalker.hide(merge_base_master)
            if merge_base_staging is not None:
                revwalker.hide(merge_base_staging)
            oid = head.get_target()
            revwalker.push(oid)

            while (oid := revwalker.next()) is not None:
                commit: Ggit.Commit = self._repo.lookup(oid, Ggit.Commit)
                base_commit_subject = get_base_commit_subject(commit.get_subject())

                # Add commit to the group.
                updates.setdefault(base_commit_subject, []).append(commit)

                if (n_revisions := n_revisions - 1) == 0:
                    break

            GLib.idle_add(self.populate_updates, updates)
        except GLib.Error as error:
            GLib.idle_add(self.show_error, error)
