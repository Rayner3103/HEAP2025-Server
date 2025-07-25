# TODO: Serve out the url of the image of the event. 
import os
from flask import Flask, request, send_from_directory
from flask_cors import CORS
from flask_apscheduler import APScheduler

from supabase import AuthApiError, AuthWeakPasswordError

from services import web as web_service
from services import event as event_service
from services import user as user_service
from services import asset as asset_service
from services import auth as auth_service
from services import webscrape as webscrape_service

class Config:
	SCHEDULER_API_ENABLED = True

app = Flask(__name__)
PORT = os.environ.get("PORT")
app.config.from_object(Config())
CORS(
	app, 
	origins=[
		"http://localhost:5173",
		"https://heap-2025-client.vercel.app",
	], 
	supports_credentials=True, 
	methods=["GET", "POST", "OPTIONS", "DELETE", "PATCH"], 
	allow_headers=["Content-Type", "Authorization"]
)

scheduler = APScheduler()
scheduler.init_app(app)

@scheduler.task('cron', id='do_scrape', minute='30', hour='14')
def scrape():
	print('Scrapping...')
	webscrape_service.scrape(print_mode="all")
	print('Scrapping ended.')

scheduler.start()

@app.route("/")
def index():
	print("Printing is healthy")
	return web_service.sendSuccess("Active")

@app.route('/jobs', methods=["GET"])
def list_jobs():
    jobs = scheduler.get_jobs()
    job_list = []
    for job in jobs:
        job_list.append({
            'id': job.id,
            'name': job.name,
            'trigger': str(job.trigger),
            'next_run_time': str(job.next_run_time) if job.next_run_time else "None"
        })
    return web_service.sendSuccess(job_list)

@app.route("/get_all", methods=["GET", "POST"])
def get_all():
	if request.method == "GET":
		try:
			events = event_service.list_events()
			assets = asset_service.get_all_assets()
			for event in events:
				if not event['image']:
					event['image'] = assets.get(event['eventId'])

			return web_service.sendSuccess(events)
		except Exception as e:
			print(e)
			return web_service.sendInternalError("Unable to fetch events")
	elif request.method == 'POST':
		# authentication
		try:
			user_id = auth_service.validate_user_session(request.headers)
		except AuthApiError:
			return web_service.sendUnauthorised('You do not have access to this item')
		except Exception:
			return web_service.sendInternalError('Unable to perform authentication')
		
		try:
			events = event_service.list_events()
			events = [event for event in events if event["createdUserId"] == user_id]
			assets = asset_service.get_all_assets()
			for event in events:
				if not event['image']:
					event['image'] = assets.get(event['eventId'])

			return web_service.sendSuccess(events)
		except Exception as e:
			print(e)
			return web_service.sendInternalError("Unable to fetch events")
	else:
		return web_service.sendMethodNotAllowed()

