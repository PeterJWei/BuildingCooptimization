import json
import web
import cloudserver
from KNN import KNearestNeighbors

urls = (
"/","train")


class train:
    trainingData = []
    trainingLabels = []
    def generate(self):
        infile = "backup2.txt"
        f = open(infile, 'r')
        x = f.readlines()
        for i in range(len(x)):
            y = x[i].split('\t')
            last = y[-1].split('\n')
            y[-1] = last[0]
            y=[int(v) for v in y]
            self.trainingData.append(y)

        infile = "backuplabels2.txt"
        f = open(infile, 'r')
        x = f.readlines()
        for j in range(len(x)):
            y = x[j]
            last = y.split('\n')
            y = last[0]
            self.trainingLabels.append(y)

        #if(len(self.trainingData)!=len(self.trainingLabels)):
        #    raise Exception("Training data and Training label length don't match.")
        #cloudserver.db.DestroyLocationSamples()
        #for i in range(len(self.trainingLabels)):
        #    cloudserver.db.addLocationSample(self.trainingLabels[i],self.trainingData[i])
        #print(str(len(self.trainingLabels))+" samples Added to database from text file.")

    def POST(self):
        raw_data=web.data()
        locs = raw_data.split(',')

        if (locs[0] == "REUP"):
            infile = "backup.txt"
            f = open(infile, 'r')
            x = f.readlines()
            self.trainingData = []
            for i in range(len(x)):
                y = x[i].split('\t')
                last = y[-1].split('\n')
                y[-1] = last[0]
                y = map(int, y)
                self.trainingData.append(y)
            infile = "backuplabels.txt"
            f = open(infile, 'r')
            x = f.readlines()
            self.trainingLabels = []
            for j in range(len(x)):
                y = x[j]
                last = y.split('\n')
                y = last[0]
                self.trainingLabels.append(y)
            infile = "backup2.txt"
            f = open(infile, 'r')
            x = f.readlines()
            for i in range(len(x)):
                y = x[i].split('\t')
                last = y[-1].split('\n')
                y[-1] = last[0]
                y = map(int, y)
                self.trainingData.append(y)
            infile = "backuplabels2.txt"
            f = open(infile, 'r')
            x = f.readlines()
            for j in range(len(x)):
                y = x[j]
                last = y.split('\n')
                y = last[0]
                self.trainingLabels.append(y)                
            print "successful reupload"
            return
        if (locs[0] == "DES"):
            self.trainingData = []
            self.trainingLabels = []
            return "successful destroy"

        l = locs[1:]
        if (locs[0] == "GET"):
            #outfile = "backup2.txt"
            #with open(outfile, 'w') as file:
            #    file.writelines('\t'.join(str(j) for j in i) + '\n' for i in self.trainingData)
            #outfile2 = "backuplabels2.txt"
            #with open(outfile2, 'w') as file:
            #    file.writelines(str(self.rooms[i]) + '\n' for i in self.trainingLabels)
            #locs = map(int, l)
            #if (len(self.trainingLabels) < self.K):
            #    ret = "not enough data,"
            #    ret += str(len(self.trainingLabels))
            #    return ret

            locs = map(int, l)
            print('Location Predict request:',locs)
            KNN = KNearestNeighbors(list(zip(self.trainingData, self.trainingLabels)))
            pairs=KNN.get_nearest_pairs(locs)
            print('Predicted pairs:',pairs)
            location = KNN.majority_vote(pairs)
            print(location)
            return str(location[0])+':'+str(location[1]) + ",LOL"
        ID = locs[0]
        intID = ID
        locs = map(int, l)
        self.trainingData.append(locs)
        self.trainingLabels.append(intID)
        print('Submitted ID=',ID)
        print('Training sample=',locs)
        cloudserver.db.addLocationSample(ID, locs)
        return str(cloudserver.db.countLocationSamples())+" LOL"

    def GET(self):
        #result = cloudserver.db.QueryLocationData(0)
        return

locationTraining = web.application(urls, locals());