from flask import Flask, request
from flask_cors import CORS
from flask_apscheduler import APScheduler

import json

from supabase import AuthApiError

from services import web as web_service
from services import event as event_service
from services import user as user_service
from services import asset as asset_service
from services import auth as auth_service
from services import webscrape as webscrape_service

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

@scheduler.task('cron', id='do_job_2', minute='*/5')
def job2():
	print('Scrapping...')
	data = webscrape_service.scrape(print_mode="critical")
	with open('output.json', 'w') as f:
		json.dump(data, f, indent=2, ensure_ascii=False)
	print('Scrapping ended.')
# scheduler.start()

@app.route("/event", methods=["GET", "POST", "PATCH", "DELETE"])
def event():
	match request.method:
		case "GET": # getting event details
			
			try:
				signup_link = request.args['signupLink']
			except:
				return web_service.sendBadRequest("Invalid request body")
			
			try:
				event = event_service.get_event_detail(signup_link)
				if (event == {}):
					return web_service.sendBadRequest("Event not exists")
				return web_service.sendSuccess(event)
			except Exception:
				return web_service.sendInternalError('Unable to retrieve event')
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
			except:
				return web_service.sendBadRequest("Invalid request body")
			
			try:
				if (not event_service.validate_create_fields(event_data)):
					return web_service.sendBadRequest("Event data is invalid")
				signup_link = event_service.create_event(event_data, user_id)
				if signup_link == "":
					return web_service.sendInternalError("Cannot create event")
				
				# handle file uploads
				files = request.files.getlist("file")
				for file in files:
					if file.filename != '':
						asset_id = asset_service.create_asset(file)
						if asset_id == "":
							return web_service.sendInternalError("Cannot create asset")
						link_success = asset_service.link_asset(signup_link, asset_id)
						if not link_success:
							return web_service.sendInternalError("Cannot link asset")
				return web_service.sendSuccess(signup_link)
			except Exception:
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
				update_data = request.get_json()['updateData']
				signup_link = request.get_json()['signupLink']
			except:
				return web_service.sendBadRequest("Invalid request body")
			
			try:
				if (not event_service.validate_edit_fields(update_data)):
					return web_service.sendBadRequest("Event data is invalid")

				event = event_service.get_event_detail(signup_link)
				if (event == {}):
					return web_service.sendBadRequest("Event not exists")
				
				if (user['role'] != 'admin' and event['createdUserId'] != user_id):
					return web_service.sendUnauthorised("You have no access to this event")

				result = event_service.edit_event(signup_link, update_data)
				if result == "":
					return web_service.sendInternalError("Unable to edit event")
				return web_service.sendSuccess(result)
			except Exception as e:
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
				signup_link = request.get_json()['signupLink']
			except:
				return web_service.sendBadRequest("Invalid request body")
			
			try:
				event = event_service.get_event_detail(signup_link)
				if (event == {}):
					return web_service.sendBadRequest("Event not exists")
				
				if (user['role'] != 'admin' and event['createdUserId'] != user_id):
					return web_service.sendUnauthorised("You have no access to this event")
				
				result = event_service.delete_event(signup_link)
				if (result == ""):
					return web_service.sendInternalError("Unable to delete event")
				return web_service.sendSuccess(result)
			except Exception as e:
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
			except Exception:
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
			except Exception as e:
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
				signup_link = req["signupLink"]
			except:
				return web_service.sendBadRequest("Invalid request body")
			
			try:
				user = user_service.get_user_detail(user_id)
				if (user == {}):
					return web_service.sendInternalError("Unexpected error. Please contact admin")
				
				# check if event existed
				event = event_service.get_event_detail(signup_link)
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
						link_success = asset_service.link_asset(signup_link, asset_id)
						if not link_success:
							return web_service.sendInternalError("Cannot link asset")
				return web_service.sendSuccess(signup_link)
			except Exception as e:
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
				signup_link = request.get_json()['signupLink']
				asset_id = request.get_json()['assetId']
			except:
				return web_service.sendBadRequest("Invalid request body")
			
			try:
				user = user_service.get_user_detail(user_id)
				if (user == {}):
					return web_service.sendInternalError("Unexpected error. Please contact admin")
				
				event = event_service.get_event_detail(signup_link)
				if (event == {}):
					return web_service.sendBadRequest("Event not exists")
				if not asset_service.validate_asset_id(asset_id):
					return web_service.sendBadRequest("Asset not exists")
				
				if user['role'] != 'admin' and user_id != event['createdUserId']:
					return web_service.sendUnauthorised("You cannot delete from this event")
					
				if asset_service.unlink_asset(signup_link, asset_id):
					return web_service.sendSuccess("Unlinked success")				
				return web_service.sendInternalError("Unable to unlink asset")
			except Exception as e:
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
			try:
				token = auth_service.sign_in(email, password)
				return web_service.sendSuccess({"access_token": token})
			except AuthApiError as e:
				return web_service.sendUnauthorised("Email or password is invalid")
			except Exception as e:
				return web_service.sendInternalError("Unable to log in")
		case _:
			return web_service.sendMethodNotAllowed()

if __name__ == '__main__':
	app.run(debug=True)