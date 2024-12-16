import os
import sys
import json
import argparse
import requests
import musicbrainzngs
from mutagen import File
from mutagen.id3 import ID3, TDRC
from torf import Torrent

def load_config(config_file="config.json"):
    """Load configuration from a JSON file."""
    try:
        with open(config_file, "r") as f:
            config = json.load(f)
        return config
    except Exception as e:
        return {}

def setup_musicbrainz(config):
    """Configure the MusicBrainz client using values from config."""
    user_agent = config.get("musicbrainz_user_agent", {})
    name = user_agent.get("name")
    version = user_agent.get("version")
    email = user_agent.get("email")
    musicbrainzngs.set_useragent(name, version, email)

def fetch_album_info(directory, config):
    """Fetch album information using MusicBrainz."""
    file_types = config.get("file_types")
    all_files = []
    for root, _, files in os.walk(directory):
        all_files.extend(os.path.join(root, f) for f in files if any(f.lower().endswith(ext) for ext in file_types))

    files = sorted(all_files)

    if not files:
        raise FileNotFoundError("No supported audio files found in the specified directory.")

    metadata = File(files[0])  # Use the first file to get metadata

    # Handle MP3 files specifically
    if files[0].lower().endswith(".mp3"):
        artist = metadata.get("TPE1", ["Unknown Artist"])[0]  # ID3 tag for artist
        album = metadata.get("TALB", ["Unknown Album"])[0]   # ID3 tag for album
        year = metadata.get("TDRC", ["Unknown Date"])[0]     # ID3 tag for date

        # If year is an ID3TimeStamp, extract just the year
        if isinstance(year, TDRC):
            year = str(year.text[0][:4])  # Extract only the year from the timestamp
        elif isinstance(year, str) and len(year) > 4:  # If it's a string but has extra details
            year = year[:4]  # Trim to just the year
    else:
        # Default FLAC handling
        artist = metadata.get("artist", ["Unknown Artist"])[0] if metadata.get("artist") else "Unknown Artist"
        album = metadata.get("album", ["Unknown Album"])[0] if metadata.get("album") else "Unknown Album"
        year = metadata.get("date", ["Unknown Date"])[0] if metadata.get("date") else "Unknown Date"

    release_id = None
    cover_url = None

    # Search for the release in MusicBrainz
    try:
        result = musicbrainzngs.search_releases(artist=artist, release=album, limit=10)
        for release in result.get("release-list", []):
            release_id = release["id"]
            try:
                cover_art = musicbrainzngs.get_image_list(release_id)
                if cover_art.get("images"):
                    cover_url = cover_art["images"][0].get("image")
                    break
            except musicbrainzngs.WebServiceError:
                continue
    except musicbrainzngs.WebServiceError as e:
        pass

    return artist, album, year, cover_url, files[0].split('.')[-1].upper(), files  # Return file type and list of files

def download_cover_art(url, output_dir):
    """Download album cover art."""
    if not url:
        return None

    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()  # Raise an HTTPError for bad responses
        cover_path = os.path.join(output_dir, "cover.jpg")
        with open(cover_path, "wb") as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
        return cover_path
    except requests.exceptions.RequestException:
        return None

def upload_to_imgbb(imgbb_api_key, image_path, imgbb_url):
    """Upload an image to imgbb and return the formatted URL."""
    if not imgbb_api_key or not os.path.exists(image_path):
        return None

    try:
        with open(image_path, "rb") as f:
            response = requests.post(
                imgbb_url,
                params={"key": imgbb_api_key},
                files={"image": f}
            )
        response.raise_for_status()
        data = response.json()
        img_url = data["data"].get("url")
        thumb_url = data["data"].get("medium", {}).get("url", img_url)
        return f"[url={img_url}][img]{thumb_url}[/img][/url]"
    except requests.exceptions.RequestException:
        return None

def determine_piece_size(directory_size):
    """Determine an optimal piece size based on the directory size."""
    if directory_size <= 50 * 1024 ** 2:  # Up to 50 MiB
        return 32 * 1024  # 32 KiB
    elif directory_size <= 150 * 1024 ** 2:  # 50 MiB to 150 MiB
        return 64 * 1024  # 64 KiB
    elif directory_size <= 350 * 1024 ** 2:  # 150 MiB to 350 MiB
        return 128 * 1024  # 128 KiB
    elif directory_size <= 512 * 1024 ** 2:  # 350 MiB to 512 MiB
        return 256 * 1024  # 256 KiB
    elif directory_size <= 1 * 1024 ** 3:  # 512 MiB to 1 GiB
        return 512 * 1024  # 512 KiB
    elif directory_size <= 2 * 1024 ** 3:  # 1 GiB to 2 GiB
        return 1024 * 1024  # 1 MiB
    else:  # 2 GiB and up
        return 2048 * 1024  # 2 MiB

