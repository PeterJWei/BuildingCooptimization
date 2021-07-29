import json
import web

import cloudserver


urls = (
	"/SaveBACNET","SaveBACNET",
	"/SaveParameters", "SaveParameters",
	"/GetParameters", "GetParameters"
)


class SaveBACNET:
    def POST(self):
    	print("Reporting BACNET")
        raw_data=web.data()
        data=json.loads(raw_data)
        for device in data:
            if device == "nwcM1_fcu" or device == "nwcM2_fcu" or device == "nwcM3_fcu" or device == "nwcM4_fcu" or device == "nwcM5_fcu" or device == "nwc1008_fcu":
                continue
#            print((device, data[device]))
            cloudserver.db.ReportEnergyValue(device, data[device], None)
        return "200 OK"

class SaveParameters:
	def POST(self):

		print("Reporting Parameters")
		raw_data=web.data()
		data=json.loads(raw_data)
		print(data)
		cloudserver.db.SaveParameters(data)

class GetParameters:
	def GET(self):
		print("Getting bacnet data")
		return cloudserver.db.GetParameters()


EnergyReportBACNET = web.application(urls, locals())
