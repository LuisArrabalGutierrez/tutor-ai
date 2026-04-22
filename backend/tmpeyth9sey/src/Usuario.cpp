
#include "Usuario.h"
#include <iostream>

using namespace std;

Usuario::Usuario()
{
    this->numpeliculas = 0;
    this->numAmigos = 0;
    this->idAmigos = new int[INCREMENTO];
    this->numreservadoAmigos = INCREMENTO;
}

Usuario::Usuario(const Usuario &orig)
{
    this->id = orig.id;
    this->nombreusuario = orig.nombreusuario;
    this->correoelectronico = orig.correoelectronico;
    this->numpeliculas = orig.numpeliculas;
    this->numAmigos = orig.numAmigos;
    this->numreservadoAmigos = orig.numreservadoAmigos;

    if (orig.idAmigos != nullptr)
    {
        this->idAmigos = new int[numreservadoAmigos];

        for (int i = 0; i < this->numAmigos; ++i)
        {
            this->idAmigos[i] = orig.idAmigos[i];
        }
    }
    else
    {
        this->idAmigos = nullptr;
    }
}

Usuario::~Usuario()
{
    if (this->idAmigos != nullptr)
    {
        delete[] this->idAmigos;
        this->idAmigos = nullptr;
    }
}

string Usuario::getCorreoElectronico() const
{
    return this->correoelectronico;
}

string Usuario::getNombreUsuario() const
{
    return this->nombreusuario;
}

int Usuario::getId() const
{
    return this->id;
}

string &Usuario::putNombreUsuario()
{
    return nombreusuario;
}

string &Usuario::putCorreoElectronico()
{
    return correoelectronico;
}

Usuario::Usuario(int newid, string newnombreusuario, string newcorreoelectronico) : id(newid), nombreusuario(newnombreusuario), correoelectronico(newcorreoelectronico),
                                                                                    numpeliculas(0), numAmigos(0), numreservadoAmigos(INCREMENTO)
{
    this->idAmigos = new int[numreservadoAmigos];

    for (int i = 0; i < numreservadoAmigos; ++i)
    {
        this->idAmigos[i] = 0;
    }
}

int &Usuario::setId()
{
    return id;
}

Usuario &Usuario::operator=(const Usuario &orig)
{
    if (this != &orig)
    {
        delete[] this->idAmigos;

        this->id = orig.id;
        this->nombreusuario = orig.nombreusuario;
        this->correoelectronico = orig.correoelectronico;
        this->numpeliculas = orig.numpeliculas;
        this->numAmigos = orig.numAmigos;
        this->numreservadoAmigos = orig.numreservadoAmigos;

        if (orig.idAmigos != nullptr)
        {
            this->idAmigos = new int[this->numreservadoAmigos];
            for (int i = 0; i < this->numAmigos; ++i)
            {
                this->idAmigos[i] = orig.idAmigos[i];
            }
        }
        else
        {
            this->idAmigos = nullptr;
        }
    }

    return *this;
}

int Usuario::getNumPeliculas() const
{
    return numpeliculas;
}

bool Usuario::anaideAmigo(int idnuevoamigo)
{
    for (int i = 0; i < numAmigos; i++)
    {
        if (idAmigos[i] == idnuevoamigo)
            return false;
    }

    if (numAmigos == numreservadoAmigos)
    {
        numreservadoAmigos += INCREMENTO;
        int *newArray = new int[numreservadoAmigos];

        for (int i = 0; i < numAmigos; i++)
        {
            newArray[i] = idAmigos[i];
        }

        delete[] idAmigos;
        idAmigos = newArray;
    }

    idAmigos[numAmigos] = idnuevoamigo;
    numAmigos++;

    return true;
}

bool Usuario::eliminaAmigo(int idamigo)
{
    int posicion = -1;

    for (int i = 0; i < numAmigos; i++)
    {
        if (idAmigos[i] == idamigo)
        {
            posicion = i;
            break;
        }
    }

    if (posicion == -1)
    {
        return false;
    }

    for (int i = posicion; i < numAmigos - 1; i++)
    {
        idAmigos[i] = idAmigos[i + 1];
    }

    numAmigos--;

    return true;
}

void Usuario::incrementaNumPeliculas()
{
    this->numpeliculas++;
}

int &Usuario::operator[](int i) const
{
    return this->idAmigos[i];
}

bool Usuario::operator==(const Usuario &dch) const
{
    return this->numpeliculas == dch.numpeliculas;
}

bool Usuario::operator!=(const Usuario &dch) const
{
    return this->numpeliculas != dch.numpeliculas;
}

bool Usuario::operator<(const Usuario &dch) const
{
    return this->numpeliculas < dch.numpeliculas;
}

bool Usuario::operator>(const Usuario &dch) const
{
    return this->numpeliculas > dch.numpeliculas;
}

bool Usuario::operator<=(const Usuario &dch) const
{
    return this->numpeliculas <= dch.numpeliculas;
}

bool Usuario::operator>=(const Usuario &dch) const
{
    return this->numpeliculas >= dch.numpeliculas;
}

std::ostream &operator<<(std::ostream &flujo, const Usuario &user)
{
    flujo << user.id << " " << user.nombreusuario << " " << user.correoelectronico << " " << user.numpeliculas << " " << user.numAmigos << ":";
    for (int i = 0; i < user.numAmigos; i++)
    {
        flujo << " " << user.idAmigos[i];
    }

    return flujo;
}
