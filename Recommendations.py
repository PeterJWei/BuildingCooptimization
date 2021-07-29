import json
import web

import cloudserver


urls = (
"/(.+)","UserRecommendations",
)



class UserRecommendations:
    def POST(self,Id):
        raw_data=web.data()
	name = cloudserver.db.PID2Name(Id)
	recommendations = cloudserver.db.get_recommendations(name)
        return recommendations
        
UserRecs = web.application(urls, locals())
