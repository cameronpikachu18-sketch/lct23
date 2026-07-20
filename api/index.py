import requests
import random
from flask import Flask, jsonify, request
import json
import os
import base64
from datetime import datetime, timedelta
import uuid
import logging
import time
from typing import Dict, List, Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GameInfo:
    def __init__(self):
        self.TitleId: str = "EB64D"  # Playfab Title Id
        self.SecretKey: str = "N7A51URUTO48XIG583NZDH9WXW8HDZ6FTJ4NN4Q3G8BK3FRDX1"  # Playfab Secret Key
        self.ApiKey: str = "OC|1166633403205472|9dde8f0a0f9c8efb2823224de58d2477"  # App Api Key

    def get_auth_headers(self):
        return {"content-type": "application/json", "X-SecretKey": self.SecretKey}

settings = GameInfo()
app = Flask(__name__)
app.start_time = time.time()

# Utility function for input validation
def validate_input(data: Dict, required_fields: List[str]) -> Optional[List[str]]:
    return [field for field in required_fields if not data.get(field)]

# Utility function for generating unique session IDs
def generate_session_id() -> str:
    return str(uuid.uuid4())

# Utility function for returning CloudScript results
def return_function_json(funcname: str, funcparam: Dict = {}, playfab_id: Optional[str] = None):
    logger.info(f"Calling function: {funcname} with parameters: {funcparam} for player {playfab_id}")
    req = requests.post(
        url=f"https://{settings.TitleId}.playfabapi.com/Server/ExecuteCloudScript",
        json={
            "PlayFabId": playfab_id,
            "FunctionName": funcname,
            "FunctionParameter": funcparam
        },
        headers=settings.get_auth_headers()
    )
    if req.status_code == 200:
        result = req.json().get("data", {}).get("FunctionResult", {})
        logger.info(f"Function result: {result}")
        return jsonify(result), req.status_code
    else:
        logger.error(f"Function execution failed, status code: {req.status_code}")
        return jsonify({}), req.status_code

# Validate Oculus nonce
def get_is_nonce_valid(nonce: str, oculusId: str) -> bool:
    if not settings.ApiKey:
        return False
    req = requests.post(
        url=f'https://graph.oculus.com/user_nonce_validate?nonce={nonce}&user_id={oculusId}&access_token={settings.ApiKey}',
        headers={"content-type": "application/json"})
    return req.json().get("is_valid", False)

CODES_GITHUB_URL = "https://github.com/redapplegtag/backendsfrr/raw/main/codes.txt"
REDEEMABLE_ITEMS = ["cosmetic1", "cosmetic2", "cosmetic3", "bundle1", "skin1", "hat1", "gloves1"]

@app.route("/", methods=["POST", "GET"])
def main():
    return """
        <html>
            <body style="font-family: sans-serif; background: #004d00; color: white; text-align: center; padding: 50px;">
                <h1>LC Tag Backend Server Running</h1>
            </body>
        </html>
    """

@app.route("/api/PlayFabAuthentication", methods=["POST", "GET"])
def playfab_authentication():
    rjson = request.get_json()
    if not rjson:
        return jsonify({"error": "No JSON body"}), 400

    required_fields = ["Nonce", "AppId", "Platform", "OculusId"]
    missing_fields = validate_input(rjson, required_fields)
    if missing_fields:
        return jsonify({"Message": f"Missing parameter(s): {', '.join(missing_fields)}", "Error": f"BadRequest-No{missing_fields[0]}"}), 401

    if rjson.get("AppId") != settings.TitleId:
        return jsonify({"Message": "Request sent for the wrong App ID", "Error": "BadRequest-AppIdMismatch"}), 400

    if rjson.get("Platform") in ["Oculus", "Quest"] and not get_is_nonce_valid(rjson["Nonce"], rjson["OculusId"]):
        return jsonify({"Message": "Invalid nonce", "Error": "BadRequest-InvalidNonce"}), 401

    url = f"https://{settings.TitleId}.playfabapi.com/Server/LoginWithServerCustomId"
    login_request = requests.post(
        url=url,
        json={
            "ServerCustomId": "OCULUS" + rjson.get("OculusId"),
            "CreateAccount": True,
        },
        headers=settings.get_auth_headers(),
    )

    if login_request.status_code == 200:
        data = login_request.json().get("data")
        session_ticket = data.get("SessionTicket")
        entity_token = data.get("EntityToken").get("EntityToken")
        playfab_id = data.get("PlayFabId")
        entity_type = data.get("EntityToken").get("Entity").get("Type")
        entity_id = data.get("EntityToken").get("Entity").get("Id")
        session_id = generate_session_id()

        return jsonify(
            {
                "PlayFabId": playfab_id,
                "SessionTicket": session_ticket,
                "EntityToken": entity_token,
                "EntityId": entity_id,
                "EntityType": entity_type,
                "SessionId": session_id,
            }
        ), 200
    else:
        return jsonify({"Error": "PlayFab Error"}), login_request.status_code

@app.route('/api/TitleData', methods=['POST', 'GET'])
def titledata():
    response_data = {
        "AutoMuteCheckedHours": {"hours": 169},
        "AutoName_Adverbs": ["Cool", "Fine", "Bald", "Bold", "Calm", "Rad", "Big", "Wild"],
        "AutoName_Nouns": ["Gorilla", "Chicken", "Sloth", "King", "Rebel", "Wizard"],
        "BundleBoardSign": "<color=#ff4141>discord.gg/NvHbcsp7cJ</color>",
        "MOTD": "<color=#FFC0CB>WELCOME TO LC TAG!</color>",
        "EnableCustomAuthentication": True,
        "LatestPrivacyPolicyVersion": "2024.09.20",
        "LatestTOSVersion": "2024.09.20",
        "TOS_2024.09.20": "discord.gg/NvHbcsp7cJ",
        "EnableTwoFactorAuth": False,
        "MaxPlayersPerRoom": 8,
        "DefaultGameMode": "Tag",
        "ServerVersion": "1.2.3",
        "ClientMinVersion": "1.2.0"
    }
    return jsonify(response_data)

# --- TOS FIX AREA ---
@app.route("/api/GetAcceptedAgreements", methods=['POST', 'GET'])
def GetAcceptedAgreements():
    # Ensured version string alignment with LatestTOSVersion/LatestPrivacyPolicyVersion in TitleData
    return jsonify({
        "PrivacyPolicy": "2024.09.20",
        "TOS": "2024.09.20",
        "EULA": "2024.09.20"
    }), 200

@app.route("/api/SubmitAcceptedAgreements", methods=['POST'])
def SubmitAcceptedAgreements():
    data = request.get_json() or {}
    playfab_id = data.get("PlayFabId")
    logger.info(f"Accepted agreements for PlayFabId: {playfab_id}")
    # Return explicit success status payload to prevent client hanging
    return jsonify({
        "result": True,
        "status": "Accepted",
        "PlayFabId": playfab_id
    }), 200
# --------------------

@app.route("/api/GetGuildInfo", methods=["POST"])
def get_guild_info():
    rjson = request.get_json() or {}
    guild_id = rjson.get("GuildId")
    if not guild_id:
        return jsonify({"error": "Missing GuildId"}), 400
    return jsonify({"guild": {"id": guild_id, "name": "Default Guild"}}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
