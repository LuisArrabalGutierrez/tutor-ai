import requests
import json

URL = "http://localhost:8000/api/chat"

# Simulamos el payload que enviaría el front
payload = {
    "mensajes": [
        {
            "role": "user", 
            "content": "Hola, he separado mi código en varios archivos. Intento calcular el doble de 5, pero el programa imprime 15 en lugar de 10. ¿Por qué falla mi lógica?"
        }
    ],
    "archivos": {
        "main.cpp": """
#include <iostream>
#include "utils.h"

using namespace std;

int main() {
    cout << "El doble de 5 es: " << calcularDoble(5) << endl;
    return 0;
}
""",
        "utils.h": """
#ifndef UTILS_H
#define UTILS_H

int calcularDoble(int n);

#endif
""",
        "utils.cpp": """
#include "utils.h"

int calcularDoble(int n) {
    // ERROR LÓGICO INTENCIONADO PARA PROBAR LA IA
    return n * 3; 
}
"""
    }
}

print("Enviando petición al Tutor IA .....")

try:
    response = requests.post(URL, json=payload)
    
    if response.status_code == 200:
        data = response.json()
        print("\n RESPUESTA DE LA IA:")
        print("-" * 50)
        print(data["respuesta"])
        print("-" * 50)
    else:
        print(f" Error del servidor: {response.status_code}")
        print(response.text)

except Exception as e:
    print(f" Error de conexión: {e}")
    print("¿Te has asegurado de que uvicorn (FastAPI) está corriendo?")