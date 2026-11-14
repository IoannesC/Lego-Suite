<img width="1672" height="941" alt="file_000000001834822f9cf25b1021da0124" src="https://github.com/user-attachments/assets/a18d2591-66ca-44b6-80e3-065768210b3a" />

### <div align="center"> <h2> LeGO Suite v0.200 </h2> </div>

LeGO Suite is the all-in-one control suite designed to get the most out of your Legion Go on Linux.

### No direct or indirect affiliation with any registered trademark. It has no affiliation or relationship whatsoever with Lenovo or any other company.

### Disclaimer
The use of this software is at the user's own risk. It comes without any kind of warranty, and the user is solely responsible for all resulting effects and consequences.
Part of this code was developed with the help of AI assistants. Everything was reviewed and tested on a Legion Go.

**Dependencies and Requirements:**

**1. Decky Loader Plugin**

Decky Loader (on SteamOS, Bazzite, or Linux).
Root permissions (configured in `plugin.json`).
Python 3 with the `hid==1.0.5` library (`requirements.txt`).
udev rules for Lenovo controllers (`idVendor=="17ef"`), configured via `install.sh`.
RyzenAdj (already included in `bin/`).
(Only for building from source): Node.js and pnpm (to install `package.json` dependencies and run `pnpm build`).

**2. Desktop App (`desktop/lego_suite_desktop.py`)**

Python 3 (`/usr/bin/python3`).
PyQt6 (for the graphical user interface and system tray icon).
XWayland / XCB (`QT_QPA_PLATFORM=xcb`, used when launching the app in `desktop/install_desktop_app.sh`).
KDE Plasma / KWin (optional): to automatically apply the borderless window rule at the top right (`kwinrulesrc` and `qdbus6`).
RyzenAdj (included in `bin/`) and udev rules for the controllers.

Optional:

InputPlumber for controller profile management and emulation (Not Handheld Daemon).
On certain distributions, you may need to remove a udev rule that hijacks the screen's accelerometer—preventing its convenient use as a vertical tablet—for InputPlumber (it uses it as a controller accelerometer, which is useless since InputPlumber can coexist and function without that rule).

Even though SimpledeckyTDP, Legion GO Remapper, and HDD are awesome utilities and my efforts are super modest, if you want to test these apps, you'll need to uninstall those first.

CSS Loader on Decky and the Colored Toggles plugin.

All-Ways-EGPU to use the eGPU in Gamescope without loopback latency when using the GPU's HDMI output (CachyOS).

### Notes on v0.198:
It has been tested and works properly on my **Lenovo Legion Go Gen 1, Z1 Extreme with 16GB of RAM on CachyOS with the LTS kernel.** I do not have access to other devices. If I ever manage to get my hands on another device or another Lenovo machine, I will gladly optimize it for those systems—or alternatively, collaborate with testers who own other machines. For the time being, if you need to test it on a device other than the Lenovo Legion Go Gen 1, please do so at your own initiative.
I would like to add more options and useful features, and I will be implementing them little by little.

### About LeGO Suite:

There are two applications in one: a handy Decky Plugin and a Desktop Application. You can use the Decky plugin without needing to download and install the desktop application. However, both complement each other and offer you even more options.

### <div align="center"> LeGO Suite Decky Plugin Version </div>

<div align="center"> <img width="326" height="449" alt="f1" src="https://github.com/user-attachments/assets/7a841a7f-e3e5-43b3-bef9-b6c555a5b6a4" /> </div>

### Installation

```bash
curl -L https://github.com/IoannesC/Lego-Suite/releases/latest/download/LeGO-Suite-Plugin-v0.200.zip -o /tmp/lego-plugin.zip && \
sudo mkdir -p ~/homebrew/plugins/LeGO-Suite && \
sudo unzip -o /tmp/lego-plugin.zip -d ~/homebrew/plugins/LeGO-Suite && \
rm /tmp/lego-plugin.zip && \
bash ~/homebrew/plugins/LeGO-Suite/install.sh && \
sudo systemctl restart plugin_loader
```

### 1. TDP (Power and Fan Control)
   
TDP Control: Global and per-game TDP adjustment (Lenovo WMI and `ryzenadj`).

GPU Control: Battery, Balance, Frequency Range, Fixed Frequency modes, and external eGPU detection/integration.

Custom profiles when connected to an eGPU:

Implemented in v0.198

<img width="300" height="381" alt="Captura de pantalla_20261113_093423" src="https://github.com/user-attachments/assets/65ad3dfe-0099-4bb4-ad71-357f19edd0ef" />

