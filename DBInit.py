import re
import pymongo

class DBInit(object):
	def _GetConfigValue(self,key):
		try:
			ret=self.config_col.find_one({"_id":key})
			return ret["value"]
		except:
			return None

	def _SetConfigValue(self,key,value):
		self.config_col.replace_one({"_id":key},{"value":value},True)

	def WriteConfigs(self):
		self.ROOM_DEFINITION=[]
		def addRoom(id, name, coord, labDefinition, spaceDefinition, windowedDefinition, maxOccupancy):
			self.ROOM_DEFINITION+=[{
				"id":id,
				"name":name,
				"coordinate": coord,
				"lab": labDefinition,
				"space": spaceDefinition,
				"windowed": windowedDefinition,
				"maxOccupancy": maxOccupancy
			}]
		addRoom("nwc10_hallway", "NWC 10F Hallway", [0,0], PUBLIC_SPACE, GENERAL_SPACE, NOT_WINDOWED, 0)
		addRoom("nwc1003b_danino", "Danino Wet Lab Space", [0, 0], DANINO_LAB, STUDENT_WORK_SPACE, WINDOWED, 4)
		addRoom("nwc10","NWC 10F Public Area", [40.810174, -73.962006], PUBLIC_SPACE, GENERAL_SPACE, NOT_WINDOWED, 0) # public area 10F, elevator bank etc.
		addRoom("nwc10m","NWC 10M Public Area", [40.810174, -73.962006], PUBLIC_SPACE, GENERAL_SPACE, NOT_WINDOWED, 0) # public area 10F, elevator bank etc.
		# exits
		addRoom("nwc8","NWC 8F Public Area", [40.810174, -73.962006], PUBLIC_SPACE, GENERAL_SPACE, WINDOWED, 0) # public area 8F
		addRoom("nwc7","NWC 7F Public Area", [40.810174, -73.962006], PUBLIC_SPACE, GENERAL_SPACE, WINDOWED, 0)# public area 7F
		addRoom("nwc4","NWC 4F Public Area", [40.810174, -73.962006], PUBLIC_SPACE, GENERAL_SPACE, WINDOWED, 0) # public area 4F

		addRoom("outOfLab", "Out of the Lab", [40.810174, -73.962006], PUBLIC_SPACE, GENERAL_SPACE, WINDOWED, 999)
		# 10F space units
		addRoom("nwc1008","NWC 1008 Office", [40.809997, -73.961983], JIANG_LAB, OFFICE_SPACE, WINDOWED, 1)
		addRoom("nwc1006","NWC 1006 Office", [40.809997, -73.961983], BURKE_LAB, OFFICE_SPACE, WINDOWED, 1)
		addRoom("nwc1007","NWC 1007 Office", [40.809997, -73.961983], TEHERANI_LAB, OFFICE_SPACE, WINDOWED, 1)
		addRoom("nwc1009","NWC 1009 Office", [40.809997, -73.961983], PUBLIC_SPACE, OFFICE_SPACE, WINDOWED, 1)
		addRoom("nwc1010","NWC 1010 Office", [40.809997, -73.961983], SAJDA_LAB, OFFICE_SPACE, WINDOWED, 1)

		addRoom("nwc1003g","1003 Optics G Lab", [40.809965, -73.962063], JIANG_LAB, STUDENT_WORK_SPACE, NOT_WINDOWED, 3)
		addRoom("nwc1003g_a", "1003 Optics G Lab A", [40.809965, -73.962063], BIOMED_LAB, STUDENT_WORK_SPACE, NOT_WINDOWED, 3)
		addRoom("nwc1003g_b", "1003 Optics G Lab B", [40.809965, -73.962063], TEHERANI_LAB, STUDENT_WORK_SPACE, NOT_WINDOWED, 3)
		addRoom("nwc1003g_c", "1003 Optics G Lab C", [40.809965, -73.962063], BIOMED_LAB, STUDENT_WORK_SPACE, NOT_WINDOWED, 3)

		#addRoom("nwc1003b","1003B Lab",[40.810022, -73.962075])
		addRoom("nwc1003b_a","1003B Lab Area A",[40.809980, -73.962159], JIANG_LAB, STUDENT_WORK_SPACE, WINDOWED, 2) # Seat for Peter/Daniel
		addRoom("nwc1003b_b","1003B Lab Area B",[40.809947, -73.962050], JIANG_LAB, STUDENT_WORK_SPACE, WINDOWED, 2) # Seat for Danny/Stephen
		addRoom("nwc1003b_c","1003B Lab Area C",[40.810005, -73.962072], JIANG_LAB, STUDENT_WORK_SPACE, WINDOWED, 2) # Seat for Rishi
		addRoom("nwc1003b_t","1003B Teherani Lab",[40.809897, -73.962138], TEHERANI_LAB, STUDENT_WORK_SPACE, WINDOWED, 4) # Prof. Teherani's space
		addRoom("nwc1003a", "1003A Hall Area", [40.809897, -73.962138], BURKE_LAB, GENERAL_SPACE, NOT_WINDOWED, 0)
		addRoom("nwc1003b", "1003B Hall Area", [40.809897, -73.962138], TEHERANI_LAB, GENERAL_SPACE, NOT_WINDOWED, 0)
		addRoom("nwc1001l", "1001L Hall Area", [40.809897, -73.962138], SAJDA_LAB, GENERAL_SPACE, NOT_WINDOWED, 0)


		# 10M space units, aisle 1-8
		addRoom("nwc1000m_a1","10M Floor, Aisle 1", [40.810050, -73.961945], BURKE_LAB, STUDENT_WORK_SPACE, WINDOWED, 4)
		addRoom("nwc1000m_a2","10M Floor, Aisle 2", [40.810038, -73.961955], BURKE_LAB, STUDENT_WORK_SPACE, WINDOWED, 4)
		addRoom("nwc1000m_a3","10M Floor, Aisle 3", [40.810021, -73.961966], DANINO_LAB, STUDENT_WORK_SPACE, WINDOWED, 4)
		addRoom("nwc1000m_a4","10M Floor, Aisle 4", [40.810005, -73.961978], DANINO_LAB, STUDENT_WORK_SPACE, WINDOWED, 4)
		addRoom("nwc1000m_a5","10M Floor, Aisle 5", [40.809986, -73.961991], TEHERANI_LAB, STUDENT_WORK_SPACE, WINDOWED, 4)
		addRoom("nwc1000m_a6","10M Floor, Aisle 6", [40.809968, -73.962003], JIANG_LAB, STUDENT_WORK_SPACE, WINDOWED, 4)
		addRoom("nwc1000m_a7","10M Floor, Aisle 7", [40.809950, -73.962017], PUBLIC_SPACE, STUDENT_WORK_SPACE, WINDOWED, 4)
		addRoom("nwc1000m_a8","10M Floor, Aisle 8", [40.809933, -73.962030], PUBLIC_SPACE, STUDENT_WORK_SPACE, WINDOWED, 4)

		# Only the lowest-layer cubicles, corresponding to localization unit

		self._SetConfigValue("ROOM_DEFINITION",self.ROOM_DEFINITION)

		self.APPLIANCE_DEFINITION=[]
		def addAppliance(Id, Name, Type, roomsRegex, actionableDefinition, dutyCycleDefinition):
			roomsMatched=[]
			for room in self.ROOM_DEFINITION:
				if re.search(roomsRegex, room["id"]):
					roomsMatched+=[room["id"]]
			item={
				"id":Id,
				"name":Name,
				"type":Type,
				"rooms":roomsMatched,
				"actionable": actionableDefinition,
				"dutyCycle": dutyCycleDefinition
			}
			self.APPLIANCE_DEFINITION+=[item]

		addAppliance("nwc1007_plug1", "Plug#1 in Prof Teherani's Office", "Electrical", "nwc1007", ACTIONABLE, NO_DUTY_CYCLE)
		addAppliance("nwc1007_plug2", "Plug#2 in Prof Teherani's Office", "Electrical", "nwc1007", ACTIONABLE, NO_DUTY_CYCLE)

		addAppliance("nwc1008_plug1", "Plug#1 in Prof Jiang's Office", "Electrical", "nwc1008", ACTIONABLE, NO_DUTY_CYCLE)
		addAppliance("nwc1008_smartvent1", "SmartVent in Prof Jiang's Office (HVAC Indirect Sensing)", "HVAC", "nwc1008", ACTIONABLE, NO_DUTY_CYCLE)
		addAppliance("nwc1008_light", "Lights in Prof Jiang's Office", "Light", "nwc1008", ACTIONABLE, NO_DUTY_CYCLE)

		addAppliance("nwc1003b_a_plug", "Plugmeter in 1003B Lab Area A (Peter)", "Electrical", "nwc1003b_a", ACTIONABLE, NO_DUTY_CYCLE)
		addAppliance("nwc1003b_b_plug", "Plugmeter in 1003B Lab Area B (Danny&Stephen)", "Electrical", "nwc1003b_b", ACTIONABLE, NO_DUTY_CYCLE)
		addAppliance("nwc1003b_c_plug", "Plugmeter in 1003B Lab Area C (Rishi)", "Electrical", "nwc1003b_c", ACTIONABLE, NO_DUTY_CYCLE)
		addAppliance("testDevice", "Aeon Labs Smart Switch 6 testings", "Electrical", "nwc1003b_c", ACTIONABLE, NO_DUTY_CYCLE)
		
		addAppliance("nwc1003g1_vav", "Heating Unit in 1003G", "HVAC", "nwc1003g.*", ACTIONABLE, NO_DUTY_CYCLE)
		addAppliance("nwc1003t2_vav", "Heating Unit in 1003b", "HVAC", "nwc1003b_a|nwc1003b_b|nwc1003b_t", ACTIONABLE, NO_DUTY_CYCLE)
		addAppliance("nwc1003o1_vav", "Heating Unit in 1003b", "HVAC", "nwc1003b_c|nwc1003b_danino", ACTIONABLE, NO_DUTY_CYCLE)
		addAppliance("nwc1008_fcu", "Heating Vent in 1008", "HVAC", "nwc1008", ACTIONABLE, NO_DUTY_CYCLE)
		addAppliance("nwcM2_fcu", "10F Mezzanine Heating Vent 1", "HVAC", "nwc1000m_a1|nwc1000m_a2|nwc1000m_a3", ACTIONABLE, NO_DUTY_CYCLE)
		addAppliance("nwcM3_fcu", "10F Mezzanine Heating Vent 2", "HVAC", "nwc1000m_a4|nwc1000m_a5", ACTIONABLE, NO_DUTY_CYCLE)
		addAppliance("nwcM1_fcu", "10F Mezzanine Heating Vent 3", "HVAC", "nwc1000m_a6|nwc1000m_a7", ACTIONABLE, NO_DUTY_CYCLE)
		addAppliance("nwcM4_fcu", "10F Mezzanine Heating Vent 4", "HVAC", "nwc1000m_a8", ACTIONABLE, NO_DUTY_CYCLE)

		# addAppliance("nwc1003b_fin", "Fin Tube Radiator in 1003B", "HVAC", "nwc1003b.*", ACTIONABLE, NO_DUTY_CYCLE)
		# addAppliance("nwc1003b_vav", "Air Vent in 1003B", "HVAC", "nwc1003b.*", ACTIONABLE, NO_DUTY_CYCLE)
		# addAppliance("nwc1003b_lex", "Fume Hoods in 1003B", "HVAC", "nwc1003b.*", ACTIONABLE, NO_DUTY_CYCLE)
		# addAppliance("nwc10_ahu", "Air Intake System for 10F", "HVAC", "nwc10.*", ACTIONABLE, NO_DUTY_CYCLE)
		# TODO: Map the FCUs (Fan Coils) to rooms, given floor plan
		# addAppliance("nwc1003g_vav", "Air Vent in 1003G", "HVAC", "nwc1003g.*", ACTIONABLE, NO_DUTY_CYCLE)
		
		addAppliance("nwc1003g_a_plug1", "Power outlet 1 in 1003G", "Electrical", "nwc1003g_a", ACTIONABLE, DUTY_CYCLE)
		addAppliance("nwc1003g_a_plug2", "Power outlet 2 in 1003G", "Electrical", "nwc1003g_a", ACTIONABLE, DUTY_CYCLE)
		addAppliance("nwc1003g_plug1", "Plugmeter in 1003G (Printer&Computer)", "Electrical", "^nwc1003g$", ACTIONABLE, DUTY_CYCLE)
		addAppliance("nwc1003g_plug2", "Plugmeter in 1003G (Soldering Station)", "Electrical", "^nwc1003g$", ACTIONABLE, DUTY_CYCLE)
		addAppliance("nwc1003g_plug3", "Plugmeter in 1003G (Projector&XBox)", "Electrical", "^nwc1003g$", ACTIONABLE, DUTY_CYCLE)
		addAppliance("nwc1003b_light", "Lights in 1003B Lab", "Light", "nwc1003b.*", ACTIONABLE, NO_DUTY_CYCLE)
		addAppliance("nwc1003g_light", "Lights in 1003G Lab", "Light", "^nwc1003g$", ACTIONABLE, NO_DUTY_CYCLE)

		addAppliance("nwc1003gA_vav", "Heating Unit in 1003G_A", "HVAC", "nwc1003g_a", ACTIONABLE, DUTY_CYCLE) #BIOMED LAB 1
		addAppliance("nwc1003gB_vav", "Heating Unit in 1003G_B", "HVAC", "nwc1003g_b", ACTIONABLE, DUTY_CYCLE) #TEHERANI LAB
		addAppliance("nwc1003gC_vav", "Heating Unit in 1003G_C", "HVAC", "nwc1003g_c", ACTIONABLE, DUTY_CYCLE) #BIOMED LAB 2
		addAppliance("nwc1003A_vav", "Heating Unit in 1003A", "HVAC", "nwc1003a", ACTIONABLE, DUTY_CYCLE)
		addAppliance("nwc1003B_vav", "Heating Unit in 1003B", "HVAC", "nwc1003b", ACTIONABLE, DUTY_CYCLE)
		addAppliance("nwc1001L_vav", "Heating Unit in 1001L", "HVAC", "nwc1001L", ACTIONABLE, DUTY_CYCLE)
		addAppliance("nwc10T1_vav", "Heating Unit in Danino Wetlab Space", "HVAC", "nwc1003b_danino", ACTIONABLE, DUTY_CYCLE)
		addAppliance("nwc10F_vav", "Heating Unit at 10F Elevators", "HVAC", "^nwc10$", ACTIONABLE, DUTY_CYCLE)
		addAppliance("nwc8F_vav", "Heating Unit at 8F Elevators", "HVAC", "^nwc8$", ACTIONABLE, DUTY_CYCLE)
		addAppliance("nwc7F_vav", "Heating Unit at 7F Elevators", "HVAC", "^nwc7$", ACTIONABLE, DUTY_CYCLE)

		for a in range(1,9,1):#1..8
			for p in range(1,3,1):#1..2
				if not (a==7 and p==1):
					addAppliance("nwc1000m_a"+str(a)+"_plug"+str(p), "Power strip #"+str(p)+" in Mezzaine Level, Aisle #"+str(a), "Electrical", "nwc1000m_a"+str(a), ACTIONABLE, NO_DUTY_CYCLE)
		
		addAppliance("nwc1000m_a6_plug3", "Power strip #3  in Mezzaine Level, Aisle #6", "Electrical", "nwc1000m_a6", ACTIONABLE, NO_DUTY_CYCLE)
		addAppliance("nwc1000m_a6_plug4", "Power strip #4  in Mezzaine Level, Aisle #6", "Electrical", "nwc1000m_a6", ACTIONABLE, NO_DUTY_CYCLE)
