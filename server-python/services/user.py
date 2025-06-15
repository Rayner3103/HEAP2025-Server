import uuid
from services import database as database_service
from services import utils

ALLOWED_FIELDS = {
    "pastEventIds",
    "name",
    "password",
    "age",
    "gender",
    "nationality",
    "mobileNumber",
    "email",
    "organisation",
    "interests",
    "role"
}

REQUIRED_FIELDS = {"password", "email", "role", "gender", "nationality"}

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
    if user_data.get("role"):
        enum_check &= user_data.get("role") in ROLE_ENUM

    email_check = "email" not in user_data or ("email" in user_data and utils.validate_email(user_data.get("email")))

    return (
        utils.validate_allowed_field(ALLOWED_FIELDS, user_data) and
        enum_check and
        email_check
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
        return response.data[0]
    return {}

def create_user(user_data):
    """
    Args:
        user_data (dict): user details

    Returns:
        string: unique UUID of the inserted data (empty string if failed)
    """

    # ensure creation of unique UUID
    user_id = uuid.uuid4()
    retrieved_user = get_user_detail(user_id)
    while (retrieved_user != {}):
        user_id = uuid.uuid4()

    user_data['userId'] = str(user_id)
    response = (
        database_service.get_db()
        .table('User')
        .insert(user_data)
        .execute()
    )

    if len(response.data) == 1:
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
        .table("User")
        .delete()
        .eq("userId", user_id)
        .execute()
    )
    if len(response.data) == 1:
        return user_id
    return ''