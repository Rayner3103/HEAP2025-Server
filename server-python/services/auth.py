from supabase import AuthApiError
from services import database as database_service

def validate_user_session(headers):
    jwt  = headers.get("Authorization", "").replace("Bearer ", "")
    if jwt == '':
        raise AuthApiError

    response = (
        database_service.get_db()
        .auth
        .get_user(jwt)
    )
    return response.user.id

def sign_in(email, password):
    payload = {
        "email": email,
        "password": password
    }

    result = dict()
    
    response = (
        database_service.get_db()
        .auth
        .sign_in_with_password(payload)
    )

    result['token'] = response.session.access_token
    result['id'] = response.user.id
    result['email'] = response.user.email

    response = (
        database_service.get_db()
        .table("User")
        .select("*")
        .eq("userId", response.user.id)
        .execute()
    )

    result['role'] = response.data[0]['role']

    return result