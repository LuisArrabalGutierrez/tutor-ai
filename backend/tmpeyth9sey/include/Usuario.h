
/*
 * File:   Usuario.h
 * Author: Luis
 *
 */

/**@class Usuario
 * @brief Esta clase almacena información acerca de un usuario de una red social sobre películas.
 * De cada usuario se almacena un id, un nombre de usuario y un correo electrónico. Se indican, además
 * el número de películas que ha visto, que determina el nivel del usuario dentro de la red, y los ids
 * de los amigos que tiene el usuario en la red social. Para los ids se usa un vector de enteros dinámico que puede
 * ir creciendo a medida que el usuario haga más amigos en la red. la constante INCREMENTO indica el número de posiciones
 * que hay que ir reservando cada vez que el vector se llena.
 *
 * La clase proporciona una serie de métodos, cuyo objetivo es poder actualizar la información del usuario.
 */

#ifndef USUARIO_H
#define USUARIO_H
#include <string>
using namespace std;
class Usuario
{
public:
  /**@brief Constructor de la clase Usuario, inicializa numpeliculas y numAmigos a 0.
   * Además reserva espacio en el vector idAmigos para que se puedan introducir ids de amigos en cualquier momento.
   * El número de amigos que reserva inicialmente viene dado por la variable INCREMENTO.
   */
  Usuario();

  /**@brief Constructor de copia. Copia los datos de orig en el objeto usuario.
   *
   */
  Usuario(const Usuario &orig);

  /** @brief Crea un objeto Usuario con un id, nombre de usuario y correo electrónico determinados.
   */
  Usuario(int newid, string newnombreusuario, string newcorreoelectronico);

  /**@brief Libera la información del vector idAmigos.
   */
  virtual ~Usuario();

  /** @brief Devuelve un string con el correo electrónico del usuario.
   * @retval Un string con el correo electrónico del usuario.
   */
  string getCorreoElectronico() const;

  /** @brief Devuelve el nick del usuario.
   * @retval Un string con el nick del usuario en la red social.
   */
  string getNombreUsuario() const;

  /** @brief Devuelve el id del usuario.
   * @retval Devuelve el id del usuario.
   */
  int getId() const;

  /**
   * @brief Devuelve un entero con el número de películas que ha visto el usuario.
   * @return  valor entero con el número de películas
   */
  int getNumPeliculas() const;

  /** @brief Devuelve una referencia al id del usuario.
   * @retval Referencia al id del usuario que permite su modificación.
   */
  int &setId();

  /** @brief Devuelve una referencia al string que contiene el nick del usuario.
   * @retval Referencia que permite la modificación del nick del usuario.
   */
  string &putNombreUsuario();

  /** @brief Devuelve una referencia al string que contiene el correo electrónico del usuario.
   * @retval Referencia que permite la modificación del correo electrónico del usuario.
   */
  string &putCorreoElectronico();

  /**
   * @brief Añade un nuevo amigo a la lista de amigos del usuario. Si el vector idAmigos está lleno entonces
   * lo aumentamos en INCREMENTO y luego añadimos el amigo. La variable numAmigos siempre debe de ser igual o menor a la variable
   * numreservadoAmigos para que no haya segmentation faults. Si la variable es igual o superior entonces este método
   * aumenta en INCREMENTO el número de valores reservados en el vector y posteriormente agrega el nuevo amigo introducido.
   * Este método comprueba también que no haya amigos repetidos en el vector. Si se intenta introducir un id que ya aparece en
   * el vector, entonces no se hace y el método devuelve false.
   * @param idnuevoamigo id del amigo que se quiere agregar a la lista de amigos.
   * @return Devuelve true si el nuevo amigo se ha introducido. Devuelve false si el amigo
   * no se ha podido introducir (generalmente, esto ocurre cuando se intenta añadir un amigo ya existente).
   */
  bool anaideAmigo(int idnuevoamigo);

  /**
   * @brief Elimina del vector de amigos un id de amigo. Si el id a eliminar no está en el vector entonces el método no hace nada,
   * devuelve false.
   * @param idamigo id del amigo que se quiere eliminar.
   * @return true si se ha realizado la eliminación correctamente. False si no se pudo eliminar (Generalmente porque el id
   * no aparezca en el vector).
   */
  bool eliminaAmigo(int idamigo);

  /**
   * @brief Devuelve el id del amigo que hay en la posición i del vector
   * @param i posición del vector de la que devolver el id del amigo
   * @return el id del amigo que hay en la posición i
   */
  int &operator[](int i) const;

  /**
   * @brief Incrementa en 1 el número de películas que el usuario de la red social ha visto.
   */
  void incrementaNumPeliculas();

  /**
   * @brief Operador de asignación (asigna los valores de orig al objeto).
   * @param orig objeto Usuario que se asigna.
   * @return Devuelve el objeto Usuario con los valores ya asignados.
   */
  Usuario &operator=(const Usuario &orig);

  /*
   * A continuación se definen los operadores de comparación entre objetos Usuario.
   * La idea es que comparen usuarios basándose en el número de películas vistas.
   * Esto servirá para poder crear un ranking de usuarios en base a este valor.
   */

  /**
   * @brief Determina si 2 usuarios han visto el mismo número de películas.
   * @param dch el otro usuario.
   * @return true si los 2 usuarios han visto el mismo número de películas.
   * false en otro caso.
   */
  bool operator==(const Usuario &dch) const;

  /**
   * @brief Determina si 2 usuarios han visto distinto número de películas.
   * @param dch el otro usuario.
   * @return true si los 2 usuarios han visto distinto número de películas.
   * false en otro caso.
   */
  bool operator!=(const Usuario &dch) const;

  /**
   * @brief Determina si el usuario izq ha visto menos películas que el usuario dch.
   * @param dch el otro usuario.
   * @return true si el usuario izq ha visto menos películas que el usuario dch.
   */
  bool operator<(const Usuario &dch) const;

  /**
   * @brief Determina si el usuario izq ha visto más películas que el usuario dch.
   * @param dch el otro usuario.
   * @return true si el usuario izq ha visto más películas que el usuario dch.
   */
  bool operator>(const Usuario &dch) const;

  /**
   * @brief Determina si el usuario izq ha visto menos o la misma cantidad de películas que el usuario dch.
   * @param dch el otro usuario.
   * @return true si el usuario izq tha visto menos o la misma cantidad de películas que el usuario dch.
   */
  bool operator<=(const Usuario &dch) const;

  /**
   * @brief Determina si el usuario izq ha visto más o la misma cantidad de películas que el usuario dch.
   * @param dch el otro usuario.
   * @return true si el usuario izq tha visto más o la misma cantidad de películas que el usuario dch.
   */
  bool operator>=(const Usuario &dch) const;

  /**@brief Operador de flujo de salida. Introduce en la variable ostream flujo
   * los valores de id, nick, correo electrónico, numpelículas y número de id de amigos en ese orden.
   * A continuación, lista los ids de los amigos del usuario.
   * Los valores están separados por espacios y después del número de amigos se pone ":".
   * Ejemplo de línea a imprimir:
   *                1 Nick1 user1@correo.es 4 6: 6 2 3 7 10 15
   * @return Devuelve flujo con los valores del objeto Usuario introducidos.
   */
  friend std::ostream &operator<<(std::ostream &flujo, const Usuario &user);

private:
  string correoelectronico;
  string nombreusuario;
  int id;
  int numpeliculas;
  int *idAmigos;
  int numAmigos;
  int numreservadoAmigos;
  static const int INCREMENTO = 5;
};

#endif /* USUARIO_H */
