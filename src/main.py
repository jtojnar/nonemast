# SPDX-FileCopyrightText: 2022 Jan Tojnar
# SPDX-License-Identifier: MIT

import sys

from gi.repository import Adw
from gi.repository import Ggit
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk
from .window import NonemastWindow


class NonemastApplication(Adw.Application):
    """The main application singleton class."""

    def __init__(self, version):
        super().__init__(
            application_id="cz.ogion.Nonemast",
            flags=Gio.ApplicationFlags.HANDLES_OPEN,
        )
        Ggit.init()
        self.version = version
        self.create_action("quit", self.on_quit_action, ["<primary>q"])
        self.create_action("about", self.on_about_action)

    def do_activate(self, repo_path=None):
        win = self.props.active_window
        if not win:
            if repo_path is None:
                repo_path = Gio.File.new_for_path(GLib.get_current_dir())
            win = NonemastWindow(application=self, repo_path=repo_path)
        win.present()

    def do_open(self, files, n_files, hint):
        if n_files != 1:
            sys.exit("error: nonemast expects exactly one path as an argument.")

        self.do_activate(repo_path=files[0])

    def on_quit_action(self, widget, _):
        self.quit()

    def on_about_action(self, widget, _):
        """Callback for the app.about action."""
        about = Adw.AboutWindow(
            transient_for=self.props.active_window,
            application_name="Not Nearly Enough Masking Tape",
            application_icon="cz.ogion.Nonemast",
            license_type=Gtk.License.MIT_X11,
            version=self.version,
            developers=["Jan Tojnar"],
            copyright="© 2022 Jan Tojnar",
        )
        about.present()

    def create_action(self, name, callback, shortcuts=None):
        """Add an application action.

        Args:
            name: the name of the action
            callback: the function to be called when the action is
              activated
            shortcuts: an optional list of accelerators
        """
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
        if shortcuts:
            self.set_accels_for_action(f"app.{name}", shortcuts)


def main(version):
    """The application's entry point."""
    app = NonemastApplication(
        version=version,
    )
    return app.run(sys.argv)
