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

from recommenderSystem import recommenderSystem


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
		self.list_of_PM_values={};
		self.list_of_temp_values={};
		self.list_of_light_values={};
		self.list_of_rooms={};
		self.list_of_appliances={};
		self.location_of_users={};
		self.list_of_users={};

		for room in self.ROOM_DEFINITION:
			room["PM"]={}
			room["appliances"]=[]
			room["users"]=[]
			room["occupancy"] = 0
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
						if applianceID == "nwcM3_fcu" or applianceID == "nwcM4_fcu":
							self.updateApplianceValue(applianceID, 0)
							continue
						elif applianceID == "nwc1000m_light":
							self.updateApplianceValue(applianceID, 0)
							continue
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
		self.DRL_recommendations=self.dbc.db.DRL_recommendations
		self.snapshots_col_users=self.dbc.db.snapshots_col_users
		self.web_registration = self.dbc.db.web_registration
		self.web_comfort_feedback = self.dbc.db.web_comfort_feedback
		self.web_rec_feedback = self.dbc.db.web_rec_feedback

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
		#self._GracefulReloadGraph()
		## Read appliance values from database; TODO: occupants location
		#self._HardcodeValues()

		# self.watchdogInit()

		self.recommender = recommenderSystem()
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
		t_rec = Thread(target=self._backgroundRecommender, args=())
		t_rec.setDaemon(True)
		t_rec.start()

	def _now(self):
		return calendar.timegm(datetime.datetime.utcnow().utctimetuple())
	def _toUnix(self, ts):
		return calendar.timegm(ts.utctimetuple())
	def _backgroundLoop(self):
		print("DBMGR _backgroundLoop started...")
		while True:
			time.sleep(self.SAMPLING_TIMEOUT_LONGEST)
			self.SaveShot()
