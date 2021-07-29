import numpy as np
import tensorflow as tf

#tf.disable_v2_behavior()


class DeepQNetwork:
	def __init__(
			self,
			n_actions=22,
			n_features=14,
			n_sparse=2,
			n_dense=12,
			e_greedy=0.9,
			e_greedy_increment=None,):

		self.n_actions = n_actions
		self.n_features = n_features
		self.n_sparse = n_sparse
		self.n_dense = n_dense
		self.epsilon_max = e_greedy
		self.epsilon_increment = e_greedy_increment
		self.epsilon = 0 if e_greedy_increment is not None else self.epsilon_max

		self.graph = tf.Graph()
		self.sess = tf.Session(graph=self.graph)
		with self.graph.as_default():
			with tf.name_scope('model_1'):
				new_saver_1 = tf.train.import_meta_graph('RLModel/checkpoint_new/checkpoint/4_100_0.051621210654.ckpt.meta')
			new_saver_1.restore(self.sess, tf.train.latest_checkpoint('RLModel/checkpoint_new/checkpoint/'))
			with tf.name_scope('model_2'):
				new_saver_2 = tf.train.import_meta_graph('RLModel/checkpoint_new/checkpoint/4_100_0.051621210654.ckpt.meta')
			new_saver_2.restore(self.sess, tf.train.latest_checkpoint('RLModel/checkpoint_new/checkpoint/'))
		self.q_eval1_e = self.graph.get_tensor_by_name('model_1/eval_net/lt1/add:0')
		self.q_eval1_c = self.graph.get_tensor_by_name('model_1/eval_net/lt2/add:0')
		self.q_eval1_q = self.graph.get_tensor_by_name('model_1/eval_net/lt3/add:0')
		self.ss1 = self.graph.get_tensor_by_name('model_1/ss:0')
		self.sd1 = self.graph.get_tensor_by_name('model_1/sd:0')
		self.q_eval2_e = self.graph.get_tensor_by_name('model_2/eval_net/lt1/add:0')
		self.q_eval2_c = self.graph.get_tensor_by_name('model_2/eval_net/lt2/add:0')
		self.q_eval2_q = self.graph.get_tensor_by_name('model_2/eval_net/lt3/add:0')
		self.ss2 = self.graph.get_tensor_by_name('model_2/ss:0')
		self.sd2 = self.graph.get_tensor_by_name('model_2/sd:0')


	def get_all_actions(self, observation):
		observation = observation[np.newaxis, :]
		actions_value1_e = self.sess.run(self.q_eval1_e, feed_dict={self.ss1: observation[:,:self.n_sparse],
															self.sd1: observation[:,self.n_sparse:]})#{self.s: observation})
		actions_value1_c = self.sess.run(self.q_eval1_c, feed_dict={self.ss1: observation[:,:self.n_sparse],
															self.sd1: observation[:,self.n_sparse:]})#{self.s: observation})
		actions_value1_q = self.sess.run(self.q_eval1_q, feed_dict={self.ss1: observation[:,:self.n_sparse],
															self.sd1: observation[:,self.n_sparse:]})#{self.s: observation})
		actions_value2_e = self.sess.run(self.q_eval2_e, feed_dict={self.ss2: observation[:,:self.n_sparse],
															self.sd2: observation[:,self.n_sparse:]})#{self.s: observation})
		actions_value2_c = self.sess.run(self.q_eval2_c, feed_dict={self.ss2: observation[:,:self.n_sparse],
															self.sd2: observation[:,self.n_sparse:]})#{self.s: observation})
		actions_value2_q = self.sess.run(self.q_eval2_q, feed_dict={self.ss2: observation[:,:self.n_sparse],
															self.sd2: observation[:,self.n_sparse:]})#{self.s: observation})
		return actions_value1_e, actions_value1_c, actions_value1_q, actions_value2_e, actions_value2_c, actions_value2_q


	def choose_action(self, observation):
		# to have batch dimension when feed into tf placeholder
		observation = observation[np.newaxis, :]
		if np.random.uniform() < self.epsilon:
			# forward feed the observation and get q value for every actions
			actions_value = self.sess.run(self.q_eval, feed_dict={self.ss: observation[:,:self.n_sparse],
																  self.sd: observation[:,self.n_sparse:]})#{self.s: observation})
			action = np.argmax(actions_value)
		else:
			action = np.random.randint(0, self.n_actions)
		return action


if __name__ == "__main__":
	test_input = [9,12,515,764,765,515,515,515,236,236,236,236,174,70]
	DQN = DeepQNetwork()
	action = DQN.choose_action(np.array(test_input))
	print("Action: " + str(action))
