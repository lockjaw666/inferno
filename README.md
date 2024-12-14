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

---

## Run options

`python3 hades.py -h` for available options. For now, use `-b` only. Set other options in `config.json`.

## Example usage

Batch mode `-b` will process entire directory:

`python3 hades.py -b -d "/path/to/artist"`

---

Single mode will process all audio files in a single directory:

`python3 hades.py -d "/path/to/artist/album"`
