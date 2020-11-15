def zero_offset(item, mismatch_penalty=-10):
	default = -100
	count=sum([1 for x in item if x!=default])
	if(count==0):count=1
	total=sum([x for x in item if x!=default])
	offset=total*1.0/count
	return [x-(int(x!=default)*offset)-(int(x==default)*(default-mismatch_penalty)) for x in item]

class KNearestNeighbors:
	def __init__(self, samplePairs):#pairs of (sample, label)
		self.samplePairs = samplePairs

	def get_nearest_pairs(self, sample, K=7):
		distances=[]
		#print("sample lengths:")
		#print((len(sample), len(self.samplePairs[0][0])))
		for i in xrange(len(self.samplePairs)):
			dist = self.EUDist(zero_offset(self.samplePairs[i][0]), zero_offset(sample))
			distances.append((dist, self.samplePairs[i][1]))
		sortedDistances = sorted(distances, key=lambda dist:dist[0])
		nearestPairs=sortedDistances[0:K]
		#return [(pair[1],1) for pair in nearestPairs]

		minDist=min([pair[0] for pair in nearestPairs])
		if minDist<1:
			minDist=1
		def weight(dist):
			if dist<1:
				dist=1
			return minDist*1.0/dist	
		return [(pair[1],weight(pair[0])) for pair in nearestPairs]
		
	def EUDist(self, Xmeas, Ymeas):
		sum = 0
		for i in xrange(len(Xmeas)):
			sum += (Ymeas[i]-Xmeas[i])*(Ymeas[i]-Xmeas[i])
		return sum

	def majority_vote(self, vote_pairs):#pair(roomID, #votes)
		def merge_same_votes(pairs):
			vote_map={}
			for pair in pairs:
				if pair[0] not in vote_map:
					vote_map[pair[0]]=0
				vote_map[pair[0]]+=pair[1]
			merged_votes=[]
			for roomID in vote_map:
				merged_votes+=[(roomID,vote_map[roomID])]
			return merged_votes

		vote_pairs=merge_same_votes(vote_pairs)
		maximum_pair = (None, 0)
		for vote in vote_pairs:
			if vote[1]>maximum_pair[1]:
				maximum_pair=vote
		return maximum_pair