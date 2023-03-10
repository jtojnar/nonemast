from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject

class CommitInfo(GObject.Object):
    class Props:
        id_gvariant: GLib.Variant
        id: str
    props: Props = ...

class PackageUpdate(GObject.Object):
    class Props:
        subject_gvariant: GLib.Variant
        commit_message_is_edited: bool
        editing_stack_page: str
        final_commit_message_rich: str
        subject: str
        final_commit_message: str
        changelog_link: str
        changes_reviewed: bool
        commits: Gio.ListStore[CommitInfo]
    props: Props = ...
