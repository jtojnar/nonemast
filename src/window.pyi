from gi.repository import Gio
from gi.repository import Adw
from gi.repository import Gtk
from .package_update import PackageUpdate

class UpdateDetails(Gtk.Box):
    class Props(Gtk.Box.Props):
        update: PackageUpdate
        changes_not_reviewed: bool
    props: Props = ...

class NonemastWindow(Adw.ApplicationWindow):
    class Props(Adw.ApplicationWindow.Props):
        updates: Gio.ListStore[PackageUpdate]
    props: Props = ...
