import web
import os
import datetime
import time
import calendar
import BACNet
import DBMgr
import Energy

db=DBMgr.DBMgr()

urls = (
	"/api/EnergyHVAC", BACNet.EnergyReportBACNET,
	"/api/EnergyReport", Energy.EnergyReport,
	"/realtime/(.*)","Realtime",
    "/realtime","Realtime",
    "/realtimeGraphs/(.*)", "RealtimeGraphs",
    "/realtimeGraphs", "RealtimeGraphs",
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

class RealtimeGraphs:
	def GET(self,person=None):
		return db.ShowRealtimeGraphs(concise=False)

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