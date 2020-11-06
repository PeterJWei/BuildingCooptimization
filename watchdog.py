import calendar
import datetime



class Watchdog:
	def _now(self):
		return calendar.timegm(datetime.datetime.utcnow().utctimetuple())

	def __init__(self, timeout_user, timeout_appliance):
		self.WATCHDOG_TIMEOUT_USER = timeout_user
		self.WATCHDOG_TIMEOUT_APPLIANCE = timeout_appliance
		self.watchdogLastSeen_User={}
		self.watchdogLastSeen_Appliance={}

	def watchdogRefresh_User(self, userID):
		if userID not in self.watchdogLastSeen_User:
			self.watchdogLastSeen_User[userID]=0
		self.watchdogLastSeen_User[userID]=max(self._now(), self.watchdogLastSeen_User[userID])

	def watchdogRefresh_Appliance(self, applID):
		if applID not in self.watchdogLastSeen_Appliance:
			self.watchdogLastSeen_Appliance[applID]=0
		self.watchdogLastSeen_Appliance[applID]=max(self._now(), self.watchdogLastSeen_Appliance[applID])

	def watchdogUserLastSeen(self, userID):
		if (userID in self.watchdogLastSeen_User):
			return self.watchdogLastSeen_User[userID]
		return None