When connecting an eGPU, the plugin detects the connection in real time, and if you enable the option, it allows you to create exclusive TDP profiles for when the eGPU is connected.

Specific TDP profiles per game, for games running on AC power, and with an eGPU connected (mutually exclusive).

CPU Controls: CPU Boost, SMT, Power Governor, and Energy Performance Preference (EPP).

Fan Curves (Fan Control): Custom temperature/fan speed curves, per-game fan profiles, and Full Fan Speed mode.

Real-time CPU and GPU temperatures, plus fan RPM.

Battery Charge Limit (80%): Battery protection via Lenovo ACPI calls.
Advanced Options: Background TDP polling, AC profiles, experimental undervolting via `ryzenadj`, and suspend/resume handling.

### 2. Controls (Controllers and Lighting)

Controller RGB Lighting: Control of the power LED and controller RGB rings (Solid, Dynamic, Pulse, Spiral modes, brightness, speed, hue, and per-game profiles).

Synchronization with the CSS Loader plugin and the Colored Toggles add-on: Sliding the controller LED lighting color (in Solid or Pulse mode) changes the Gamescope UI theme accent color in real time.

**Button and Gyroscope Remapping**: Assignment of back buttons (`Y1`, `Y2`, `Y3`, `M2`, `M3`), Touchpad enable/disable toggle, and per-game left/right gyroscope remapping.

Controller vibration intensity adjustment.

Factory reset option that erases any custom controller configuration.

And many other options for you to discover on your own.

### <div align="center"> LeGO Suite Desktop App Version </div>

<div align="center">  <img width="368" height="307" alt="f2" src="https://github.com/user-attachments/assets/e8ab1454-5ddc-4f9e-9cd4-84a83304eb3e" /> </div>

### Installation

```bash
curl -L https://github.com/IoannesC/Lego-Suite/releases/latest/download/LeGO-Suite-Desktop-v0.200.zip -o /tmp/lego-desktop.zip && \
mkdir -p /tmp/lego-desktop && \
unzip -o /tmp/lego-desktop.zip -d /tmp/lego-desktop && \
bash /tmp/lego-desktop/desktop/install_desktop_app.sh && \
rm -rf /tmp/lego-desktop /tmp/lego-desktop.zip
```

It offers the same functionality as the plugin, but without per-game profiles. It uses and modifies the default Gamescope profile while on the desktop so you can adjust it in real time (useful when running design or productivity apps that require extra power without having to switch back to Decky). In the Display section, it can inject the proper screen coordinates for the Legion Go so you can use it as a tablet and enable automatic screen rotation based on device orientation.

## Credits & Acknowledgments

This project is based on and inspired by the outstanding work of the Decky Loader community and Linux / Lenovo Legion Go tool developers:

