# INFERNO
FLAC/MP3 Audio Uploader for UNIT3D Trackers.


**NOTE:** This is a personal tool developed to do things quick and dirty. While there is little to no error checking, script will try to correct certain things. That being said, it is your responsibility to check everything and make sure what you upload is correct.


## Features

* Extracts Vorbis/ID3 tags from FLAC/MP3 files
* Check for existing cover art (cover.jpg)
* Downloads album cover art from MusizBrainz
* Uploads album cover art to imgbb.com
* Generates text file with all gathered information
* Generates `.torrent` file
* Uploads torrent via tracker API
* Auto-inject torrent URL into qBittorrent
* Anonymous and non-anonymous uploads
* Single album processing or batch all
* Set tracker options (personal release, double upload)
* Handling of multi-disc albums
* Generate and upload `mediainfo` with torrent file (requires MediaInfo installation)
* Options configurable via `config.toml`
* Supports Linux and MacOS (Windows: ¯\\_(ツ)_/¯ )

---

## Installation

1. Clone/download the repository
2. Place in whichever directory works for you
3. Install dependencies `pip3 install -r requirements.txt`
4. Edit `./config/config.toml`


## Run options

`python3 inferno.py -h` for available options.

For now, use `-b`, `-anon`, `-t`, `-pr`, `-du`, `-s`, `-br`, `-i` only. Set other options in `./config/config.toml`.

## Example usage

* Single (default) mode will process all audio files in a single directory:

  `python3 inferno.py -t trk -d "/path/to/artist/album"`

* Batch mode `-b` will process entire artist directory:

  `python3 inferno.py -t trk -b -d "/path/to/artist"`

* If provided `-anon` parameter will set the upload as anonymous:

  `python3 inferno.py -anon -t trk -b -d "/path/to/artist"`

* If provided `-i` parameter will auto-inject torrent to qBittorrent:

  `python3 inferno.py -i -anon -t trk -b -d "/path/to/artist"`

## Example terminal output

Successful Upload:
```
##############################
Artist - Album - Year
------------------------------
Cover Art: Artist - Album - Year.jpg
Track List: tracklist.txt
Torrent File: Artist - Album - Year (FLAC).torrent
Uploaded Torrent: https://tracker.com/torrent/download/1234567890
##############################
```
Duplicate torrent:
```
##############################
Artist - Album - Year
------------------------------
Cover Art: Artist - Album - Year.jpg
Track List: tracklist.txt
Torrent File: Artist - Album - Year (FLAC).torrent
Upload Error: This torrent already exists on the tracker.
##############################
```

## Example tracklist.txt

Script will get links for medium and full size images for display

```
Tracklist:

1. Track 1 [3:48]
2. Track 2 [4:39]
3. Track 3 [3:59]
4. Track 4 [2:58]
5. Track 5 [4:44]
6. Track 6 [4:49]
7. Track 7 [2:57]
8. Track 8 [3:53]

Album Length: 31:47

[url=https://i.ibb.co/DXxg/Artist-Album-Year.jpg][img]https://i.ibb.co/pf9T/Artist-Album-Year.jpg[/img][/url]
```
