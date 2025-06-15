def sendSuccess(data):
    return {"status": True, "error": "", "data": data}, 200

def sendBadRequest(error):
    return {"status": False, "error": error, "data": ""}, 400

def sendInternalError(error):
    return {"status": False, "error": error, "data": ""}, 500

def sendMethodNotAllowed():
    return {"status": False, "error": "Method Not Allowed", "data": ""}, 405