# SPDX-FileCopyrightText: 2022 Jan Tojnar
# SPDX-License-Identifier: MIT

project(
  'nonemast',
  version: '0.1.0',
  meson_version: '>= 0.64.0',
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

blueprint_compiler = find_program(
  'blueprint-compiler',
  version: '>= 0.8.2',
  required: true,
  native: true,
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
subdir('src/nonemast')
subdir('po')
subdir('tests')

devenv = environment()
# Make nonemast module available without installation.
devenv.prepend('PYTHONPATH', meson.current_source_dir() / 'src')
# Make nonemast program available on devenv’s PATH (Meson only auto-adds executables).
devenv.prepend('PATH', meson.current_build_dir() / 'src/nonemast')
# Make about dialog see icon.
devenv.prepend('XDG_DATA_DIRS', meson.current_source_dir() / 'data')
meson.add_devenv(devenv)

gnome.post_install(
  gtk_update_icon_cache: true,
  update_desktop_database: true,
)
