# SPDX-FileCopyrightText: 2022 Jan Tojnar
# SPDX-License-Identifier: MIT

from gi.repository import Adw
from gi.repository import Ggit
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk
from collections import OrderedDict
from typing import List, Optional
import html
import re
import threading


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


def has_changelog_reviewed_tag(line: str) -> bool:
    return re.match(r"^Changelog-Reviewed-By: ", line)


def find_changelog_link(lines: List[str]) -> Optional[str]:
    # Heuristics: First line starting with a URL is likely a changelog.
    for line in lines:
        line = line.strip()
        if line.startswith("https://"):
            return line
    return None


class PackageUpdate(GObject.Object):
    __gtype_name__ = "PackageUpdate"

    def __init__(self, subject: str, commits: List[Ggit.Commit], **kwargs):
        super().__init__(**kwargs)
        self._subject = subject
        self._commits = Gio.ListStore.new(CommitInfo)
        self._message_lines = []
        for commit in commits:
            self._commits.append(CommitInfo(commit=commit))

            subject, *msg_lines = commit.get_message().splitlines()
            if subject.startswith('fixup! '):
                continue
            elif subject.startswith('amend! '):
                # Starting from scratch.
                self._message_lines = []
            elif not subject.startswith('squash! '):
                # The subject from non-squash commits remains.
                self._message_lines += [subject]

            self._message_lines += msg_lines

        self._changes_reviewed = any(
            has_changelog_reviewed_tag(line) for line in self._message_lines
        )
        url = find_changelog_link(self._message_lines)
        self._changelog_link = (
            f"<a href='{html.escape(url)}'>{html.escape(url)}</a>"
            if url is not None
            else "No changelog detected."
        )

    @GObject.Property(type=str)
    def subject(self):
        return self._subject

    @GObject.Property(type=GObject.TYPE_VARIANT)
    def subject_gvariant(self):
        return GLib.Variant.new_string(self._subject)

    @GObject.Property(type=str)
    def changelog_link(self):
        return self._changelog_link

    @GObject.Property(type=bool, default=False)
    def changes_reviewed(self):
        return self._changes_reviewed

    @changes_reviewed.setter
    def changes_reviewed(self, changes_reviewed):
        self._changes_reviewed = changes_reviewed

    @GObject.Property(type=bool, default=False)
    def changes_not_reviewed(self):
        return not self._changes_reviewed

    @changes_not_reviewed.setter
    def changes_not_reviewed(self, changes_not_reviewed):
        self._changes_reviewed = not changes_not_reviewed

    @GObject.Property(type=Gio.ListStore)
    def commits(self):
        return self._commits


class CommitInfo(GObject.Object):
    """Wrapper around Ggit.Commit exposing properties as GObject properties."""

    __gtype_name__ = "CommitInfo"

    def __init__(self, commit: Ggit.Commit, **kwargs):
        super().__init__(**kwargs)
        self._commit = commit

    @GObject.Property(type=str)
    def id(self):
        return self._commit.get_id().to_string()


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


@Gtk.Template(resource_path="/cz/ogion/Nonemast/update-details.ui")
class UpdateDetails(Gtk.Box):
    __gtype_name__ = "UpdateDetails"

    _update = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @GObject.Property(type=PackageUpdate)
    def update(self):
        return self._update

    @update.setter
    def update(self, update):
        self._update = update


@Gtk.Template(resource_path="/cz/ogion/Nonemast/window.ui")
class NonemastWindow(Adw.ApplicationWindow):
    __gtype_name__ = "NonemastWindow"

    updates_list_stack = Gtk.Template.Child()
    updates_list_error = Gtk.Template.Child()
    updates_list_view = Gtk.Template.Child()

    # Mapping between updates’ commit subjects and their indices in updates_store.
    _updates_subject_indices = {}

    updates_store = Gio.ListStore.new(PackageUpdate)

    details_stack = Gtk.Template.Child()
    update_details = Gtk.Template.Child()

    _repo: Ggit.Repository

    def __init__(self, repo_path: Gio.File, **kwargs):
        super().__init__(**kwargs)

        self._repo_path = repo_path

        self._updates_selection = Gtk.SingleSelection(model=self.updates_store)
        self.updates_list_view.set_model(self._updates_selection)
        self._updates_selection.connect(
            "notify::selected-item", self.on_selected_item_changed
        )

        action = Gio.SimpleAction.new("mark-as-reviewed", GLib.VariantType.new("s"))
        action.connect("activate", self.mark_as_reviewed)
        self.add_action(action)

        thread = threading.Thread(
            target=self.load_commit_history,
            daemon=True,
        )
        thread.start()

    def mark_as_reviewed(self, action, parameter):
        original_commit_subject = parameter.get_string()
        head: Ggit.OId = self._repo.get_head().get_target()
        current_commit: Ggit.Commit = self._repo.lookup(head, Ggit.Commit)

        try:
            config: Ggit.Config = self._repo.get_config().snapshot()
            author_name = config.get_string("user.name")
            author_email = config.get_string("user.email")
        except:
            make_error_dialog(
                parent=self,
                text="Missing Git Identity",
                secondary_text="Please <a href='https://www.git-scm.com/book/en/v2/Getting-Started-First-Time-Git-Setup#_your_identity'>configure Git with your name and e-mail address</a> for commit authorship.",
                secondary_use_markup=True,
            ).show()
            return

        try:
            author = Ggit.Signature.new_now(
                name=author_name,
                email=author_email,
            )
            commit_message = f"squash! {original_commit_subject}\n\nChangelog-Reviewed-By: {author_name}"

            # Create an empty squash commit adding Changelog-Reviewed-By tag to the commit message.
            new_commit_oid: Ggit.OId = self._repo.create_commit(
                update_ref="HEAD",
                author=author,
                committer=author,
                message_encoding="UTF-8",
                message=commit_message,
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
        update = self.updates_store.get_item(
            self._updates_subject_indices[original_commit_subject]
        )
        update.props.changes_reviewed = True
        update.props.changes_not_reviewed = False
        update.props.commits.append(CommitInfo(commit=new_commit))

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
            self.updates_store.append(update)
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

            # Determine merge bases between the current branch and master and staging branches.
            merge_base_staging = get_merge_base(
                self._repo,
                head.get_target(),
                self._repo.lookup_branch("staging", Ggit.BranchType.LOCAL).get_target(),
            )
            merge_base_master = get_merge_base(
                self._repo,
                head.get_target(),
                self._repo.lookup_branch("master", Ggit.BranchType.LOCAL).get_target(),
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
