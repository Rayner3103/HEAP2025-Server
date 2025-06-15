import re
import filecmp
import tempfile
import os
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}

def validate_email(email):
    # Simple regex for basic email validation
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return re.match(pattern, email) is not None

def validate_allowed_field(allowed_fields, data):
    return not set(data.keys()) - allowed_fields

def validate_required_field(required_fields, data):
    return not required_fields - set(data.keys())

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def files_are_equal(file_path, asset):
    asset_path = os.path.join("./uploads/temp", secure_filename(asset.filename))
    asset.save(asset_path)
    
    cmp = filecmp.cmp(file_path, asset_path, shallow=False)

    os.remove(asset_path)

    return cmp