#			self.watchdogCheckUser()
#			self.watchdogCheckAppliance()
	def _backgroundRecommender(self):
		print("Recommender System started...")
		while True:
			time.sleep(10)
			recommendations1, recommendations2, locations = self.recommender._loopRecommendations(self.location_of_users, self.list_of_rooms, self.list_of_appliances)
			self.save_recommendations(recommendations1, recommendations2, locations)
			time.sleep(60)

		

	def save_recommendations(self, recommendations1, recommendations2, locations):
		self.DRL_recommendations.insert({
			"timestamp":datetime.datetime.utcnow(),
			"data1":recommendations1,
			"data2":recommendations2,
			"locations": locations
			})
	
	def modify_recommendations(self, person, r_type):
		entry = self.DRL_recommendations.find_one(sort=[("timestamp", pymongo.DESCENDING)])
		recs1 = entry["data1"]
		recs2 = entry["data2"]
		location = entry["locations"]
		person = self.PID2Name(person)
		if person in recs1 and person in recs2 and person in location:
			if r_type == "move":
				new_recs = []
				for rec in recs1[person]:
					print(rec)
					if rec["t"] != "move":
						new_recs.append(rec)
				recs1[person] = new_recs
				print("New number of recs: " + str(len(recs1[person])))
		self.DRL_recommendations.insert({
			"timestamp":datetime.datetime.utcnow(),
			"data1":recs1,
			"data2":recs2,
			"locations": location
			})
		

	def get_recommendations(self, person):
		entry = self.DRL_recommendations.find_one(sort=[("timestamp", pymongo.DESCENDING)])
		recs1 = entry["data1"]
		recs2 = entry["data2"]
		location = entry["locations"]
		if person in recs1 and person in recs2 and person in location:
			data = {"recommendations1":recs1[person],
				"recommendations2":recs2[person],
				"loc":location[person]}
			return self._encode(data,True)
		return None
		
	def PID2Name(self, PID):
		condition = {}
		entry = self.web_registration.find_one({"PID":PID})
		if "name" in entry:
			name = entry["name"]
		elif "Name" in entry:
			name = entry["Name"]
		else:
			name = "Peter"
		return name
		
			
	def _getShotRooms(self, concise=True):
		return self.list_of_rooms
	def _getShotAppliances(self, concise=True):
		print("Getting Appliances")
		for appliance in self.list_of_appliances:
			print((appliance, self.list_of_appliances[appliance]["value"]))
			
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

	def calculateLocationEnergyFootprint(self, roomID, encoded=True):
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
		for applianceID in app_list:
			app = self.list_of_appliances[applianceID]
			appValue = app["value"]
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
			if app["total_users"] > 0:
				appValue = app["value"]/(1.0*app["total_users"])
			else:
				appValue = app["value"]
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
	
	def ReportPMValue(self, sensorID, PM1, PM25, PM10):
		self.list_of_PM_values[sensorID] = [float(PM1), float(PM25), float(PM10)]
		PM2room = {
			"nwc10MPeter": ["nwc1000m_a5", "nwc1000m_a6"],
			"nwc10MJoe": ["nwc1000m_a1", "nwc1000m_a2"],
			"nwc1003B": ["nwc1003b_a", "nwc1003b_b"],
			"nwc1003G": ["nwc1003g", "nwc1003g_a", "nwc1003g_c"],
			"nwc1008_fcu": ["nwc1008"],
			"nwc1003E": ["nwc1003E"]
		}
		if sensorID not in PM2room:
			print("No spaces assigned to sensor " + sensorID)
			return
		for room in PM2room[sensorID]:
			self.list_of_rooms[room]["PM"]["PM1"] = PM1
			self.list_of_rooms[room]["PM"]["PM25"] = PM25
			self.list_of_rooms[room]["PM"]["PM10"] = PM10
	def ReportTempValue(self, applianceID, T, P, H):
		Temp2room = {
			"nwc1003B_parameters": ["nwc1003b_a", "nwc1003b_b"],
			"nwc1008_parameters": ["nwc1008"],
			"nwc1000m_a1_parameters": ["nwc1000m_a1"],
			"nwc1000m_a2_parameters": ["nwc1000m_a2"],
			"nwc1000m_a5_parameters": ["nwc1000m_a5"],
			"nwc1000m_a6_parameters": ["nwc1000m_a6"],
			"nwc1003g_parameters": ["nwc1003g"],
			"nwc1003gA_parameters": ["nwc1003g_a"],
			"nwc1003gB_parameters": ["nwc1003g_c"],
			"nwc1003E_parameters": ["nwc1003E"]
		}
		self.list_of_temp_values[applianceID] = [float(T), float(P), float(H)]
		if applianceID not in Temp2room:
			print("No spaces assigned to sensor " + applianceID)
			return
		for room in Temp2room[applianceID]:
			self.list_of_rooms[room]["Temperature"] = float(T)
			self.list_of_rooms[room]["Pressure"] = float(P)
			self.list_of_rooms[room]["Humidity"] = float(H)
	def ReportLightValue(self, applianceID, raw_value):
		self.list_of_light_values[applianceID] = raw_value
		
	def ReportEnergyValue(self, applianceID, value, raw_data=None):
		"maintenance tree node's energy consumption item, and update a sum value"
		known_room=None
		defaultValueFilter = {
			"nwc1003t2_vav": 19231,
			"nwc1003o1_vav": 1560,
			"nwc1003gA_vav": 3078,
			"nwc1003gC_vav": 3079,
			"nwc1003g1_vav": 537
		}
		try:
			if (applianceID not in self.list_of_appliances):
				print("applianceID " + applianceID + " not in list of appliances.")
				return
			app=self.list_of_appliances[applianceID]
			if applianceID in defaultValueFilter and int(value) == defaultValueFilter[applianceID]:
				return
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

	def ReportUserData(self, person, camera, x, y, loc, temperature):
		if camera == "thermal5":
			if person not in ["Peter", "Yanchen"]:
				person = "Peter"
			self.list_of_users[person] = {"camera": camera, "x": int(x), "y": int(y), "location": loc, "temp": temperature}
			self.ReportLocationAssociation(person, loc)
				
		if person in ["Joe", "Mark"] and camera != "thermal3":
			return
		if person in ["Lei"] and camera != "thermal3" and camera != "thermal2":
			return
		if person in ["Abhi", "Ankur"] and camera != "thermal6":
			return
		if person in ["Peter", "Yanchen"] and camera != "thermal5" and camera != "thermal1" and camera != "thermal7":
			return
		if person in ["Fred"] and camera != "thermal4":
			return
		if camera == "thermal4":
			self.list_of_users["Fred"] = {"camera": camera, "x": int(x), "y": int(y), "temp": temperature}
			self.ReportLocationAssociation("Fred", "nwc1008")
			return
		if person in ["Unknown"]:
			return
		self.list_of_users[person] = {"camera": camera, "x": int(x), "y": int(y), "location": loc, "temp": temperature}
		self.ReportLocationAssociation(person, loc)


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
		#print("\n\n\n\n\n\n\n")
		#print(self.location_of_users)
		#print("\n\n\n\n\n\n\n")

		if newS!=None:
			self.list_of_rooms[newS]["phantom_user"]=personID
			self.list_of_rooms[newS]["phantom_time"] = int(time.mktime(datetime.datetime.now().timetuple()))

		#"people change; should we update now?"
