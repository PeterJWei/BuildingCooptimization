import json
import web

import cloudserver


urls = (
"/(.+)/SavePlug","SavePlug", #raw values: watts, kwh
"/(.+)/SaveHVAC","SaveHVAC",  #raw values: pressure+temp
"/(.+)/SaveLight","SaveLight", #raw values: on or off / watts
"/(.+)/SaveParameters","SaveParameters",
"/(.+)","Save",
"/SaveBACNET","SaveBACNET"
)



class SaveParameters:
    def POST(self, Id):
        print("Saving parameters for: " + Id)
        raw_data = web.data()
        try:
            data = json.loads(raw_data)
        except ValueError:
            print("Invalid data")
        if ("temp" in data and "pressure" in data and "altitude" in data and "humidity" in data):
            print("Temp: " + str(data["temp"]))
            cloudserver.db.ReportTempValue(
                Id, 
                float(data["temp"]),
                float(data["pressure"]),
                float(data["humidity"]))

class SaveLight:
    def _powerLimits(self, power, lightVal, threshold):
        if lightVal > threshold:
            return 0
        else:
            return power
    def POST(self, Id):
        print("Saving light value for: " + Id)
        raw_data = web.data()
        try:
            data = json.loads(raw_data)
        except ValueError:
            print("Invalid data")
        if ("light" in data):
            cloudserver.db.ReportLightValue(Id, int(data["light"]))
            if Id == "nwc1003g_light":
                cloudserver.db.ReportEnergyValue(Id, self._powerLimits(300, data["light"], 900), None)
            elif Id == "nwc1000m_a6_light":
                cloudserver.db.ReportEnergyValue(Id, self._powerLimits(225, data["light"], 1000), None)
            elif Id == "nwc1000m_a1_light":
                cloudserver.db.ReportEnergyValue(Id, self._powerLimits(225, data["light"], 1000), None)
            elif Id == "nwc1000m_a2_light":
                cloudserver.db.ReportEnergyValue(Id, self._powerLimits(225, data["light"], 1000), None)
            elif Id == "nwc1000m_a5_light":
                cloudserver.db.ReportEnergyValue(Id, self._powerLimits(225, data["light"], 1000), None)
            elif Id == "nwc1003gA_light":
                cloudserver.db.ReportEnergyValue(Id, self._powerLimits(300, data["light"], 1000), None)
            elif Id == "nwc1003gB_light":
                cloudserver.db.ReportEnergyValue(Id, self._powerLimits(300, data["light"], 1000), None)
            elif Id == "nwc1008":
                cloudserver.db.ReportEnergyValue(Id, self._powerLimits(300, data["light"], 1000), None)




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
