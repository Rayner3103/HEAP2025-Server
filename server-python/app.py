from flask import Flask, request
from flask_cors import CORS
from flask_apscheduler import APScheduler

from werkzeug.utils import secure_filename

from services import web as web_service
from services import event as event_service
from services import user as user_service
from services import asset as asset_service
from services import utils

class Config:
	SCHEDULER_API_ENABLED = True

app = Flask(__name__)
app.config.from_object(Config())
CORS(
	app, 
	origins=[
		"http://localhost:5173",
		"https://heap-2025-client-nxadv9yht-rayner3103s-projects.vercel.app"
	], 
	supports_credentials=True, 
	methods=["GET", "POST", "OPTIONS", "DELETE", "PATCH"], 
	allow_headers=["Content-Type", "Authorization"]
)

scheduler = APScheduler()
scheduler.init_app(app)

@scheduler.task('cron', id='do_job_2', minute='*')
def job2():
	print('Job 2 executed')
scheduler.start()

@app.route("/event", methods=["GET", "POST", "PATCH", "DELETE"])
def event():
	# TODO: make GET, PATCH, DELETE accessible to only those created the event
	match request.method:
		case "GET":
			try:
				event_id = request.args['eventId']
			except:
				return web_service.sendBadRequest("Invalid request body")
			
			try:
				event = event_service.get_event_detail(event_id)
				if (event == {}):
					return web_service.sendBadRequest("Event not exists")
				return web_service.sendSuccess(event)
			except Exception as e:
				return web_service.sendInternalError(str(e))
		case "POST":
			try:
				event_data = dict(request.form)
			except:
				return web_service.sendBadRequest("Invalid request body")
			
			try:
				if (not event_service.validate_create_fields(event_data)):
					return web_service.sendBadRequest("Event data is invalid")
				event_id = event_service.create_event(event_data, "")
				if event_id == "":
					return web_service.sendInternalError("Unable to create event")
				
                # handle file uploads
				files = request.files.getlist("file")
				for file in files:
					if file.filename != '':
						asset_id = asset_service.create_asset(file)
						if asset_id == "":
							return web_service.sendInternalError("Cannot create asset")
						link_success = asset_service.link_asset(event_id, asset_id)
						if not link_success:
							return web_service.sendInternalError("Cannot link asset")
				return web_service.sendSuccess(event_id)
			except Exception as e:
				return web_service.sendInternalError(str(e))
		case "PATCH":
			try:
				update_data = request.get_json()['updateData']
				event_id = request.get_json()['eventId']
			except:
				return web_service.sendBadRequest("Invalid request body")
			
			try:
				if (not event_service.validate_edit_fields(update_data)):
					return web_service.sendBadRequest("Event data is invalid")

				event = event_service.get_event_detail(event_id)
				if (event == {}):
					return web_service.sendBadRequest("Event not exists")

				result = event_service.edit_event(event_id, update_data)
				if result == "":
					return web_service.sendInternalError("Unable to edit user")
				return web_service.sendSuccess(result)
			except Exception as e:
				return web_service.sendInternalError(str(e))
		case "DELETE":
			try:
				event_id = request.get_json()['eventId']
			except:
				return web_service.sendBadRequest("Invalid request body")
			
			try:
				event = event_service.get_event_detail(event_id)
				if (event == {}):
					return web_service.sendBadRequest("Event not exists")
				
				result = event_service.delete_event(event_id)
				if (result == ""):
					return web_service.sendInternalError("Unable to delete event")
				return web_service.sendSuccess(result)
			except Exception as e:
				return web_service.sendInternalError(str(e))
		case _:
			return web_service.sendMethodNotAllowed()
		
@app.route("/user", methods=["GET", "POST", "PATCH", "DELETE"])
def user():
	# TODO: make GET, PATCH, DELETE accessible to only the user itself
	match request.method:
		case "GET":
			try:
				user_id = request.args['userId']
			except:
				return web_service.sendBadRequest("Invalid request body")
			try:
				
				user = user_service.get_user_detail(user_id)
				if (user == {}):
					return web_service.sendBadRequest("User not exists")
				return web_service.sendSuccess(user)
			except Exception as e:
				return web_service.sendInternalError(str(e))
		case "POST":
			try:
				user_data = request.get_json()['userData']
			except:
				return web_service.sendBadRequest("Invalid request body")
			try:
				if (not user_service.validate_create_fields(user_data)):
					return web_service.sendBadRequest("User data is invalid")
				
				result = user_service.create_user(user_data)
				if result == "":
					return web_service.sendInternalError("Unable to create user")
				return web_service.sendSuccess(result)
			except Exception as e:
				return web_service.sendInternalError(str(e))
		case "PATCH":
			try:
				update_data = request.get_json()['updateData']
				user_id = request.get_json()['userId']
			except:
				return web_service.sendBadRequest("Invalid request body")
			try:
				
				if (not user_service.validate_edit_fields(update_data)):
					return web_service.sendBadRequest("User data is invalid")
				
				user = user_service.get_user_detail(user_id)
				if user == {}:
					return web_service.sendBadRequest("User not exists")
					
				result = user_service.edit_user(user_id, update_data)
				if result == "":
					return web_service.sendInternalError("Unable to edit user")
				return web_service.sendSuccess(result)
			except Exception as e:
				return web_service.sendInternalError(str(e))
		case "DELETE":
			try:
				user_id = request.get_json()['userId']
			except:
				return web_service.sendBadRequest("Invalid request body")
			try:
				
				user = user_service.get_user_detail(user_id)
				if (user == {}):
					return web_service.sendBadRequest("User not exists")
				
				result = user_service.delete_user(user_id)
				if (result == ""):
					return web_service.sendInternalError("Unable to delete user")
				return web_service.sendSuccess(result)
			except Exception as e:
				return web_service.sendInternalError(str(e))
		case _:
			return web_service.sendMethodNotAllowed()

@app.route('/asset', methods=["POST", "DELETE"])
def asset():
	match request.method:
		case "POST":
			try:
				req = dict(request.form)
				event_id = req["eventId"]
			except:
				return web_service.sendBadRequest("Invalid request body")
			
			try:
				# check if event existed
				event = event_service.get_event_detail(event_id)
				if (event == {}):
					return web_service.sendBadRequest("Event not exists")

                # handle file uploads
				files = request.files.getlist("file")
				for file in files:
					if file.filename != '':
						asset_id = asset_service.create_asset(file)
						if asset_id == "":
							return web_service.sendInternalError("Cannot create asset")
						link_success = asset_service.link_asset(event_id, asset_id)
						if not link_success:
							return web_service.sendInternalError("Cannot link asset")
				return web_service.sendSuccess(event_id)
			except Exception as e:
				return web_service.sendInternalError(str(e))
		case "DELETE":
			try:
				event_id = request.get_json()['eventId']
				asset_id = request.get_json()['assetId']
			except:
				return web_service.sendBadRequest("Invalid request body")
			
			try:
				event = event_service.get_event_detail(event_id)
				if (event == {}):
					return web_service.sendBadRequest("Event not exists")
				if not asset_service.validate_asset_id():
					return web_service.sendBadRequest("Asset not exists")
					
				if asset_service.unlink_asset(event_id, asset_id):
					web_service.sendSuccess("Unlinked success")
				return web_service.sendInternalError("Unable to unlink asset")
			except Exception as e:
				return web_service.sendInternalError(str(e))
		case _:
			return web_service.sendMethodNotAllowed()
				

if __name__ == '__main__':
	app.run(debug=True)