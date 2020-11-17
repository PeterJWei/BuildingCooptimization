import pymongo
import datetime
import time
import calendar
import traceback
import json
import pprint
import copy
from threading import Thread
import sys
from watchdog import Watchdog
from Email import SendEmail

class MongoJsonEncoder(json.JSONEncoder):
	def default(self, obj):
		if isinstance(obj, datetime.datetime):
			#return obj.isoformat()
			utc_seconds = calendar.timegm(obj.utctimetuple())
			return utc_seconds
		elif isinstance(obj, datetime.date):
			return obj.isoformat()
		elif isinstance(obj, datetime.timedelta):
			return (datetime.datetime.min + obj).time().isoformat()
		elif isinstance(obj, ObjectId):
			return str(obj)
		else:
			return super(MongoJsonEncoder, self).default(obj)

def add_log(msg,obj):
	print("Got log:"+msg)
	print(obj)
	traceback.print_exc()
	pymongo.MongoClient().log_db.log.insert({
		"msg":msg,
		"obj":obj,
		"timestamp":datetime.datetime.utcnow()
		});

class DBMgr(object):
	def _GetConfigValue(self,key):
		try:
			ret=self.config_col.find_one({"_id":key})
			return ret["value"]
		except:
			return None

	def _SetConfigValue(self,key,value):
		self.config_col.replace_one({"_id":key},{"value":value},True)

	def _ReadConfigs(self):
		print("Setting up configs...")
		self.ROOM_DEFINITION=self._GetConfigValue("ROOM_DEFINITION")
		self.APPLIANCE_DEFINITION=self._GetConfigValue("APPLIANCE_DEFINITION")
		self.SAMPLING_TIMEOUT_SHORTEST=self._GetConfigValue("SAMPLING_TIMEOUT_SHORTEST")
		self.SAMPLING_TIMEOUT_LONGEST=self._GetConfigValue("SAMPLING_TIMEOUT_LONGEST")
		self.WATCHDOG_TIMEOUT_USER=self._GetConfigValue("WATCHDOG_TIMEOUT_USER")
		self.WATCHDOG_TIMEOUT_APPLIANCE=self._GetConfigValue("WATCHDOG_TIMEOUT_APPLIANCE")
		

	def _ConstructInMemoryGraph(self):
		self.list_of_rooms={};
		self.list_of_appliances={};
		self.location_of_users={};

		for room in self.ROOM_DEFINITION:
			room["appliances"]=[]
			room["users"]=[]
			self.list_of_rooms[room["id"]]=room

		for appliance in self.APPLIANCE_DEFINITION:
			appliance["value"]=0
			appliance["total_users"]=0
			appliance["rooms"].sort()
			self.list_of_appliances[appliance["id"]]=appliance
			for roomID in appliance["rooms"]:
				self.list_of_rooms[roomID]["appliances"]+=[appliance["id"]]

		for room in self.ROOM_DEFINITION:
			self.list_of_rooms[room["id"]]["appliances"].sort()
		
		## Finished appliance bipartite graph.

	def _HardcodeValues(self):
		if ("nwc1000m_light" in self.list_of_appliances):
			self.list_of_appliances["nwc1000m_light"]["value"] = 300
		if ("nwc10hallway_light" in self.list_of_appliances):
			self.list_of_appliances["nwc10hallway_light"]["value"] = 100
		if ("nwc10elevator_light" in self.list_of_appliances):
			self.list_of_appliances["nwc10elevator_light"]["value"] = 150
		if ("nwc8_light" in self.list_of_appliances):
			self.list_of_appliances["nwc8_light"]["value"] = 150
		if ("nwc7_light" in self.list_of_appliances):
			self.list_of_appliances["nwc7_light"]["value"] = 150
		if ("nwc1003b_light" in self.list_of_appliances):
			self.list_of_appliances["nwc1003b_light"]["value"] = 300


	def _GracefulReloadGraph(self):
		print('Reloading values...')
		try:
			latest_snapshot=self.todayCumulativeEnergy.find_one(sort=[("_log_timestamp", pymongo.DESCENDING)]);
			if (latest_snapshot != None):
				self.cumulativeEnergy = latest_snapshot["value"]
				print("Loaded: " + str(self.cumulativeEnergy))
			else:
				print("Didn't recover cumulative energy")
		except Exception as e: print e
		try:
			latest_snapshot=self.snapshots_col_appliances.find_one(sort=[("timestamp", pymongo.DESCENDING)]);
			if latest_snapshot!=None:
				for applianceID in latest_snapshot["data"]:
					value=latest_snapshot["data"][applianceID]["value"]
					if value>0:
						print('Recovered Appliance:',applianceID, value)
						self.updateApplianceValue(applianceID, value)
			else:
				print('Appliance latest snapshot not found.')
		except Exception:
			add_log('failed to recover appliance power values during graceful reload.',latest_snapshot)

		try:
			latest_snapshot=self.snapshots_col_users.find_one(sort=[("timestamp", pymongo.DESCENDING)]);
			if latest_snapshot!=None:
				for userID in latest_snapshot["data"]:
					roomID=latest_snapshot["data"][userID]["location"]
					print('Recovered Location:',userID,roomID)
					#self.updateUserLocation(userID, roomID, None)
			else:
				print('User location latest snapshot not found.')
		except Exception:
			add_log('failed to recover user locations during graceful reload.',latest_snapshot)
	

