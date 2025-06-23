import requests
from django.conf import settings


def get_primary_card_from_remote(card_number, business_id):
    try:
        response = requests.get(
            settings.AUTH_SERVER_URL + "/get-primary-card/",
            params={"card_number": card_number, "business_id": business_id},
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()

            if data.get("success") and data.get("primary_card_number"):
                return {
                    "success": True,
                    "primary_card_number": data["primary_card_number"],
                    "message": data.get("message", "")
                }

            # If physical card exists but not mapped
            if data.get("primary_card_number") == card_number and not data.get("is_associated", True):
                return {
                    "success": False,
                    "primary_card_number": None,
                    "message": data.get("message", "Card is not mapped.")
                }

            # Physical card doesn't exist
            return {
                "success": False,
                "primary_card_number": None,
                "message": data.get("message", "Card is not associated with this business.")
            }

    except requests.RequestException:
        return {
            "success": False,
            "primary_card_number": None,
            "message": "External request failed. Try again later."
        }




# def get_primary_card_from_remote(card_number, business_id):
#     """
#     Resolve secondary card to primary card via external auth server API.
#     Handles mapped cards, directly associated primary cards, and invalid cards.
#     """
#     try:
#         response = requests.get(
#             settings.AUTH_SERVER_URL + "/get-primary-card/",
#             params={"card_number": card_number, "business_id": business_id},
#             timeout=5
#         )
#         if response.status_code == 200:
#             data = response.json()

#             # ✅ Case 1: Card is mapped to a primary card
#             if data.get("success") and data.get("primary_card_number") and data["primary_card_number"] != card_number:
#                 return {
#                     "success": True,
#                     "primary_card_number": data["primary_card_number"],
#                     "message": "Mapped secondary card resolved to primary."
#                 }

#             # ✅ Case 2: Card is not mapped but is directly associated (primary card)
#             if data.get("primary_card_number") == card_number and data.get("is_associated", False):
#                 return {
#                     "success": True,
#                     "primary_card_number": card_number,
#                     "message": "Primary card is directly associated with business."
#                 }

#             # ❌ Case 3: Card is not associated at all
#             return {
#                 "success": False,
#                 "primary_card_number": None,
#                 "message": data.get("message", "Card is not associated with this business.")
#             }

#     except requests.RequestException:
#         return {
#             "success": False,
#             "primary_card_number": None,
#             "message": "External request failed. Try again later."
#         }

#     # ❌ Final fallback in case of unknown error
#     return {
#         "success": False,
#         "primary_card_number": None,
#         "message": "Card is not associated with this business."
#     }






# import requests
# from django.conf import settings


# def get_primary_card_from_remote(card_number, business_id):
#     """
#     Resolve secondary card to primary card via external auth server API.
#     If no mapping is found, return original card only if it is associated.
#     """
#     try:
#         response = requests.get(
#             settings.AUTH_SERVER_URL + "/get-primary-card/",
#             params={"card_number": card_number, "business_id": business_id},
#             timeout=5
#         )
#         if response.status_code == 200:
#             data = response.json()

#             # Case 1: primary card number is returned and is associated
#             if data.get("success") and data.get("primary_card_number"):
#                 return {
#                     "success": True,
#                     "primary_card_number": data["primary_card_number"]
#                 }

#             # Case 2: card is not mapped but is directly associated
#             elif data.get("primary_card_number") == card_number and data.get("is_associated", False):
#                 return {
#                     "success": True,
#                     "primary_card_number": card_number
#                 }

#     except requests.RequestException:
#         pass

#     # Case 3: completely invalid card
#     return {
#         "success": False,
#         "message": "Card is not associated with this business.",
#         "primary_card_number": None
#     }