def calculate_directory_size(directory):
    """Calculate the total size of files in a directory."""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(directory):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size

def generate_track_list(files, output_file, cover_url=None):
    """Generate a text file with track names, lengths, and album cover URL."""
    track_list = []
    disc_tracks = {}
    total_seconds = 0

    for file in files:
        metadata = File(file)
        disc_number = metadata.get("discnumber", ["1"])[0]
        title = metadata.get("title", [os.path.splitext(os.path.basename(file))[0]])[0]
        duration = int(metadata.info.length)
        total_seconds += duration
        minutes, seconds = divmod(duration, 60)
        if disc_number not in disc_tracks:
            disc_tracks[disc_number] = []
        disc_tracks[disc_number].append(f"{len(disc_tracks[disc_number]) + 1}. {title} [{minutes}:{seconds:02d}]")

    total_minutes, total_seconds = divmod(total_seconds, 60)

    # Write the tracklist grouped by disc
    with open(output_file, "w") as f:
        f.write("Tracklist:\n\n")
        if len(disc_tracks) > 1:
            for disc_number, tracks in sorted(disc_tracks.items()):
                f.write(f"Disc {disc_number}:\n")
                f.write("\n".join(tracks))
                f.write("\n\n")
        else:
            for tracks in disc_tracks.values():
                f.write("\n".join(tracks))
                f.write("\n\n")
        f.write(f"Album Length: {total_minutes}:{total_seconds:02d}\n")

        # Add cover URL if available
        if cover_url:
            f.write(f"\n{cover_url}\n")

def create_torrent(directory, output_file, tracker_announce):
    """Generate a .torrent file with dynamic piece size."""
    directory_size = calculate_directory_size(directory)
    piece_size = determine_piece_size(directory_size)

    torrent = Torrent(
        path=directory,
        trackers=[tracker_announce],
        piece_size=piece_size,
        private=True,
    )
    torrent.generate()
    torrent.write(output_file)

def upload_torrent_to_tracker(torrent_path, tracklist_path, artist, album, year, file_type, tracker_api_url, tracker_api_token, anonymous):
    """Upload the generated torrent file to the tracker."""
    try:
        with open(torrent_path, "rb") as torrent_file:
            with open(tracklist_path, "r") as tracklist_file:
                description = tracklist_file.read()

            # Set the type_id dynamically based on file_type
            if file_type.lower() == 'flac':
                type_id = 7  # FLAC
            elif file_type.lower() == 'mp3':
                type_id = 8  # MP3
            else:
                raise ValueError(f"Unsupported file type: {file_type}")

            files = {"torrent": torrent_file}
            data = {
                "name": f"{artist} - {album} {year} {file_type}",
                "description": description,
                "category_id": 3,
                "type_id": type_id,
                "anonymous": anonymous,
                "api_token": tracker_api_token,
                "tmdb": 0,
                "imdb": 0,
                "tvdb": 0,
                "mal": 0,
                "igdb": 0,
                "stream": 0,
                "sd": 0
            }
            headers = {
                "Authorization": f"Bearer {tracker_api_token}",
                "Accept": "application/json"
            }
            response = requests.post(tracker_api_url, data=data, files=files, headers=headers)
            
            if response.status_code == 200:
                # Parse the JSON response and extract the URL
                response_data = response.json()
                torrent_url = response_data.get("data")
                
                if torrent_url:
                    print(f"Uploaded Torrent: {torrent_url}")
                else:
                    print("Error: No torrent URL returned.")
            elif response.status_code == 404 and 'info_hash' in response.json().get('data', {}):
                # Handle case where torrent already exists
                print("Upload Error: This torrent already exists on the tracker.")
            else:
                print(f"Failed to upload torrent: {response.status_code} - {response.json()}")
    except Exception as e:
        print(f"Error uploading torrent: {e}")

