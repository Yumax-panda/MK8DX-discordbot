from typing import Any, Optional, Union
from datetime import datetime, timedelta
from deta import Deta
import pandas as pd
import asyncio
import json
import re
import os

from .timezones import TZ

deta = Deta(os.environ['DB_KEY'])


async def set_lounge_id(user_id: Union[int, str], lounge_id: Union[int, str]) -> None:
    db = deta.AsyncBase('user')
    payload = {str(user_id): str(lounge_id)}

    try:
        await db.update(key='lounge_ids', updates=payload)
    except:
        await db.put(key ='lounge_ids', data=payload)

    await db.close()


async def get_lounge_ids() -> dict[str, str]:
    db = deta.AsyncBase('user')
    data: dict = await db.get('lounge_ids')
    await db.close()

    try:
        data.pop('key')
    except (KeyError, AttributeError):
        return {}

    return data


async def set_team_name(guild_id: int, name: str) -> None:
    db = deta.AsyncBase('guild')
    payload = {str(guild_id): name}

    try:
        await db.update(key='name', updates=payload)
    except:
        await db.put(key ='name', data=payload)

    await db.close()


async def get_team_name(guild_id: int) -> Optional[str]:
    db = deta.AsyncBase('guild')
    data: dict = await db.get(key='name')
    await db.close()

    if data is None:
        return None

    return data.get(str(guild_id))


async def get_results(guild_id: int) -> list[dict]:
    db = deta.AsyncBase('results')
    data: dict = await db.get(key=str(guild_id))
    await db.close()

    if data is None:
        return []

    return data['data']


async def overwrite_results(guild_id: int, results: list[dict]) -> None:
    db = deta.AsyncBase('results')
    await db.put(key = str(guild_id), data = {'data': results})
    await db.close()
    return


async def post_result(guild_id: int, **payload: dict) -> None:
    """
    Parameters
    ----------
    enemy : `str`
    score : `int`
    enemyScore : `int`
    date : `str`
    """
    df = pd.DataFrame((await get_results(guild_id)) + [payload])
    df['date'] = pd.to_datetime(df['date'], infer_datetime_format = True).copy()
    df.sort_values(by='date', ascending=True)
    df['date'] = df['date'].astype(str)
    await overwrite_results(
        guild_id,
        df.drop_duplicates().to_dict('records')
    )
    return


async def get_gather(guild_id: int) -> dict:
    db = deta.AsyncBase('gather')
    data: dict = await db.get(key=str(guild_id))
    await db.close()

    if data is None:
        return {}

    return json.loads(data['data'])


async def post_gather(guild_id: int, payload: dict) -> None:
    db = deta.AsyncBase('gather')

    try:
        await db.update(
            key = str(guild_id),
            updates = {'data': json.dumps(payload)}
        )
    except:
        await db.put(
            key = str(guild_id),
            data = {'data': json.dumps(payload)}
        )

    await db.close()
    return


def get(l: list, i: int) -> Any:
    if len(l) <= i: return None
    return l[i]


def get_integers(text: str) -> list[int]:
    return list(map(int, re.findall(r'-?[0-9]+', text)))


def get_dt(text: str, locale: Optional[str] = None) -> datetime:

    if locale is None:
        locale = 'ja'

    now = datetime.utcnow() + timedelta(hours=TZ.from_locale(locale).offset)
    nums = list(map(int,re.findall(r'[0-9]+', text)))[:4][::-1]
    return datetime(
        year=get(nums, 3) or now.year,
        month=get(nums, 2) or now.month,
        day=get(nums, 1) or now.day,
        hour= get(nums, 0) or now.hour,
    )


def get_fc(text: str) -> Optional[str]:
    d_txt = re.sub(r'\D', '', text)

    if len(d_txt) != 12:
        return None

    return f'{d_txt[:4]}-{d_txt[4:8]}-{d_txt[8:]}'


def get_discord_id(text: str) -> Optional[int]:
    d_txt = re.sub(r'\D', '', text)

    if len(d_txt) >= 17 and len(d_txt) <=19:
        return int(d_txt)

    return None


def maybe_param(txt: str) -> tuple[Optional[str], Optional[int], Optional[str]]:
    d_id = get_discord_id(txt)
    fc = get_fc(txt)

    if d_id is not None:
        return None, d_id, None

    if fc is not None:
        return None, None, fc

    return txt, None, None


async def update_sokuji(data: dict, user_ids: set[str]) -> None:
    db = deta.AsyncBase('sokuji')
    await asyncio.gather(*[asyncio.create_task(db.put(data=data, key=user_id)) for user_id in user_ids])
    await db.close()
