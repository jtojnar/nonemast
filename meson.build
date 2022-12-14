# SPDX-FileCopyrightText: 2022 Jan Tojnar
# SPDX-License-Identifier: MIT

project(
  'nonemast',
  version: '0.1.0',
  meson_version: '>= 0.59.0',
  license: 'MIT',
  default_options: [
    'warning_level=2',
  ],
)

i18n = import('i18n')
gnome = import('gnome')
python = import('python')

python3 = python.find_installation(
  'python3',
  modules: [
    'gi',
  ],
)

dependency('gtk4', version: '>= 4.6.0')
dependency('libadwaita-1', version: '>= 1.2.alpha')
dependency('libgit2-glib-1.0', version: ['>= 1.0.0'])

nonemast_prefix = get_option('prefix')
nonemast_bindir = nonemast_prefix / get_option('bindir')
nonemast_localedir = nonemast_prefix / get_option('localedir')
nonemast_datadir = nonemast_prefix / get_option('datadir')
nonemast_pkgdatadir = nonemast_datadir / meson.project_name()

application_id = 'cz.ogion.Nonemast'

subdir('data')
subdir('src')
subdir('po')
subdir('tests')

gnome.post_install(
  gtk_update_icon_cache: true,
  update_desktop_database: true,
)
