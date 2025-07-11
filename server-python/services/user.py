from services import database as database_service
from services import utils
# TODO: change password api
ALLOWED_FIELDS = {
    "name",
    "age",
    "gender",
    "nationality",
    "teleUsername",
    "email",
    "organisation",
    "interests",
    "role",
    "userId",
    "password"
}

REQUIRED_FIELDS = {"email", "role", "gender", "nationality", 'password'}

GENDER_ENUM = {"male", "female", "others"}
NATIONALITY_ENUM = {"Citizen", "Resident", "Others"}
ROLE_ENUM = {"admin", "organiser", "user"}

def validate_create_fields(user_data):
    """
    Validate if user_data for create is complete

    Args:
        user_data (dict): contains client sent user_data

    Returns:
        boolean: true if all fields are intact
    """
    return (
        # check if have extra fields
        (utils.validate_allowed_field(ALLOWED_FIELDS, user_data)) and
        # check if required fields are there
        (utils.validate_required_field(REQUIRED_FIELDS, user_data)) and
        # Enum validations
        (user_data.get("gender") in GENDER_ENUM) and
        (user_data.get("nationality") in NATIONALITY_ENUM) and
        (user_data.get("role") in ROLE_ENUM) and 
        (utils.validate_email(user_data.get("email")))
    )

def validate_edit_fields(user_data):
    """
    Validate if user_data for edit is complete

    Args:
        user_data (dict): contains client sent user_data

    Returns:
        boolean: true if all fields are intact
    """
    enum_check = True
    if user_data.get("gender"):
        enum_check &= user_data.get("gender") in GENDER_ENUM
    if user_data.get("nationality"):
        enum_check &= user_data.get("nationality") in NATIONALITY_ENUM

    email_check = "email" not in user_data or ("email" in user_data and utils.validate_email(user_data.get("email")))

    return (
        utils.validate_allowed_field(ALLOWED_FIELDS, user_data) and
        enum_check and
        email_check and
        not user_data.get('role')
    )

def get_user_detail(user_id):
    """
    Gets user profile details

    Args:
        user_id (string): unique UUID of user

    Returns:
        dict: data of one user
    """
    response = (
        database_service.get_db()
        .table("User")
        .select("*")
        .eq("userId", user_id)
        .execute()
    )
    if len(response.data) == 1:
        user = response.data[0]
        # Fetch interests
        interests_response = (
            database_service.get_db()
            .table("UserInterest")
            .select("interest")
            .eq("userId", user_id)
            .execute()
        )
        interests = [item["interest"] for item in interests_response.data] if interests_response.data else []
        user["interests"] = interests
        return user
    return {}

def create_user(user_data):
    """
    Args:
        user_data (dict): user details

    Returns:
        string: unique UUID of the inserted data (empty string if failed)
    """
    # sign up an account
    response = (
        database_service.get_db()
        .auth
        .sign_up({
            "email": user_data['email'],
            'password': user_data['password']
        })
    )

    if not response.user.id:
        return ''
    
    user_id = response.user.id

    user_data['userId'] = str(user_id)
    user_data.pop('password', None)

    interests = user_data.pop('interests', None)

    response = (
        database_service.get_db()
        .table('User')
        .insert(user_data)
        .execute()
    )

    if len(response.data) == 1:
        interest_records = []
        for interest in interests:
            interest_records.append({ "userId": user_id, "interest": interest})

        response = (
            database_service.get_db()
            .table('UserInterest')
            .insert(interest_records)
            .execute()
        )

        return user_id
    return ''

def edit_user(user_id, update_data):
    """
    Args:
        user_id (string): user UUID
        update_data (dict): user details to be updated

    Returns:
        string: unique UUID of the updated data (empty string if failed)
    """
    # Handle interests update
    if "interests" in update_data:
        # Delete old interests
        response = (
            database_service.get_db()
            .table('UserInterest')
            .delete()
            .eq('userId', user_id)
            .execute()
        )

        interests = update_data.pop("interests")
        if interests:
            interest_records = [
                {
                    "userId": user_id, 
                    "interest": interest
                } for interest in interests
            ]
            response = (
                database_service.get_db()
                .table('UserInterest')
                .insert(interest_records).execute()
            )

    response = (
        database_service.get_db()
        .table('User')
        .update(update_data)
        .eq('userId', user_id)
        .execute()
    )

    if len(response.data) == 1:
        return user_id
    return ''

def delete_user(user_id):
    """
    Args:
        user_id (string): user UUID

    Returns:
        string: unique UUID of the deleted data (empty string if failed)
    """
    
    response = (
        database_service.get_db()
        .table('UserInterest')
        .delete()
        .eq("userId", user_id)
        .execute()
    )

    response = (
        database_service.get_db()
        .table("User")
        .delete()
        .eq("userId", user_id)
        .execute()
    )
    if len(response.data) != 1:
        return ''
    
    response = (
        database_service.get_auth_admin()
        .auth
        .admin
        .delete_user(user_id)
    )
    return user_id