import os
import uuid
from werkzeug.utils import secure_filename
from services import database as database_service
from services import utils

UPLOAD_FOLDER = './uploads'
SERVER_ASSET_PATH = os.getenv("SERVER_ASSET_PATH")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # This will create the folder if it doesn't exist

def validate_asset_id(asset_id):
    return asset_id in [f for f in os.listdir(UPLOAD_FOLDER)]

def get_assets_by_event_id(event_id):
    """
    Args: 
        event_id (string): event id that is realted to the assets

    Return:
        array of string: a list of paths to the asset access route (e.g. https://localhost:5000/uploads/<asset_id>)
    """
    response = (
        database_service.get_db()
        .table("AssetMap")
        .select("*")
        .eq("eventId", event_id)
        .execute()
    )

    result = []
    if (response and response.data):
        for record in response.data:
            result.append(record['assetId'])

    return result   
         
def get_all_assets():
    """
    Return:
        array of tuple (event_id, paths to the asset): all records in the assetMap table
    """
    response = (
        database_service.get_db()
        .table("AssetMap")
        .select("*")
        .execute()
    )

    result = dict()
    if (response and response.data):
        for record in response.data:
            if record['eventId'] not in result:
                result[record['eventId']] = []
            result[record['eventId']].append((record['assetId']))

    return result       

def link_asset(event_id, asset_id):
    """
    Args:
        event_id (string): event eventId
        asset_id (string): asset UUID

    Return:
        boolean: True if the operation is successful
    """
    # check if the link has existed
    response = (
        database_service.get_db()
        .table("AssetMap")
        .select("*")
        .eq("assetId", asset_id)
        .eq("eventId", event_id)
        .execute()
    )
    if len(response.data) > 0:
        return True

    # link the asset with event
    response = (
        database_service.get_db()
        .table("AssetMap")
        .insert(dict({
            "eventId": str(event_id),
            "assetId": str(asset_id)
        }))
        .execute()
    )
    if len(response.data) != 1:
        return False
    
    # update the asset table for number of reference
    currentCount = (
        database_service.get_db()
        .table("Asset")
        .select("numberOfReference")
        .eq("assetId", asset_id)
        .single()
        .execute()
        .data
        .get("numberOfReference")
    )

    response = (
        database_service.get_db()
        .table("Asset")
        .update({"numberOfReference": currentCount + 1})
        .eq("assetId", asset_id)
        .execute()
    )

    return len(response.data) == 1

def unlink_asset(event_Id, asset_id):
    """
    Args:
        event_Id (string): event eventId
        asset_id (string): asset UUID

    Return:
        boolean: True if the operation is successful  
    """
    # Remove from db
    response = (
        database_service.get_db()
        .table("AssetMap")
        .delete()
        .eq("eventId", event_Id)
        .eq("assetId", asset_id)
        .execute()
    )
    if (len(response.data) != 1):
        return False        
    
    # check if still referenced by others
    currentCount = (
        database_service.get_db()
        .table("Asset")
        .select("numberOfReference")
        .eq("assetId", asset_id)
        .single()
        .execute()
        .data
        .get("numberOfReference")
    )

    if currentCount > 1:
        response = (
            database_service.get_db()
            .table("Asset")
            .update({"numberOfReference": currentCount - 1})
            .eq("assetId", asset_id)
            .execute()
        )
    else:
        response = (
            database_service.get_db()
            .table("Asset")
            .delete()
            .eq("assetId", asset_id)
            .execute()
        )

        if len(response.data) != 1:
            return False
        
        os.remove(os.path.join(UPLOAD_FOLDER, asset_id))
    return len(response.data) == 1

def create_asset(asset):
    """
    Takes in an asset and save it to file system if the file has not been in the system. Otherwise, return UUID associated to the asset. 

    Args:
        asset (file): a file that is being uploaded
    Return:
        string: asset UUID (empty string if failed)    
    """
    # check if file is totally new
    for f in os.listdir(UPLOAD_FOLDER):
        if (f == "temp"):
            continue
        if utils.files_are_equal(os.path.join(UPLOAD_FOLDER, f), asset):
            asset.seek(0)
            asset_id = str(f)
            return asset_id
    
    # generate asset UUID
    asset_id = str(uuid.uuid4())
    all_assets_id = [f for f in os.listdir(UPLOAD_FOLDER)]
    while (asset_id in all_assets_id):
        asset_id = str(uuid.uuid4())

    # save asset
    asset.seek(0)
    asset.save(os.path.join(UPLOAD_FOLDER, asset_id))

    # insert and entry in db
    asset.seek(0, 2)  # Move to end of file
    file_size = asset.tell()
    asset.seek(0)     # Reset pointer to start

    file_name = secure_filename(asset.filename)
    asset_data = dict({
        "assetId": asset_id,
        "fileSize": file_size,
        "originalFileName": file_name,
        "numberOfReference": 0
    })

    response = (
        database_service.get_db()
        .table("Asset")
        .insert(asset_data)
        .execute()
    )

    if len(response.data) != 1:
        return ""
    return asset_id
