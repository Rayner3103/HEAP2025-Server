# from supabase import create_client, Client
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions
from dotenv import load_dotenv
import os

try:
    load_dotenv()  # Load environment variables from .env file

    url: str = os.environ.get('SUPABASE_URL')
    key: str = os.environ.get('SUPABASE_KEY_SERVICE_ROLE')
    db: Client = create_client(supabase_url=url, supabase_key=key)
    print('SuperBase client created.')
except Exception as e:
    print("Error initiating SuperBase client", e)

def get_db():
    return db

def get_auth_admin():
    return create_client(
        os.environ.get('SUPABASE_URL'),
        os.environ.get('SUPABASE_KEY_SERVICE_ROLE'),
        options=ClientOptions(
            auto_refresh_token=False,
            persist_session=False,
        )
    )

# for devs
def get_root_user_id():
    response = db.auth.sign_in_with_password({
        "email": "raynersimzhiheng@gmail.com",
        "password": os.environ.get('SUPABASE_ROOT_USER_PASSWORD')
    })
    return response.user.id
