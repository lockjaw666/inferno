# + INFERNO +
FLAC/MP3 Audio Uploader for UNIT3D Trackers.


**NOTE:** This is a personal tool developed to do things quick and dirty. While there is little to no error checking, script will try to correct certain things. That being said, it is your responsibility to check everything and make sure what you upload is correct.


## Features

* Extracts Vorbis/ID3 tags from FLAC/MP3 files
* Check for existing cover art (cover.jpg etc.)
* Downloads album cover art from MusizBrainz
* Uploads album cover art to imgbb.com
* Generates text file with all gathered information
* Generates `.torrent` file
* Uploads torrent via tracker API
* Per tracker upload template
* Auto-inject torrent URL into qBittorrent
* Anonymous and non-anonymous uploads
* Single album processing or batch all
* Set tracker options (personal release, double upload etc.)
* Handling of multi-disc albums
* Generate and upload `mediainfo` with torrent file (requires MediaInfo installation)
* Dry Run mode
* Options configurable via `config.toml`
* Supports Linux and MacOS (Windows: ¯\\_(ツ)_/¯ )

---

## Installation

1. Clone/download the repository
2. Place in whichever directory works for you
3. Install dependencies `pip3 install -r requirements.txt`
4. Edit `./config/config.toml`
5. Install `MediaInfo`
   * Linux: `apt install madiainfo`
   * MacOS: [MediaInfo CLI](https://mediaarea.net/en/MediaInfo/Download/Mac_OS)

## Run options

`python3 inferno.py -h` for available options.

 Set other options in `./config/config.toml`.

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
+ Artis - Album Year +
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[+] - Cover Art: Uploaded existing cover art
[+] - Track List: tracklist.txt
[+] - Torrent File: Artist - Album - Year (FLAC).torrent
[+] - Uploaded Torrent: https://tracker.com/torrent/download/xxx
[+] - Torrent added to qBittorrent
```
Duplicate torrent:
```
+ Artis - Album Year +
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[+] - Cover Art: Uploaded existing cover art
[+] - Track List: tracklist.txt
[+] - Torrent File: Artist - Album - Year (FLAC).torrent
[-] - Upload Error: This torrent already exists on the tracker.
```
Dry Run mode:
```
+ Artis - Album Year +
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[DRY RUN] - Output Directory: /path/to/output/directory
[DRY RUN] - Cover Art: /path/to/album/directory/cover.jpg
[DRY RUN] - Tracklist: /path/to/output/directory
[DRY RUN] - Torrent File: 'Artist - Album Year CD FLAC Lossless.torrent'
[DRY RUN] - Upload Torrent: 'Artist - Album Year CD FLAC Lossless.torrent'
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

## Supported trackers

* [YOiNKED](https://yoinked.org)
* [FearNoPeer](https://fearnopeer.com)
* [Aither](https://aither.cc) - Coming soon
