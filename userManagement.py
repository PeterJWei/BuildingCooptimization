import web
import cloudserver
import subprocess as command

urls = ("/","userManagement",
	"/newUser/", "newUserManagement",
	"/checkUser/", "checkLogin",
	"/returnUser/", "checkLoginNew",
	"/login/", "login",
	"/loginWeb/", "loginWeb",
	"/logout/", "logout",
	"/addPush/", "addPush",
	"/addDevice/", "addDevice")

class userManagement:
	def POST(self):
		raw_data=web.data()
		userData=raw_data.split(',')
		if (len(userData) == 0):
			return "no username provided"
		length = len(userData)
		deviceID = userData[0]
		if (len(userData) == 1):
			if (not cloudserver.db.deviceIDCheckAvailability(deviceID)):
				return "0" #already registered
			else:
				return "1" #need to register
		if (len(userData) == 2):
			if (not cloudserver.db.deviceIDCheckAvailability(deviceID)): #not available
				return "device already registered"
			if (not cloudserver.db.screenNameCheckAvailability(userData[1])): #not available
				return "screen name taken"
			cloudserver.db.screenNameRegister(userData[1], deviceID, True)
			return "0"
		if (len(userData) == 3):
			cloudserver.db.userIDRemoveAll(deviceID)
			return "0"
		if (len(userData) == 4): # device ID, username, nothing, nothing
			username = userData[1]
			if (cloudserver.db.updateName(deviceID, username)):
				return "0" #successfully changed device ID
			        
                        else:
				return "1" #screen name not found
		return "too many parameters"

class newUserManagement:
	def POST(self):
		raw_data=web.data()
		userData=raw_data.split(',')
		if (len(userData) != 4):
			return "1"
		deviceID = userData[0]
		name = userData[1]
		email = userData[2]
		password = userData[3]
		if (cloudserver.db.fullRegistration(deviceID, name, email, password)):
                        print "Updating Dashboard"
                        dash = command.Popen("python /home/icsl/python_webservice/static/freeboard/genDash.py > /home/icsl/python_webservice/static/freeboard/dashboard.json", stdout = command.PIPE, shell = True)
                        (output, err) = dash.communicate()
                        dash_status = dash.wait()
                        print "status of dashboard update:", output
			return "0"
		else:
			return "2"

class checkLogin:
	def POST(self):
		raw_data=web.data()
		return cloudserver.db.checkLoginFlow(raw_data)

class checkLoginNew:
	def POST(self):
		raw_data=web.data()
		status = cloudserver.db.checkLoginFlow(raw_data)
		username = ""
		if (status == "0" or status == "1"):
			username = cloudserver.db.getNameFromDeviceID(raw_data)
		json_return = {
			"status":status,
			"username":username,
			"energySaved":0,
			"labname":"unknown",
			"rewardsClaimed":0,
			"suggestionsTaken":0
		}
		return cloudserver.db._encode(json_return, False)

class login:
	def POST(self):
		raw_data=web.data()
		userData=raw_data.split(',')
		if (len(userData) != 3):
			return "1"
		deviceID = userData[0]
		email = userData[1]
		password = userData[2]
		print("device ID is " + str(deviceID))
		return cloudserver.db.login(deviceID, email, password)

##########################################
class loginWeb:
	def POST(self):
		raw_data=web.data()
		userData=raw_data.split(',')
		if (len(userData) != 2):
			return "1"
		email = userData[0]
		password = userData[1]
		return cloudserver.db.loginWeb(email, password)
##########################################


class addPush:
	def POST(self):
		raw_data=web.data()
		userData=raw_data.split(',')
		if (len(userData) != 2):
			return "1"
		deviceID = userData[0]
		token = userData[1]
		return cloudserver.db.addPushToken(deviceID, token)

class addDevice:
	def POST(self):
		raw_data=web.data()
		userData=raw_data.split(',')
		if (len(userData) != 2):
			return "1"
		deviceID = userData[0]
		deviceToken = userData[1]
		return cloudserver.db.addDeviceToken(deviceID, deviceToken)

class logout:
	def POST(self):
		raw_data=web.data()
		return cloudserver.db.logout(raw_data)

	def GET(self):
		user_data = web.input(id=None)
		if user_data.id == None:
			return "Error: please provide valid user ID."
		if (cloudserver.db.getControl(user_data.id) == True):
			return "true"
		else:
			return "false"
		return "true"


userMGM = web.application(urls, locals());