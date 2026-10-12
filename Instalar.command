#!/bin/zsh
cd "${0:A:h}"
if [[ ! -x .venv/bin/python ]]; then
  task_python=$(command -v python3.12 || command -v python3.11)
  if [[ -z "$task_python" ]]; then
    print "Instala Python 3.12 (o 3.11) y vuelve a ejecutar este archivo. Consulta README.md."
    read "?Pulsa Intro para cerrar..."
    exit 1
  fi
  "$task_python" -m venv .venv || exit 1
fi
.venv/bin/python -m pip install -r requirements-lock.txt || exit 1
.venv/bin/python scripts/preparar_local.py
read "?Preparado. Pulsa Intro para cerrar..."
