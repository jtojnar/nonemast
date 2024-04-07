# SPDX-FileCopyrightText: 2023 Jan Tojnar
# SPDX-License-Identifier: MIT

from linkify_it import LinkifyIt
from typing import Optional
import html
import re


def has_changelog_reviewed_tag(line: str) -> bool:
    return re.match(r"^Changelog-Reviewed-By: ", line) is not None


def find_changelog_link(lines: list[str]) -> Optional[str]:
    # Heuristics: First line starting with a URL is likely a changelog.
    for line in lines:
        line = line.strip()
        if line.startswith("https://"):
            return line
    return None


def linkify_html(text: str) -> str:
    linkify = LinkifyIt()

    if not linkify.test(text):
        return ""

    result = ""
    last_index = 0
    for match in linkify.match(text):
        link = f"<a href='{html.escape(match.url)}'>{html.escape(match.text)}</a>"
        result += html.escape(text[last_index : match.index]) + link
        last_index = match.last_index

    result += text[last_index:]

    return result


def get_base_commit_subject(subject: str) -> str:
    return re.sub(r"^(fixup! |squash! |amend! )+", "", subject)
