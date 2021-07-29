import json
import web
import cloudserver
import math

urls = (
	"/SensorNodeOccupancy", "SensorNodeOccupancy",
	"/SensorNodeData", "SensorNodeData",
	"/SaveLocation", "SaveLocation",
	"/SensorNodeCount", "SensorNodeCount"
)

class SensorNodeOccupancy:
	def POST(self):
		print("Reporting from ICSL Lambda")
		raw_data = web.data()
		data = json.loads(raw_data)
		cameraIDMap = {
			"thermal0": "nwc1003E",
			"thermal1": "nwc1003b_b",
			"thermal2": "nwc1000m_a2",
			"thermal3": "nwc1000m_a1",
			"thermal4": "nwc1008",
			"thermal5": "nwc1000m_a6",
			"thermal6": "nwc1000m_a5",
			"thermal7": "nwc1003g",
			"thermal8": "nwc1003E"
		}
		CID = data["cameraID"]
		if CID not in cameraIDMap:
			print("Camera " + CID + " not in known camera map")
			return "200 OK"
		cameraID = cameraIDMap[data["cameraID"]]
		try: 
			occupancy = int(data["occupancy"])
		except ValueError:
			return "201 Invalid occupancy"
		cloudserver.db.recordOccupancy(cameraID, int(data["occupancy"]))
		return "200 OK"

class SensorNodeData:
	def POST(self):
		print("Reporting from ICSL Lambda")
		raw_data = web.data()
		data = json.loads(raw_data)
		thermalCameraParameters = {
			"thermal0": (131, 121, 60, 0, 60),
#			"nwc1000m_a6"
			"thermal5": (1024, 427, 160, 15, 59),
			#"nwc1000m_a5": 
			"thermal6": (1024, 364, 160, 30, 67),
			#"nwc1000m_a2": 
			"thermal2": (1024, 137, 210, 30, 67),
			#"nwc1000m_a1": 
			"thermal3": (1024, 74, 225, 25, 67),
			#"nwc1008":
			"thermal4": (372, 413, 135, 0, 60),
			#"nwc1003B"
			"thermal1": (21, 341, 315, 0, 60),
			#"nwc1003G"
			"thermal7": (161, 338, 225, 0, 60),
			#"nwc1003E"
			"thermal8": (131, 121, 60, 0, 60)
		}
		thermalCameraLocations = {
			"thermal0": "nwc1003E",
			"thermal1": "nwc1003b_b",
			"thermal2": "nwc1000m_a2",
			"thermal3": "nwc1000m_a1",
			"thermal4": "nwc1008",
			"thermal5": "nwc1000m_a6",
			"thermal6": "nwc1000m_a5",
			"thermal7": "nwc1003g",
			"thermal8": "nwc1003E"
		}
		
		meters2pixels = 17.01936
		for person in data:
			if "cameraID" in data[person]:
				if data[person]["cameraID"] not in thermalCameraParameters:
					print("No camera named " + data[person]["cameraID"])
				loc = thermalCameraLocations[data[person]["cameraID"]]
				x, y, yaw, pitch, height = thermalCameraParameters[data[person]["cameraID"]]
				h_rad = math.radians(yaw + float(data[person]["hangle"]))
				v_rad = math.radians(pitch + float(data[person]["vangle"]))
				planar_d = math.cos(v_rad) * float(data[person]["distance"])
				delta_x = math.cos(h_rad) * planar_d * meters2pixels * 3.048
				delta_y = math.sin(h_rad) * planar_d * meters2pixels * 3.048
				x_pix, y_pix = x + delta_x, y - delta_y
				print(x, y, yaw, pitch, float(data[person]["hangle"]), float(data[person]["vangle"]), float(data[person]["distance"]), planar_d, delta_x, delta_y, data[person]["temp"])
				if data[person]["temp"] == "None":
					max_temp = 38
				else:
					max_temp = int(data[person]["temp"])
				print(max_temp)
				cloudserver.db.ReportUserData(person, data[person]["cameraID"], x_pix, y_pix, loc, max(max_temp, 37))
			else:
				print("Invalid occupant data")
				return "201 invalid data"
		return "200 OK"

class SaveLocation:
	def POST(self):
		print("Reporting Location")
		raw_data = web.data()
		data = json.loads(raw_data)
		for user in data:
			if user == "Hengjiu":
				continue
			print((user, data[user]))
			cloudserver.db.ReportLocationAssociation(user, data[user])
		return "200 OK"

LocationReport = web.application(urls, locals())
