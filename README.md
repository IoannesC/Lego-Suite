<img width="1672" height="941" alt="file_000000001834822f9cf25b1021da0124" src="https://github.com/user-attachments/assets/a18d2591-66ca-44b6-80e3-065768210b3a" />

### <div align="center"> <h2> LeGO Suite v0.198 </h2> </div>

LeGO Suite is the all-in-one control suite designed to get the most out of your Legion Go on Linux.

### No direct or indirect affiliation with any registered trademark. It has no affiliation or relationship whatsoever with Lenovo or any other company.

### Disclaimer
The use of this software is at the user's own risk. It comes without any kind of warranty, and the user is solely responsible for all resulting effects and consequences.

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

CSS Loader on Decky and the Color Toggles plugin.

All-Ways-EGPU to use the eGPU in Gamescope without loopback latency when using the GPU's HDMI output (CachyOS).

### Notes on v0.198:
It has been tested and works properly on my **Lenovo Legion Go Gen 1, Z1 Extreme with 16GB of RAM on CachyOS with the LTS kernel.** I do not have access to other devices. If I ever manage to get my hands on another device or another Lenovo machine, I will gladly optimize it for those systems—or alternatively, collaborate with testers who own other machines. For the time being, if you need to test it on a device other than the Lenovo Legion Go Gen 1, please do so at your own initiative.
I would like to add more options and useful features, and I will be implementing them little by little.

### About LeGO Suite:

There are two applications in one: a handy Decky Plugin and a Desktop Application. You can use the Decky plugin without needing to download and install the desktop application. However, both complement each other and offer you even more options.

### <div align="center"> LeGO Suite Decky Plugin Version </div>

<div align="center"> <img width="326" height="449" alt="f1" src="https://github.com/user-attachments/assets/7a841a7f-e3e5-43b3-bef9-b6c555a5b6a4" /> </div>

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

Synchronization with the CSS Loader plugin and the Color Toggles add-on: Sliding the controller LED lighting color (in Solid or Pulse mode) changes the Gamescope UI theme accent color in real time.

**Button and Gyroscope Remapping**: Assignment of back buttons (`Y1`, `Y2`, `Y3`, `M2`, `M3`), Touchpad enable/disable toggle, and per-game left/right gyroscope remapping.

Controller vibration intensity adjustment.

Factory reset option that erases any custom controller configuration.

And many other options for you to discover on your own.

### <div align="center"> LeGO Suite Desktop App Version </div>

<div align="center">  <img width="368" height="307" alt="f2" src="https://github.com/user-attachments/assets/e8ab1454-5ddc-4f9e-9cd4-84a83304eb3e" /> </div>

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
