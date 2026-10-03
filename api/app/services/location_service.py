"""Turn a US ZIP code or city + state into coordinates and a time zone,
using Aladhan's address lookup (already used for prayer times)."""
import re
import httpx

US_STATES = {
    "AL","AK","AZ","AR","CA","CO","CT","DE","DC","FL","GA","HI","ID","IL","IN","IA","KS",
    "KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY","NC",
    "ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV","WI","WY","PR",
}


class LocationLookupError(Exception):
    """The lookup service could not be reached."""


def resolve_location(zip_code=None, city=None, state=None, country: str = "US"):
    """Returns a dict of user fields, None if the place can't be found,
    or raises LocationLookupError if the service is unreachable."""
    zip_code = (zip_code or "").strip()
    city = " ".join((city or "").split())
    state = (state or "").strip().upper()

    if zip_code:
        if not re.fullmatch(r"\d{5}", zip_code):
            return None
        address = f"{zip_code}, {country}"
        label = f"ZIP {zip_code}"
    elif city and state in US_STATES:
        address = f"{city}, {state}, {country}"
        label = f"{city.title()}, {state}"
    else:
        return None

    try:
        r = httpx.get("https://api.aladhan.com/v1/timingsByAddress",
                      params={"address": address, "method": 2},
                      follow_redirects=True, timeout=12)
        data = r.json()
    except Exception as e:
        print(f"location lookup error: {e}")
        raise LocationLookupError(str(e))

    if data.get("code") != 200 or not isinstance(data.get("data"), dict):
        return None
    meta = data["data"].get("meta") or {}
    lat, lng, tz = meta.get("latitude"), meta.get("longitude"), meta.get("timezone")
    if lat is None or lng is None or not tz:
        return None
    return {
        "zip_code": zip_code or None,
        "city": city.title() if city else None,
        "state": state or None,
        "location_label": label,
        "latitude": float(lat),
        "longitude": float(lng),
        "timezone": tz,
    }
