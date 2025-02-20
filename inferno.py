import os
import sys
import shutil
import subprocess
import tomli
import argparse
import requests
import musicbrainzngs
from mutagen import File
from torf import Torrent

# Load configuration from a TOML file in the 'config' directory
def load_config():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_file = os.path.join(base_dir, "config", "config.toml")
    try:
        with open(config_file, "rb") as f:
            config = tomli.load(f)
        return config
    except Exception as e:
        log_message(f"Error loading config: {e}", level="ERROR")
        return {}

# Load tracker specific dynamic configurations
def get_tracker_config(config, tracker_name):
    trackers = config.get("trackers", {})
    return trackers.get(tracker_name, {})

# Logo function
def inferno_logo():
    """Display ASCII logo from a text file."""
    config = load_config()
    logo_file = config.get("inferno_logo")

    try:
        with open(os.path.join(logo_file), "r") as f:
            print(f.read())
    except FileNotFoundError:
        log_message("Logo file 'config/logo.txt' not found.", level="ERROR")

# Log setup and formatting
def log_message(message, level="SUCCESS", dry_run=False):
    levels = {
        "INFO": "[i] -",
        "WARNING": "[w] -",
        "ERROR": "[-] -",
        "SUCCESS": "[+] -",
        "DRY RUN": "[DRY RUN] -"
    }
    prefix = levels.get(level, "[INFO]")
    print(f"{prefix} {message}")

