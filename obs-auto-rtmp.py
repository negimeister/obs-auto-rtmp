import os
import time
import requests
import xml.etree.ElementTree as ET
import obsws_python as obs

# Configuration
NGINX_RTMP_STATUS_URL = os.getenv("NGINX_RTMP_STATUS_URL", "https://rtmp.example.com/status")
SRT_STATUS_URL = os.getenv("SRT_STATUS_URL", "https://srt.example.com/streams")
OBS_HOST = os.getenv("OBS_HOST", "192.168.1.39")
OBS_PORT = int(os.getenv("OBS_PORT", 4455))  # Default to port 4455
OBS_PASSWORD = os.getenv("OBS_PASSWORD", "")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 5))  # Default to 5 seconds
RTMP_BASE_URL = os.getenv("RTMP_BASE_URL", "rtmp://rtmp.example.com")
SRT_BASE_URL = os.getenv("SRT_BASE_URL", "srt://srt.example.com?streamid=play/")
SCENE_PREFIX = os.getenv("SCENE_PREFIX", "stream_")  # Default prefix for scenes

def get_rtmp_streams():
    """Fetch active RTMP streams from the NGINX RTMP status."""
    print("Fetching active RTMP streams...")
    try:
        response = requests.get(NGINX_RTMP_STATUS_URL)
        response.raise_for_status()

        # Parse the XML response
        root = ET.fromstring(response.content)
        streams = []
        for stream in root.findall(".//stream"):
            stream_name = stream.find("name").text
            if stream_name:
                streams.append({"name": stream_name, "url": f"{RTMP_BASE_URL}/{stream_name}"})
        print(f"Active streams: {streams}")
        return streams
    except requests.RequestException as e:
        print(f"Error fetching RTMP streams: {e}")
        return None
    except ET.ParseError as e:
        print(f"Error parsing RTMP XML response: {e}")
        return None

def get_srt_streams():
    """Fetch active SRT streams from a status server returning JSON."""
    try:
        response = requests.get(SRT_STATUS_URL)
        response.raise_for_status()
        data = response.json()
        streams = []
        for entry in data:
            stream_name = entry.get("name")
            if stream_name:
                streams.append({"name": stream_name, "url": f"{SRT_BASE_URL}{stream_name}"})
        return streams
    except requests.RequestException as e:
        print(f"Error fetching SRT streams: {e}")
        return []
    except ValueError as e:
        print(f"Invalid JSON from SRT server: {e}")
        return []

def add_vlc_source(client, scene, stream):
    """Add a VLC source to a scene for the given stream."""
    source_name = f"VLC_{stream}"
    source_settings = {
        "playlist": [
            {
                "value": stream.url,
                "hidden": False
            }
        ],
        "loop": True,
        "playback_behavior": "always_play"
    }
    try:
        client.create_input(
            sceneName=scene,
            inputName=source_name,
            inputKind="vlc_source",
            inputSettings=source_settings,
            sceneItemEnabled=True
        )
        client.set_input_audio_monitor_type(source_name, "OBS_MONITORING_TYPE_MONITOR_AND_OUTPUT")
        print(f"Added VLC source '{source_name}' to scene '{scene}'")
    except Exception as e:
        print(f"Failed to add VLC source '{source_name}' to scene '{scene}': {e}")
        client.remove_scene(scene)

def add_ffmpeg_source(client, scene, stream):
    """Add an FFmpeg source to a scene for the given stream."""
    print(f"Adding FFmpeg source for stream: {stream['name']}")
    source_name = f"FFmpeg_{stream['name']}"
    source_settings = {
        "input": stream["url"],
        "is_local_file": False,
        "restart_on_activate": False,
         "buffering_mb": 6
    }
    try:
        client.create_input(
            sceneName=scene,
            inputName=source_name,
            inputKind="ffmpeg_source",
            inputSettings=source_settings,
            sceneItemEnabled=True,
        )
        client.set_input_audio_monitor_type(source_name, "OBS_MONITORING_TYPE_MONITOR_AND_OUTPUT")
        print(f"Added FFmpeg source '{source_name}' to scene '{scene}'")
    except Exception as e:
        print(f"Failed to add FFmpeg source '{source_name}' to scene '{scene}': {e}")
        client.remove_scene(scene)




def manage_scenes(client, active_streams):
    """Create or remove scenes in OBS based on active RTMP streams."""
    existing_scenes = set(scene["sceneName"] for scene in client.get_scene_list().scenes)
    print(f"active streams: {active_streams}")
    print(f"Existing scenes: {existing_scenes}")
    for stream in active_streams:
        print(f"Processing stream: {stream}")
        scene_name = f"{SCENE_PREFIX}{stream['name']}"
        if scene_name not in existing_scenes:
            print(f"Creating scene for stream: {stream}")
            client.create_scene(scene_name)
            add_ffmpeg_source(client, scene_name, stream) 

    for scene in list(existing_scenes):
        if scene.startswith(SCENE_PREFIX) and scene[len(SCENE_PREFIX):] not in [s["name"] for s in active_streams]:
            print(f"Removing scene for stream: {scene}")
            client.remove_scene(scene)

def main():
    print("Connecting to OBS")
    with obs.ReqClient(host=OBS_HOST, port=OBS_PORT, password=OBS_PASSWORD) as client:
        print("Connected to OBS")
        # Fetch existing scenes
        while True:
            active_streams = get_rtmp_streams() + get_srt_streams()
            if active_streams is not None:
                manage_scenes(client, active_streams)
            time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
