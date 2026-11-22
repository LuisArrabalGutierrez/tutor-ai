import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_websocket_terminal_conexion():
    # Comprobamos que el túnel se abre sin crashear y lo cerramos de inmediato
    # para que no se quede colgado esperando a que Docker arranque.
    with client.websocket_connect("/ws/terminal") as websocket:
        assert websocket is not None
        websocket.close()


def test_la_terminal_tiene_home_usable_pero_limitado_y_raiz_de_solo_lectura():
    """F-3 en la terminal: la raíz es de solo lectura; /home/alumno es un tmpfs con el .bashrc de /etc/skel."""
    import subprocess, uuid
    from routers.terminal import docker_run_args
    ordenes = (
        "test -f ~/.bashrc && echo BASHRC_OK\n"
        "printf 'int main(){return 0;}' > a.c && gcc a.c -o a && ./a && echo COMPILA_OK\n"
        "dd if=/dev/zero of=~/relleno bs=1M count=200 2>&1\n"
        "touch /etc/x 2>&1\n"
        "exit\n"
    )
    r = subprocess.run(["docker", "run", "-i", "--rm", *docker_run_args(f"tutor_term_test_{uuid.uuid4().hex[:8]}")],
                       input=ordenes, capture_output=True, text=True, timeout=60)
    salida = r.stdout + r.stderr
    assert "BASHRC_OK" in salida and "COMPILA_OK" in salida, salida
    assert "No space left on device" in salida
    assert "Read-only file system" in salida

def test_al_arrancar_se_borran_las_terminales_huerfanas(monkeypatch):
    """F-7: si la API muere con terminales abiertas, sus contenedores siguen vivos; el arranque los borra."""
    import asyncio, subprocess, uuid
    from routers import terminal
    prefijo = f"tutor_test_huer_{uuid.uuid4().hex[:6]}_"
    monkeypatch.setattr(terminal, "TERMINAL_PREFIX", prefijo)
    ajeno = f"tutor_test_ajeno_{uuid.uuid4().hex[:6]}"
    for nombre in (prefijo + "a", ajeno):
        subprocess.run(["docker", "run", "-d", "--rm", "--name", nombre, "tutor-ugr-image", "sleep", "300"],
                       check=True, capture_output=True)
    try:
        assert asyncio.run(terminal.cleanup_orphan_terminals()) == 1
        vivos = subprocess.run(["docker", "ps", "--format", "{{.Names}}"], capture_output=True, text=True).stdout.split()
        assert prefijo + "a" not in vivos
        assert ajeno in vivos  # solo toca su propio prefijo
    finally:
        subprocess.run(["docker", "rm", "-f", prefijo + "a", ajeno], capture_output=True)