#		self.OptionalSaveShot();

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

	def DashboardRequest(self, PID):
		ret={
			"timestamp":self._now()
		}
		condition = {
			"PID": PID
		}
		recs = self.web_rec_feedback.find(condition)
		titles = {}
		total_energy = 0
		total_comfort = 0
		total_aq = 0
		setpoints = 0
		moves = 0
		unknown = 0
		for rec in recs:
			title = rec["title"]
			if title[0] == "C":
				setpoints += 1
			elif title[0] == "M":
				moves += 1
			else:
				unknown += 1
			energy = rec["energy"]
			energy = int(energy[:-3])
			total_energy += energy
			aq = rec["aq"]
			aq = int(aq[:-1])
			total_aq += aq
			comfort = rec["comfort"]
			comfort = int(comfort[:-1])
			total_comfort += comfort
			
			if title in titles:
				titles[title] += 1
			else:
				titles[title] = 1
		
		max_title = ""
		max_title_count = 0
		for title in titles:
			if titles[title] > max_title_count:
				max_title_count = titles[title]
				max_title = title
		ret["max_title"] = max_title
		ret["max_title_count"] = max_title_count
		ret["cum_energy"] = total_energy
		ret["cum_comfort"] = total_comfort
		ret["cum_aq"] = total_aq
		ret["setpoints"] = setpoints
		ret["moves"] = moves
		ret["unknown"] = unknown
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
	def ShowRealtimePMParameters(self):
		ret={
			"timestamp":self._now()
		}
		PM1_dict, PM25_dict, PM10_dict = {}, {}, {}
		for sensorID in self.list_of_PM_values:
			(PM1, PM25, PM10) = self.list_of_PM_values[sensorID]
			PM1_dict[sensorID] = PM1
			PM25_dict[sensorID] = PM25
			PM10_dict[sensorID] = PM10
		ret["PM1"] = PM1_dict
		ret["PM25"] = PM25_dict
		ret["PM10"] = PM10_dict
		return self._encode(ret, True)
	def ShowRealtimeTempParameters(self):
		ret={
			"timestamp":self._now()
		}
		T_dict, P_dict, H_dict = {}, {}, {}
		for applianceID in self.list_of_temp_values:
			(T, P, H) = self.list_of_temp_values[applianceID]
			T_dict[applianceID] = T
			P_dict[applianceID] = P
			H_dict[applianceID] = H
		ret["raw_temp_values"] = T_dict
		ret["raw_pressure_values"] = P_dict
		ret["raw_humidity_values"] = H_dict
		return self._encode(ret, True)

	def ShowRealtimeLights(self):
		ret={
			"timestamp":self._now()
		}
		appliancePower = {}
		ret["raw_light_values"] = self.list_of_light_values
		for applianceID in self.list_of_light_values:
			if applianceID in self.list_of_appliances:
				appliancePower[applianceID] = self.list_of_appliances[applianceID]["value"]
		ret["power"] = appliancePower
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
			energy = self.calculateEnergyFootprint(location, encoded=False)
			ret["energy"][user] = [energy["value"], energy["HVAC"], energy["Light"], energy["Electrical"]]
		return self._encode(ret,True)

	def ShowRealtimeDashboard(self, locations):
		ret={
			"timestamp":self._now()
		}
		location_data = {}
		for location in locations:
			data = {}
			PM1 = 10
			PM25 = 5
			PM10 = 12.5
			if "PM" in self.list_of_rooms[location] and "PM1" in self.list_of_rooms[location]["PM"]:
				PM1 = self.list_of_rooms[location]["PM"]["PM1"]
				PM25 = self.list_of_rooms[location]["PM"]["PM25"]
				PM10 = self.list_of_rooms[location]["PM"]["PM10"]
			if (location not in self.list_of_rooms):
				print(location + " not found")
				continue
			T, P, H = 0, 0, 0
			if "Temperature" in self.list_of_rooms[location]:
				T = self.list_of_rooms[location]["Temperature"]
				P = self.list_of_rooms[location]["Pressure"]
				H = self.list_of_rooms[location]["Humidity"]
			energyDict = self.calculateLocationEnergyFootprint(location, encoded=False)
			if location == "nwc1003b_b":
				energyDict = self.calculateLocationEnergyFootprint("nwc1003b_c", encoded=False)
			data["HVAC"] = energyDict["HVAC"]
			data["Light"] = energyDict["Light"]
			data["Electrical"] = energyDict["Electrical"]
			data["PM1"] = PM1
			data["PM25"] = PM25
			data["PM10"] = PM10
			data["Temperature"] = T
			data["Pressure"] = P
			data["Humidity"] = H
			location_data[location] = data
		if "nwc1000m_a1" in location_data and "nwc1000m_a2" in location_data:
			location_data["nwc1000m_a1"]["Light"] = location_data["nwc1000m_a2"]["Light"]
		ret["location_data"] = location_data
