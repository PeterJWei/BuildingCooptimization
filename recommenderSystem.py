import numpy as np
# import tensorflow.compat.v1 as tf

# tf.disable_v2_behavior()
from DeepQLearning import DeepQNetwork as DQN
import datetime

class recommenderSystem:
	def __init__(self):
		self.setup()


	def setup(self):
		self.checkInterval = 15
		self.person_states = ["Peter",
				"Yanchen",
				"Hengjiu",
				"Mark",
				"Joe",
				"Lei",
				"Abhi",
				"Ankur",
				"Anjaly",
				"Jingping",
				"Chenye",
				"Fred",
				"Stephen"]
		self.room_states = ["1003E", "1003B_A", "1003B_B", "1003G_A",
			   "1003G_B", "1003G_C", "1000M_A1", "1000M_A2",
			   "1000M_A5", "1000M_A6", "1008"]
		self.room_names = [
			"nwc1003E", "nwc1003b_a", "nwc1003b_b", "nwc1003g", "nwc1003g_a",
			"nwc1003g_c", "nwc1000m_a1", "nwc1000m_a2", "nwc1000m_a5", "nwc1000m_a6",
			"nwc1008"
		]
		self.long_names = [
			"NWC 1003E (Burke Lab Space)", "NWC 1003B Lab Space A (Peter)", "NWC 1003B Lab Space B (Yanchen/Hengjiu)", "NWC 1003G Laser Lab Space A (ICSL)", "NWC1003G Laser Lab Space B (TitanX)", "NWC1003G Laser Lab Space C (Hone/Schuck Lab)", "NWC 1000M Aisle 1 (Joe/Mark)", "NWC 1000M Aisle 2 (Lei)" , "NWC 1000M Aisle 5 (Teherani)", "NWC 1000M Aisle 6 (ICSL)", "Professor Jiang's Office"	
		]
		self.default = {
			"Peter": "1003B_A",
			"Yanchen": "1000M_A6",
			"Hengjiu": "1003B_B",
			"Mark": "1000M_A1",
			"Joe": "1000M_A1",
			"Lei": "1000M_A2",
			"Abhi": "1000M_A5",
			"Ankur": "1000M_A5",
			"Anjaly": "1000M_A5",
			"Jingping": "1000M_A6",
			"Chenye": "1003B_B",
			"Fred": "1008",
			"Stephen": "1003G_A"
		}
		
		n_actions = len(self.room_states) * len(self.person_states) + 4 * len(self.person_states)
		n_sparse = len(self.person_states)
		n_dense = len(self.room_states) * 6 + 1 # each room energy and 1 for time
		n_features = n_sparse + n_dense
		e_greedy = 0.9
		self.model = DQN(
			n_actions,
			n_features,
			n_sparse,
			n_dense, 
			e_greedy)


	def _loopRecommendations(self, users, rooms, appliances):
		# Get state from parameters
		state = []
		locations = {}
		for i, person in enumerate(self.person_states):
			user_loc = None
			if person in users and users[person] in self.room_names:
				person_state = self.room_names.index(users[person])
				print((person, self.room_names[person_state]))
				user_loc = self.long_names[person_state]
			else:
				person_state = self.room_states.index(self.default[person])# + i*len(self.room_states)
				user_loc = self.long_names[person_state]
			locations[person] = user_loc
			state.append(person_state)
		print("\n\n\n\n\n")
		print(locations)
		print("\n\n\n\n\n")
		room_energies = self.get_room_energies(rooms, appliances)
		for room in self.room_names:
			state.append(room_energies[room])
		for room in self.room_names:
			if room in rooms and "Temperature" not in rooms[room]:
				print(room + " has no attribute Temperature")
				state.append(72.0)
			else:
				state.append(rooms[room]["Temperature"])
		for room in self.room_names:
			if room in rooms and "Humidity" not in rooms[room]:
				print(room + " has no attribute Humidity")
				state.append(20.0)
			else:
				state.append(rooms[room]["Humidity"])
		for room in self.room_names:
			if room in rooms and "PM" not in rooms[room]:
				print(room + " has no attribute PM")
				state.append(5.0)
			elif room in rooms and "PM" in rooms[room] and "PM25" not in rooms[room]["PM"]:
				print(room + " has no attribute PM/PM25")
				state.append(5.0)
			else:
				PM25 = rooms[room]["PM"]["PM25"]
				state.append(self.get_PM25(PM25))
		for room in self.room_names:
			if room in rooms and "PM" in rooms[room]:
				print(room + " has no attribute PM")
				state.append(5.0)
			elif room in rooms and "PM" in rooms[room] and "PM10" not in rooms[room]["PM"]:
				print(room + " has no attribute PM/PM10")
				state.append(5.0)
			else:
				PM10 = rooms[room]["PM"]["PM10"]
				state.append(self.get_PM10(PM10))
		for room in self.room_names:
			state.append(0)
		HOUR = datetime.datetime.now().hour
		MINUTE = datetime.datetime.now().minute
		minutes = HOUR * 60 + MINUTE
		ts = minutes // 15
		state.append(ts) #update

		action_scores1_e, action_scores1_c, action_scores1_q, action_scores2_e, action_scores2_c, action_scores2_q = self.model.get_all_actions(np.array(state))
		recommendations1, recommendations2 = {}, {}
		for i, person in enumerate(self.person_states):
			personal_recs1, personal_recs2 = [], []
			# personal_scores = action_scores[0][i*len(self.room_states):(i+1)*len(self.room_states)]
			personal_scores1_e = action_scores1_e[0][i*len(self.room_states):(i+1)*len(self.room_states)]
			personal_scores1_c = action_scores1_c[0][i*len(self.room_states):(i+1)*len(self.room_states)]
			personal_scores1_q = action_scores1_q[0][i*len(self.room_states):(i+1)*len(self.room_states)]
			personal_scores2_e = action_scores2_e[0][i*len(self.room_states):(i+1)*len(self.room_states)]
			personal_scores2_c = action_scores2_c[0][i*len(self.room_states):(i+1)*len(self.room_states)]
			personal_scores2_q = action_scores2_q[0][i*len(self.room_states):(i+1)*len(self.room_states)]

			# print("personal scores")
			# print(personal_scores)
			top_k1 = sorted(range(len(personal_scores1_e)), key=lambda i: personal_scores1_e[i])[-10:]
