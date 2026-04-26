import re


def parse_message(message: str):
    try:
        data = {}

        # Event
        event_match = re.search(r'^(.*?)\sTime=', message)
        if event_match:
            data["event"] = event_match.group(1)

        # Time
        time_match = re.search(r'Time=([0-9\-:\s]+)', message)
        if time_match:
            data["time"] = time_match.group(1)

        # Price
        price_match = re.search(r'Price=([\d\.]+)', message)
        if price_match:
            data["price"] = float(price_match.group(1))

        # Type
        type_match = re.search(r'Type=(\w+)', message)
        if type_match:
            data["type"] = type_match.group(1)

        # Strike
        strike_match = re.search(r'Strike=(\d+)', message)
        if strike_match:
            data["strike"] = int(strike_match.group(1))

        # Flag (default True)
        flag_match = re.search(r'Flag=(\w+)', message)
        if flag_match:
            data["flag"] = flag_match.group(1).lower() == "true"
        else:
            data["flag"] = True

        # ✅ AMO (default False)
        amo_match = re.search(r'Amo=(\w+)', message)
        if amo_match:
            data["amo"] = amo_match.group(1).lower() == "true"
        else:
            data["amo"] = False

        return data

    except Exception as e:
        return {"error": str(e)}