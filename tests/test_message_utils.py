# SPDX-FileCopyrightText: 2022 Jan Tojnar
# SPDX-License-Identifier: MIT

try:
    from ..src.nonemast.message_utils import linkify_html
except:
    # For some reason, the above fails with the following inside nix-build:
    #     ImportError: attempted relative import beyond top-level package
    from src.nonemast.message_utils import linkify_html


def test_link_detection() -> None:
    got = linkify_html(
        """glib: 2.78.4 → 2.80.0

https://gitlab.gnome.org/GNOME/glib/-/compare/2.78.4...2.80.0
"""
    )
    want = """glib: 2.78.4 → 2.80.0

<a href='https://gitlab.gnome.org/GNOME/glib/-/compare/2.78.4...2.80.0'>https://gitlab.gnome.org/GNOME/glib/-/compare/2.78.4...2.80.0</a>
"""

    assert got == want


def test_unusual_domain() -> None:
    got = linkify_html(
        """glib: 2.78.4 → 2.80.0

Changelog-Reviewed-By: Me <hello@nix.dev>
"""
    )
    want = """glib: 2.78.4 → 2.80.0

Changelog-Reviewed-By: Me &lt;<a href='mailto:hello@nix.dev'>hello@nix.dev</a>>
"""

    assert got == want