#        addAppliance("nwc1000m_a7_plug1", "Power strip #3 (Refrigerator&Zack) in Mezzaine Level, Aisle #6", "Electrical", "nwc1000m_a6", ACTIONABLE, NO_DUTY_CYCLE)
		addAppliance("nwc1000m_a1_plug3", "Power strip #3 in Mezzaine Level, Aisle #1", "Electrical", "nwc1000m_a1", ACTIONABLE, NO_DUTY_CYCLE)

		addAppliance("nwc1000m_light", "Shared Lighting in Mezzaine Level", "Light", "nwc1000m_.*", NOT_ACTIONABLE, NO_DUTY_CYCLE)
		addAppliance("nwc10hallway_light", "Hallway Lights", "Light", "nwc10_hallway", NOT_ACTIONABLE, NO_DUTY_CYCLE)
		addAppliance("nwc10elevator_light", "Common Area Lights", "Light", "^nwc10$", NOT_ACTIONABLE, NO_DUTY_CYCLE)
		addAppliance("nwc8_light", "8F Common Area Lights", "Light", "^nwc8$", NOT_ACTIONABLE, NO_DUTY_CYCLE)
		addAppliance("nwc7_light", "7F Common Area Lights", "Light", "^nwc7$", NOT_ACTIONABLE, NO_DUTY_CYCLE)


		self._SetConfigValue("APPLIANCE_DEFINITION",self.APPLIANCE_DEFINITION)

		# Snapshot timeout, in seconds
		self._SetConfigValue("SAMPLING_TIMEOUT_SHORTEST", 6)
		self._SetConfigValue("SAMPLING_TIMEOUT_LONGEST", 60*2)

		self._SetConfigValue("WATCHDOG_TIMEOUT_USER", 60*20)
		self._SetConfigValue("WATCHDOG_TIMEOUT_APPLIANCE", 60*20)


	def __init__(self):
		self.name="DB Initialization"
		print(self.name)
		self.dbc=pymongo.MongoClient()
		self.config_col=self.dbc.db.config
		self.WriteConfigs()
		print(self._GetConfigValue("APPLIANCE_DEFINITION"))

DBInit()