#		users = {"Peter": {"x":125, "y":60, "floor":"10", "temp":94}}
		users = self.list_of_users
		print(users)
		ret["occupants"] = users
		return self._encode(ret, True)
		

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

		timestamp = datetime.datetime.utcnow()
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

	def recordOccupancy(self, room, occupancy):
		if room in self.list_of_rooms:
			self.list_of_rooms[room]["occupancy"] = occupancy
		else:
			print("No room called " + room + " to assign occupancy " + str(occupancy))

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
	
	def webLogin(self, PID):
		user = self.web_registration.find_one({"PID":PID})
		registered = (user is not None)
		if registered and "name" in user:
			print("Login: " + user["name"])
		return registered

	def webSubmitComfort(self, PID, comfort):
		comfortFeedback = {
			"timestamp":self._now(),
			"PID": PID,
			"comfort": int(comfort)
		}
		return self.web_comfort_feedback.insert(comfortFeedback)
		
	def SubmitRecommendations(self, PID, recs, location): 
		one_selected = False
		two_selected = False
		for rec in recs:
			print((rec, rec["list"], rec["title"][0]))
			print((rec["list"]==1, rec["title"][0]=="M"))
			if rec["list"] == 1:
				if rec["title"][0] == "M":
					self.modify_recommendations(PID, "move")
				one_selected = True
			if rec["list"] == 2:
				two_selected = True
			recFeedback = {
				"timestamp":self._now(),
				"location": location,
				"PID": PID,
				"list": rec["list"],
				"energy": rec["energy"],
				"comfort": rec["comfort"],
				"aq": rec["aq"],
				"global": rec["global"],
				"title": rec["title"],
				"desc": rec["desc"],
				"opt": rec["opt"],
				"rank": rec["rank"]
			}
			self.web_rec_feedback.insert(recFeedback)
		if not one_selected:
			recFeedback = {
				"location": location,
				"timestamp": self._now(),
				"PID": PID,
				"list": 1,
				"rank": -1
			}
			self.web_rec_feedback.insert(recFeedback)
		if not two_selected:
			recFeedback = {
				"location": location,
				"timestamp": self._now(),
				"PID": PID,
				"list": 2,
				"rank": -1
			}
			self.web_rec_feedback.insert(recFeedback)
		return True

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









