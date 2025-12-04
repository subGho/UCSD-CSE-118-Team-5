import requests

VSH_URL = "https://www.virtualsmarthome.xyz/url_routine_trigger/activate.php?trigger=110aeef9-cc0b-43af-9ddc-a64dd6a1b79c&token=bcfb8f78-72cd-473f-920e-979a43c66d57&response=html"

def trigger_alexa_routine():
    try:
        resp = requests.get(VSH_URL, timeout=3)
        resp.raise_for_status()
        print("Triggered Alexa routine successfully.")
    except Exception as e:
        print(f"Failed to trigger Alexa routine: {e}")


trigger_alexa_routine()  