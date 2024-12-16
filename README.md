# HADES
FLAC/MP3 Audio Uploader for UNIT3D Trackers


## Features

* Extracts Vorbis/ID3 tags from FLAC/MP3 files
* Downloads album cover art from MusizBrainz
* Uploads album cover art to imgbb.com
* Generates text file with all gathered information
* Generates `.torrent` file
* Uploads torrent via tracker API
* Anonymous and non-anonymous uploads
* Single album processing or batch all
* Handling of multi-disc albums
* Options configurable via `config.json`
* Supports Linux and MacOS (Windows: ¯\\_(ツ)_/¯ )

---

## Installation

1. Clone/download the repository
2. Place in whichever directory works for you
3. Install dependencies `pip3 install -r requirements.txt`
4. Edit `config.json`


## Run options

`python3 hades.py -h` for available options.

For now, use `-b`, `-anon` and `-t` only. Set other options in `config.json`.

## Example usage

* Single (default) mode will process all audio files in a single directory:

  `python3 hades.py -t trk -d "/path/to/artist/album"`

* Batch mode `-b` will process entire artist directory:

  `python3 hades.py -t trk -b -d "/path/to/artist"`

* If provided `-anon` flag will set the upload as anonymous:

  `python3 hades.py -anon -t trk -b -d "/path/to/artist"`

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
