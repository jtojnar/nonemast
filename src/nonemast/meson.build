# SPDX-FileCopyrightText: 2022 Jan Tojnar
# SPDX-License-Identifier: MIT

moduledir = join_paths(nonemast_pkgdatadir, 'nonemast')

blueprint_sources = files(
  'update-details-commit-item.blp',
  'gtk/help-overlay.blp',
  'window.blp',
  'update-details.blp',
  'update-item.blp',
)

blueprints = custom_target(
  'blueprints',
  input: blueprint_sources,
  output: '.',
  command: [
    blueprint_compiler,
    'batch-compile',
    '@OUTPUT@',
    '@CURRENT_SOURCE_DIR@',
    '@INPUT@',
  ],
)

gnome.compile_resources(
  'nonemast',
  'nonemast.gresource.xml',
  dependencies: blueprints,
  gresource_bundle: true,
  install: true,
  install_dir: nonemast_pkgdatadir,
)

conf = configuration_data()
conf.set('PYTHON', python3.full_path())
conf.set('VERSION', meson.project_version())
conf.set('localedir', nonemast_localedir)
conf.set('pkgdatadir', nonemast_pkgdatadir)

configure_file(
  input: 'nonemast.in',
  output: 'nonemast',
  configuration: conf,
  install: true,
  install_dir: nonemast_bindir,
)

nonemast_sources = [
  '__init__.py',
  'git_utils.py',
  'main.py',
  'message_utils.py',
  'operations/ensure_coauthors.py',
  'package_update.py',
  'window.py',
]

install_data(
  nonemast_sources,
  install_dir: moduledir,
  preserve_path: true,
)
