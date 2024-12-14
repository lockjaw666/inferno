# HADES
FLAC Audio Uploader for UNIT3D Trackers


## Features

* Extracts Vorbis tags from FLAC files
* Downloads album cover art from MusizBrainz
* Uploads album cover art to imgbb.com
* Generates text file with all gathered information
* Generates `.torrent` file
* Uploads torrent via tracker API
* Single album processing or batch all
* Options configurable via `config.json`
* Supports Linux and MacOS (Windows: ¯\\_(ツ)_/¯ )

---

## Installation

1. Clone/download the repository
2. Place in whichever directory works for you
3. Install dependencies `pip3 install -r requirements.txt`
4. Edit `config.json`


## Run options

`python3 hades.py -h` for available options. For now, use `-b` only. Set other options in `config.json`.

## Example usage

Single (default) mode will process all audio files in a single directory:

`python3 hades.py -d "/path/to/artist/album"`

Batch mode `-b` will process entire directory:

`python3 hades.py -b -d "/path/to/artist"`

## Example terminal output

Successful Upload:

##############################
Weezer - Maladroit - 2002
------------------------------
Cover Art: Weezer - Maladroit - 2002.jpg
Track List: tracklist.txt
Torrent File: Weezer - Maladroit - 2002 (FLAC).torrent
Uploaded Torrent: https://tracker.com/torrent/download/1234567890
##############################

Duplicate torrent:

##############################
Weezer - Maladroit - 2002
------------------------------
Cover Art: Weezer - Maladroit - 2002.jpg
Track List: tracklist.txt
Torrent File: Weezer - Maladroit - 2002 (FLAC).torrent
Upload Error: This torrent already exists on the tracker.
##############################

