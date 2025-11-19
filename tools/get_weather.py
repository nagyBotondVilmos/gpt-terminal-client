import os
import requests

import os
import requests
import yaml

WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")

def get_weather(location: str) -> str:
    """
    Returns the full weather API response in a structured YAML format.
    """
    try:
        response = requests.get(
            url="http://api.weatherapi.com/v1/current.json",
            params={
                "key": WEATHER_API_KEY,
                "q": location
            },
            timeout=10
        )
        response.raise_for_status()
        data = response.json()

        # Convert the full JSON response to YAML string
        yaml_data = yaml.dump(data, sort_keys=False)
        return yaml_data

    except requests.RequestException as e:
        return f"Error fetching weather: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"

