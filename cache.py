import msal
import os
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path)
CLIENT_ID = os.environ["CLIENT_ID"]

AUTHORITY = "https://login.microsoftonline.com/consumers"
SCOPES = ["Tasks.ReadWrite"]
CACHE_FILE = os.path.join(os.path.dirname(__file__), "token_cache.bin")


def load_cache():
    cache = msal.SerializableTokenCache()
    if os.path.exists(CACHE_FILE):
        cache.deserialize(open(CACHE_FILE, "r").read())
    return cache


def save_cache(cache):
    if cache.has_state_changed:
        with open(CACHE_FILE, "w") as f:
            f.write(cache.serialize())


def get_access_token():
    cache = load_cache()

    app = msal.PublicClientApplication(
        client_id=CLIENT_ID, authority=AUTHORITY, token_cache=cache
    )

    # ① まずキャッシュから取得（サイレント認証）
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
        if result and "access_token" in result:
            save_cache(cache)
            return result["access_token"]

    # ② キャッシュに無い or 期限切れ → Device Code Flow を実行
    flow = app.initiate_device_flow(scopes=SCOPES)
    print(flow["message"])  # 表示されたURLにアクセスしてコードを入力

    result = app.acquire_token_by_device_flow(flow)
    save_cache(cache)

    if "access_token" not in result:
        raise RuntimeError(result)

    return result["access_token"]