#			top_k2 = sorted(range(len(personal_scores2_q)), key=lambda i: personal_scores2_q[i])[-3:]
			top_k2 = []#sorted(range(len(personal_scores2_q)), key=lambda i: personal_scores2_q[i])[-3:]
			# top_k = sorted(range(len(personal_scores)), key=lambda i: personal_scores[i])[-5:]
			# print(top_k)
			
			############## Setpoint Recommendations ############
			offset = len(self.room_states) * len(self.person_states)
			personal_scores3_e = action_scores1_e[0][offset+i*4:offset+(i+1)*4]
			personal_scores3_c = action_scores1_c[0][offset+i*4:offset+(i+1)*4]
			personal_scores3_q = action_scores1_q[0][offset+i*4:offset+(i+1)*4]
			personal_scores4_e = action_scores2_e[0][offset+i*4:offset+(i+1)*4]
			personal_scores4_c = action_scores2_c[0][offset+i*4:offset+(i+1)*4]
			personal_scores4_q = action_scores2_q[0][offset+i*4:offset+(i+1)*4]
			top_k3 = sorted(range(len(personal_scores3_e)), key=lambda i: personal_scores3_e[i])[-4:]
#			top_k4 = sorted(range(len(personal_scores4_q)), key=lambda i: personal_scores4_q[i])[-2:]
			top_k4 = sorted(range(len(personal_scores4_q)), key=lambda i: personal_scores4_q[i])
			for i, index in enumerate(top_k1):
				personal_rec = {}
				new_location = self.room_states[index]
				new_location_long = self.long_names[index]
				old_location = self.long_names.index(locations[person])
