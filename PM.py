import json
import web

import cloudserver


urls = (
"/(.+)", "SavePM"
)

class SavePM:
    def POST(self, Id):
        raw_data = web.data()
        try:
            data = json.loads(raw_data)
        except ValueError:
            print("Invalid data")
        if ("PM1" in data and "PM25" in data and "PM10" in data):
#            print([data["PM1"], data["PM25"], data["PM10"]])
            cloudserver.db.ReportPMValue(
                Id,
                float(data["PM1"]),
                float(data["PM25"]),
                float(data["PM10"])
            )
        else:
            print("Missing fields in json")

PMReport = web.application(urls, locals())