# Extract media info from first file using mediainfo
def get_media_info(file_path):
    try:
        result = subprocess.run(["mediainfo", file_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return result.stdout
    except Exception as e:
        log_message(f"Error extracting media info from {file_path}: {e}", level="ERROR")
        return None

# Clear the contents of the output directory if the setting is enabled.
def clear_output_directory(output_dir):
    if not os.path.exists(output_dir):
        log_message(f"Output directory '{output_dir}' does not exist. Skipping clearing.", level="INFO")
        return

    try:
        for root, dirs, files in os.walk(output_dir):
            for file in files:
                os.remove(os.path.join(root, file))
            for dir in dirs:
                shutil.rmtree(os.path.join(root, dir))
        log_message(f"Cleared contents of output directory: {output_dir}", level="SUCCESS")
    except Exception as e:
        log_message(f"Error while clearing output directory '{output_dir}': {e}", level="ERROR")

# Inject torrent URL in qBittorrent with options
def qb_inject(config, torrent_url, directory, dry_run=False):
    if dry_run:
        log_message(f"Simulating torrent injection to qBittorrent with URL: {torrent_url}", level="INFO", dry_run=True)
        return
    
    qb_url = config['qBittorrent']['qb_url']
    username = config['qBittorrent']['username']
    password = config['qBittorrent']['password']
    category = config['qBittorrent']['category']
    tags = config['qBittorrent']['tags']
    paused = config['qBittorrent']['paused']

    # Set custom save path with config file. Uncomment and edit below and "save_path" in config/config.toml
    # save_path_template = config['qBittorrent']['save_path']
    # save_path = save_path_template.format(artist=artist, file_type=file_type.lower())

    # Set save path to album parent directory (ex. /downloads/music/artist/). Comment this if using config.toml for path
    save_path = os.path.dirname(directory)

    # Create a session to maintain cookies
    session = requests.Session()

    # Perform the login
    login_data = {'username': username, 'password': password}
    login_response = session.post(f'{qb_url}/api/v2/auth/login', data=login_data)

    # Add the torrent from the URL
    torrent_data = {
        'urls': torrent_url,
        'savepath': save_path,
        'category': category,
        'tags': tags,
        'paused': paused
    }

    add_torrent_response = session.post(f'{qb_url}/api/v2/torrents/add', data=torrent_data)

    # Check if the torrent was successfully added
    if add_torrent_response.status_code == 200:
        log_message(f"Torrent added to qBittorrent", level="SUCCESS")
    else:
        log_message(f"Failed to add torrent! Status code: {add_torrent_response.status_code}, Response: {add_torrent_response.text}", level="ERROR")

# Configure the MusicBrainz client using values from config
def setup_musicbrainz(config):
    user_agent = config.get("musicbrainz", {})
    name = user_agent.get("name")
    version = user_agent.get("version")
    email = user_agent.get("email")
    musicbrainzngs.set_useragent(name, version, email)

# Fetch album information using MusicBrainz
def fetch_album_info(directory, config):
    file_types = config.get("file_types")
    all_files = []
    for root, _, files in os.walk(directory):
        all_files.extend(os.path.join(root, f) for f in files if any(f.lower().endswith(ext) for ext in file_types))

    files = sorted(all_files)

    if not files:
        raise FileNotFoundError("No supported audio files found in the specified directory.")

    metadata = File(files[0])
    file_extension = files[0].lower().split(".")[-1]
    # MP3 metadata
    if file_extension == "mp3":
        artist = metadata.get("TPE1", ["Unknown Artist"])[0]
        album = metadata.get("TALB", ["Unknown Album"])[0]
        year = metadata.get("TDRC", ["Unknown Date"])[0]
    # FLAC metadata
    elif file_extension == "flac":
        artist = metadata.get("artist", ["Unknown Artist"])[0]
        album = metadata.get("album", ["Unknown Album"])[0]
        year = metadata.get("date", ["Unknown Date"])[0]
    # M4A metadata
    elif file_extension == "m4a":
        artist = metadata.get("\xa9ART", ["Unknown Artist"])[0]
        album = metadata.get("\xa9alb", ["Unknown Album"])[0]
        year = metadata.get("\xa9day", ["Unknown Date"])[0]

    # If date tag contains full date, convert to 4 digit year
    try:
        year = str(year)
        if len(year) >= 4 and year[:4].isdigit():
            year = year[:4]
        else:
            year = "Unknown Year"
    except (TypeError, ValueError):
        year = "Unknown Year"

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

    return artist, album, year, cover_url, files[0].split('.')[-1].upper(), files

# Check for the existence of cover art based on config
def local_cover_art(directory, valid_cover_art, artist, album):
    # Process valid_cover_art to replace placeholders
    valid_cover_art_processed = [
        name.format(artist=artist, album=album) for name in valid_cover_art
    ]
    
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower() in [name.lower() for name in valid_cover_art_processed]:
                return os.path.join(root, file)
    return None

# Download cover art from MusicBrainz if it doesn't exist locally
def download_cover_art(url, output_dir):
    if not url:
        return None

    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        cover_path = os.path.join(output_dir, "cover.jpg")
        with open(cover_path, "wb") as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
        return cover_path
    except requests.exceptions.RequestException:
        return None

# Upload album cover art to imgBB API
def upload_to_imgbb(imgbb_api_key, image_path, imgbb_url, dry_run=False):
    if dry_run:
        log_message(f"Simulating upload to imgBB for image: {image_path}", level="INFO", dry_run=True)
        return f"[url=DRY_RUN][img=DRY_RUN][/img][/url]"
    
    if not imgbb_api_key or not os.path.exists(image_path):
        return None
    try:
        with open(image_path, "rb") as f:
            response = requests.post(
                imgbb_url,
                params={"key": imgbb_api_key},
                files={"image": f}
            )
        
        # Parse the JSON response
        data = response.json()
        # Check for API rate limit error in the response
        if response.status_code != 200:
            if data.get("status_code") == 400 and data.get("error", {}).get("code") == 100:
                log_message(data["error"]["message"], level="ERROR")
                return None
            log_message("Error:", data.get("error", {}).get("message", "Unknown error"), level="ERROR")
            return None

        img_url = data["data"].get("url")
        thumb_url = data["data"].get("medium", {}).get("url", img_url)
        return f"[url={img_url}][img]{thumb_url}[/img][/url]"
    except requests.exceptions.RequestException as e:
        log_message(e, level="ERROR")
        return None

# Determine optimal piece size based on the directory size. Taken from RED
def determine_piece_size(directory_size):
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

# Calculate the total size of files in a directory
def calculate_directory_size(directory):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(directory):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size

# Generate a text file with track names, lengths, and album cover URL
def generate_track_list(config, files, output_file, cover_url=None):
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

        # Signature line
        signature = config.get("signature")
        f.write(f"{signature}")

# Generate a .torrent file with dynamic piece size
def create_torrent(directory, output_file, tracker_announce, artist, album, year, source, file_type, bitrate):
    directory_size = calculate_directory_size(directory)
    piece_size = determine_piece_size(directory_size)

    torrent = Torrent(
        path=directory,
        trackers=[tracker_announce],
        piece_size=piece_size,
        private=True,
    )

    # Ensure the name is set correctly inside the torrent
    torrent.name = os.path.basename(os.path.abspath(directory))
    torrent.generate()
    torrent.write(output_file)

# Upload torrent to the selected tracker
def upload_torrent(
    torrent_path, tracklist_path, artist, album, year, file_type, tracker_api_url,
    tracker_api_token, anonymous, personal_release, doubleup, internal, refundable, featured, sticky, source, bitrate, tracker_name, config, args, directory, media_info, dry_run=False
):
    if dry_run:
        log_message("Simulating torrent upload to tracker.", level="INFO", dry_run=True)
        return
    
    tracker_config = get_tracker_config(config, tracker_name)
    category_id = tracker_config.get("category_id")
    type_ids = tracker_config.get("type_ids", {})

    try:
        # Set the type_id dynamically based on file_type
        type_id = type_ids.get(file_type.lower())
        if type_id is None:
            raise ValueError(f"Unsupported file type '{file_type}' for tracker '{tracker_name}'")
        
        with open(torrent_path, "rb") as torrent_file:
            with open(tracklist_path, "r") as tracklist_file:
                description = tracklist_file.read()

            files = {"torrent": torrent_file}
            data = {
                "name": f"{artist} - {album} {year} {source} {file_type} {bitrate}",
                "description": description,
                "category_id": category_id,
                "type_id": type_id,
                "anonymous": anonymous,
                "personal_release": personal_release,
                "doubleup": doubleup,
                "internal": internal,
                "refundable": refundable,
                "featured": featured,
                "sticky": sticky,
                "api_token": tracker_api_token,
                "mediainfo": media_info,
                "tmdb": 0,
                "imdb": 0,
                "tvdb": 0,
                "mal": 0,
                "igdb": 0,
                "stream": 0,
                "sd": 0,
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
                    log_message(f"Uploaded Torrent: {torrent_url}", level="SUCCESS")
                    # Inject the torrent URL into qBittorrent
                    if args.inject:
                        qb_inject(config, torrent_url, directory)
                else:
                    log_message("No torrent URL returned.", level="ERROR")
            elif response.status_code == 404 and 'info_hash' in response.json().get('data', {}):
                # Handle case where torrent already exists
                log_message("This torrent already exists on the tracker.", level="WARNING")
            else:
                log_message(f"Torrent Upload: {response.status_code} - {response.json()}", level="ERROR")
    except Exception as e:
        log_message(f"{e}", level="ERROR")

def process_album(directory, tracker_name, config, output_base, tracker_announce, tracker_api_url, tracker_api_token, anonymous, personal_release, doubleup, internal, refundable, featured, sticky, source, bitrate, args):
    try:
        # Fetch album info and set up output directory
        artist, album, year, cover_url, file_type, files = fetch_album_info(directory, config)
        print(f"\n\n+ {artist} - {album} {year} +\n{'━' * 50}")

        # Extract media info for the first track
        first_track_path = files[0]
        media_info = get_media_info(first_track_path)

    except Exception as e:
        log_message(f"\n{'-' * 30}\nAlbum: {directory} - {str(e)}\n{'#' * 30}")
        return

    output_dir = os.path.join(output_base, artist, f"{album} ({year})")
    if not args.dry_run:
        os.makedirs(output_dir, exist_ok=True)
    else:
        log_message(f"Output Directory: {output_dir}", level="DRY RUN")

    # Check if cover art exists in the directory
    valid_cover_art = config.get("valid_cover_art")
    cover_path = local_cover_art(directory, valid_cover_art, artist, album)

    if cover_path:
        if args.dry_run:
            log_message(f"Cover Art: {cover_path}", level="DRY RUN")
        else:
            try:
                uploaded_cover_url = upload_to_imgbb(config.get("imgbb_api_key"), cover_path, config.get("imgbb_url"))
                log_message("Cover Art: Uploaded existing cover art", level="SUCCESS")
            except Exception as e:
                log_message(f"Error uploading local cover art: {str(e)}", level="ERROR")
    else:
        log_message("No local cover art found.", level="DRY RUN", dry_run=args.dry_run)
        if cover_url:
            if args.dry_run:
                log_message(f"Would download: {cover_url}", level="DRY RUN")
            else:
                try:
                    cover_path = download_cover_art(cover_url, output_dir)
                    if cover_path:
                        cover_file_name = f"{artist} - {album} {year}.jpg"
                        cover_file_path = os.path.join(output_dir, cover_file_name)
                        os.rename(cover_path, cover_file_path)
                        uploaded_cover_url = upload_to_imgbb(config.get("imgbb_api_key"), cover_file_path, config.get("imgbb_url"))
                    else:
                        log_message("Cover Art: Not Found", level="ERROR")
                except Exception as e:
                    log_message(f"Error downloading cover art: {str(e)}", level="ERROR")

    # Generate tracklist
    if args.dry_run:
        log_message(f"Tracklist: {output_dir}", level="DRY RUN")
    else:
        try:
            tracklist_file = os.path.join(output_dir, config.get("tracklist_filename"))
            generate_track_list(config, files, tracklist_file, cover_url=uploaded_cover_url)
            log_message(f"Tracklist File: {os.path.basename(tracklist_file)}")
        except Exception as e:
            log_message(f"Error generating track list for album {album}: {str(e)}", level="ERROR")

    # Generate .torrent file with dynamic file type in name
    if args.dry_run:
        log_message(f"Torrent File: '{artist} - {album} {year} {source} {file_type} {bitrate}.torrent'", level="DRY RUN")
    else:
        try:
            torrent_file = os.path.join(output_dir, f"{artist} - {album} {year} {source} {file_type} {bitrate}.torrent")
            create_torrent(directory, torrent_file, tracker_announce, artist, album, year, source, file_type, bitrate)
            log_message(f"Torrent File: {os.path.basename(torrent_file)}")
        except Exception as e:
            log_message(f"Error creating torrent file for album {album}: {str(e)}", level="ERROR")

    # Upload the torrent file to the tracker
    if args.dry_run:
        log_message(f"Upload Torrent: '{artist} - {album} {year} {source} {file_type} {bitrate}.torrent'", level="DRY RUN")
    else:
        try:
            upload_torrent(torrent_file, tracklist_file, artist, album, year, file_type, tracker_api_url, tracker_api_token, anonymous, personal_release, doubleup, internal, refundable, featured, sticky, source, bitrate, tracker_name, config, args, directory, media_info)
        except Exception as e:
            log_message(f"Error uploading torrent for album {album}: {str(e)}", level="ERROR")

def batch_process(artist_directory, tracker_name, config, output_base, tracker_announce, tracker_api_url, tracker_api_token, anonymous, personal_release, doubleup, internal, refundable, featured, sticky, source, bitrate, args):
    # Process all albums in the artist directory
    for album_dir in os.listdir(artist_directory):
        album_path = os.path.join(artist_directory, album_dir)
        if os.path.isdir(album_path):
            process_album(album_path, tracker_name, config, output_base, tracker_announce, tracker_api_url, tracker_api_token, anonymous, personal_release, doubleup, internal, refundable, featured, sticky, source, bitrate, args)

def main():

    # Load configuration from config.json
    config = load_config()

    # Check if the logo should be displayed
    if config.get("display_logo", True):
        inferno_logo()

    # Setup MusicBrainz with the configuration
    setup_musicbrainz(config)

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Audio uploader for UNIT3D trackers.")
    parser.add_argument("-d", "--directory", required=True, help="Path to the directory containing audio files or an artist directory.")
    parser.add_argument("-b", "--batch", action="store_true", help="Batch process all albums in an artist directory.")
    parser.add_argument("-o", "--output", help="Output directory. Defaults to config.json if not specified.")
    parser.add_argument("-t", "--tracker", required=True, help="Tracker name from config.json.")
    parser.add_argument("-anon", "--anonymous", action="store_true", help="Set upload as anonymous. Defaults to non-anonymous, if not specified.")
    parser.add_argument("-s", "--source", required=True, help="Source of the files (e.g., WEB, CD).")
    parser.add_argument("-br", "--bitrate", required=False, help="Bitrate of the files (e.g., V0, 320).")
    parser.add_argument("-pr", "--personal_release", action="store_true", help="Set upload as personal release. Defaults to non-personal release, if not specified.")
    parser.add_argument("-du", "--doubleup", action="store_true", help="Set torrent as double upload. Only available to staff and internal users.")
    parser.add_argument("-in", "--internal", action="store_true", help="Set torrent as internal release. Only available to staff and internal users.")
    parser.add_argument("-re", "--refundable", action="store_true", help="Set torrent as refundable release. Only available to staff and internal users.")
    parser.add_argument("-f", "--featured", action="store_true", help="Set torrent as featured release. Only available to staff and internal users.")
    parser.add_argument("-st", "--sticky", action="store_true", help="Set torrent as sticky release. Only available to staff and internal users.")
    parser.add_argument("-i", "--inject", action="store_true", help="Inject the torrent URL into qBittorrent after upload.")
    parser.add_argument("-dr", "--dry-run", action="store_true", help="Simulate operations without making actual changes.")

    args = parser.parse_args()

    # Fallback if no config value or command line argument is provided
    directory = args.directory
    tracker_name = args.tracker
    tracker_config = config.get("trackers", {}).get(tracker_name)

    if not tracker_config:
        log_message(f"Error: Tracker flag must be provided or provided tracker code is incorrect.", level="WARNING")
        sys.exit(1)

    tracker_announce = tracker_config.get("tracker_announce")
    tracker_api_url = tracker_config.get("tracker_api_url")
    tracker_api_token = tracker_config.get("tracker_api_token")
    output_base = args.output or config.get("output_dir") or os.getcwd()

    # Set the 'anonymous' value based on the flag
    anonymous = 1 if args.anonymous else 0

    # Set the 'personal_release' value based on the flag
    personal_release = 1 if args.personal_release else 0

    # Set the 'doubleup' value based on the flag
    doubleup = 1 if args.doubleup else 0

    # Set the 'internal' value based on the flag
    internal = 1 if args.internal else 0

    # Set the 'refundable' value based on the flag
    refundable = 1 if args.refundable else 0

    # Set the 'featured' value based on the flag
    featured = 1 if args.featured else 0

    # Set the 'sticky' value based on the flag
    sticky = 1 if args.sticky else 0

    if args.batch:
        batch_process(directory, tracker_name, config, output_base, tracker_announce, tracker_api_url, tracker_api_token, anonymous, personal_release, doubleup, internal, refundable, featured, sticky, args.source, args.bitrate, args)
    else:
        process_album(directory, tracker_name, config, output_base, tracker_announce, tracker_api_url, tracker_api_token, anonymous, personal_release, doubleup, internal, refundable, featured, sticky, args.source, args.bitrate, args)

    # Resolve the output directory
    output_base = args.output or config.get("output_dir")
    if not output_base:
        log_message("No output directory specified. Please provide one in the config file or via the '-o' option.", level="ERROR")
        sys.exit(1)

    # Clear the output directory if the setting is enabled
    if config.get("clear_output_dir"):
        clear_output_directory(output_base)

    print(f"\n+ And so we ascend, our task in the Inferno complete +\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n(╯°□°)╯︵ ┻━┻\n")
        sys.exit(0)
