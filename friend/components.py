"""
MIT License

Copyright (c) 2022 mizuyoukan-ao
Copyright (c) 2023-present Yumax-panda

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from typing import (
    Any,
    Optional,
    Union,
    TypedDict,
    NamedTuple,
)
from discord import (
    ApplicationContext,
    Interaction,
    InputTextStyle,
    Embed,
    EmbedField,
    File,
    Colour,
    ButtonStyle
)
from discord.ext.pages import Paginator
from discord.ui import (
    Modal,
    InputText,
    View,
    Button,
    Item
)

from aiohttp import ClientSession
import asyncio
import base64
import hashlib
import random
import re
import secrets
import string

from .errors import *
from .response_type import ResponseType
from .switch_user import MinimalUserPayload ,MinimalUser, SwitchUser
from errors import MyError
from common.utils import deta


class APITokenPayload(TypedDict):
    id: str
    access: str


class UserInfoPayload(TypedDict):
    language: str
    country: str
    birthday: str


class F(TypedDict):
    f: str
    timestamp: int
    request_id: str


class NSOTokenPayload(TypedDict):
    token: str
    expiresIn: int


class StoredSessionTokenPayload(TypedDict):
    key: str
    value: str


class StoredNSOTokenPayload(TypedDict):
    key: str
    __expires: int
    value: str


class _Client(NamedTuple):
    client_id: str
    host: str


class _Url(NamedTuple):
    authorize: str
    session_token: str
    api_token: str
    me: str
    login: str


Nintendo = _Client(
    client_id="71b963c1b7b6d119",
    host="accounts.nintendo.com"
)

Url = _Url(
    authorize="https://accounts.nintendo.com/connect/1.0.0/authorize",
    session_token="https://accounts.nintendo.com/connect/1.0.0/api/session_token",
    api_token="https://accounts.nintendo.com/connect/1.0.0/api/token",
    me="https://api.accounts.nintendo.com/2.0.0/users/me",
    login="https://api-lp1.znc.srv.nintendo.net/v3/Account/Login"
)

_RE = re.compile(r"npf71b963c1b7b6d119:\/\/auth#session_state=([0-9a-f]{64})&session_token_code=([A-Za-z0-9-._]+)&state=([A-Za-z]{50})")
_FC_RE = re.compile(r'[0-9]{4}\-[0-9]{4}\-[0-9]{4}') #Regular expression for switch friend code.


async def _get(discord_id: Union[str, int], base_name: str) -> Any:
    db = deta.AsyncBase(base_name)
    data = await db.get(str(discord_id))
    await db.close()
    return data


async def _set(
    discord_id: Union[str, int],
    base_name: str,
    payload: Any,
    expire_in: Optional[int] = None
) -> None:
    db = deta.AsyncBase(base_name)

    if expire_in is not None:
        e = expire_in-10
    else:
        e = None

    await db.put(
        data=payload,
        key=str(discord_id),
        expire_in = e
    )
    await db.close()


async def get_session_token(discord_id: Union[str, int]) -> Optional[StoredSessionTokenPayload]:
    return await _get(discord_id, 'sessionToken')


async def set_session_token(discord_id: Union[str, int], token: str) -> None:
    await _set(discord_id, 'sessionToken', token)


async def get_nso_token(discord_id: Union[str, int]) -> Optional[StoredNSOTokenPayload]:
    return await _get(discord_id, 'nsoToken')


async def set_nso_token(
    discord_id: Union[str, int],
    token: str,
    expire_in: int
) -> None:
    await _set(discord_id, 'nsoToken', token, expire_in)


async def set_users_data(id: Union[str, int], users: list[MinimalUser]) -> None:
    await _set(id, 'requests', [u.to_dict() for u in users])


async def get_users_data(id: Union[str, int]) -> list[MinimalUser]:
    data: MinimalUserPayload = await _get(id, 'requests')
    if data is None:
        return []
    else:
        return list(map(lambda x: MinimalUser.from_dict(x), data["value"]))


async def handle_error(error: Exception, interaction: Interaction) -> None:
    content: str = None

    if isinstance(error, MyError):
        content = error.localized_content(interaction.locale)
    else:
        print(error)
        content = (
            "予期しないエラーが発生しました。" if interaction.locale == 'ja'
            else "Unexpected error occurred."
        )

    if interaction.response.is_done():
        await interaction.followup.send(content, ephemeral=True)
    else:
        await interaction.response.send_message(content, ephemeral=True)


class BaseView(View):

    def __init__(
        self,
        *items: Item,
        timeout: Optional[float] = 180.0,
    ) -> None:
        super().__init__(
            *items,
            timeout=timeout,
            disable_on_timeout=True
        )

    async def on_error(
        self,
        error: Exception,
        item: Item,
        interaction: Interaction
    ) -> None:
        await handle_error(error, interaction)


class RedirectURI:

    __slots__ = (
        'session_state',
        'session_token_code',
        'response_state'
    )

    def __init__(self, uri: str) -> None:
        m = _RE.match(uri)

        try:
            self.session_state = m.group(1)
            self.session_token_code = m.group(2)
            self.response_state = m.group(3)
        except (IndexError, AttributeError):
            raise InvalidURL
        else:
            if not self.is_valid():
                raise InvalidURL

    def is_valid(self) -> bool:
        return (
            self.session_state is not None
            and self.session_token_code is not None
            and self.response_state is not None
        )

    def __str__(self) -> str:
        return "\n".join([f"{attr}: {getattr(self, attr)}" for attr in RedirectURI.__slots__])


async def get_api_token(session_token: str) -> APITokenPayload:
    async with ClientSession() as session:
        async with session.post(Url.api_token,
            data={
                "client_id": Nintendo.client_id,
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer-session-token",
                "session_token": session_token
            }
        ) as response:
            if response.status != 200:
                raise AuthorizationFailure
            else:
                data= await response.json()
                return {
                    "id": data["id_token"],
                    "access": data["access_token"]
                }


async def get_user_info(access_token: str) -> UserInfoPayload:
    async with ClientSession() as session:
        async with session.get(Url.me,
            headers={'Authorization': f'Bearer {access_token}'}
        ) as response:
            if response.status != 200:
                raise AuthorizationFailure
            else:
                data = await response.json()
                return {
                    "language": data["language"],
                    "country": data["country"],
                    "birthday": data["birthday"]
                }


async def get_f(id_token: str) -> F:
    async with ClientSession() as session:
        async with session.post('https://api.imink.app/f',
            json={
                "token": id_token,
                "hash_method": 1
            }
        ) as response:
            if response.status != 200:
                raise AuthorizationFailure
            else:
                data = await response.json()
                return data


async def create_nso_token(session_token: str) -> NSOTokenPayload:
    api_token = await get_api_token(session_token)
    user_info = await get_user_info(api_token["access"])
    f = await get_f(api_token["id"])

    async with ClientSession() as session:
        async with session.post(Url.login,
            json={
                "parameter":{
                    "naIdToken": api_token['id'],
                    "timestamp": str(f['timestamp']),
                    "requestId": f["request_id"],
                    "f": f["f"],
                    "language": user_info["language"],
                    "naCountry": user_info["country"],
                    "naBirthday": user_info["birthday"]
                }
            },
            headers={
                'Content-Type': 'application/json; charset=utf-8',
                'User-Agent': 'com.nintendo.znca/2.2.0 (Android/10)',
                'X-ProductVersion': '2.5.0',
                'X-Platform': 'Android'
            }
        ) as response:
            if response.status != 200:
                raise AuthorizationFailure
            else:
                cred = (await response.json())["result"]["webApiServerCredential"]
                data: NSOTokenPayload = {
                    "token": cred["accessToken"],
                    "expiresIn": cred["expiresIn"]
                }
                return data


async def get_token(discord_id: Union[str, int]) -> str:
    """get NSO token from discord ID"""
    if (token_payload := await get_nso_token(discord_id)) is None:
        if (session_token := await get_session_token(discord_id)) is None:
            raise TokenNotFound
        token_payload = await create_nso_token(session_token["value"])
        token = token_payload["token"]
        await set_nso_token(discord_id, token, expire_in=token_payload["expiresIn"]-10)
    else:
        token = token_payload["value"]
    return token


async def search_user(
    discord_id: Union[str, int],
    switch_fc: str
) -> SwitchUser:
    """search user and get user_id"""

    token = await get_token(discord_id)

    async with ClientSession() as session:
        async with session.post("https://api-lp1.znc.srv.nintendo.net/v3/Friend/GetUserByFriendCode",
            json={
                "parameter": {
                    "friendCode": switch_fc
                }
            },
            headers={
                "Authorization": "Bearer {}".format(token)
            }
        ) as response:
            data = await response.json()

            if "errorMessage" in data or response.status != 200:
                raise AuthorizationFailure
            else:
                return SwitchUser(
                    data=data["result"],
                    fc=switch_fc
                )


class LoginModal(Modal):

    def __init__(
        self,
        verifier: str,
        locale: str = 'ja'
    ):
        super().__init__(
            InputText(
                style=InputTextStyle.short,
                custom_id='auth_uri',
                placeholder="npf71b963c1b7b6d119://auth#...",
                required=True,
                label="Login URL"
            ),
            custom_id=verifier,
            title={'ja':'ログイン'}.get(locale, 'Login'),
            timeout=180.0
        )

    async def callback(self, interaction: Interaction) -> None:
        await interaction.response.defer()

        uri = RedirectURI(self.children[0].value)
        verifier = interaction.custom_id

        async with ClientSession() as session:
            async with session.post(Url.session_token,
                data={
                    "client_id": Nintendo.client_id,
                    "session_token_code": uri.session_token_code,
                    "session_token_code_verifier": verifier,
                }
            ) as response:
                if response.status != 200:
                    raise AuthorizationFailure
                else:
                    session_token: str = (await response.json())["session_token"]
                    await set_session_token(
                        discord_id=interaction.user.id,
                        token= session_token
                    )
                    nso_token = await create_nso_token(session_token)
                    await set_nso_token(
                        interaction.user.id,
                        nso_token["token"],
                        expire_in=nso_token["expiresIn"]-10
                    )
                    await interaction.followup.send(
                        {'ja': 'ログインしました。'}.get(interaction.locale, 'Successfully Logged in.'),
                        ephemeral=True
                    )
                    return


    async def on_error(self, error: Exception, interaction: Interaction) -> None:
        await handle_error(error, interaction)


class LoginButton(Button):

    def __init__(self, verifier: str):
        super().__init__(
            label='Next',
            custom_id=verifier
        )

    async def callback(self, interaction: Interaction):
        await interaction.response.send_modal(LoginModal(self.custom_id, interaction.locale))


async def send_url(ctx: ApplicationContext) -> None:
    e = Embed(title="Login")

    verifier = secrets.token_bytes(32)
    verifier_b64 = base64.urlsafe_b64encode(verifier).decode().replace("=", "")

    s256 = hashlib.sha256()
    s256.update(verifier_b64.encode())

    state = "".join(random.choice(string.ascii_letters) for _ in range(50))

    challenge_b64 = base64.urlsafe_b64encode(s256.digest()).decode().replace("=", "")

    url = f"https://accounts.nintendo.com/connect/1.0.0/authorize?state={state}&redirect_uri=npf71b963c1b7b6d119://auth&client_id=71b963c1b7b6d119&scope=openid%20user%20user.birthday%20user.mii%20user.screenName&response_type=session_token_code&session_token_code_challenge={challenge_b64}&session_token_code_challenge_method=S256&theme=login_form"

    e.description = {
        'ja': f'[こちら]({url})をクリックし、ログインをした後に「この人にする」のリンク先をコピペしてください。'
    }.get(ctx.locale, f'Click [here]({url}) and copy Link address of **select this account** button.')
    file = File("images/intro.jpg", filename="intro.jpg")
    e.set_image(url="attachment://intro.jpg")

    view = BaseView(LoginButton(verifier_b64))

    await ctx.respond(embed=e, view=view, ephemeral=True, file=file)


class RequestEmbed(Embed):

    def __init__(
        self,
        user: SwitchUser,
        locale: str = 'ja'
    ) -> None:
        super().__init__(
            color=Colour.blue(),
            title=user.name,
            description=f"`{user.fc}`"
        )
        self.set_author(
            name={'ja':'フレンド申請'}.get(locale, 'Friend Request'),
            icon_url=user.image_uri
        )


class RequestButton(Button):

    def __init__(
        self,
        nsoId: str,
        locale: str = 'ja'
    ) -> None:
        super().__init__(
            style=ButtonStyle.secondary,
            label={"ja": "申請"}.get(locale, 'Apply'),
            custom_id=nsoId
        )


    async def callback(self, interaction: Interaction):
        await interaction.response.defer()
        token = await get_token(interaction.user.id)

        async with ClientSession() as session:
            async with session.post("https://api-lp1.znc.srv.nintendo.net/v3/FriendRequest/Create",
                json={
                    "parameter":{
                        "nsaId": self.custom_id
                    }
                },
                headers={
                    "Authorization": "Bearer {}".format(token)
                }
            ) as response:
                data=await response.json()
                if "errorMessage" in data or response.status != 200:
                    raise RequestFailure(ResponseType.judge(data))
                else:
                    await interaction.followup.send(
                        ephemeral=True,
                        content={'ja':"申請しました"}.get(interaction.locale, 'Successfully sent.')
                    )


class DeleteButton(Button):

    def __init__(self, locale: Optional[str] = None) -> None:
        locale = locale or 'ja'
        super().__init__(
            style=ButtonStyle.danger,
            label={"ja": "終了"}.get(locale, "Quit"),
            custom_id="fc_finish_button"
        )

    async def callback(self, interaction: Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        is_ja = self.label == '終了'

        if interaction.message:
            view: View = self.view
            if self.view is not None:
                view.disable_all_items()
                await interaction.message.edit(view=view)
            await interaction.followup.send(
                "終了しました。" if is_ja else "Finished",
                ephemeral=True
            )
            return
        else:
            await interaction.followup.send(
                "何らかの理由で失敗しました。" if is_ja else "Failed to quit for some reason.",
                ephemeral=True
            )
            return



class RequestView(BaseView):

    def __init__(
        self,
        id: str,
        ephemeral: bool,
        locale: Optional[str] = None
    ):
        locale: str = locale or 'ja'
        super().__init__(timeout=180.0)
        self.add_item(RequestButton(id, locale))

        if not ephemeral:
            self.add_item(DeleteButton(locale))

    async def on_error(self, error: Exception, item: RequestButton, interaction: Interaction) -> None:
        await handle_error(error, interaction)


async def apply_request_by_user(token: str, user: MinimalUser) -> Union[bool, ResponseType]:
    """Apply a request using minimal user data. If success, returns True."""

    async with ClientSession() as session:
        async with session.post("https://api-lp1.znc.srv.nintendo.net/v3/FriendRequest/Create",
            json={
                "parameter":{
                    "nsaId": user.nsa_id
                }
            },
            headers={
                "Authorization": "Bearer {}".format(token)
            }
        ) as response:
            data=await response.json()
            if "errorMessage" in data or response.status != 200:
                return ResponseType.judge(data)
            else:
                return True




class MultipleRequestsButton(Button):
    """This button is used to apply requests."""

    def __init__(self, interaction: Interaction) -> None:
        super().__init__(
            style=ButtonStyle.secondary,
            label={"ja": "申請"}.get(interaction.locale, 'Apply'),
            custom_id=str(interaction.id)
        )


    async def callback(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        users = await get_users_data(self.custom_id)

        if not users:
            raise FCNotFound

        token = await get_token(interaction.user.id)
        success: list[EmbedField] = []
        failed: list[EmbedField] = []

        for user in users:
            field = EmbedField(name=user.name, value=f"> {user.fc}", inline=False)

            if res := await apply_request_by_user(token, user):
                success.append(field)
            else:
                field.name += f" ({res.brief(interaction.locale)})" if res.brief(interaction.locale) else ""
                failed.append(field)

            await asyncio.sleep(4.0)

        is_ja = interaction.locale == 'ja'
        embeds: list[Embed] = []

        if success:
            embeds.append(Embed(title="申請完了" if is_ja else "Successfully applied", color=Colour.green(), fields=success))
        if failed:
            e = Embed(title="申請ができませんでした" if is_ja else "Failed to apply", color=Colour.red(), fields=failed)
            embeds.append(e)

        is_compact = len(embeds) == 1

        await Paginator(
            pages=embeds,
            show_disabled= not is_compact,
            show_indicator= not is_compact,
            author_check=False
        ).respond(interaction=interaction, ephemeral=True)


async def _search_with_token(token: str, switch_fc: str) -> Optional[MinimalUser]:
    async with ClientSession() as session:
        async with session.post("https://api-lp1.znc.srv.nintendo.net/v3/Friend/GetUserByFriendCode",
            json={
                "parameter": {
                    "friendCode": switch_fc
                }
            },
            headers={
                "Authorization": "Bearer {}".format(token)
            }
        ) as response:
            data = await response.json()

            if "errorMessage" in data or response.status != 200:
                return None
            else:
                return SwitchUser(
                    data=data["result"],
                    fc=switch_fc
                ).to_minimal()


async def _multiple_requests(ctx: ApplicationContext, text: str, ephemeral: bool) -> None:
    codes = _FC_RE.findall(text)

    if not codes:
        raise FCNotFound
    if len(codes) > 12:
        raise TooManyInputs

    token = await get_token(ctx.user.id)
    users: list[MinimalUser] = []

    for code in codes:
        user = await _search_with_token(token, code)

        if user is not None:
            users.append(user)

        await asyncio.sleep(5.0)

    if not users:
        raise FCNotFound

    await set_users_data(ctx.interaction.id, users)
    is_ja = ctx.locale == 'ja'
    e = Embed(
        title="以下のユーザーへ申請します" if is_ja else "Apply",
        color=Colour.blue(),
        fields=[
            EmbedField(name=f'{num+1}: {u.name}', value=f'> {u.fc}', inline=False) for num, u in enumerate(users)
        ]
    )

    view = BaseView(MultipleRequestsButton(ctx.interaction))

    if not ephemeral:
        view.add_item(DeleteButton(ctx.locale))

    await ctx.respond(view=view, ephemeral=ephemeral, embed=e)
