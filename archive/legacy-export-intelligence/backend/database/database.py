"""In-memory database stub.

This module contains simple lists of dictionaries representing seller and
buyer profiles. The intent is to mimic a datastore without involving
external dependencies. In a real system these would be loaded from a
persistent data store and kept current via CRUD operations.
"""

from typing import List, Dict


def load_seller_profiles() -> List[Dict]:
    """Return a list of example seller profiles.

    Each seller profile contains an identifier, HS code, country, price range,
    minimum order quantity and certifications. These are used by the
    matching service to score potential buyers.
    """
    return [
        {
            "id": "seller_001",
            "hs_code": "330499",
            "country": "KR",
            "price_range": [5.0, 8.0],
            "moq": 1000,
            "certifications": ["FDA", "ISO"]
        },
        {
            "id": "seller_002",
            "hs_code": "300490",
            "country": "KR",
            "price_range": [1.0, 3.0],
            "moq": 5000,
            "certifications": ["CE"]
        },
        {
            "id": "seller_003",
            "hs_code": "210690",
            "country": "KR",
            "price_range": [2.0, 4.0],
            "moq": 2000,
            "certifications": []
        },
    ]


def load_buyer_profiles() -> List[Dict]:
    """Return a list of example buyer profiles.

    Buyer profiles include details such as the product HS code they are
    interested in, target country, budget per unit and acceptable MOQ as
    well as required certifications.
    """
    return [
        {
            "id": "buyer_001",
            "hs_code": "330499",
            "country": "US",
            "price_range": [6.0, 9.0],
            "moq": 1000,
            "certifications": ["FDA"]
        },
        {
            "id": "buyer_002",
            "hs_code": "300490",
            "country": "VN",
            "price_range": [2.0, 5.0],
            "moq": 2000,
            "certifications": ["CE"]
        },
        {
            "id": "buyer_003",
            "hs_code": "210690",
            "country": "CN",
            "price_range": [3.0, 4.5],
            "moq": 1500,
            "certifications": []
        },
        {
            "id": "buyer_004",
            "hs_code": "330499",
            "country": "JP",
            "price_range": [5.0, 7.0],
            "moq": 800,
            "certifications": ["ISO"]
        },
    ]