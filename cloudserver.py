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
	"/EnergyReport", Energy.EnergyReport,
	'/', 'index'
)


class index:
	def GET(self):
		return "200 OK"


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