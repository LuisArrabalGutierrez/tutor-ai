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