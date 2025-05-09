# A Virtual Turntable

University of Manchester - Third Year Project (COMP30040)

## Brief

Written by **Sean Bechhofer**: https://studentnet.cs.manchester.ac.uk/ugt/year3/project/projectbookdetails.php?projectid=55259

> Vinyl is back! According to the [NME](https://www.nme.com/news/music/uk-vinyl-sales-2023-reach-highest-level-since-1990-3563676), UK sales of vinyl in 2023 were the highest seen since 1990. Vinyl has always remained popular among niche genres, but we are also seeing mainstream artists like Taylor Swift and Lana Del Ray releasing, and selling large volumes of albums on the format. Vinyl records have also recently been added in to the ONS "Basket of Goods and Services": a carefully selected set of items representative of the goods and services that UK consumers typically spend their money on ([ONS](https://www.ons.gov.uk/news/news/arecordrevivalthatscookingupastormvinylmusicandairfryersspintheirwayintothebasketofgoods)).
>
> Fans of the format claim better sound reproduction, with a fuller frequency range and a "warmth" lacking in digital formats such as CD. Playing vinyl requires specialist equipment: while the ritual of putting a disc on the turntable and dropping the needle is, for some, part of the experience, it can also be seen as an inconvenience.
>
> The aim of this project will be to develop an application that supports a blending of the physical and digital worlds. A physical artefact such as an LP is scanned using a camera. The information on the label or cover is then used to identify the release which can be played. This content could be retrieved from a streaming service such as Spotify or Apple Music, an artist site such as Bandcamp [Bandcamp](https://bandcamp.com/), or the user's own personal media library. This would then allow a user to "play" their records without a turntable. Although the audio quality may not match that of vinyl, such an application would appeal to those who like to collect vinyl for its own sake, or who appreciate the larger format artwork that comes with an old school LP. The application could run on a mobile phone or specialist hardware such as a Raspberry Pi equipped with a camera.
> Example methods that could be used for identification of the release include bar codes, QR codes or OCR acting on label text.
>
> For a stretch goal, the application could be extended to cover other media: the cassette tape ([Guardian](https://www.theguardian.com/music/2023/apr/20/fun-way-consume-music-why-sales-of-cassette-tapes-soaring)) is also experiencing a come back, although the [eight-track](https://en.wikipedia.org/wiki/8-track_cartridge) is unlikely to be retrieved from the dustbin of history.
> The project should be considered as challenging. It will require integration of several technologies and some creativity.

# Application
## Installation

### Prerequisites

- bun
```bash
$ curl -fsSL https://bun.sh/install | bash
```
- Python
- Caddy
```bash
$ sudo apt install caddy
```
- mp4a.40.2 codec (already included by default in Windows)

- [Spotify Developer Application](https://developer.spotify.com/dashboard)
  - Spotify Premium account required to use the Web Playback SDK
  - Non-local redirect URI should be setup for network hosting
- [Discogs API v2 Application](https://www.discogs.com/settings/developers) (optional)
- a web browser with DRM support

### Server

```bash
$ cd ./server
$ python3 -m venv ./.venv/virtual-turntable/
$ source ./.venv/virtual-turntable/bin/activate
$ pip install -r requirements.txt
```

### Client

```bash
$ cd ./client
$ bun install
```

### Certificates

You will need to configure:
1. Update `Caddyfile` to have `<yourHostName>.local`
2. Update references in the code from `raspjerrypi.local` to the above
    - `process.env.HOST_NAME` in `./client/vite.config.ts` 
    - `HOSTNAME` in `./server/.env`
3. Configure a redirect URI in the Spotify Dev Dashboard to support `https://<yourHostName>.local/virtual-turntable/auth/callback`

### Notes

<details><summary>Note for Raspberry Pi users!</summary>

#### DRM Access
The Raspberry Pi uses an ARM-based architecture, meaning **official Widevine builds** are not available for browsers like Firefox. This affects the ability to play DRM-protected content such as Spotify's SDK, as used in this project.

Widevine is a **proprietary DRM technology** developed by **Google**, and no official support exists for ARM64 Linux systems. While Widevine is not officially available for ARM64 Linux, some users have successfully adapted aarch64 builds from ChromeOS images using tools like **[Asahi Linux's Widevine Installer](https://github.com/AsahiLinux/widevine-installer)**.

**Note:** This information is provided for awareness only. Users should ensure they comply with all relevant terms and conditions of the services they use.

<details><summary>Note for non-Raspbian users</summary>

#### GPIO Permissions
When using a non-Raspbian OS, such as Ubuntu, the Raspberry Pi's GPIO pins are not immediately accessible, so the `lgpio` library is used to expose them. However, this will require the python file to be run using `sudo`, to have sufficient permissions. This causes conflicts with `venv`'s localised instance configuration. This can be fixed, by setting up a configuration group:
```bash
$ sudo apt install python3-lgpio
$ pip install lgpio
$ sudo apt install rpi.gpio-common
$ sudo adduser "${USER}" dialout
$ sudo reboot
```

</details>
<hr />
</details>

<details><summary>Note for Linux users</summary>

#### Audio Codec
The Spotify Web Playback SDK (used in the client application) requires a mp4a.40.2 audio codec to function (in Firefox, at least). This is not included by default in many Linux distros (such as Ubuntu).

You will see the following warning in the browser console, and be unable to play audio:
```
Cannot play media. No decoders for requested formats: audio/mp4; codecs="mp4a.40.2", audio/mp4; codecs="mp4a.40.2"
```

To fix this:
```bash
$ sudo apt update
$ sudo apt install ubuntu-restricted-extras
```
<hr />
</details>

<details><summary>Note for Windows users</summary>

#### General Usage
This project is desgined specifically to run on a Raspberry Pi running any Linux OS. It may be useful to run this program on Windows for development purposes, with limited functionality (no hardware control, etc.).

In order to do this, you will need to:
- use `python` instead of `python3` in below instructions.
- use `./dev.bat` instead of `./dev.sh` to boot the program.
- use `./.venv/virtual-turntable/Scripts/activate` to enter venv.
- follow the other steps under this note.

#### Mocking LGPIO
The `lgpio` library stands for **Linux** General-Purpose Input/Output. As such, it is not functionally available for Windows systems. In order to avoid missing library errors, you can install a prebuilt mock version for Windows.

```bash
$ pip install --only-binary :all: lgpio
```

Additionally, you will want to set the server to not instantiate its `PiController` class, as this will cause runtime errors on Windows. To do so, append the following flag to the server's `.env` file.

```py
GPIO_ACCESS='off'
```

<hr />
</details>

### APIs
This project makes use of multiple APIs, including:
- [Spotify Web Playback SDK](https://developer.spotify.com/documentation/web-playback-sdk/) and [Spotify Web API](https://developer.spotify.com/documentation/web-api/)
  - Finding and playing music
  - **Essential!**
- [Discogs API v2](https://www.discogs.com/developers)
  - Finding additional data (such as centre labels) of albums
  - *Optional!*
- [Cover Art Archive](https://musicbrainz.org/doc/Cover_Art_Archive/API)
  - Training data for the album-detection model
  - *Only needed for training models*

The keys required by these APIs can be found in the `./server/.env` and `./client/.env` files. Enter your keys here.

## Usage

### Running the Application

```bash
$ sudo caddy run
```
**Note:** you may need to stop caddy if it is already running under `systemctl`, or, you can add this repo's `Caddyfile` to the root config.

```bash
$ cd ./server
$ source ./.venv/virtual-turntable/bin/activate
$ python3 ./runner.py
```

```bash
$ cd ./client
$ bun run dev
```

When accessing the client application, you will be warned with a `SEC_ERROR_UNKNOWN_ISSUER` error. This is because in order to allow DRM-content and secure media functions, HTTPS/WSS is required, and this is achieved by using Caddy's self-signed certificates, which are not automatically trusted. You can either manually [entrust Caddy as a CA](https://caddyserver.com/docs/automatic-https) on each device, or you can authorise your browser to make an exception, as if it were a dev environmnet.