@app.route("/event", methods=["GET", "POST", "PATCH", "DELETE"])
def event():
	match request.method:
		case "GET": # getting event details
			try:
				event_id = request.args['eventId']
			except:
				return web_service.sendBadRequest("Invalid request body")
			
			try:
				event = event_service.get_event_detail(event_id)
				if (event == {}):
					return web_service.sendBadRequest("Event not exists")

				if (not event['image']):
					event['image'] = asset_service.get_assets_by_event_id(event_id)
				return web_service.sendSuccess(event)
			except Exception as e:
				print(e)
				return web_service.sendInternalError('Invalid event ID')
		case "POST": # creating event
			# authentication
			try:
				user_id = auth_service.validate_user_session(request.headers)
			except AuthApiError:
				return web_service.sendUnauthorised('You do not have access to this item')
			except Exception:
				return web_service.sendInternalError('Unable to perform authentication')

			user = user_service.get_user_detail(user_id)
			if user['role'] != 'admin' and user['role'] != 'organiser':
				return web_service.sendUnauthorised("You cannot create an event")
			
			try:
				event_data = dict(request.form)
				tags = request.form.getlist('tags')
				event_data.pop("image", '')
				event_data['tags'] = tags
			except:
				return web_service.sendBadRequest("Invalid request body")				
			
			try:
				if (not event_service.validate_create_fields(event_data)):
					return web_service.sendBadRequest("Event data is invalid")

				if event_service.check_has_event_by_signup_link_and_name(event_data['signupLink'], event_data['title']):
					return web_service.sendBadRequest("Event already exists")

				event_id = event_service.create_event(event_data, user_id)
				if event_id == "":
					return web_service.sendInternalError("Cannot create event")
				
				# handle file uploads
				files = request.files.getlist("image")
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
				print(e)
				return web_service.sendInternalError('Cannot create event')
		case "PATCH": # updating event
			# authentication
			try:
				user_id = auth_service.validate_user_session(request.headers)
			except AuthApiError:
				return web_service.sendUnauthorised('You do not have access to this item')
			except Exception:
				return web_service.sendInternalError('Unable to perform authentication')
			
			user = user_service.get_user_detail(user_id)
			if user['role'] != 'admin' and user['role'] != 'organiser':
				return web_service.sendUnauthorised("You cannot update an event")
			
			try:
				update_data = dict(request.form)
				event_id = update_data.pop("eventId", '')
				tags = request.form.getlist('tags')
				update_data.pop("image", '')
				update_data['tags'] = tags
			except Exception:
				print(update_data)
				return web_service.sendBadRequest("Invalid request body")	
			
			try:
				if (not event_service.validate_edit_fields(update_data)):
					return web_service.sendBadRequest("Event data is invalid")

				event = event_service.get_event_detail(event_id)
				if (event == {}):
					return web_service.sendBadRequest("Event not exists")

				if (user['role'] != 'admin' and event['createdUserId'] != user_id):
					return web_service.sendUnauthorised("You have no access to this event")
				
				# handle image change
				files = request.files.getlist("image")
				if len(files) > 0:
					if (not event['image']):
						asset_ids = asset_service.get_assets_by_event_id(event_id)
						for asset_id in asset_ids:
							asset_service.unlink_asset(event_id, asset_id)
					else:
						update_data['ímage'] = None

				for file in files:
					if file.filename != '':
						asset_id = asset_service.create_asset(file)
						if asset_id == "":
							return web_service.sendInternalError("Cannot create asset")
						link_success = asset_service.link_asset(event_id, asset_id)
						if not link_success:
							return web_service.sendInternalError("Cannot link asset")

				result = event_service.edit_event(event_id, update_data)
				if result == "":
					return web_service.sendInternalError("Unable to edit event")
				return web_service.sendSuccess(result)
			except Exception as e:
				print(e)
				return web_service.sendInternalError('Cannot update event')
		case "DELETE": # deleting event
			# authentication
			try:
				user_id = auth_service.validate_user_session(request.headers)
			except AuthApiError:
				return web_service.sendUnauthorised('You do not have access to this item')
			except Exception:
				return web_service.sendInternalError('Unable to perform authentication')
			
			user = user_service.get_user_detail(user_id)
			if user['role'] != 'admin' and user['role'] != 'organiser':
				return web_service.sendUnauthorised("You cannot delete an event")

			try:
				print(request.get_json())
				event_id = request.get_json()['eventId']
			except:
				return web_service.sendBadRequest("Invalid request body")
			
			try:
				event = event_service.get_event_detail(event_id)
				if (event == {}):
					return web_service.sendBadRequest("Event not exists")
				
				if (user['role'] != 'admin' and event['createdUserId'] != user_id):
					return web_service.sendUnauthorised("You have no access to this event")

				# handle delete image
				asset_ids = asset_service.get_assets_by_event_id(event_id)
				for asset_id in asset_ids:
					asset_service.unlink_asset(event_id, asset_id)
				
				result = event_service.delete_event(event_id)
				if (result == ""):
					return web_service.sendInternalError("Unable to delete event")
				return web_service.sendSuccess(result)
			except Exception as e:
				print(e)
				return web_service.sendInternalError('Cannot delete event')
		case _:
			return web_service.sendMethodNotAllowed()

