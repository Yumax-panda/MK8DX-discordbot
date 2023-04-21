BOT_IDS = (123456789)

MY_ID = 123456789
LOG_CHANNEL_ID = 1081604309063581816
SUPPORT_ID = 1071251903649939479

IGNORE_CHANNELS = []

RANK_DATA = {
            "Grandmaster": {
                "color": 0xA3022C,
                "url": "https://i.imgur.com/EWXzu2U.png"},
            "Master": {
                "color": 0xD9E1F2,
                "url": "https://i.imgur.com/3yBab63.png"},
            "Diamond": {
                "color": 0xBDD7EE,
                "url": "https://i.imgur.com/RDlvdvA.png"},
            "Ruby":{
                "color":0xD51C5E,
                "url": "https://i.imgur.com/WU2NlJQ.png"},
            "Sapphire": {
                "color": 0x286CD3,
                "url": "https://i.imgur.com/bXEfUSV.png"},
            "Platinum": {
                "color": 0x3FABB8,
                "url": "https://i.imgur.com/8v8IjHE.png"},
            "Gold": {
                "color": 0xFFD966,
                "url": "https://i.imgur.com/6yAatOq.png"},
            "Silver": {
                "color": 0xD9D9D9,
                "url": "https://i.imgur.com/xgFyiYa.png"},
            "Bronze": {
                "color": 0xC65911,
                "url": "https://i.imgur.com/DxFLvtO.png"},
            "Iron": {
                "color": 0x817876,
                "url": "https://i.imgur.com/AYRMVEu.png"},
        }


def get_rank(mmr: int) -> str:

    if mmr >= 17000:
        return "Grandmaster"
    elif mmr >= 16000:
        return "Master"
    elif mmr >= 15000:
        return "Diamond 2"
    elif mmr >= 14000:
        return "Diamond 1"
    elif mmr >= 13000:
        return "Ruby 2"
    elif mmr >= 12000:
        return "Ruby 1"
    elif mmr >= 11000:
        return "Sapphire 2"
    elif mmr >= 10000:
        return "Sapphire 1"
    elif mmr >= 9000:
        return "Platinum 2"
    elif mmr >= 8000:
        return "Platinum 1"
    elif mmr >= 7000:
        return "Gold 2"
    elif mmr >= 6000:
        return "Gold 1"
    elif mmr >= 5000:
        return "Silver 2"
    elif mmr >= 4000:
        return "Silver 1"
    elif mmr >= 3000:
        return "Bronze 2"
    elif mmr >= 2000:
        return "Bronze 1"
    elif mmr >= 1000:
        return "Iron 2"
    else:
        return "Iron 1"
