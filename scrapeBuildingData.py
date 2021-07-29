import pymongo
import csv
import calendar
import datetime
import time

dbc = pymongo.MongoClient()
print(dbc)
snapshots_col_appliances = dbc.db.snapshots_col_appliances
print(snapshots_col_appliances)
end=time.mktime(datetime.date.today().timetuple())
start=end-(86400*30*2)
#currentTime = calendar.timegm(datetime.datetime.utcnow().utctimetuple())
#lastHour = datetime.datetime.utcnow() - timedelta(hours=24)
#lastHourTime = calendar.timegm(lastHour.utctimetuple())
print(start)
print(datetime.datetime.utcfromtimestamp(start))
condition = {
	"timestamp": {
		"$gte":datetime.datetime.utcfromtimestamp(start),
	}
}
#measurement = snapshots_col_appliances.find_one()
#print(measurement)
iterator = snapshots_col_appliances.find(condition).sort([("timestamp", pymongo.DESCENDING)])
timestamps = []
data = {}
for shot in iterator:
	lst = shot["data"]
	timestamps.append(shot["timestamp"])
	for appl in lst:
		if appl not in data:
			data[appl] = []
		data[appl].append(lst[appl]["value"])
#print(timestamps)
#for appl in data:
#	print(data[appl])	
print(len(timestamps))
for appl in data:
	if len(data[appl]) != len(timestamps):
		print("Sizes don't match!")

appliances = [appl for appl in data]
first_row = ["Timestamp"] + appliances
print(first_row)
energyData = []
for t in range(len(timestamps)):
	new_row = []
	for appl in appliances:
		new_row.append(data[appl][t])
	energyData.append(new_row)
		
with open("newDataset.csv", "w") as csvfile:
	writer = csv.writer(csvfile, delimiter=',')
	writer.writerow(first_row)
	for t, dat in enumerate(energyData):
		writer.writerow([timestamps[t]] + dat)
	
