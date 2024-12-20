# SPDX-FileCopyrightText: 2022 Jan Tojnar
# SPDX-License-Identifier: MIT

import sys

from gi.repository import Adw
from gi.repository import Ggit
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk
from .window import NonemastWindow
from typing import Callable, Optional, Sequence, TypeVar


class NonemastApplication(Adw.Application):
    """The main application singleton class."""

    _base_revspec: Optional[str] = None

    def __init__(self, version: str):
        super().__init__(
            application_id="cz.ogion.Nonemast",
            flags=Gio.ApplicationFlags.HANDLES_OPEN,
        )
        Ggit.init()
        self.version = version
        self._setup_commandline()
        self.create_action("quit", self.on_quit_action, ["<primary>q"])
        self.create_action("about", self.on_about_action)

    def _setup_commandline(self):
        self.add_main_option(
            long_name="base-commit",
            short_name=ord("b"),
            flags=GLib.OptionFlags.NONE,
            arg=GLib.OptionArg.STRING,
            description="Revspec describing the first commit to include in the review (default: merge base between master and staging branches)",
            arg_description="<rev>",
        )

    def do_activate(self, repo_path: Optional[Gio.File] = None) -> None:
        win = self.props.active_window
        if not win:
            if repo_path is None:
                repo_path = Gio.File.new_for_path(GLib.get_current_dir())
            win = NonemastWindow(
                application=self,
                repo_path=repo_path,
                base_revspec=self._base_revspec,
            )
        win.present()

    def do_handle_local_options(self, options: GLib.VariantDict) -> int:
        if (base_revspec := options.lookup_value("base-commit")) is not None:
            self._base_revspec = base_revspec.get_string()

        return -1

    def do_open(self, files: Sequence[Gio.File], n_files: int, hint: str) -> None:
        if n_files != 1:
            sys.exit("error: nonemast expects exactly one path as an argument.")

        self.do_activate(repo_path=files[0])

    def on_quit_action(
        self,
        action: Gio.SimpleAction,
        _parameter: None,
    ) -> None:
        self.quit()

    def on_about_action(
        self,
        action: Gio.SimpleAction,
        _parameter: None,
    ) -> None:
        """Callback for the app.about action."""
        about = Adw.AboutDialog(
            application_name="Not Nearly Enough Masking Tape",
            application_icon="cz.ogion.Nonemast",
            license_type=Gtk.License.MIT_X11,
            version=self.version,
            developers=["Jan Tojnar"],
            copyright="© 2022 Jan Tojnar",
        )
        about.present(self.props.active_window)

    T = TypeVar("T", bound=GLib.Variant | None)

    def create_action(
        self,
        name: str,
        callback: Callable[[Gio.SimpleAction, T], None],
        shortcuts: list[str] = [],
    ) -> None:
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


def main(version: str) -> int:
    """The application's entry point."""
    app = NonemastApplication(
        version=version,
    )
    return app.run(sys.argv)
