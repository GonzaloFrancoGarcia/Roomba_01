# Mosquito Hunter - Segunda Práctica

## Descripción
Mosquito Hunter es un juego en el que un mosquito rebelde intenta picar a la gente que duerme, mientras tú, armado con una chancla, debes aplastarlo. Con un entorno dinámico, música envolvente y animaciones suavizadas, este juego pondrá a prueba tus reflejos y precisión.

## cliente-servidor
- **roomba.py**: Contiene la lógica principal de la simulación (movimiento del mosquito, generación de partículas, restricciones de zonas) y el renderizado.
- **servidor.py**: Ejecuta la simulación en un servidor TCP. Se encarga de actualizar el estado del juego (mosquito, zonas, partículas) y enviar dicha información a los clientes. Además, procesa el comando "SQUASH" para eliminar al mosquito.
- **cliente.py**: Se conecta al servidor para recibir y renderizar de forma suave el estado del juego. Permite al jugador (chancla) moverse únicamente dentro de las zonas definidas y, cuando colisiona con el mosquito, pulsar la barra espaciadora para enviar la orden de "SQUASH".

## Controles
- **Flechas del teclado:** Mueven al jugador (chancla) en las cuatro direcciones, respetando los límites de las zonas permitidas.
- **Barra espaciadora:** Cuando el jugador colisiona con el mosquito, pulsa SPACE para aplastar al mosquito (se envía el comando "SQUASH" al servidor).

## Objetivo
Evita que el mosquito cause problemas y elimínalo antes de que sea demasiado tarde. ¡Sé rápido y preciso para ganar!

## Requerimientos e Instalación
Para ejecutar correctamente el juego y la comunicación cliente-servidor se requiere:

- **Python 3.x** (se recomienda Python 3.11 o superior)
- **pygame**: Para la parte gráfica y de audio.
- Las librerías **socket** y **threading** son parte de la librería estándar de Python y no requieren instalación adicional.

### Instalación de pygame
Si aún no lo tienes instalado, puedes hacerlo mediante pip:

```bash
pip install pygame