#				old_location_i = person_state
				new_room = self.room_names[index]
				old_room = self.room_names[old_location]
#				print((old_location, old_location_i))
				if old_room == new_room:
					rank = i
					personal_rec["title"] = "No Change"
					personal_rec["desc"] = "No Change"
					personal_rec["opt"] = "No Change"
					personal_rec["rank"] = rank
					personal_rec["energy"] = 0 
					personal_rec["comfort"] = 0
					personal_rec["aq"] = 0 
					personal_rec["t"] = "move"
					personal_recs1.append(personal_rec)
					continue
				new_energy = room_energies[self.room_names[index]]
				old_energy = room_energies[self.room_names[old_location]]
				predicted_energy = old_energy - new_energy
				if new_room in rooms and "Temperature" in rooms[new_room]:
					new_temp = rooms[new_room]["Temperature"]
					if new_temp < 50: new_temp = new_temp * 9/5 + 32
				else:
					new_temp = 72.0
				if old_room in rooms and "Temperature" in rooms[old_room]:
					old_temp = rooms[old_room]["Temperature"]
					if old_temp < 50: old_temp = old_temp * 9/5 + 32
				else:
					old_temp = 72.0
				predicted_comfort = abs(old_temp - 72) - abs(new_temp - 72)
				#predicted_AQ = old_PM - old_PM * (1 - 0.05 * abs(change))
				#new_temp = old_temp + change
				if (old_temp - 72) == 0:
					predicted_comfort = (abs(old_temp - 72) - abs(new_temp - 72))/1.0
				else:
					predicted_comfort = (abs(old_temp - 72) - abs(new_temp - 72)) / abs(old_temp - 72)
				if new_room in rooms and "PM" in rooms[new_room] and "PM25" in rooms[new_room]["PM"]:
					new_PM = rooms[new_room]["PM"]["PM25"]
					new_PM = self.get_PM25(new_PM)
				else:
					new_PM = 5.0
				if old_room in rooms and "PM" in rooms[old_room] and "PM25" in rooms[old_room]["PM"]:
					old_PM = rooms[old_room]["PM"]["PM25"]
					old_PM = self.get_PM25(old_PM)
				else:
					old_PM = 10.0
				predicted_AQ = old_PM - new_PM

				energy = predicted_energy#personal_scores1_e[index]
				comfort = predicted_comfort #personal_scores1_c[index]
				aq = predicted_AQ #personal_scores1_q[index]
				title = "Move to: " + new_location
				desc = "Moving to " + new_location_long + " results in:"
				opt = "Comfort change: " + str(abs(comfort)) + ", Air Quality Change: " + str(abs(aq))
				rank = i
				personal_rec["title"] = title
				personal_rec["desc"] = desc
				personal_rec["opt"] = opt
				personal_rec["rank"] = rank
				personal_rec["energy"] = str(energy)
				personal_rec["comfort"] = str(comfort)
				personal_rec["aq"] = str(aq)
				personal_rec["t"] = "move"
				personal_recs1.append(personal_rec)
			for i, index in enumerate(top_k3):
				personal_rec = {}
				old_location = person_state
				old_energy = room_energies[self.room_names[old_location]]
				old_room = self.room_names[old_location]
				if old_room in rooms and "Temperature" in rooms[old_room]:
					old_temp = rooms[old_room]["Temperature"]
					if old_temp < 50: old_temp = old_temp * 9/5 + 32
				else:
					old_temp = 72.0
				if old_room in rooms and "PM" in rooms[old_room] and "PM25" in rooms[old_room]["PM"]:
					old_PM = rooms[old_room]["PM"]["PM25"]
					old_PM = self.get_PM25(old_PM)
				else:
					old_PM = 10.0
				if index == 0:
					change = -2
					modifier = 0.8
				elif index == 1:
					change = -1
					modifier = 0.9
				elif index == 2:
					change = 1
					modifier = 1.05
				elif index == 3:
					change = 2
					modifier = 1.15
				predicted_AQ = old_PM - old_PM * (1 - 0.05 * abs(change))
				new_temp = old_temp + change
				if (old_temp - 72) == 0:
					predicted_comfort = (abs(old_temp - 72) - abs(new_temp - 72))/1.0
				else:
					predicted_comfort = (abs(old_temp - 72) - abs(new_temp - 72)) / abs(old_temp - 72)
				energy = old_energy - old_energy * modifier#personal_scores3_e[index]
				comfort = predicted_comfort #personal_scores3_c[index]
				aq = predicted_AQ #personal_scores3_q[index]
				title = "Change Setpoint: " + str(change) + " degrees"
				desc = "Change Setpoint by " + str(change) + " degrees"
				opt = "Comfort change: " + str(abs(comfort)) + ", Air Quality Change: " + str(abs(aq))
				rank = i
				personal_rec["title"] = title
				personal_rec["desc"] = desc
				personal_rec["opt"] = opt
				personal_rec["rank"] = rank
				personal_rec["energy"] = str(energy)
				personal_rec["comfort"] = str(comfort)
				personal_rec["aq"] = str(aq)
				personal_rec["t"] = "setpoint"
				personal_recs1.append(personal_rec)
			for i, index in enumerate(top_k2):
				personal_rec = {}
				new_location = self.room_states[index]
				new_location_long = self.long_names[index]
				old_location = person_state
				new_room = self.room_names[index]
				old_room = self.room_names[old_location]
				new_energy = room_energies[self.room_names[index]]
				old_energy = room_energies[self.room_names[old_location]]
				predicted_energy = old_energy - new_energy
				if new_room in rooms and "Temperature" in rooms[new_room]:
					new_temp = rooms[new_room]["Temperature"]
					if new_temp < 50: new_temp = new_temp * 9/5 + 32
				else:
					new_temp = 72.0
				if old_room in rooms and "Temperature" in rooms[old_room]:
					old_temp = rooms[old_room]["Temperature"]
					if old_temp < 50: old_temp = old_temp * 9/5 + 32
				else:
					old_temp = 72.0
				predicted_comfort = abs(old_temp - 72) - abs(new_temp - 72)
				if new_room in rooms and "PM" in rooms[new_room] and "PM25" in rooms[new_room]["PM"]:
					new_PM = rooms[new_room]["PM"]["PM25"]
					new_PM = self.get_PM25(new_PM)
				else:
					new_PM = 5.0
				if old_room in rooms and "PM" in rooms[old_room] and "PM25" in rooms[old_room]["PM"]:
					old_PM = rooms[old_room]["PM"]["PM25"]
					old_PM = self.get_PM25(old_PM)
				else:
					old_PM = 10.0
				predicted_AQ = old_PM - new_PM
				energy = predicted_energy #personal_scores2_e[index]
				comfort = predicted_comfort #personal_scores2_c[index]
				aq = predicted_AQ #personal_scores2_q[index]
				title = "Move to: " + new_location
				desc = "Moving to " + new_location_long + " results in:"
				opt = "Comfort change: " + str(abs(comfort)) + ", Air Quality Change: " + str(abs(aq))
				rank = i
				personal_rec["title"] = title
				personal_rec["desc"] = desc
				personal_rec["opt"] = opt
				personal_rec["rank"] = rank
				personal_rec["energy"] = str(energy)
				personal_rec["comfort"] = str(comfort)
				personal_rec["aq"] = str(aq)
				personal_rec["t"] = "move"
				personal_recs2.append(personal_rec)
			for i, index in enumerate(top_k4):
				personal_rec = {}
				old_location = person_state
				old_energy = room_energies[self.room_names[old_location]]
				old_room = self.room_names[old_location]
				if old_room in rooms and "Temperature" in rooms[old_room]:
					old_temp = rooms[old_room]["Temperature"]
					if old_temp < 50: old_temp = old_temp * 9/5 + 32
				else:
					old_temp = 72.0
				if old_room in rooms and "PM" in rooms[old_room] and "PM25" in rooms[old_room]["PM"]:
					old_PM = rooms[old_room]["PM"]["PM25"]
					old_PM = self.get_PM25(old_PM)
				else:
					old_PM = 10.0
				if index == 0:
					change = -2
					modifier = 0.8
				elif index == 1:
					change = -1
					modifier = 0.9
				elif index == 2:
					change = 1
					modifier = 1.05
				elif index == 3:
					change = 2
					modifier = 1.10
				new_temp = old_temp + change
				if (old_temp - 72) == 0:
					predicted_comfort = (abs(old_temp - 72) - abs(new_temp - 72))/1.0
				else:
					predicted_comfort = (abs(old_temp - 72) - abs(new_temp - 72)) / abs(old_temp - 72)
				predicted_AQ = old_PM - old_PM * (1 - 0.05 * abs(change))
