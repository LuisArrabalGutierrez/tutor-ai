

#include "ConjuntoUsuarios.h"
#include <iostream>
#include <string>

using namespace std;
ConjuntoUsuarios::ConjuntoUsuarios(int k)
{

    this->tamreservado = k;
    this->numusuarios = 0;
    this->vectorUsuarios = new Usuario[k];
}

ConjuntoUsuarios &ConjuntoUsuarios::operator=(const ConjuntoUsuarios &orig)
{
    if (this != &orig)
    {
        delete[] this->vectorUsuarios;

        this->numusuarios = orig.numusuarios;
        this->tamreservado = orig.tamreservado;

        if (orig.vectorUsuarios != nullptr)
        {
            this->vectorUsuarios = new Usuario[this->tamreservado];

            for (int i = 0; i < this->numusuarios; i++)
            {
                this->vectorUsuarios[i] = orig.vectorUsuarios[i];
            }
        }
        else
        {
            this->vectorUsuarios = nullptr;
        }
    }

    return *this;
}

ConjuntoUsuarios::ConjuntoUsuarios(const ConjuntoUsuarios &orig)
{
    this->numusuarios = orig.numusuarios;
    this->tamreservado = orig.tamreservado;

    if (orig.vectorUsuarios != nullptr)
    {
        this->vectorUsuarios = new Usuario[this->tamreservado];

        for (int i = 0; i < tamreservado; i++)
        {
            this->vectorUsuarios[i] = orig.vectorUsuarios[i];
        }
    }
}

ConjuntoUsuarios::~ConjuntoUsuarios()
{
    if (this->vectorUsuarios != nullptr)
    {
        delete[] this->vectorUsuarios;
        this->vectorUsuarios = nullptr;
    }
}

ConjuntoUsuarios::ConjuntoUsuarios(int n, string *nombresusuario, string *correoselectronicos)
{
    // tamaño de nombres y correos : n
    this->tamreservado = n;
    this->numusuarios = n;
    this->vectorUsuarios = new Usuario[n];

    if (nombresusuario != nullptr && correoselectronicos != nullptr)
    {
        for (int i = 1; i < n; i++)
        {
            this->vectorUsuarios[i] = Usuario(i, nombresusuario[i], correoselectronicos[i]);
        }
    }
}

string ConjuntoUsuarios::rankingUsuarios()
{
    string resultado = "";

    Usuario **arrayOrdenado = new Usuario *[numusuarios];

    for (int i = 0; i < numusuarios; i++)
    {
        arrayOrdenado[i] = &vectorUsuarios[i];
    }

    for (int i = 0; i < numusuarios - 1; i++)
    {
        int max = i;
        for (int j = i + 1; j < numusuarios; j++)
        {
            if (*arrayOrdenado[j] > *arrayOrdenado[max])
            {
                max = j;
            }
        }

        // cambia la posicion
        Usuario *temp = arrayOrdenado[i];
        arrayOrdenado[i] = arrayOrdenado[max];
        arrayOrdenado[max] = temp;
    }

    for (int i = 0; i < numusuarios; i++)
    {
        resultado += arrayOrdenado[i]->getNombreUsuario() + " " +
                     arrayOrdenado[i]->getCorreoElectronico() + ": " +
                     to_string(arrayOrdenado[i]->getNumPeliculas()) + "\n";
    }

    delete[] arrayOrdenado;

    return resultado;
}

std::ostream &operator<<(std::ostream &flujo, const ConjuntoUsuarios &conjuser)
{
    flujo << conjuser.numusuarios << "\n";

    for (int i = 0; i < conjuser.numusuarios; i++)
    {
        // se sobrecarga con el de la clase usuario
        flujo << conjuser.vectorUsuarios[i] << "\n";
    }

    return flujo;
}

ConjuntoUsuarios &ConjuntoUsuarios::operator+=(const Usuario &newuser)
{
    if (this->numusuarios == this->tamreservado)
    {
        this->resize(this->tamreservado + INCREMENTO);
    }

    this->vectorUsuarios[this->numusuarios] = newuser;
    this->numusuarios++;

    this->ordenaporId();

    return *this;
}

bool ConjuntoUsuarios::eliminaUsuario(int userid)
{
    int pos = -1;
    for (int i = 0; i < this->numusuarios; i++)
    {
        if (vectorUsuarios[i].getId() == userid)
        {
            pos = i;
            break;
        }
    }

    if (pos == -1)
    {
        return false;
    }

    for (int i = pos; i < numusuarios - 1; i++)
    {
        this->vectorUsuarios[i] = this->vectorUsuarios[i + 1];
    }
    numusuarios--;
    return true;
}

int ConjuntoUsuarios::buscaUsuario(int userid)
{
    int pos = -1;

    for (int i = 0; i < numusuarios; i++)
    {
        if (userid == this->vectorUsuarios[i].getId())
            pos = i;
        return pos;
    }

    return pos;
}

int ConjuntoUsuarios::buscaUsuario(string nombreusuario)
{
    int pos = -1;

    for (int i = 0; i < numusuarios; i++)
    {
        if (nombreusuario == this->vectorUsuarios[i].getNombreUsuario())
            pos = i;
        return pos;
    }

    return pos;
}

void ConjuntoUsuarios::optimizar()
{
    if (tamreservado != numusuarios)
    {
        tamreservado = numusuarios;

        Usuario *nuevo = new Usuario[numusuarios];
        for (int i = 0; i < numusuarios; i++)
        {
            nuevo[i] = vectorUsuarios[i];
        }

        delete[] vectorUsuarios;
        vectorUsuarios = nuevo;
    }
}

Usuario &ConjuntoUsuarios::operator[](int i) const
{
    return this->vectorUsuarios[i];
}

void ConjuntoUsuarios::ordenaporId()
{
    for (int i = 0; i < numusuarios - 1; i++)
    {
        int min = i;
        for (int j = i + 1; j < numusuarios; j++)
        {
            if (vectorUsuarios[j].getId() < vectorUsuarios[min].getId())
            {
                min = j;
            }
        }

        if (min != i)
        {
            Usuario temp = vectorUsuarios[i];
            vectorUsuarios[i] = vectorUsuarios[min];
            vectorUsuarios[min] = temp;
        }
    }
}

void ConjuntoUsuarios::resize(int newtam)
{
    if (newtam > tamreservado)
    {
        tamreservado = newtam;

        Usuario *nuevo = new Usuario[tamreservado];
        for (int i = 0; i < numusuarios; i++)
        {
            nuevo[i] = vectorUsuarios[i];
        }

        delete[] vectorUsuarios;
        vectorUsuarios = nuevo;
    }
}

ConjuntoUsuarios ConjuntoUsuarios::operator+(const ConjuntoUsuarios &right) const
{
    int totalUsuarios = this->numusuarios + right.numusuarios;
    ConjuntoUsuarios nuevoConjunto(totalUsuarios);

    // copia el primero
    for (int i = 0; i < this->numusuarios; i++)
    {
        nuevoConjunto.vectorUsuarios[i] = this->vectorUsuarios[i];
    }

    // copia el segundo
    for (int i = 0; i < right.numusuarios; i++)
    {
        nuevoConjunto.vectorUsuarios[this->numusuarios + i] = right.vectorUsuarios[i];
    }

    nuevoConjunto.numusuarios = totalUsuarios;

    nuevoConjunto.ordenaporId();

    return nuevoConjunto;
}
