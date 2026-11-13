# LeGO Suite v0.198

**LeGO Suite** es la suite integral de control de energía, ventilación, eGPU e interfaz de mandos para Lenovo Legion Go en Decky Loader y modo escritorio.

## Pestañas del Plugin

### 1. TDP (Energía y Ventilación)
- **Control de TDP**: Ajuste de TDP global y por juego (WMI de Lenovo y `ryzenadj`).
- **Control de GPU y eGPU**: Modos Batería, Balance, Rango de frecuencias, Frecuencia fija y detección/integración con eGPUs externas.
- **Controles de CPU**: CPU Boost, SMT, Gobernador de energía (Power Governor) y Preferencia de rendimiento energético (EPP).
- **Curvas de Ventilación (Fan Control)**: Curvas de temperatura/velocidad de ventilador personalizadas, perfiles de ventilación por juego y modo de velocidad máxima (Full Fan Speed).
- **Límite de Carga de Batería (80%)**: Protección de batería mediante llamadas ACPI de Lenovo.
- **Brillo Adaptativo (ALS)**: Sensor de luz ambiental configurable.
- **Opciones Avanzadas**: Polling de TDP en segundo plano, perfiles AC, undervolt experimental vía `ryzenadj`, y manejo de suspensión/reanudación.

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
