from services import database as database_service
from services import utils

# TODO: hande edit & read & list event tag

ALLOWED_FIELDS = {
    "title",
    "briefDescription",
    "descripiton",
    "eventType",
    "organisers",
    "startTime",
    "endTime",
    "mode",
    "venue",
    "signupDeadline",
    "signupLink",
    "tags",
    "origin",
    "link",
    "additionalInformation"
}

REQUIRED_FIELDS = {"title", "eventType", "mode", "origin"}

EVENT_TYPE_ENUM = {"Talks", "Workshops", "Case Comps", "Hackathons", "Others"}
MODE_ENUM = {"offline", "online", "hybrid", "tba", "unknown"}
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
    if event_data.get("origin"):
        enum_check &= event_data.get("origin") in ORIGIN_ENUM

    return (
        utils.validate_allowed_field(ALLOWED_FIELDS, event_data) and
        enum_check
    )


def list_events():
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
    db = database_service.get_db()
    response = (
        db
        .table("Event")
        .select("*")
        .execute()
    )
    events = response.data

    for i in range(len(events)):
        event = events[i]

        signup_link = event['signupLink']
        response = (
            db
            .table("EventTag")
            .select("*")
            .eq('signupLink', signup_link)
            .execute()
        )
        if response.data:
            events[i]['tags'] = [data['tag'] for data in response.data]
        else:
            events[i]['tags'] = []

    return events

def get_event_detail(signup_link):
    """
    Gets specificevent details

    Args:
        signup_link (string): unique signup_link of event

    Returns:
        dict: data of one event
    """
    response = (
        database_service.get_db()
        .table("Event")
        .select("*")
        .eq("signupLink", signup_link)
        .execute()
    )
    if len(response.data) == 1:
        event = response.data[0]

        signup_link = event['signupLink']
        response = (
            database_service.get_db()
            .table("EventTag")
            .select("*")
            .eq('signupLink', signup_link)
            .execute()
        )
        if response.data:
            event['tags'] = [data['tag'] for data in response.data]
        else:
            event['tags'] = []
        return event
    return {}

def create_event(event_data, user_id):
    """
    Args:
        event_data (dict): event details
        user_id (string): UUID of user that creates the event
    Returns:
        string: unique signupLink of the inserted data (empty string if failed)
    """
    event_data['createdUserId'] = str(user_id)
    tags = event_data.pop('tags', None)
    
    response = (
        database_service.get_db()
        .table('Event')
        .insert(event_data)
        .execute()
    )

    if len(response.data) == 1:
        tag_records = []
        for tag in tags:
            tag_records.append({ "signupLink": event_data['signupLink'], "tag": tag})

        response = (
            database_service.get_db()
            .table('EventTag')
            .insert(tag_records)
            .execute()
        )

        return event_data['signupLink']
    return ''

def edit_event(signup_link, update_data):
    """
    Args:
        signup_link (string): event signup link
        update_data (dict): event details to be updated

    Returns:
        string: unique signup_link of the updated data (empty string if failed)
    """
    # Handle tags update
    if "tags" in update_data:
        # Delete old tags
        response = (
            database_service.get_db()
            .table('EventTag')
            .delete()
            .eq('signupLink', signup_link)
            .execute()
        )

        tags = update_data.pop("interests")
        if tags:
            tag_records = [
                {
                    "signupLink": signup_link, 
                    "tag": tag
                } for tag in tags
            ]
            response = (
                database_service.get_db()
                .table('EventTag')
                .insert(tag_records).execute()
            )

    response = (
        database_service.get_db()
        .table('Event')
        .update(update_data)
        .eq('signupLink', signup_link)
        .execute()
    )

    if len(response.data) == 1:
        return signup_link
    return ''

def delete_event(signup_link):
    """
    Args:
        signup_link (string): event signup link

    Returns:
        string: unique UUID of the deleted data (empty string if failed)
    """
    response = (
        database_service.get_db()
        .table('EventTag')
        .delete()
        .eq("signupLink", signup_link)
        .execute()
    )
    
    response = (
        database_service.get_db()
        .table("Event")
        .delete()
        .eq("signupLink", signup_link)
        .execute()
    )
    if len(response.data) == 1:
        return signup_link
    return ''