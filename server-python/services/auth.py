from services import database as database_service

def validate_user_session(headers):
    jwt  = headers.get("Authorization", "").replace("Bearer ", "")
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
    response = (
        database_service.get_db()
        .auth
        .sign_in_with_password(payload)
    )
    return response.session.access_token

def sign_out():
    response = (
        database_service.get_db()
        .auth
        .sign_out()
    )
    return response