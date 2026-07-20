#!/bin/bash

# Entra nella cartella in cui si trova questo file .command
cd "$(dirname "$0")" || exit 1

VENV_DIR=".venv"
PYTHON_BIN="$VENV_DIR/bin/python"
PIP_BIN="$VENV_DIR/bin/pip"

# Crea l'ambiente virtuale se non esiste
if [ ! -x "$PYTHON_BIN" ]; then
    echo "Creazione ambiente virtuale..."
    python3 -m venv "$VENV_DIR" || {
        echo "Errore durante la creazione dell'ambiente virtuale."
        read -r -p "Premi Invio per chiudere..."
        exit 1
    }

    echo "Aggiornamento di pip..."
    "$PYTHON_BIN" -m pip install --upgrade pip || {
        echo "Errore durante l'aggiornamento di pip."
        read -r -p "Premi Invio per chiudere..."
        exit 1
    }

    echo "Installazione delle dipendenze..."
    "$PIP_BIN" install -r requirements.txt || {
        echo "Errore durante l'installazione delle dipendenze."
        read -r -p "Premi Invio per chiudere..."
        exit 1
    }
fi

# Avvia il programma usando direttamente il Python della virtualenv
"$PYTHON_BIN" launch_api_rest_desk.py
EXIT_CODE=$?

if [ "$EXIT_CODE" -ne 0 ]; then
    echo
    echo "Il programma è terminato con errore. Codice: $EXIT_CODE"
    read -r -p "Premi Invio per chiudere..."
fi

exit "$EXIT_CODE"
