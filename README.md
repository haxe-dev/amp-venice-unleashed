# AMP template: Battlefield 3 (Venice Unleashed)

Generic-module template for [CubeCoders AMP](https://cubecoders.com/AMP) that runs a
[Venice Unleashed](https://veniceunleashed.net) Battlefield 3 dedicated server under Wine
(AMP's `cubecoders/ampbase:wine-stable` container on Linux).

## Usage

1. In ADS → Settings → Instance Deployment → Configuration Repositories add
   `haxe-dev/amp-venice-unleashed:main`, then fetch templates.
2. Create an instance from **Battlefield 3 (Venice Unleashed)** (container recommended) and run **Update**.
3. Upload your full, up-to-date Battlefield 3 installation into `venice-unleashed/bf3/`
   (`bf3.exe` directly inside).
4. Create a server key at <https://veniceunleashed.net/keys> and upload it as
   `venice-unleashed/instance/server.key`.
5. Activate BF3: on a PC with the EA app run `vu.exe -activate -lsx`, copy the token between the
   single quotes and paste it into the **EA Activation Token** setting. It is used on the next start.
6. Set an admin/RCON password, edit `venice-unleashed/instance/Admin/MapList.txt` / `ModList.txt`, start.

Ports: 25200/UDP (game), 7948/UDP (Harmony), 47200/TCP (RCON, e.g. Procon).

See the official hosting docs: <https://docs.veniceunleashed.net/hosting/prereq/>
