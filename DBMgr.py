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

		self.config_col=self.dbc.db.config
		self.snapshots_col_rooms=self.dbc.db.snapshots_col_rooms
		self.snapshots_col_appliances=self.dbc.db.snapshots_col_appliances
		self.snapshots_col_users=self.dbc.db.snapshots_col_users

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
		self.watchdogRefresh_Appliance(applianceID)

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