####################################################################
## Room ID and Appliance IDs functions #############################
####################################################################
	def RoomIdToName(self,id):
		return self.list_of_rooms[id]["name"]
	def RoomIDToLab(self,id):
		return self.list_of_rooms[id]["lab"]
	def ApplIdToName(self,id):
		return self.list_of_appliances[id]["name"]
	def ApplIdToVal(self,id):
		return self.list_of_appliances[id]["value"]
	def ApplIdToType(self,id):
		return self.list_of_appliances[id]["type"]
	def ApplIdToRoom(self,id):
		return self.list_of_appliances[id]["room"]
####################################################################

	def _encode(self,data,isPretty):
		return MongoJsonEncoder().encode(data)
	def __init__(self, start_bg_thread=True):
		self.dbc=pymongo.MongoClient()

		self.registration_col1=self.dbc.db.registration_col1
		self.ranking = self.dbc.db.ranking
		self.config_col=self.dbc.db.config
		self.raw_data=self.dbc.db.raw_data
		self.snapshots_col_rooms=self.dbc.db.snapshots_col_rooms
		self.snapshots_col_appliances=self.dbc.db.snapshots_col_appliances
		self.snapshots_col_users=self.dbc.db.snapshots_col_users

		self.snapshots_parameters=self.dbc.db.snapshots_parameters
		self._latestSuccessShot=0

		self._ReadConfigs()
		self.watchdog = Watchdog(
			self.WATCHDOG_TIMEOUT_USER,
			self.WATCHDOG_TIMEOUT_APPLIANCE)
		## Data Structure Init: bipartite graph between rooms and appls
		## TODO: Add a web interface to update config in db, and pull new config into memory.

		self._ConstructInMemoryGraph()
		## Construct bipartite graph.
		# self._accumulator()
		self._GracefulReloadGraph()
		## Read appliance values from database; TODO: occupants location
		self._HardcodeValues()

		# self.watchdogInit()

		if start_bg_thread:
			self.startDaemon()

		self.snapshots_col_rooms=self.dbc.db.snapshots_col_rooms
		self.snapshots_col_appliances=self.dbc.db.snapshots_col_appliances
		self.snapshots_col_users=self.dbc.db.snapshots_col_users
		## Start the snapshot thread if not running "python DBMgr.py"
		## (perform self-test if it is.)

		##if __name__ != "__main__":
		##	self.recover_from_latest_shot()

	def startDaemon(self):
		t=Thread(target=self._backgroundLoop,args=())
		t.setDaemon(True)
		t.start()

	def _now(self):
		return calendar.timegm(datetime.datetime.utcnow().utctimetuple())
	def _toUnix(self, ts):
		return calendar.timegm(ts.utctimetuple())
	def _backgroundLoop(self):
		print("DBMGR _backgroundLoop started...")
		while True:
			time.sleep(self.SAMPLING_TIMEOUT_LONGEST)
			self.SaveShot()
			self.watchdogCheckUser()
			self.watchdogCheckAppliance()

	def _getShotRooms(self, concise=True):
		return self.list_of_rooms
	def _getShotAppliances(self, concise=True):
		return self.list_of_appliances
	def _getShotPersonal(self, concise=True):
		personal_consumption={}
		cached_per_room_consumption={}
		for user_id in self.location_of_users:
			try:
				roomID=self.location_of_users[user_id]
				if roomID==None:
					continue
				if (roomID not in cached_per_room_consumption):
					cached_per_room_consumption[roomID]=self.calculateRoomFootprint(roomID)
				personal_consumption[user_id]=cached_per_room_consumption[roomID]
				personal_consumption[user_id]["location"]=roomID
			except:
				add_log("fail to trace person's consumption; id:",user_id)

		return personal_consumption

	def updateApplianceValue(self, applianceID, value):
		self.list_of_appliances[applianceID]["value"]=int(float(value))

	def calculateRoomFootprint(self, roomID):
		app_list=self.list_of_rooms[roomID]["appliances"]
		ret={
			"value":0,
			"consumptions":[]
		}
		total_con=0.0
		for applianceID in app_list:
			app=self.list_of_appliances[applianceID]
			app["share"]=app["value"]/(1.0*app["total_users"])

			total_con+=app["share"]
			ret["consumptions"]+=[app]
		ret["value"]=total_con
		return ret

	def calculateEnergyFootprint(self, roomID, encoded=True):
		ret={
			"value":0,
			"HVAC":0,
			"Light":0,
			"Electrical":0
		}
		if (roomID is None):
			return ret
		app_list=self.list_of_rooms[roomID]["appliances"]
		total_con = 0.0
		print("starting appliances")
		for applianceID in app_list:
			app = self.list_of_appliances[applianceID]
			appValue = app["value"]/(1.0*app["total_users"])
			total_con += appValue
			if (app["type"] == "Electrical"):
				ret["Electrical"] += appValue
				continue
			if (app["type"] == "HVAC"):
				ret["HVAC"] += appValue
				continue
			if (app["type"] == "Light"):
				ret["Light"] += appValue
		ret["value"]=total_con
		if (encoded):
			return self._encode(ret, False)
		return ret

	def ReportEnergyValue(self, applianceID, value, raw_data=None):
		"maintenance tree node's energy consumption item, and update a sum value"
		known_room=None
		try:
			if (applianceID not in self.list_of_appliances):
				print("applianceID " + applianceID + " not in list of appliances.")
				return
			app=self.list_of_appliances[applianceID]
			known_room=app["rooms"]
			if value<0:
				add_log("Negative value found on energy report?",{
					"deviceID":applianceID,
					"value":value,
					"raw":raw_data
					})
				return
			self.updateApplianceValue(app["id"], value)

		except:
			add_log("failed to report energy value on device",{
				"known_room":known_room,
				"deviceID":applianceID,
				"value":value,
				"raw":raw_data
				})
			return

		self.LogRawData({
			"type":"energy_report",
			"roomID":known_room,
			"applianceID":applianceID,
			"value":value,
			"raw":raw_data
			})
		self.watchdog.watchdogRefresh_Appliance(applianceID)

	def watchdogRefresh_User(self, userID):
		if userID not in self.watchdog.watchdogLastSeen_User:
			self.watchdog.watchdogLastSeen_User[userID]=0
		self.watchdog.watchdogLastSeen_User[userID]=max(self._now(), self.watchdog.watchdogLastSeen_User[userID])

	def updateUserLocation(self, user_id, in_id=None, out_id=None):
		self.location_of_users[user_id]=in_id
		if in_id==out_id:
			return
		## TODO: optimize, merge In-ops and Out-ops and remove unnecessary update to common appliances
		if in_id!=None and self.list_of_rooms[in_id]!=None:
			self.list_of_rooms[in_id]["users"]+=[user_id]
			for applianceID in self.list_of_rooms[in_id]["appliances"]:
				self.list_of_appliances[applianceID]["total_users"]+=1
		if out_id!=None and self.list_of_rooms[out_id]!=None:
			if (user_id in self.list_of_rooms[out_id]["users"]):
				self.list_of_rooms[out_id]["users"].remove(user_id)
				for applianceID in self.list_of_rooms[out_id]["appliances"]:
					self.list_of_appliances[applianceID]["total_users"]-=1

	def LogRawData(self,obj):
		obj["_log_timestamp"]=datetime.datetime.utcnow()
		self.raw_data.insert(obj)

	def watchdogCheckUser(self):
		outOfRange_List=[]
		minTime=self._now()-self.watchdog.WATCHDOG_TIMEOUT_USER

		for userID in self.watchdog.watchdogLastSeen_User:
			if self.watchdog.watchdogLastSeen_User[userID]<minTime:
				outOfRange_List+=[userID]
				if userID in location_of_users:
					oldS=location_of_users[userID]
					self.updateUserLocation(userID, "outOfLab", oldS)
		for userID in self.location_of_users:
			if userID not in self.watchdog.watchdogLastSeen_User:
				oldS=self.location_of_users[userID]
				self.updateUserLocation(userID, "outOfLab", oldS)

		self.LogRawData({
			"type":"watchdogCheck_User",
			"time":self._now(),
			"minTime":minTime,
			"outOfRange_List":outOfRange_List,
			"raw":self.watchdog.watchdogLastSeen_User,
			})
		for userID in outOfRange_List:
			if (userID in self.watchdog.watchdogLastSeen_User):
				last_seen=self.watchdog.watchdogLastSeen_User[userID]
			else:
				last_seen=None
			#self.ReportLocationAssociation(userID, "outOfLab", {"Note":"Reported by Watchdog","last_seen": last_seen})

	def ReportLocationAssociation(self, personID, roomID, raw_data=None):
		#self.watchdogUserLastSeen()
		print("Reporting Location for user:")
		print(personID)
		oldS=None
		newS=roomID
		if personID in self.location_of_users:
			oldS=self.location_of_users[personID]

		self.LogRawData({
			"type":"location_report",
			"roomID":roomID,
			"personID":personID,
			"raw":raw_data,
			"oldS":oldS,
			"newS":newS
			})
		self.watchdogRefresh_User(personID)

		if roomID!=None and roomID not in self.list_of_rooms:
			#"if no legitimate roomID, then he's out of tracking."
			newS=None
			# self.recordEvent(personID,"illegitimateLocationReported",roomID)
		# else:
			# self.recordEvent(personID,"locationChange",roomID)

		self.updateUserLocation(personID, newS, oldS)

		if newS!=None:
			self.list_of_rooms[newS]["phantom_user"]=personID
			self.list_of_rooms[newS]["phantom_time"] = int(time.mktime(datetime.datetime.now().timetuple()))

		#"people change; should we update now?"
		self.OptionalSaveShot();

	def watchdogCheckAppliance(self):
		notWorking_List=[]
		minTime=self._now()-self.watchdog.WATCHDOG_TIMEOUT_APPLIANCE
		futureTime=self._now()+86400
		
		#for applID in self.watchdogLastSeen_Appliance:
		for applID in self.list_of_appliances:
			if self.list_of_appliances[applID]["value"]>0:
				# for all working(value>0) appliances
				if applID in self.watchdog.watchdogLastSeen_Appliance:
					if self.watchdog.watchdogLastSeen_Appliance[applID]<minTime:
						notWorking_List+=[applID]
				else:
					#start-up issue, maybe the first report haven't arrived yet.
					self.watchdog.watchdogLastSeen_Appliance[applID]=self._now()

		for applID in notWorking_List:
			last_seen=self.watchdog.watchdogLastSeen_Appliance[applID]
			self.watchdog.watchdogLastSeen_Appliance[applID]=futureTime
			self.ReportEnergyValue(applID, 0, {"Note":"Reported by Watchdog","last_seen": last_seen})

		title="Energy Monitoring Appliance Down: "+str(notWorking_List)
		body="Dear SysAdmin,\nThe following appliance ID has not been reporting to the system for >15 minutes."
		body+="\n\n"+"\n".join([str(x) for x in notWorking_List])+"\n\n"
		body+="Please debug as appropriate.\nNote: this warning will repeat every 24 hours."
		body+="\n\nSincerely, system watchdog."

		if len(notWorking_List)>0:
			email_ret=SendEmail(title, body)

	def ShowRealtime(self, person=None, concise=True):
		#save into database, with: timestamp, additional data
		ret={
			"timestamp":self._now()
		}
		if person and person in self.location_of_users:
			roomID=self.location_of_users[person]
			if roomID!=None:
				ret["personal"]=self.calculateRoomFootprint(roomID)
				#ret["location"]=roomID
				ret["location"]=self.list_of_rooms[roomID]
		else:
			ret["rooms"]=self._getShotRooms(concise)
			ret["appliances"]=self._getShotAppliances(concise)
			ret["personal"]=self._getShotPersonal(concise)
			ret["locations"]=self.location_of_users
			ret["watchdog_user"]=self.watchdog.watchdogLastSeen_User
			ret["watchdog_appl"]=self.watchdog.watchdogLastSeen_Appliance
		return self._encode(ret,True)

	def ShowRealtimeGraphs(self, single=True, concise=True):
		ret={
			"timestamp":self._now()
		}
		condition = {
			"timestamp":{
				"$gte":datetime.datetime.utcnow()-datetime.timedelta(hours=1),
				"$lt":datetime.datetime.utcnow()
			}
		}
		energy = {}
		timestamps = {}
		if single:
			shot = self.snapshots_col_appliances.find_one(sort=[("timestamp", pymongo.DESCENDING)])
			appliance_list = shot["data"]
			for appliance in appliance_list:
				if appliance not in energy:
					assert(appliance not in timestamps)
					energy[appliance] = []
					timestamps[appliance] = []
				energy[appliance].append(appliance_list[appliance]["value"])
				timestamps[appliance].append(shot["timestamp"])
		else:
			iterator = self.snapshots_col_appliances.find(condition).sort([("timestamp", pymongo.DESCENDING)])
			for shot in iterator:
				appliance_list = shot["data"]
				for appliance in appliance_list:
					if appliance not in energy:
						assert(appliance not in timestamps)
						energy[appliance] = []
						timestamps[appliance] = []
					energy[appliance].append(appliance_list[appliance]["value"])
					timestamps[appliance].append(shot["timestamp"])
		ret["rooms"]=self._getShotRooms(concise)
		ret["appliances"]=self._getShotAppliances(concise)
		ret["applianceEnergy"] = energy
		ret["applianceTimestamps"] = timestamps
		ret["personal"]=self._getShotPersonal(concise)
		ret["locations"]=self.location_of_users
		ret["watchdog_user"]=self.watchdog.watchdogLastSeen_User
		ret["watchdog_appl"]=self.watchdog.watchdogLastSeen_Appliance

		return self._encode(ret,True)

	def ShowRealtimeUsers(self):
		ret={
			"timestamp":self._now()
		}
		ret["locations"] = self.location_of_users
		ret["watchdog_user"]=self.watchdog.watchdogLastSeen_User
		ret["energy"] = {}
		for user in self.location_of_users:
			location = self.location_of_users[user]
			energy = self.calculateEnergyFootprint("nwc1000m_a6")
			ret["energy"][user] = [energy["value"], energy["HVAC"], energy["Light"], energy["Electrical"]]
		return self._encode(ret,True)

	def SaveParameters(self, parameters):
		self.snapshots_parameters.insert({
			"timestamp":datetime.datetime.utcnow(),
			"data":parameters
			})

	def SaveShot(self, any_additional_data=None):
		#save into database, with: timestamp, additional data
		# self.accumulate()
		# obj = {"value":self.cumulativeEnergy}
		# obj["_log_timestamp"]=datetime.datetime.utcnow()
		# self.todayCumulativeEnergy.insert(obj)

		self.snapshots_col_rooms.insert({
			"timestamp":datetime.datetime.utcnow(),
			"data":self._getShotRooms()
			})

		self.snapshots_col_appliances.insert({
			"timestamp":datetime.datetime.utcnow(),
			"data":self._getShotAppliances()
			})
			
		self.snapshots_col_users.insert({
			"timestamp":datetime.datetime.utcnow(),
			"data":self._getShotPersonal()
			})

		self._latestSuccessShot=self._now();
		return True

	def OptionalSaveShot(self):
		#"minimum interval: 10s; in lieu with regular snapshotting"
		if self._latestSuccessShot< self._now() -10 :
			self.SaveShot();


	def addLocationSample(self, label, sample):
		return self.dbc.loc_db.sample_col.insert({
			"label":label,
			"sample":sample,
			"timestamp":datetime.datetime.utcnow()
		})

	def getAllLocationSamples(self):
		return list(self.dbc.loc_db.sample_col.find())

	def DestroyLocationSamples(self):
		self.dbc.loc_db.sample_col.remove({})

	def getAllUsers(self):
		usernames = []
		users = list(self.registration_col1.find())
		#print users
		for user in users:
			if "name" not in user:
				continue
			#print "debug", user
			usernames.append(user["name"])
		nameList = ",".join(usernames)
		ret = {
				"names":usernames
		}
		return self._encode(ret, False)
