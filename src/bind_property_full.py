# SPDX-FileCopyrightText: 2020 Tran Quang Loc
# SPDX-License-Identifier: MIT
# PackageHomePage: https://github.com/quangloc99/force-break-timer/blob/bfbb1e6515dce836957708787d6a78f6c54aba39/force_break/helper.py

import gi
from gi.repository import GObject


# This is just a simple "polyfill" for GObject.Object#bind_property_full
# somehow they make this method "unsupported". But this method is
# so usefull, I decided to make one.
# TODO: another functionallity like unbind
class FullPropertyBinder(GObject.Object):
    def __init__(
        self,
        source_obj,
        src_prop_name,
        dest_obj,
        dest_prop_name,
        flag,
        source_to_dest=None,
        dest_to_source=None,
    ):
        super().__init__()
        self.source_obj = source_obj.weak_ref(self.unbind)
        self.dest_obj = dest_obj.weak_ref(self.unbind)
        self.source_prop_name = src_prop_name
        self.dest_prop_name = dest_prop_name
        self.source_to_dest = source_to_dest
        self.dest_to_source = dest_to_source
        self.flag = flag
        self._bound = False
        self._source_connector_id = None
        self._dest_connector_id = None
        self._do_bind()

    def _do_bind(self):
        assert not self._bound
        self._source_connector_id = self.source_obj().connect(
            "notify::" + self.source_prop_name, self._on_source_change
        )
        if self.flag == GObject.BindingFlags.BIDIRECTIONAL:
            self._dest_connector_id = self.dest_obj().connect(
                "notify::" + self.dest_prop_name, self._on_dest_change
            )

        if (self.flag & GObject.BindingFlags.SYNC_CREATE) > 0:
            self._on_source_change()
        self._bound = True

    def unbind(self):
        if not self._bound:
            return
        self._bound = False
        if self.source_obj() is not None and self._source_connector_id is not None:
            self.source_obj().disconnect(self._source_connector_id)

        if self.dest_obj() is not None and self._dest_connector_id is not None:
            self.dest_obj().disconnect(self._dest_connector_id)

    def _on_source_change(self, *args, **kwargs):
        value = self.source_to_dest(
            self.source_obj().get_property(self.source_prop_name)
        )
        if value != self.dest_obj().get_property(self.dest_prop_name):
            self.dest_obj().set_property(self.dest_prop_name, value)

    def _on_dest_change(self, *args, **kwargs):
        value = self.dest_to_source(self.dest_obj().get_property(self.dest_prop_name))
        if value != self.source_obj().get_property(self.source_prop_name):
            self.source_obj().set_property(self.source_prop_name, value)


def bind_property_full(
    source: GObject.Object,
    source_property: str,
    target: GObject.Object,
    target_property: str,
    flags: GObject.BindingFlags,
    transform_to=None,
    transform_from=None,
):
    return FullPropertyBinder(
        source,
        source_property,
        target,
        target_property,
        flags,
        transform_to,
        transform_from,
    )
