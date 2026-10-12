#!/bin/zsh
cd "${0:A:h}"
if [[ ! -x .venv/bin/python ]]; then
  print "Ejecuta primero Instalar.command"
else
  .venv/bin/python scripts/crear_usuario.py
fi
read "?Pulsa Intro para cerrar..."