####################################################################
## Login Information, for self.registration_col1 ###################
####################################################################
	def screenNameCheckAvailability(self, screenName):
		return len(list(self.registration_col1.find({"screenName":screenName}))) == 0
	
	def deviceIDCheckAvailability(self, deviceID):
		return len(list(self.registration_col1.find({"userID":deviceID}))) == 0

	def screenNameRegister(self, screenName, userID, control=True):
		self.LogRawData({
			"type":"screenNameRegister",
			"time":self._now(),
			"screenName":screenName,
			"userID":userID,
			"rewards":0,
			"tempRewards":0
			})
		try:
			self.registration_col1.insert({
				"screenName":screenName,
				"userID":userID,
				"control":control,
				"balance":0,
				"tempBalance":0
				})
			return True
		except pymongo.errors.DuplicateKeyError:
			return False

	def userIDRemoveAll(self, userID):
		self.registration_col1.remove({"userID":userID})

	def updateName(self, deviceID, username):
		itm = self.registration_col1.find_one({"screenName": username})
		if (itm is None):
			return False
		self.registration_col1.update(
			{"screenName": username}, 
			{"$set": {"userID": deviceID}}, multi=True)
		return True

	def fullRegistration(self, deviceID, name, email, password):
		try:
			self.registration_col1.insert({
				"userID": deviceID})
			print("successfully inserted new user")
			self.registration_col1.update({"userID": deviceID},{"$set":{
				"name": name,
				"email": email,
				"password": password,
				"control": True,
				"balance": 0,
				"tempBalance": 0,
				"loggedIn": True
				}})
			return True
		except pymongo.errors.DuplicateKeyError:
			return False

	def checkLoginFlow(self, deviceID):
		user = self.registration_col1.find_one({"userID": deviceID})
		if user is not None:
			if user.get("loggedIn"):
				return "0" #user is logged in
			else:
				return "1" #user not logged in
		return "404" #user not registered

	def getNameFromDeviceID(self, deviceID):
		user = self.registration_col1.find_one({"userID": deviceID})
		return user.get("name")

	def login(self, deviceID, email, password):
		user = self.registration_col1.find_one({"userID": deviceID})
		if user is not None:
			if (user.get("email") == email) and (user.get("password") == password):
				self.registration_col1.update({"userID":deviceID}, {"$set":{"loggedIn":True}})
				return "0"
			else:
				return "1"
		user = self.registration_col1.find_one({"email": email, "password":password})
		if user is None:
			return "404"
		newInput = {}
		newInput["userID"] = deviceID
		newInput["control"] = user.get("control")
		newInput["password"] = user.get("password")
		newInput["name"] = user.get("name")
		newInput["loggedIn"] = True
		newInput["tempBalance"] = user.get("tempBalance")
		newInput["balance"] = user.get("balance")
		newInput["email"] = user.get("email")
		self.registration_col1.insert(newInput)
		return "0"

	def logout(self, deviceID):
		try:
			self.registration_col1.update({"userID": deviceID},
				{"$set":{"loggedIn": False}})
			return "0"
		except pymongo.errors.DuplicateKeyError:
			return "1"

	def addPushToken(self, deviceID, token):
		try:
			self.registration_col1.update({"userID":deviceID}, {"$set":{"token":token}})
			return "0"
		except pymongo.errors.DuplicateKeyError:
			return "404"
		return "400"

	def addDeviceToken(self, deviceID, deviceToken):
		try:
			user = self.registration_col1.find_one({"userID": deviceID})
			if (user is not None):
				if ("devices" not in user):
					self.registration_col1.update({"userID":deviceID}, {"$set":{"devices":[deviceToken]}})
					return "0"
				else:
					devices = user.get("devices")
					devices.append(deviceToken)
					self.registration_col1.update({"userID":deviceID}, {"$set":{"devices":devices}})
					return "0"
			return "1"
		except pymongo.errors.DuplicateKeyError:
			return "404"
		return "400"

	def userIDLookup(self, userID):
		ret=list(self.registration_col1.find({"userID":userID}))
		if len(ret)!=1:
			return None
		if "name" in ret[0]:
			return ret[0]["name"]
		return ret[0]["screenName"]

	def getControl(self, userID):
		user = self.registration_col1.find_one({"userID":userID})
		if user != None:
			if "control" in user:
				return user.get("control")
		return True

	def getUserLocation(self, user_id):
		if user_id in self.location_of_users:
			return self.location_of_users[user_id]
		else:
			return None



	def getUserTempBalance(self, deviceID):
		U = list(self.registration_col1.find({"userID":deviceID}))
		if (len(U) == 0):
			return None
		doc = U[0]
		return doc["tempBalance"]

	def getUserBalance(self, deviceID):
		U = list(self.registration_col1.find({"userID":deviceID}))
		if (len(U) == 0):
			return None
		doc = U[0]
		return doc["balance"]

	def getAttributes(self, username, encodeJson=True):
		json_return={
			"username":"username",
			"frequency":0,
			"wifi":True,
			"public":True,
			"lab":0,
			"affiliation":0
		}
		itm = self.ranking.find_one({"user":username})

		json_return["username"] = username
		if (itm == None):
			#print("username not found: " + username)
			if (encodeJson == True):
				return self._encode(json_return, False)
			else:
				return json_return
		json_return["lab"] = self.labInt(itm.get("lab"))
		json_return["affiliation"] = self.affiliationInt(itm.get("affiliation"))
		json_return["frequency"] = itm.get("frequency")
		json_return["wifi"] = itm.get("wifi")
		json_return["public"] = itm.get("public")
		if (encodeJson == True):
			return self._encode(json_return, False)
		else:
			return json_return

	def labInt(self, x):
		return {
			'Burke Lab':1,
			'Teherani Lab': 2,
			'Professor Teherani\'s Lab':2,
			'Jiang Lab': 3,
			'Sajda Lab': 4,
			'Danino Lab': 5
		}[x]

	def affiliationInt(self, x):
		return {
			'Student':1,
			'Professor':2,
			'Employee':1
		}[x]









