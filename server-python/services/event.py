import uuid
from services import database as database_service
from services import utils

ALLOWED_FIELDS = {
    "title",
    "tagLine",
    "descripiton",
    "eventType",
    "organisers",
    "startTime",
    "endTime",
    "mode",
    "venue",
    "signupDeadline",
    "signupLink",
    "themes",
    "eventStatus",
    "additionalInformation",
    "origin",
}

REQUIRED_FIELDS = {"title", "eventType", "mode", "eventStatus", "origin"}

EVENT_TYPE_ENUM = {"Talk", "Workshop", "Case Competition", "Hackathon", "Others"}
MODE_ENUM = {"Offline", "Online", "Hybrid", "TBA"}
EVENT_STATUS_ENUM = {"active", "postponed", "cancelled"}
ORIGIN_ENUM = {"web", "upload"}

def validate_create_fields(event_data):
    """
    Validate if event_data for create is complete

    Args:
        event_data (dict): contains client sent event_data

    Returns:
        boolean: true if all fields are intact
    """
    return (
        # check if have extra fields
        (utils.validate_allowed_field(ALLOWED_FIELDS, event_data)) and
        # check if required fields are there
        (utils.validate_required_field(REQUIRED_FIELDS, event_data)) and
        # Enum validations
        (event_data.get("eventType") in EVENT_TYPE_ENUM) and
        (event_data.get("mode") in MODE_ENUM) and
        (event_data.get("eventStatus") in EVENT_STATUS_ENUM) and
        (event_data.get("origin") in ORIGIN_ENUM)
    )

def validate_edit_fields(event_data):
    """
    Validate if event_data for edit is complete

    Args:
        event_data (dict): contains client sent event_data

    Returns:
        boolean: true if all fields are intact
    """
    enum_check = True
    if event_data.get("eventType"):
        enum_check &= event_data.get("eventType") in EVENT_TYPE_ENUM
    if event_data.get("mode"):
        enum_check &= event_data.get("mode") in MODE_ENUM
    if event_data.get("eventStatus"):
        enum_check &= event_data.get("eventStatus") in EVENT_STATUS_ENUM
    if event_data.get("origin"):
        enum_check &= event_data.get("origin") in ORIGIN_ENUM

    return (
        utils.validate_allowed_field(ALLOWED_FIELDS, event_data) and
        enum_check
    )


def list_events(filter_objects, search_term='', sort_by='', ascending=True):
    """
    list all events

    Args:
        filter_object (list of dict): a list of filter objects
        search_term (string): string to be matched with the title of the event
        sort_by (string): column name that we need to sort by
        ascending (boolean): boolean to show if we sort by ascending

    Returns:
        list of dict: a list of all events
    """

    # TODO: filtering function
    response = (
        database_service.get_db()
        .table("Event")
        .select("*")
        .ilike("title", f"%{search_term}%")
        .execute()
    )
    return response.data

def get_event_detail(event_id):
    """
    Gets specificevent details

    Args:
        event_id (string): unique UUID of event

    Returns:
        dict: data of one event
    """
    response = (
        database_service.get_db()
        .table("Event")
        .select("*")
        .eq("eventId", event_id)
        .execute()
    )
    if len(response.data) == 1:
        return response.data[0]
    return {}

def create_event(event_data, user_id):
    """
    Args:
        event_data (dict): event details
        user_id (string): UUID of user that creates the event

    Returns:
        string: unique UUID of the inserted data (empty string if failed)
    """

    # ensure creation of unique UUID
    event_id = str(uuid.uuid4())
    retrieved_event = get_event_detail(event_id)
    while (retrieved_event != {}):
        event_id = str(uuid.uuid4())

    created_user_id = database_service.get_root_user_id()

    event_data['eventId'] = str(event_id)
    event_data['createdUserId'] = str(created_user_id)
    response = (
        database_service.get_db()
        .table('Event')
        .insert(event_data)
        .execute()
    )

    if len(response.data) == 1:
        return event_id
    return ''

def edit_event(event_id, update_data):
    """
    Args:
        event_id (string): event UUID
        update_data (dict): event details to be updated

    Returns:
        string: unique UUID of the updated data (empty string if failed)
    """
    response = (
        database_service.get_db()
        .table('Event')
        .update(update_data)
        .eq('eventId', event_id)
        .execute()
    )

    if len(response.data) == 1:
        return event_id
    return ''

def delete_event(event_id):
    """
    Args:
        event_id (string): event UUID

    Returns:
        string: unique UUID of the deleted data (empty string if failed)
    """
    response = (
        database_service.get_db()
        .table("Event")
        .delete()
        .eq("eventId", event_id)
        .execute()
    )
    if len(response.data) == 1:
        return event_id
    return ''