import os
import time
import requests
import xml.etree.ElementTree as ET
import obsws_python as obs

# Configuration
NGINX_RTMP_STATUS_URL = os.getenv("NGINX_RTMP_STATUS_URL", "https://rtmp.example.com/status")
OBS_HOST = os.getenv("OBS_HOST", "192.168.1.39")
OBS_PORT = int(os.getenv("OBS_PORT", 4455))  # Default to port 4455
OBS_PASSWORD = os.getenv("OBS_PASSWORD", "")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 5))  # Default to 5 seconds
STREAM_BASE_URL = os.getenv("STREAM_BASE_URL", "rtmp://rtmp.example.com")
SCENE_PREFIX = os.getenv("SCENE_PREFIX", "stream_")  # Default prefix for scenes

def get_active_streams():
    """Fetch active RTMP streams from the NGINX RTMP status."""
    try:
        response = requests.get(NGINX_RTMP_STATUS_URL)
        response.raise_for_status()

        # Parse the XML response
        root = ET.fromstring(response.content)
        streams = []
        for stream in root.findall(".//stream"):
            stream_name = stream.find("name").text
            if stream_name:
                streams.append(stream_name)
        return streams
    except requests.RequestException as e:
        print(f"Error fetching RTMP streams: {e}")
        return None
    except ET.ParseError as e:
        print(f"Error parsing RTMP XML response: {e}")
        return None

def add_vlc_source(client, scene, stream):
    """Add a VLC source to a scene for the given stream."""
    source_name = f"VLC_{stream}"
    source_settings = {
        "playlist": [
            {
                "value": f"{STREAM_BASE_URL}/{stream}",
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
    source_name = f"FFmpeg_{stream}"
    source_settings = {
        "input": f"{STREAM_BASE_URL}/{stream}",
        "is_local_file": False,
        "restart_on_activate": False
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
    for stream in active_streams:
        scene_name = f"{SCENE_PREFIX}{stream}"
        if scene_name not in existing_scenes:
            print(f"Creating scene for stream: {stream}")
            client.create_scene(scene_name)
            add_ffmpeg_source(client, scene_name, stream) 

    for scene in list(existing_scenes):
        if scene.startswith(SCENE_PREFIX) and scene[len(SCENE_PREFIX):] not in active_streams:
            print(f"Removing scene for stream: {scene}")
            client.remove_scene(scene)

def main():
    with obs.ReqClient(host=OBS_HOST, port=OBS_PORT, password=OBS_PASSWORD) as client:
        # Fetch existing scenes
        while True:
            active_streams = get_active_streams()
            if active_streams is not None:
                manage_scenes(client, active_streams)
            time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