def process_album(directory, config, output_base, tracker_announce, tracker_api_url, tracker_api_token, anonymous):
    try:
        # Fetch album info and set up output directory
        artist, album, year, cover_url, file_type, files = fetch_album_info(directory, config)
        print(f"\n{'#' * 30}\n{artist} - {album} - {year}\n{'-' * 30}")
    except Exception as e:
        print(f"\n{'#' * 30}\nError processing album in directory: {directory} - {str(e)}\n{'#' * 30}")
        return

    output_dir = os.path.join(output_base, artist, f"{album} ({year})")
    os.makedirs(output_dir, exist_ok=True)

    # Download the cover art if available
    cover_path = None
    if cover_url:
        try:
            cover_path = download_cover_art(cover_url, output_dir)
            if cover_path:
                cover_file_name = f"{artist} - {album} - {year}.jpg"
                cover_file_path = os.path.join(output_dir, cover_file_name)
                os.rename(cover_path, cover_file_path)
                print(f"Cover Art: {cover_file_name}")
                # Upload cover art to imgbb
                imgbb_api_key = config.get("imgbb_api_key")
                imgbb_url = config.get("imgbb_url")
                uploaded_cover_url = upload_to_imgbb(imgbb_api_key, cover_file_path, imgbb_url)
            else:
                print("Cover Art: Not Found")
                uploaded_cover_url = None
        except Exception as e:
            print(f"Error downloading cover art: {str(e)}")
            uploaded_cover_url = None

    # Generate tracklist.txt file
    try:
        tracklist_file = os.path.join(output_dir, config.get("tracklist_filename"))
        generate_track_list(files, tracklist_file, cover_url=uploaded_cover_url)
        print(f"Track List: {os.path.basename(tracklist_file)}")
    except Exception as e:
        print(f"Error generating track list for album {album}: {str(e)}")

    # Generate .torrent file with dynamic file type in name
    try:
        torrent_file = os.path.join(output_dir, f"{artist} - {album} - {year} ({file_type}).torrent")
        create_torrent(directory, torrent_file, tracker_announce)
        print(f"Torrent File: {os.path.basename(torrent_file)}")
    except Exception as e:
        print(f"Error creating torrent file for album {album}: {str(e)}")

    # Upload the torrent file to the tracker
    try:
        upload_torrent_to_tracker(torrent_file, tracklist_file, artist, album, year, file_type, tracker_api_url, tracker_api_token, anonymous)
    except Exception as e:
        print(f"Error uploading torrent for album {album}: {str(e)}")

    print(f"{'#' * 30}\n")

def batch_process(artist_directory, config, output_base, tracker_announce, tracker_api_url, tracker_api_token, anonymous):
    # Process all albums in the artist directory
    for album_dir in os.listdir(artist_directory):
        album_path = os.path.join(artist_directory, album_dir)
        if os.path.isdir(album_path):
            process_album(album_path, config, output_base, tracker_announce, tracker_api_url, tracker_api_token, anonymous)

def main():
    # Load configuration from config.json
    config = load_config()

    # Setup MusicBrainz with the configuration
    setup_musicbrainz(config)

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Generate a .torrent file and metadata for audio files.")
    parser.add_argument("-d", "--directory", help="Path to the directory containing audio files or an artist directory.")
    parser.add_argument("-b", "--batch", action="store_true", help="Batch process all albums in an artist directory.")
    parser.add_argument("-o", "--output", help="Output directory.")
    parser.add_argument("-t", "--tracker", help="Tracker. Mandatory.")
    parser.add_argument("-anon", "--anonymous", action="store_true", help="Set upload as anonymous.")
    args = parser.parse_args()

    # Fallback if no config value or command line argument is provided
    directory = args.directory
    tracker_name = args.tracker
    tracker_config = config.get("trackers", {}).get(tracker_name)

    if not tracker_config:
        print(f"Error: Tracker flag must be provided or provided tracker code is incorrect.")
        sys.exit(1)

    tracker_announce = tracker_config.get("tracker_announce")
    tracker_api_url = tracker_config.get("tracker_api_url")
    tracker_api_token = tracker_config.get("tracker_api_token")

    output_base = args.output or config.get("output_dir") or os.getcwd()

    # Set the 'anonymous' value based on the flag
    anonymous = 1 if args.anonymous else 0

    if args.batch:
        batch_process(directory, config, output_base, tracker_announce, tracker_api_url, tracker_api_token, anonymous)
    else:
        process_album(directory, config, output_base, tracker_announce, tracker_api_url, tracker_api_token, anonymous)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nUser stopped script execution.")
        sys.exit(0)  # Ensure a clean exit with status 0
