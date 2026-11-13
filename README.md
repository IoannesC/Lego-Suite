<img width="1672" height="941" alt="file_000000001834822f9cf25b1021da0124" src="https://github.com/user-attachments/assets/a18d2591-66ca-44b6-80e3-065768210b3a" />

### LeGO Suite v0.198

LeGO Suite es la suite integral de control para sacarle el mayor provecho a tu Legion Go en Linux. 

### Sin vinculación directa o indirecta con ninguna marca registrada. No tiene afiliación ni relación ninguna con Lenovo ni con ninguna otra empresa. 

### Descargo de responsabilidad
El uso de este software es responsabilidad de quien lo utiliza. Carece de cualquier tipo de garantía y es el usuario el único responsable para todos los efectos conducentes.


### Notas sobre la v0.198:
Está probada y funciona correctamente en mi Lenovo Legion Go Gen 1, Z1 Extreme con 16Gb de RAM. No tengo acceso a otros dispositivos. Si llego a conseguir ponerle las manos encima a otro dispositivo o a otra máquina de Lenovo, con gusto optimizaré para esos sistemas; o en su defecto testers con otras máquinas. Por el momento si necesitas probarlo en tu equipo que no es Lenovo Legion Go Gen 1, hazlo por tu propia iniciativa.
Me gustaría agregar más opciones y más funcionalidades utiles, poco a poco lo iré haciendo. 

### Sobre LeGO Suite:

Hay dos aplicaciones en una. Un práctico Plugin para Decky y una aplicación para escritorio. Puedes utilizar el plugin para Decky sin necesidad de descargar e instalar la aplicación de escritorio. Pero ambas se complementan y te ofrecen más opciones. 

<div align="center"> ### LeGO Suite Versión Decky Plugin </div>

<img width="326" height="449" alt="f1" src="https://github.com/user-attachments/assets/7a841a7f-e3e5-43b3-bef9-b6c555a5b6a4" />



### 1. TDP (Energía y Ventilación).
   
Control de TDP**: Ajuste de TDP global y por juego (WMI de Lenovo y `ryzenadj`).
Control de GPU y eGPU**: Modos Batería, Balance, Rango de frecuencias, Frecuencia fija y detección/integración con eGPUs externas.
Controles de CPU**: CPU Boost, SMT, Gobernador de energía (Power Governor) y Preferencia de rendimiento energético (EPP).
Curvas de Ventilación (Fan Control)**: Curvas de temperatura/velocidad de ventilador personalizadas, perfiles de ventilación por juego y modo de velocidad máxima (Full Fan Speed).
Límite de Carga de Batería (80%)**: Protección de batería mediante llamadas ACPI de Lenovo.
Opciones Avanzadas**: Polling de TDP en segundo plano, perfiles AC, undervolt experimental vía `ryzenadj`, y manejo de suspensión/reanudación.

### 2. Controls (Mandos e Iluminación)
- **Iluminación RGB de Controles**: Control del LED de encendido y anillos RGB de los mandos (modos Solid, Dynamic, Pulse, Spiral, brillo, velocidad, tono/hue y perfiles por juego).
- **Remapeo de Botones y Giroscopio**: Asignación de botones traseros (`Y1`, `Y2`, `Y3`, `M2`, `M3`), activación/desactivación del Touchpad y remapeo de giroscopios izquierdo/derecho por juego.

---

## Agradecimientos y Créditos (Credits & Acknowledgments)

Este proyecto se basa e inspira en el excelente trabajo de la comunidad de Decky Loader y desarrolladores de herramientas para Linux y Lenovo Legion Go:

- **[SimpleDeckyTDP](https://github.com/aarron-lee/SimpleDeckyTDP)** por [Aarron Lee](https://github.com/aarron-lee) — Arquitectura base de control térmico, TDP, curvas de ventilador y estructura original del plugin.
- **[LegionGoRemapper](https://github.com/aarron-lee/LegionGoRemapper)** por [Aarron Lee](https://github.com/aarron-lee) — Protocolo de comunicación HID de mandos, perfiles de remapeo y control de anillos RGB.
- **[All-Ways-EGPU](https://github.com/egpu-io/all-ways-egpu)** — Por la lógica, detección y gestión de GPU externa (eGPU) en Linux.
- **[Decky Loader](https://github.com/SteamDeckHomebrew/decky-loader)** — Por la plataforma, API y entorno para plugins en SteamOS / Bazzite.
- **[RyzenAdj](https://github.com/FlyGoat/RyzenAdj)** — Por las herramientas y biblioteca de gestión de energía para procesadores AMD Ryzen.
- **Handheld Daemon (HHD) / InputPlumber** — Por el soporte de emulación de mandos, perfiles y drivers en Linux.

Muchas gracias a todos los autores, mantenedores y contribuidores de estos proyectos de código abierto.
