

/*
 * File:   ConjuntoUsuarios.h
 * Author: Luis
 *
 */

#ifndef CONJUNTOUSUARIOS_H
#define CONJUNTOUSUARIOS_H
#include "Usuario.h"
#include <iostream>
#include <fstream>
using namespace std;

/**
 * @class ConjuntoUsuarios
 * @brief Los objetos ConjuntoUsuarios manejan a un conjunto de Usuarios que
 * forman parte de una red social de películas. En esta primera versión, la clase está compuesta
 * por un vector de Usuarios. Los Usuarios están ordenados en el vector en base a
 * sus ids. Cada Usuario tiene un id diferente pero no tienen porque ser consecutivos
 * ya que se permite que los usuarios se borren de la red social. Por ejemplo, si el Usuario 1
 * Juan, el Usuario 2, Pedro y el Usuario 3 Lucas están en la red pero el Usuario 2 se borra,
 * en el vector están 1,Juan y 3,Lucas no habiendo ningún usuario con id 2.
 *
 */
class ConjuntoUsuarios
{
public:
    /**
     * @brief Inicializa el vector de usuarios a un tamaño reservado específico.
     * @param k tamaño reservado (este puede ir incrementándose conforme sea necesario).
     */
    ConjuntoUsuarios(int k = INCREMENTO);

    /**
     * @brief Constructor de copia de la clase conjuntoUsuarios
     * @param orig objeto ConjuntoUsuarios desde donde se copia la información.
     */
    ConjuntoUsuarios(const ConjuntoUsuarios &orig);

    /**
     * @brief Destructor de la clase. Libera el espacio reservado.
     */
    virtual ~ConjuntoUsuarios();

    /**
     * @brief Se inicializa el objeto ConjuntoUsuarios con la información de los
     * vectores de cadenas que contienen los nombres de usuario y los correos electrónicos.
     * Los ids se van asignando desde el 1 en adelante siguiendo el orden de
     * los valores que contienen los 2 vectores. Si se utiliza este constructor entonces el tamaño
     * reservado coincide con el del número de usuarios.
     * @param n Número de elementos en los vectores nombres de usuario y correos electrónicos.
     * @param nombresusuario Vector con los nombres de usuario.
     * @param correoselectronicos Vector con los correos electrónicos de los usuarios.
     */
    ConjuntoUsuarios(int n, string *nombresusuario, string *correoselectronicos);
    /**
     * @brief Devuelve un string que imprime la lista de usuarios ordenados por el número
     * de películas que han visto.
     * @return Un string de los usuarios separados por el caracter \n. Cada linea
     * imprimirá en orden: id, nombre, apellidos, número de películas vistas.
     * El usuario con mejor índice será el primero y el peor el último.
     */
    string rankingUsuarios();

    /**
     * @brief Operador de asignación.
     * @param orig objeto ConjuntoUsuarios que es asignado.
     * @return objeto ConjuntoUsuarios con los datos de orig asignados.
     */
    ConjuntoUsuarios &operator=(const ConjuntoUsuarios &orig);

    /*
     * @brief Introduce en el flujo de datos toda la información de un conjunto de usuarios.
     * Utilizamos el operador << de la clase Usuario para hacer este proceso. Entre usuario y
     * usuario se introduce el caracter "\n" para que cada uno aparezca en una línea diferente
     * si lo imprimimos con cout.
     */
    friend std::ostream &operator<<(std::ostream &flujo, const ConjuntoUsuarios &conjuser);

    /**
     * @brief Añade un nuevo usuario al vector de Usuarios.
     * @param newuser Nuevo usuario que se añade al vector.
     * @return El objeto ConjuntoUsuarios con el usuario añadido. Debe estar siempre ordenado
     * por id. Es importante tener en cuenta que los ids no tienen porque ser números
     * enteros continuos porque los usuarios se pueden eliminar del vector. Puede asumirse
     * que no hay ids repetidos. Puede utilizarse el método ordenaporId para ordenar el vector.
     */
    ConjuntoUsuarios &operator+=(const Usuario &newuser);

    /**
     * @brief Elimina del vector de Usuarios al que tenga un determinado id.
     * @param userid id del usuario a eliminar del vector.
     */
    bool eliminaUsuario(int userid);

    /**
     * @brief Devuelve la posición en el vector del usuario cuyo id es igual al indicado.
     * @param userid id del usuario que buscamos.
     * @return -1 si no hay ningún usuario con esa id o el número de posición en caso
     * de haberlo.
     */
    int buscaUsuario(int userid);

    /**
     * @brief Devuelve la posición en el vector del usuario cuyo nombre es igual al indicado.
     * @param nombreusuario nombre del usuario que buscamos.
     * @return -1 si no hay ningún usuario con ese nombre o el número de posición en caso
     * de haberlo.
     */
    int buscaUsuario(string nombreusuario);

    /**
     * @brief Minimiza el espacio reservado haciendo que tamreservado = numusuarios y ese sea
     * justo el número de espacios reservado en el vector.
     */
    void optimizar();

    /**
     * @brief operador de acceso al vector de Usuarios.
     * @param i posición del usuario que queremos devolver.
     * @return El objeto usuario que está localizado en la posición i.
     */
    Usuario &operator[](int i) const;

    /*
     * @brief Une dos conjuntos ConjuntoUsuarios en 1 solo. left y right se unen y
     * se devuelve un conjunto ConjuntoUsuarios que tiene a las personas que hay en
     * ambos conjuntos.
     * @param right ConjuntoUsuario con los segundos Usuarios.
     * @return un objeto ConjuntoUsuarios con todos los elementos de los objetos
     * left y right.
     */
    ConjuntoUsuarios operator+(const ConjuntoUsuarios &right) const;

private:
    /**
     * @brief Ordena los usuarios de un objeto ConjuntoUsuarios en base a su id.
     */
    void ordenaporId();

    /**
     * @brief Aumenta el tamaño reservado del vector. La información del vector de
     * Usuarios se mantiene.
     * @pre newtam debe ser mayor que el tamaño reservado actualmente.
     * @param newtam Nuevo tamaño de espacio reservado.
     */
    void resize(int newtam);

    /* Vector de objetos Usuario
     */
    Usuario *vectorUsuarios;
    /* Número de usuarios en el objeto */
    int numusuarios;
    /*Tamaño reservado en el vector*/
    int tamreservado;
    /*Número de elementos nuevos a reservar en el vector cada vez que nos quedamos sin espacio*/
    static const int INCREMENTO = 5;
};

#endif /* CONJUNTOUSUARIOS_H */