@app.route("/event/<event_id>", methods=["DELETE"])
def delete_event(event_id):
	match request.method:
		case "DELETE": # deleting event
			# authentication
			try:
				user_id = auth_service.validate_user_session(request.headers)
			except AuthApiError:
				return web_service.sendUnauthorised('You do not have access to this item')
			except Exception:
				return web_service.sendInternalError('Unable to perform authentication')
			
			user = user_service.get_user_detail(user_id)
			if user['role'] != 'admin' and user['role'] != 'organiser':
				return web_service.sendUnauthorised("You cannot delete an event")
			
			try:
				event = event_service.get_event_detail(event_id)
				if (event == {}):
					return web_service.sendBadRequest("Event not exists")
				
				if (user['role'] != 'admin' and event['createdUserId'] != user_id):
					return web_service.sendUnauthorised("You have no access to this event")

				# handle delete image
				asset_ids = asset_service.get_assets_by_event_id(event_id)
				for asset_id in asset_ids:
					asset_service.unlink_asset(event_id, asset_id)
				
				result = event_service.delete_event(event_id)
				if (result == ""):
					return web_service.sendInternalError("Unable to delete event")
				return web_service.sendSuccess(result)
			except Exception as e:
				print(e)
				return web_service.sendInternalError('Cannot delete event')
		case _:
			return web_service.sendMethodNotAllowed()

		
@app.route("/user", methods=["GET", "POST", "PATCH", "DELETE"])
def user():
	match request.method:
		case "GET": # get user profile data
			# authentication
			try:
				user_id = auth_service.validate_user_session(request.headers)
			except AuthApiError:
				return web_service.sendUnauthorised('You do not have access to this item')
			except Exception:
				return web_service.sendInternalError('Unable to perform authentication')
			
			try:
				request_user_id = request.args['userId']
			except:
				return web_service.sendBadRequest("Invalid request body")
			
			try:	
				user = user_service.get_user_detail(user_id)
				if (user == {}):
					return web_service.sendInternalError("Unexpected error. Please contact admins")
				
				if user['role'] != 'admin' and user_id != request_user_id:
					return web_service.sendUnauthorised("You cannot access this user")

				request_user = user_service.get_user_detail(request_user_id)
				if (request_user == {}):
					return web_service.sendBadRequest("User not exists")
				return web_service.sendSuccess(user)
			except Exception as e:
				print(e)
				return web_service.sendInternalError('Cannot get user data')
		case "POST": # create an account
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
			except AuthWeakPasswordError as e:
				return web_service.sendBadRequest("Password must be at least 6 characters long and include at least one uppercase letter, one lowercase letter, one number, and one special character (e.g., !@#$%)")
			except Exception as e:
				print(e)
				return web_service.sendInternalError('Cannot create an account')
		case "PATCH": # update user profile
			# authentication
			try:
				user_id = auth_service.validate_user_session(request.headers)
			except AuthApiError:
				return web_service.sendUnauthorised('You do not have access to this item')
			except Exception:
				return web_service.sendInternalError('Unable to perform authentication')
			
			try:
				update_data = request.get_json()['updateData']
				request_user_id = request.get_json()['userId']
			except:
				return web_service.sendBadRequest("Invalid request body")
			
			try:
				if (not user_service.validate_edit_fields(update_data)):
					return web_service.sendBadRequest("User data is invalid")
				
				user = user_service.get_user_detail(user_id)
				if user == {}:
					return web_service.sendInternalError("Unexpected error. Please contact admin")
				
				if user['role'] != 'admin' and user_id != request_user_id:
					return web_service.sendUnauthorised("You cannot access this user")

				request_user = user_service.get_user_detail(request_user_id)
					
				result = user_service.edit_user(request_user_id, update_data)
				if result == "":
					return web_service.sendInternalError("Unable to edit user")
				return web_service.sendSuccess(result)
			except Exception as e:
				print(e)
				return web_service.sendInternalError('Cannot edit user')
		case "DELETE": # remove account
			# authentication
			try:
				user_id = auth_service.validate_user_session(request.headers)
			except AuthApiError:
				return web_service.sendUnauthorised('You do not have access to this item')
			except Exception:
				return web_service.sendInternalError('Unable to perform authentication')
			
			try:
				request_user_id = request.get_json()['userId']
			except:
				return web_service.sendBadRequest("Invalid request body")
			
			try:
				user = user_service.get_user_detail(user_id)
				if (user == {}):
					return web_service.sendInternalError("Unexpected error. Please contact admin")
				
				if user['role'] != 'admin' and user_id != request_user_id:
					return web_service.sendUnauthorised("You cannot access this user")

				request_user = user_service.get_user_detail(request_user_id)
				
				result = user_service.delete_user(request_user_id)
				if (result == ""):
					return web_service.sendInternalError("Unable to delete user")
				return web_service.sendSuccess(result)
			except Exception as e:
				print(e)
				return web_service.sendInternalError('Cannot delete user')
		case _:
			return web_service.sendMethodNotAllowed()

