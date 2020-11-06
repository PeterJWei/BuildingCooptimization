import json
import web

import cloudserver


urls = (
"/(.+)/SavePlug","SavePlug", #raw values: watts, kwh
"/(.+)/SaveHVAC","SaveHVAC",  #raw values: pressure+temp
"/(.+)/SaveLight","SaveLight", #raw values: on or off / watts
"/(.+)","Save",
"/SaveBACNET","SaveBACNET"
)

class Save:
    def POST(self,Id):
        raw_data=web.data()
        data = None
        try:
            data=json.loads(raw_data)
        except ValueError:
            print("Invalid data")
        if (data is None):
            return "201 NOT OK"
        if ('raw' not in data):
            cloudserver.db.ReportEnergyValue(Id,data['energy'],None)
        else:
            cloudserver.db.ReportEnergyValue(Id,data['energy'],data['raw'])
        return "200 OK"
        
class SaveHVAC:
    def POST(self,room):
        raw_data=web.data()
        data=json.loads(raw_data)
        name=data['name']
        temperature=data['temperature']
        windSpeed=data['windSpeed']
        cloudserver.db.SaveHVAC(name, temperature, windSpeed)
        return "200 OK"


    def GET(self,room):
        return "{0}".format(room)



class SavePlug:
    def POST(self,room):
        raw_data = web.data() # you can get data use this method
        data=json.loads(raw_data)

        description=data["name"]
        energy=data["energy"]
        power=data["power"]
        cloudserver.db.SavePlug(room,description,energy,power)

        return "200 OK"
EnergyReport = web.application(urls, locals())