#				predicted_comfort = abs(old_temp - 72) - abs(new_temp - 72)
				energy = old_energy - old_energy * modifier #personal_scores4_e[index]
				comfort = predicted_comfort #personal_scores4_c[index]
				aq = predicted_AQ #personal_scores4_q[index]
				title = "Change Setpoint: " + str(change) + " degrees"
				desc = "Change Setpoint by " + str(change) + " degrees"
				opt = "Comfort change: " + str(abs(comfort)) + ", Air Quality Change: " + str(abs(aq))
				rank = i
				personal_rec["title"] = title
				personal_rec["desc"] = desc
				personal_rec["opt"] = opt
				personal_rec["rank"] = rank
				personal_rec["energy"] = str(energy)
				personal_rec["comfort"] = str(comfort)
				personal_rec["aq"] = str(aq)
				personal_rec["t"] = "setpoint"
				personal_recs2.append(personal_rec)
			no_setpoint_rec = {
				"title": "No Setpoint Change",
				"desc": "No change",
				"opt": "Comfort change: 0%, Air Quality Change: 0%",
				"rank": 5,
				"energy": 0,
				"comfort": 0,
				"aq": 0,
				"t": "setpoint"
			}
			personal_recs2.append(no_setpoint_rec)
			personal_recs1 = sorted(personal_recs1, key=lambda rec: float(rec["energy"]))
			personal_recs2 = sorted(personal_recs2, key=lambda rec: float(rec["aq"]))
			recommendations1[person] = personal_recs1
			recommendations2[person] = personal_recs2
		return recommendations1, recommendations2, locations

	def get_PM25(self, particle_count):
		PM25 = [(0, 50, 0, 12.0),
			(51, 100, 12.0, 35.4),
			(101, 150, 35.4, 55.4),
			(151, 200, 55.4, 150.4),
			(201, 300, 150.4, 250.4),
			(301, 400, 250.4, 350.4),
			(401, 500, 350.4, 500.4)]
		PM25C = particle_count * 0.044896 # micro g/m^3
		for tup in PM25:
			Il, Ih, Cl, Ch = tup
			if Cl <= PM25C and Ch >= PM25C:
				return (Ih-Il)*1.0/(Ch-Cl)*(PM25C-Cl)+Il
		return 0

	def get_PM10(self, particle_count):
		PM10 = [(0, 50, 0, 54.0),
			(51, 100, 54.0, 154.0),
			(101, 150, 154.0, 254.0),
			(151, 200, 254.0, 354.0),
			(201, 300, 354.0, 424.0),
			(301, 400, 424.0, 504.0),
			(401, 500, 504.0, 604.0)]
		PM10C = particle_count * 0.74824 # micro g/m^3
		for tup in PM10:
			Il, Ih, Cl, Ch = tup
			if Cl <= PM10C and Ch >= PM10C:
				return (Ih-Il)*1.0/(Ch-Cl)*(PM10C-Cl)+Il
		return 0

	def get_room_energies(self, rooms, appliances):
		room_energies = {}
		for room in self.room_names:
			total_energy = 0.0
			app_list = rooms[room]["appliances"]
			for applianceID in app_list:
				app = appliances[applianceID]
				total_energy += app["value"]
			room_energies[room] = total_energy
		return room_energies
