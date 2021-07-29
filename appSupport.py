import web
import cloudserver
import json

urls = ("/", "appSupport",
"/localization/", "userLocalizationAPI", 
"/userNames/", "userNames",
"/buildingFootprint/", "buildingFootprint",
"/webLogin/", "webLogin",
"/webSubmit/", "webSubmitComfort",
"/dashboardRequest/", "dashboardRequest",
"/recsSubmit/", "submitRecommendations",
"/SubmitLocation/", "submitLoc",
"/multipleUsers/", "multipleUsers")

class userNames:
	def GET(self):
		return cloudserver.db.getAllUsers()

class appSupport:
	def GET(self):
		data = web.input(id=None)
		if cloudserver.db.userIDLookup(data.id) == None:
			return "Invalid userID"
		else:
			if cloudserver.db.getControl(data.id):
				ret={
					"value":0,
					"HVAC":0,
					"Light":0,
					"Electrical":0
				}
				return cloudserver.db._encode(ret, False)
			location = cloudserver.db.getUserLocation(data.id)
			ret = cloudserver.db.calculateEnergyFootprint(location)
			return ret
		return "How did you get here"

class multipleUsers:
	def GET(self):
		data = web.input()
		ret={
			"HVAC1":0,
			"Light1":0,
			"Electrical1":0,
			"HVAC2":0,
			"Light2":0,
			"Electrical2":0,
			"HVAC3":0,
			"Light3":0,
			"Electrical3":0
		}
		location1 = cloudserver.db.getUserLocation(data.user1)
		ret1 = cloudserver.db.calculateEnergyFootprint(location1, False)
		ret["HVAC1"] = ret1["HVAC"]
		ret["Light1"] = ret1["Light"]
		ret["Electrical1"] = ret1["Electrical"]
		location2 = cloudserver.db.getUserLocation(data.user2)
		ret2 = cloudserver.db.calculateEnergyFootprint(location2, False)
		ret["HVAC2"] = ret2["HVAC"]
		ret["Light2"] = ret2["Light"]
		ret["Electrical2"] = ret2["Electrical"]
		location3 = cloudserver.db.getUserLocation(data.user3)
		ret3 = cloudserver.db.calculateEnergyFootprint(location3, False)
		ret["HVAC3"] = ret3["HVAC"]
		ret["Light3"] = ret3["Light"]
		ret["Electrical3"] = ret3["Electrical"]
		return cloudserver.db._encode(ret, False)

class webLogin:
	def POST(self):
		raw_data = web.data()
		try:
			data = json.loads(raw_data)
		except ValueError:
			print("Invalid data")
			return json.dumps({"success": False, "error": "201 Invalid Data"})
		if "PID" not in data:
			print("Invalid data")
			return json.dumps({"success": False, "error": "201 Invalid Data"})
		registered = cloudserver.db.webLogin(data["PID"])
		if not registered:
			print("Invalid ID")
			return json.dumps({"success": False, "error": "201 Invalid ID"})
		return json.dumps({"success": True})


class submitRecommendations:
	def POST(self):
		raw_data = web.data()
		try:
			data = json.loads(raw_data)
		except ValueError:
			print("Invalid recommendations")
			return json.dumps({"success": False, "error": "201 Invalid Data"})
		if "Recs" not in data or "PID" not in data or "Location" not in data:
			print("Invalid recommendations")
			return json.dumps({"success": False, "error": "201 Invalid Data"})
		print(data)
		submitted = cloudserver.db.SubmitRecommendations(data["PID"], data["Recs"], data["Location"])
		return json.dumps({"success": True})


class submitLoc:
	def POST(self):
		raw_data = web.data()
		try:
			data = json.loads(raw_data)
		except ValueError:
			print("Invalid Request, location submit")
			return json.dumps({"success": False})
		
		if "PID" not in data:
			print("No PID supplied")
			return json.dumps({"success": False})
		person = cloudserver.db.PID2Name(data["PID"])
		loc = data["Location"]
		return cloudserver.db.ReportLocationAssociation(person, loc)


class dashboardRequest:
	def POST(self):
		raw_data = web.data()
		try:
			data = json.loads(raw_data)
		except ValueError:
			print("Invalid Request")
			return json.dumps({"success": False})
		if "PID" not in data:
			print("No PID supplied")
			return json.dumps({"success": False})
		return cloudserver.db.DashboardRequest(data["PID"])


class webSubmitComfort:
	def POST(self):
		raw_data = web.data()
		try:
			data = json.loads(raw_data)
		except ValueError:
			print("Invalid data")
			return json.dumps({"success": False, "error": "201 Invalid Data"})
		if "PID" not in data or "Comfort" not in data:
			print("Invalid data")
			return json.dumps({"success": False, "error": "201 Invalid Data"})
		registered = cloudserver.db.webLogin(data["PID"])
		if not registered:
			print("Invalid ID")
			return json.dumps({"success": False, "error": "201 Not Registered"})
		if int(data["Comfort"]) < -3 or int(data["Comfort"]) > 3:
			print("Invalid Comfort")
			return json.dumps({"success": False, "error": "201 Invalid Comfort"})
		feedback = cloudserver.db.webSubmitComfort(data["PID"], data["Comfort"])
		if feedback:
			return json.dumps({"success": True})
		return json.dumps({"success": False, "error": "201 Invalid Feedback"})
	

class buildingFootprint:
	def GET(self):
		return cloudserver.db.buildingEnergyFootprint()


class userLocalizationAPI:
	def GET(self):
		return cloudserver.db.getUserLocalizationAPI()
appURL = web.application(urls, locals());
