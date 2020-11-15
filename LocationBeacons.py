import json
import web
import cloudserver

import locationTraining

urls = (
	"/", "BeaconVals")


class BeaconVals:
	predictor = locationTraining.LocationPredictor()

	def POST(self):
		raw_data = web.data()
		locs = raw_data.split(',')
		l = locs[1:]
		ID = locs[0]
		locs = map(int, l)

		location = self.predictor.personal_classifier(ID, locs)
		checkUnknown = False

		#HACK TO FIX 7th BEACON POWER OVERWHELMING
        if (locs[6] != -100):
            for i in range(len(locs)):
                if (i != 6 and locs[i] != -100):
                    checkUnknown = True
                    break
            if (checkUnknown == False):
                cloudserver.db.watchdogRefresh_User(ID)


        for loc in locs:
            if (loc != -100):
                checkUnknown = True
                break
        if (checkUnknown == False):
            unknown_return={
            "location":"Unknown Location",
            "location_id":"Unknown Location",
            "balance":cloudserver.db.getUserBalance(ID),
            "tempBalance":cloudserver.db.getUserTempBalance(ID),
            "suggestions":[]
            }

            cloudserver.db.ReportLocationAssociation(ID, "outOfLab")
            return cloudserver.db._encode(unknown_return,False)

        cloudserver.db.ReportLocationAssociation(ID, location)
        balance_server = cloudserver.db.getUserBalance(ID)
        tempBalance_server = cloudserver.db.getUserTempBalance(ID)
        if (balance_server is None):
            balance_server = 0
            tempBalance_server = 0
        json_return={
            "location":"Location Name",
            "location_id":"locationIDString",
            "balance":balance_server,
            "tempBalance": tempBalance_server,
            "suggestions":[]
        }
        json_return["location_id"]=location
        json_return["location"]=cloudserver.db.RoomIdToName(location)
        return cloudserver.db._encode(json_return,False)


Beacons = web.application(urls, locals());