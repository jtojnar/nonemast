# SPDX-FileCopyrightText: 2023 Jan Tojnar
# SPDX-License-Identifier: MIT

from linkify_it import LinkifyIt
from linkify_it.tlds import TLDS
from typing import Optional
import html
import re


def has_trailer(trailer: str, line: str, user: str = "") -> bool:
    trailer_re = re.escape(trailer)
    user_re = re.escape(user)
    return (
        re.search(
            rf"^{trailer_re}: {user_re}",
            line,
            re.IGNORECASE | re.MULTILINE,
        )
        is not None
    )


def find_changelog_link(lines: list[str]) -> Optional[str]:
    # Heuristics: First line starting with a URL is likely a changelog.
    for line in lines:
        line = line.strip()
        if line.startswith("https://"):
            return line
    return None


def linkify_html(text: str) -> str:
    linkify = LinkifyIt().tlds(TLDS)

    if not linkify.test(text):
        return html.escape(text)

    result = ""
    last_index = 0
    for match in linkify.match(text):
        link = f"<a href='{html.escape(match.url)}'>{html.escape(match.text)}</a>"
        result += html.escape(text[last_index : match.index]) + link
        last_index = match.last_index

    result += html.escape(text[last_index:])

    return result


def get_base_commit_subject(subject: str) -> str:
    return re.sub(r"^(fixup! |squash! |amend! )+", "", subject)