- **[SimpleDeckyTDP](https://github.com/aarron-lee/SimpleDeckyTDP)** by [Aarron Lee](https://github.com/aarron-lee) — Core thermal control architecture, TDP, fan curves, and original plugin structure.
- **[LegionGoRemapper](https://github.com/aarron-lee/LegionGoRemapper)** by [Aarron Lee](https://github.com/aarron-lee) — Controller HID communication protocol, remapping profiles, and RGB ring control.
- **[All-Ways-EGPU](https://github.com/egpu-io/all-ways-egpu)** — For external GPU (eGPU) detection and management logic on Linux.
- **[Decky Loader](https://github.com/SteamDeckHomebrew/decky-loader)** — For the plugin platform, API, and environment on SteamOS / Bazzite.
- **[RyzenAdj](https://github.com/FlyGoat/RyzenAdj)** — For the power management tools and library for AMD Ryzen processors.
- **Handheld Daemon (HHD) / InputPlumber** — For controller emulation support, profiles, and drivers on Linux.

Many thanks to all the authors, maintainers, and contributors of these open-source projects.

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-ffdd00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://www.buymeacoffee.com/ioannesc)

<details>
<summary> 🇪🇸 Traducción al Español (Haz clic para desplegar) </summary>

<img width="1672" height="941" alt="file_000000001834822f9cf25b1021da0124" src="https://github.com/user-attachments/assets/a18d2591-66ca-44b6-80e3-065768210b3a" />

### <div align="center"> <h2> LeGO Suite v0.200 </h2> </div>

LeGO Suite es la suite integral de control para sacarle el mayor provecho a tu Legion Go en Linux. 

### Sin vinculación directa o indirecta con ninguna marca registrada. No tiene afiliación ni relación ninguna con Lenovo ni con ninguna otra empresa. 

### Descargo de responsabilidad
El uso de este software es responsabilidad de quien lo utiliza. Carece de cualquier tipo de garantía y es el usuario el único responsable para todos los efectos conducentes.

Parte de este código se desarrolló con ayuda de asistentes de IA. Todo fue revisado y probado en una Legion Go.

**Dependencias y requerimientos:**

**1. Plugin de Decky Loader**

Decky Loader (en SteamOS, Bazzite o Linux).
Permisos root (configurado en plugin.json).
Python 3 con la librería hid==1.0.5 (requirements.txt).
Reglas udev para mandos Lenovo (idVendor=="17ef"), que se configuran con install.sh.
RyzenAdj (ya viene incluido en bin/).
(Solo para compilar desde código fuente): Node.js y pnpm (para instalar dependencias de package.json y ejecutar pnpm build).

**2. App de Escritorio (desktop/lego_suite_desktop.py)**

Python 3 (/usr/bin/python3).
PyQt6 (para la interfaz gráfica y el icono en la bandeja del sistema).
XWayland / XCB (QT_QPA_PLATFORM=xcb, usado al lanzar la app en desktop/install_desktop_app.sh).
KDE Plasma / KWin (opcional): para aplicar automáticamente la regla de ventana sin bordes arriba a la derecha (kwinrulesrc y qdbus6).
RyzenAdj (incluido en bin/) y las reglas udev para los mandos.

Opcionales:

Input Plumber para la gestión y emulación de perfiles de los mandos (No Handheld Daemon).
En ciertas distros, habría que liberar de una regla Udev que secuestra el acelerometro de la pantalla -Y su conveniente uso como tablet vertical- para Input Plumber (Lo utiliza como acelerometro de los mandos, pero es inutil, dado que puede coexistir el uso por Input Plumber sin esa regla). 

Aunque SimpledeckyTDP, Legion GO Remmaper, y HHD son grandísimas utilidades y mis esfuerzos son sumamente modestos, si quieres probar estas aplicaciones, debes eliminar previamente las mencionadas. 

CSS Loader en Decky y el complemento Colored Toggles.

Allwaysegpu para utilizar la eGPU en Gamescope sin latencia de regreso al utilizar el HDMI de la GPU (CachyOS).

### Notas sobre la v0.198:
Está probada y funciona correctamente en mi **Lenovo Legion Go Gen 1, Z1 Extreme con 16Gb de RAM en CachyOS con kernel LTS.** No tengo acceso a otros dispositivos. Si llego a conseguir ponerle las manos encima a otro dispositivo o a otra máquina de Lenovo, con gusto optimizaré para esos sistemas; o en su defecto testers con otras máquinas. Por el momento si necesitas probarlo en tu equipo que no es Lenovo Legion Go Gen 1, hazlo por tu propia iniciativa.
Me gustaría agregar más opciones y más funcionalidades utiles, poco a poco lo iré haciendo. 

### Sobre LeGO Suite:

Hay dos aplicaciones en una. Un práctico Plugin para Decky y una aplicación para escritorio. Puedes utilizar el plugin para Decky sin necesidad de descargar e instalar la aplicación de escritorio. Pero ambas se complementan y te ofrecen más opciones. 

### <div align="center"> LeGO Suite Versión Decky Plugin </div>

<div align="center"> <img width="326" height="449" alt="f1" src="https://github.com/user-attachments/assets/7a841a7f-e3e5-43b3-bef9-b6c555a5b6a4" /> </div>

### Instalación

```bash
curl -L https://github.com/IoannesC/Lego-Suite/releases/latest/download/LeGO-Suite-Plugin-v0.200.zip -o /tmp/lego-plugin.zip && \
sudo mkdir -p ~/homebrew/plugins/LeGO-Suite && \
sudo unzip -o /tmp/lego-plugin.zip -d ~/homebrew/plugins/LeGO-Suite && \
rm /tmp/lego-plugin.zip && \
bash ~/homebrew/plugins/LeGO-Suite/install.sh && \
sudo systemctl restart plugin_loader
```

### 1. TDP (Energía y Ventilación).
   
Control de TDP: Ajuste de TDP global y por juego (WMI de Lenovo y `ryzenadj`).

Control de GPU: Modos Batería, Balance, Rango de frecuencias, Frecuencia fija y detección/integración con eGPUs externas.

Perfiles personalizados si se está conectado a una eGPU:

Implementada en v0.198

<img width="300" height="381" alt="Captura de pantalla_20261113_093423" src="https://github.com/user-attachments/assets/65ad3dfe-0099-4bb4-ad71-357f19edd0ef" />



Al conectar una eGPU, el Plugin detecta en tiempo real la conexión, y si activas la opción, te permite crear perfiles de TDP exclusivos con la eGPU conectada. 

Perfiles específicos de TDP por juego, por juegos con carga al alimentador de corriente y con eGPU conectada (Excluyentes entre sí). 

Controles de CPU: CPU Boost, SMT, Gobernador de energía (Power Governor) y Preferencia de rendimiento energético (EPP).

Curvas de Ventilación (Fan Control): Curvas de temperatura/velocidad de ventilador personalizadas, perfiles de ventilación por juego y modo de velocidad máxima (Full Fan Speed).

Temperatura de CPU y GPU en tiempo real, y RPM del ventilador. 

Límite de Carga de Batería (80%): Protección de batería mediante llamadas ACPI de Lenovo.
Opciones Avanzadas: Polling de TDP en segundo plano, perfiles AC, undervolt experimental vía `ryzenadj`, y manejo de suspensión/reanudación.

### 2. Controles (Mandos e Iluminación)

Iluminación RGB de Controles: Control del LED de encendido y anillos RGB de los mandos (modos Solid, Dynamic, Pulse, Spiral, brillo, velocidad, tono/hue y perfiles por juego).

Sincronización con el plugin CSS Loader y el complemento Colored Toggles: Al deslizar la iluminación del led de los mandos (En solido ó pulso) se cambia en tiempo real el acento del tema de la interfaz del Gamescope. 

Remapeo de Botones y Giroscopio**: Asignación de botones traseros (`Y1`, `Y2`, `Y3`, `M2`, `M3`), activación/desactivación del Touchpad y remapeo de giroscopios izquierdo/derecho por juego.

Ajuste de intensidad de vibración del mando. 

Opción de reseteo de fábrica que borra cualquier configuración del mismo.

Y otras opciones más que podrás descubrir por ti mismo. 

### <div align="center"> LeGO Suite Versión App de Escritorio </div>

<div align="center">  <img width="368" height="307" alt="f2" src="https://github.com/user-attachments/assets/e8ab1454-5ddc-4f9e-9cd4-84a83304eb3e" /> </div>

### Installation

```bash
curl -L https://github.com/IoannesC/Lego-Suite/releases/latest/download/LeGO-Suite-Desktop-v0.200.zip -o /tmp/lego-desktop.zip && \
mkdir -p /tmp/lego-desktop && \
unzip -o /tmp/lego-desktop.zip -d /tmp/lego-desktop && \
bash /tmp/lego-desktop/desktop/install_desktop_app.sh && \
rm -rf /tmp/lego-desktop /tmp/lego-desktop.zip
```

Ofrece la misma funcionalidad del plugin, pero sin perfiles específicos. Utiliza y modifica el perfil predeterminado del Gamescope al estar en el escritorio y poder modificar en tiempo real el mismo (Si utilizamos aplicaciones de diseño o productividad que requieren cierta potencia, y no queremos regresar a Decky). En el apartado Pantalla, puede inyectar las coordenadas correctas de la pantalla de la Legion Go, para utilizarla como Tablet y activar el giro automático según la posición de la misma.

## Agradecimientos y Créditos (Credits & Acknowledgments)

Este proyecto se basa e inspira en el excelente trabajo de la comunidad de Decky Loader y desarrolladores de herramientas para Linux y Lenovo Legion Go:

- **[SimpleDeckyTDP](https://github.com/aarron-lee/SimpleDeckyTDP)** por [Aarron Lee](https://github.com/aarron-lee) — Arquitectura base de control térmico, TDP, curvas de ventilador y estructura original del plugin.
- **[LegionGoRemapper](https://github.com/aarron-lee/LegionGoRemapper)** por [Aarron Lee](https://github.com/aarron-lee) — Protocolo de comunicación HID de mandos, perfiles de remapeo y control de anillos RGB.
- **[All-Ways-EGPU](https://github.com/egpu-io/all-ways-egpu)** — Por la lógica, detección y gestión de GPU externa (eGPU) en Linux.
- **[Decky Loader](https://github.com/SteamDeckHomebrew/decky-loader)** — Por la plataforma, API y entorno para plugins en SteamOS / Bazzite.
- **[RyzenAdj](https://github.com/FlyGoat/RyzenAdj)** — Por las herramientas y biblioteca de gestión de energía para procesadores AMD Ryzen.
- **Handheld Daemon (HHD) / InputPlumber** — Por el soporte de emulación de mandos, perfiles y drivers en Linux.

Muchas gracias a todos los autores, mantenedores y contribuidores de estos proyectos de código abierto.

</details>
