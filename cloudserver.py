import web
import json
import os
import datetime
import time
import calendar
import BACNet
import FaceID
import DBMgr
import Energy
import PM
import userManagement
import LocationBeacons
import appSupport
import Recommendations
#import scrapeBuildingData
db=DBMgr.DBMgr()

urls = (
	"/api/Test", "TestPost",
	"/api/EnergyHVAC", BACNet.EnergyReportBACNET,
	"/api/FaceIDLocation", FaceID.LocationReport,
	"/api/EnergyReport", Energy.EnergyReport,
        "/api/PMReport", PM.PMReport,
	"/api/userManagement", userManagement.userMGM,
	"/api/appSupport", appSupport.appURL,
	"/api/Beacons", LocationBeacons.Beacons,
	"/api/Recommendations", Recommendations.UserRecs,
	"/realtime/(.*)","Realtime",
    "/realtime","Realtime",
    "/realtimeGraphs/(.*)", "RealtimeGraphs",
    "/realtimeGraphs", "RealtimeGraphs",
    "/realtimeGraphsSingle/(.*)", "RealtimeGraphsSingle",
    "/realtimeGraphsSingle", "RealtimeGraphsSingle",
    "/realtimeUsers/(.*)", "RealtimeUsers",
    "/realtimeUsers", "RealtimeUsers",
    "/realtimeLights/(.*)", "RealtimeLights",
    "/realtimeLights", "RealtimeLights",
    "/realtimeTemps/(.*)", "RealtimeTemps",
    "/realtimeTemps", "RealtimeTemps",
    "/realtimePM/(.*)", "RealtimePM",
    "/realtimePM", "RealtimePM",
    "/realtimeUsersSingle/(.*)", "RealtimeUsersSingle",
    "/realtimeUsersSingle", "RealtimeUsersSingle",
    "/realtimeDashboard", "RealtimeDashboardSingle",
    "/realtimeDashboard/(.*)", "RealtimeDashboardSingle",
	'/', 'index'
)


class index:
	def GET(self):
		return "200 OK"

class Realtime:
	def GET(self,person=None):
		if "full" in web.input():
			return db.ShowRealtime(concise=False)
		# if "personal" in web.input():
		# 	return db.ShowRealtimePersonalSummary()
		return db.ShowRealtime(person)

class TestPost:
	def POST(self):
		print("Reporting Location")
		raw_data = web.data()
#		data = json.loads(raw_data)
#		print(data)
		return "200 OK"
class RealtimeGraphs:
	def GET(self,person=None):
		return db.ShowRealtimeGraphs(single=False, concise=False)
class RealtimeGraphsSingle:
	def GET(self,person=None):
		return db.ShowRealtimeGraphs(single=True, concise=False)
class RealtimeTemps:
	def GET(self, temp=None):
		return db.ShowRealtimeTempParameters()
class RealtimePM:
	def GET(self, sensor=None):
		return db.ShowRealtimePMParameters()
class RealtimeLights:
	def GET(self, light=None):
		return db.ShowRealtimeLights()
class RealtimeUsers:
	def GET(self,person=None):
		return db.ShowRealtimeUsers()
class RealtimeUsersSingle:
	def GET(self,person=None):
		return db.ShowRealtimeUsers()
class RealtimeDashboardSingle:
	def GET(self,rooms=None):
		web.header('Access-Control-Allow-Origin', '*')
		web.header('Access-Control-Allow-Credentials', 'true')
		locations = ["nwc1003E", "nwc1003g", "nwc1003g_a", "nwc1003g_c", "nwc1008", "nwc1000m_a1", "nwc1000m_a2", "nwc1000m_a5", "nwc1000m_a6", "nwc1003b_a", "nwc1003b_b"]
		return db.ShowRealtimeDashboard(locations)
class MyApplication(web.application):
	def run(self, port=8080, *middleware):
		func = self.wsgifunc(*middleware)
		return web.httpserver.runsimple(func, ('0.0.0.0', port))
def notfound():
	return web.notfound("404 Not Found")

	# You can use template result like below, either is ok:
	#return web.notfound(render.notfound())
	#return web.notfound(str(render.notfound()))
def run():
	app = MyApplication(urls, globals())
	app.notfound = notfound
	app.run(port=8000)
