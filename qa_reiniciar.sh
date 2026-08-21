#!/bin/bash
# Reinicia SOLO el uvicorn de QA (:8001).
#
# Nada de `pkill -f uvicorn`: ese patrón también caza al propio shell que lo
# ejecuta y, peor, al uvicorn de producción en :8000. Aquí se busca el proceso
# que tiene el puerto 8001 abierto y se verifica que sea python antes de matarlo.
set -u
PUERTO=8001
DIR=/home/phoenix/inventario-qa
UVICORN=/home/phoenix/.local/bin/uvicorn

for pid in $(ss -lptnH "sport = :$PUERTO" 2>/dev/null | grep -oP 'pid=\K[0-9]+' | sort -u); do
    exe=$(readlink "/proc/$pid/exe" 2>/dev/null)
    case "$exe" in
        *python*) echo "deteniendo QA (pid $pid)"; kill "$pid" ;;
        *) echo "ojo: el puerto $PUERTO lo tiene $exe (pid $pid), no lo toco" ;;
    esac
done

sleep 2
cd "$DIR" || exit 1
setsid nohup "$UVICORN" main:app --host 0.0.0.0 --port "$PUERTO" \
    > /tmp/qa$PUERTO.log 2>&1 < /dev/null &
sleep 5

codigo=$(curl -s -o /dev/null -w '%{http_code}' "http://localhost:$PUERTO/docs")
echo "QA :$PUERTO -> $codigo"
echo "producción :8000 -> $(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/) ($(systemctl is-active inventario))"
[ "$codigo" = "200" ] || tail -15 /tmp/qa$PUERTO.log