@app.route('/asset', methods=["POST", "DELETE"])
def asset():
	match request.method:
		case "POST": # upload files
			# authentication
			try:
				user_id = auth_service.validate_user_session(request.headers)
			except AuthApiError:
				return web_service.sendUnauthorised('You do not have access to this item')
			except Exception:
				return web_service.sendInternalError('Unable to perform authentication')
			
			try:
				req = dict(request.form)
				event_id = req["eventId"]
			except:
				return web_service.sendBadRequest("Invalid request body")
			
			try:
				user = user_service.get_user_detail(user_id)
				if (user == {}):
					return web_service.sendInternalError("Unexpected error. Please contact admin")
				
				# check if event existed
				event = event_service.get_event_detail(event_id)
				if (event == {}):
					return web_service.sendBadRequest("Event not exists")
				
				if user['role'] != 'admin' and user_id != event['createdUserId']:
					return web_service.sendUnauthorised("You cannot upload to this event")

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
				print(e)
				return web_service.sendInternalError('Cannot upload file')
		case "DELETE": # delete files
			# authentication
			try:
				user_id = auth_service.validate_user_session(request.headers)
			except AuthApiError:
				return web_service.sendUnauthorised('You do not have access to this item')
			except Exception:
				return web_service.sendInternalError('Unable to perform authentication')
			
			try:
				event_id = request.get_json()['eventId']
				asset_id = request.get_json()['assetId']
			except:
				return web_service.sendBadRequest("Invalid request body")
			
			try:
				user = user_service.get_user_detail(user_id)
				if (user == {}):
					return web_service.sendInternalError("Unexpected error. Please contact admin")
				
				event = event_service.get_event_detail(event_id)
				if (event == {}):
					return web_service.sendBadRequest("Event not exists")
				if not asset_service.validate_asset_id(asset_id):
					return web_service.sendBadRequest("Asset not exists")
				
				if user['role'] != 'admin' and user_id != event['createdUserId']:
					return web_service.sendUnauthorised("You cannot delete from this event")
					
				if asset_service.unlink_asset(event_id, asset_id):
					return web_service.sendSuccess("Unlinked success")				
				return web_service.sendInternalError("Unable to unlink asset")
			except Exception as e:
				print(e)
				return web_service.sendInternalError('Cannot delete file')
		case _:
			return web_service.sendMethodNotAllowed()

@app.route('/login', methods=["POST"])
def login():
	match request.method:
		case "POST": # login
			try:
				email = request.get_json()['email']
				password = request.get_json()['password']
			except:
				return web_service.sendBadRequest("Invalid request body")

			if (not user_service.validate_user_email(email)):
				return web_service.sendBadRequest("Email not found. Please create an account first.")

			try:
				data = auth_service.sign_in(email, password)
				return web_service.sendSuccess(data)
			except AuthApiError as e:
				return web_service.sendUnauthorised("Wrong password")
			except Exception as e:
				print(e)
				return web_service.sendInternalError("Unable to log in")
		case _:
			return web_service.sendMethodNotAllowed()

@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    return send_from_directory(uploads_dir, filename)

@app.route('/health')
def health():
		return web_service.sendSuccess("Success")

if __name__ == '__main__':
	app.run(debug=False, port=PORT, host='0.0.0.0')