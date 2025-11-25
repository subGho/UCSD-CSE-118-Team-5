#!/usr/bin/env python3

import requests


def main():

    door_status = ""
    walk_through_status = ""

    print("Is door open?")
    door_open_str = input().lower()
    if door_open_str == "yes":
        door_status = "Open"
        print("Door is open !")
    elif door_open_str == "no":
        door_status = "Closed"
        print("Door is not open !")
    else:
        door_status = ""

    print("Did you walk through?")
    walk_through_str = input().lower()
    if walk_through_str == "yes":
        walk_through_status = "True"
        print("You walked through !")
    elif walk_through_str == "no":
        walk_through_status = "False"
        print("You did not walk through !")
    else:
        walk_through_status = ""


    print("What is the temperature?")
    indoor_temp = input()

    try:
    # Attempt to convert the input to an integer
        indoor_temp = int(indoor_temp)
        # print(f"The input '{indoor_temp}' is a valid integer.")
    # You can proceed with using the 'value' variable as an integer here
    except ValueError:
        # Handle the error if the conversion fails
        print(f"The input '{indoor_temp}' is not a valid integer.")

    if door_status and walk_through_status:
        payload = {
            "userId": "subhon",
            "doorStatus": door_status,
            "walkThroughStatus": walk_through_status,
            "indoorTemp": indoor_temp,
        }
        try:
            response = requests.post(
                "http://localhost:8000/weather",
                json=payload,
                timeout=5,
            )
            response.raise_for_status()
            print("POST sent. Server response:")
            print(response.json())
        except requests.exceptions.RequestException as exc:
            print(f"Failed to send POST: {exc}")
    else:
        print("Conditions not met: doorOpen and walkThrough fields must both be populated.")


if __name__ == "__main__":
    main()
