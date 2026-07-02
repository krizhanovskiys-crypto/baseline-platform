"""Court Registry — the single source of truth for Tennis Zones and courts.

Baseline does not use administrative city districts. It uses Tennis Zones —
groupings that reflect how tennis players actually think about locations
across the Greater Toronto Area. Every real public court in the registry is
grouped under the zone players would expect to find it in.

This module is intentionally a pure, side-effect-free data + lookup layer
(no ORM, no session) so it is trivially swappable for a database-backed
Court model later: callers only depend on TENNIS_ZONES and
get_courts_for_zone(), never on the dict's internal shape.
"""

COURTS_BY_ZONE: dict[str, list[str]] = {
    "Downtown": [
        "Ramsden Park",
        "Trinity Bellwoods Park",
        "Withrow Park",
        "Christie Pits Park",
        "Stanley Park",
        "Riverdale Park",
        "Moss Park",
    ],
    "West Toronto / Etobicoke": [
        "Colonel Samuel Smith Park",
        "Tom Riley Park",
        "Centennial Park",
        "Eglinton Flats",
        "Echo Valley Park",
        "Etobicoke Valley Park",
        "West Deane Park",
        "High Park",
        "Rennie Park",
    ],
    "North York": [
        "Oriole Park",
        "Newtonbrook Park",
        "Earl Bales Park",
        "Edithvale Park",
        "Amesbury Park",
        "Bayview Village Park",
        "Kirkwood Park",
        "Baycrest Park",
    ],
    "Scarborough": [
        "Thomson Memorial Park",
        "Birchmount Park",
        "Guildwood Park",
        "Milliken Park",
        "Scarborough Bluffs Park",
        "L'Amoreaux Park",
        "North Bendale Park",
    ],
    "Mississauga": [
        "Hunter's Green Park",
        "Brookmede Park",
        "Mississauga Valley Park",
        "Applewood Park",
        "Whiteoaks Park",
        "Meadowwood Park",
        "Tecumseh Park",
    ],
    "Vaughan": [
        "Maple Community District Park",
        "Woodbridge Highlands Park",
        "North Thornhill District Park",
        "Dufferin District Park",
        "Vaughan Crest Park",
        "York Hill District Park",
        "Chatfield Park",
    ],
    "Markham / Richmond Hill": [
        "Ada Mackenzie Park",
        "Bayview Glen Park",
        "Willow Grove Park",
        "Bayview Hill Park",
        "Crosby Park",
        "Mount Pleasant Park",
        "Newberry Park",
    ],
    "Oakville / Burlington": [
        "Coronation Park",
        "River Oaks Park",
        "Glenashton Park",
        "Glen Abbey Park",
        "Bolus Gardens Parkette",
        "Brant Hills Park",
        "Ireland Park",
    ],
}

# Zones, in the order they should be presented — derived from the registry
# itself so there is exactly one place that defines "what is a zone".
TENNIS_ZONES: list[str] = list(COURTS_BY_ZONE.keys())


def get_courts_for_zone(zone: str) -> list[str]:
    """Return the registry courts for a Tennis Zone, or [] for an unknown zone.

    Unknown zones (e.g. a value saved before this sprint that no longer
    matches a current zone name) intentionally return an empty list rather
    than raising — the caller still allows adding a custom court, so a
    player is never blocked from completing their profile.
    """
    return list(COURTS_BY_ZONE.get(zone, []))
