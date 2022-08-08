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

