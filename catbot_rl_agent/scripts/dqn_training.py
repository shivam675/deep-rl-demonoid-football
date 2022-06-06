# import imp
import gym
from stable_baselines import DQN
from stable_baselines.common.evaluation import evaluate_policy
import catbot_env
import rospkg
from gym import wrappers
import rospy
    
# Create environment
# env = gym.make('LunarLander-v2')
env = gym.make('bipedal-catbot-v0')

rospack = rospkg.RosPack()
pkg_path = rospack.get_path('catbot_rl_agent')
outdir = pkg_path + '/training_results'
env = wrappers.Monitor(env, outdir, force=True)
rospy.logdebug("Monitor Wrapper started")
# Instantiate the agent
model = DQN('MlpPolicy', env, learning_rate=1e-3, prioritized_replay=True, verbose=1)
# Train the agent
model.learn(total_timesteps=int(2e5))
# Save the agent
model.save("dqn_lunar")
del model  # delete trained model to demonstrate loading

# Load the trained agent
model = DQN.load("dqn_lunar")

# Evaluate the agent
mean_reward, std_reward = evaluate_policy(model, model.get_env(), n_eval_episodes=10)

# Enjoy trained agent
obs = env.reset()
for i in range(1000):
    action, _states = model.predict(obs)
    obs, rewards, dones, info = env.step(action)
    env.render()