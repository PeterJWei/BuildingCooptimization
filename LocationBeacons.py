import json
import web
import cloudserver

from KNN import KNearestNeighbors

urls = (
	"/", "BeaconVals")

class LocationPredictor:
    trainingData = []
    trainingLabels = []
    def __init__(self):
        self.addTrainingSamples()
        #read sample data from DB
        samples=cloudserver.db.getAllLocationSamples()
        pairs=[(s["sample"],s["label"]) for s in samples]

        #prepare KNN
        self.KNN=KNearestNeighbors(pairs)

        #list_of_rooms={}
        list_of_rooms_each_lab={}
        for room in cloudserver.db.ROOM_DEFINITION:
            id=room["id"]
            lab=room["lab"]
            #if id not in list_of_rooms:
            #    list_of_rooms[id]=id

            if lab not in list_of_rooms_each_lab:
                list_of_rooms_each_lab[lab]=[]
            list_of_rooms_each_lab[lab]+=[id]

        #prepare lab prior, as a list of votes (roomID, #vote)
        prior_vote_const=2
        self.prior_votes={}
        self.prior_votes[0]=[]
        for lab in list_of_rooms_each_lab:
            if lab>0:
                prior=[]
                for id in list_of_rooms_each_lab[lab]:
                    prior.append((id,prior_vote_const))
                self.prior_votes[lab]=prior

        print("prior votes:")
        print(self.prior_votes)

    def addSamples(self, sampleFile):
        infile = sampleFile + ".txt"
        print("Loading from " + infile + "...")
        f = open(infile, 'r')
        x = f.readlines()
        self.trainingData = []
        for i in range(len(x)):
            y = x[i].split('\t')
            last = y[-1].split('\n')
            y[-1] = last[0]
            y = map(int, y)
            self.trainingData.append(y)
        infile = sampleFile + "Labels.txt"
        print("Loading from " + infile + "...")
        f = open(infile, 'r')
        x = f.readlines()
        self.trainingLabels = []
        for j in range(len(x)):
            y = x[j]
            last = y.split('\n')
            y = last[0]
            self.trainingLabels.append(y)

        assert(len(self.trainingData) > 0)
        assert(len(self.trainingData) == len(self.trainingLabels))
        for k in range(len(self.trainingData)):
            cloudserver.db.addLocationSample(self.trainingLabels[k], self.trainingData[k])


    def addTrainingSamples(self):
        cloudserver.db.DestroyLocationSamples()
        samples=cloudserver.db.getAllLocationSamples()
        if (len(samples) > 0):
            print(str(len(samples)) + " samples found")
            return
        print("no samples found")
        infile = "trainingFiles/trainingFilesList.txt"
        f = open(infile, 'r')
        x = f.readlines()
        for i in range(len(x)):
            filename = x[i]
            last = filename.split('\n')
            self.addSamples(last[0])
            print("added samples from " + last[0])
        print "successful reupload"

    def personal_classifier(self, ID, sample):
        prior=[]
        screenName=cloudserver.db.userIDLookup(ID)
        if screenName!=None:
            usernameAttributes = cloudserver.db.getAttributes(screenName, False)
            labInt = usernameAttributes["lab"]
            prior=self.prior_votes[labInt]

        nearest_votes=self.KNN.get_nearest_pairs(sample)
        result_pair=self.KNN.majority_vote(prior+nearest_votes)

        return result_pair[0]
     
        #prepare prior knowledge, or None
        #run KNN
        #find maximum
        #return roomID

class BeaconVals:
	predictor = LocationPredictor()

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