# A Virtual Turntable

Univeristy of Manchester - Third Year Project (COMP30040)

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
- Python
- mp4a.40.2 codec (included in Windows)

### Server

```bash
$ cd ./server
$ python3 -m venv ./.venv/virtual-turntable/
$ source ./.venv/virtual-turntable/bin/activate
$ pip install -r requirements.txt
```
note: use `python` for Windows systems.

### Client

```bash
$ cd ./client
$ bun install
```

#### Note for Linux users!
The Spotify Web Playback SDK (used in the client application) requires a mp4a.40.2 audio codec to function. This is not included by default in many Linux dsitros (such as Ubuntu).

You will see the following warning in the browser console, and be unable to play audio:
```
Cannot play media. No decoders for requested formats: audio/mp4; codecs="mp4a.40.2", audio/mp4; codecs="mp4a.40.2"
```

To fix this:
```bash
$ sudo apt update
$ sudo apt install ubuntu-restricted-extras
```

## Usage

```bash
$ ./dev.sh
```
note: use `dev.bat` for Windows, _although_, this project is designed for use primary with a Raspberry Pi (especially the server module), and hence it is recommended to use Linux.

**or**

```bash
$ cd ./server
$ source ./.venv/virtual-turntable/bin/activate
$ python3 ./runner.py
```

```bash
$ cd ./client
$ bun run dev
```
