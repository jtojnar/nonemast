# SPDX-FileCopyrightText: 2022 Jan Tojnar
# SPDX-License-Identifier: MIT

tests_enabled = get_option('tests')
pytest = find_program('py.test', required: tests_enabled)
find_program('git', required: tests_enabled)

if pytest.found()
  test(
    'Unit tests',
    pytest,
    workdir: meson.project_source_root(),
  )
endif

test(
  'Lint Blueprint coding style',
  blueprint_compiler,
  args: [
    'format',
  ] + blueprint_sources,
)

run_target(
  'lint-blp',
  command: [
    blueprint_compiler,
    'format',
    '--fix',
  ] + blueprint_sources,
)

black = find_program('black', required: false)
if black.found()
  python_sources = [
    meson.current_source_dir(),
    meson.current_source_dir() / '../src/',
  ]

  test(
    'Lint Python coding style',
    black,
    args: [
      '--check',
      '--diff',
    ] + python_sources,
  )

  run_target(
    'lint',
    command: [
      black,
      '--check',
      '--diff',
    ] + python_sources,
  )

  run_target(
    'lint-fix',
    command: [
      black,
    ] + python_sources,
  )
else
  run_target(
    'lint',
    command: [
      python3,
      '-c',
      'import sys; print("error: lint target requires ‘black’ tool to be available on PATH. If you have Nix, you can get it by running nix-shell.", file=sys.stderr); sys.exit(1)',
    ],
  )

  run_target(
    'lint-fix',
    command: [
      python3,
      '-c',
      'import sys; print("error: lint-fix target requires ‘black’ tool to be available on PATH. If you have Nix, you can get it by running nix-shell.", file=sys.stderr); sys.exit(1)',
    ],
  )
endif
