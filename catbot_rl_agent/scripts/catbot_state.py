#!/usr/bin/env python3

import rospy
from gazebo_msgs.msg import ContactsState
from sensor_msgs.msg import Imu
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Point, Quaternion, Vector3
from sensor_msgs.msg import JointState
import tf
import numpy
import math

"""
 wrenches:
      -
        force:
          x: -0.134995398774
          y: -0.252811705608
          z: -0.0861598399337
        torque:
          x: -0.00194729925705
          y: 0.028723398244
          z: -0.081229664152
    total_wrench:
      force:
        x: -0.134995398774
        y: -0.252811705608
        z: -0.0861598399337
      torque:
        x: -0.00194729925705
        y: 0.028723398244
        z: -0.081229664152
    contact_positions:
      -
        x: -0.0214808318267
        y: 0.00291348151391
        z: -0.000138379966267
    contact_normals:
      -
        x: 0.0
        y: 0.0
        z: 1.0
    depths: [0.000138379966266991]
  -
    info: "Debug:  i:(2/4)     my geom:monoped::lowerleg::lowerleg_contactsensor_link_collision_1\
  \   other geom:ground_plane::link::collision         time:50.405000000\n"
    collision1_name: "monoped::lowerleg::lowerleg_contactsensor_link_collision_1"
    collision2_name: "ground_plane::link::collision"

"""
"""
std_msgs/Header header
  uint32 seq
  time stamp
  string frame_id
gazebo_msgs/ContactState[] states
  string info
  string collision1_name
  string collision2_name
  geometry_msgs/Wrench[] wrenches
    geometry_msgs/Vector3 force
      float64 x
      float64 y
      float64 z
    geometry_msgs/Vector3 torque
      float64 x
      float64 y
      float64 z
  geometry_msgs/Wrench total_wrench
    geometry_msgs/Vector3 force
      float64 x
      float64 y
      float64 z
    geometry_msgs/Vector3 torque
      float64 x
      float64 y
      float64 z
  geometry_msgs/Vector3[] contact_positions
    float64 x
    float64 y
    float64 z
  geometry_msgs/Vector3[] contact_normals
    float64 x
    float64 y
    float64 z
  float64[] depths
"""

class CatbotState(object):

    def __init__(self, max_height, min_height, abs_max_roll, abs_max_pitch, joint_increment_value = 0.05, done_reward = -1000.0, alive_reward=10.0, desired_force=7.08, desired_yaw=0.0, weight_r1=1.0, weight_r2=1.0, weight_r3=1.0, weight_r4=1.0, weight_r5=1.0, discrete_division=10):
        rospy.logdebug("Starting Catbot State Class object...")
        self.desired_world_point = Vector3(0.0, 0.0, 0.0)
        self._min_height = min_height
        self._max_height = max_height
        self._abs_max_roll = abs_max_roll
        self._abs_max_pitch = abs_max_pitch
        self._joint_increment_value = joint_increment_value
        self._done_reward = done_reward
        self._alive_reward = alive_reward
        self._desired_force = desired_force
        self._desired_yaw = desired_yaw

        self._weight_r1 = weight_r1
        self._weight_r2 = weight_r2
        self._weight_r3 = weight_r3
        self._weight_r4 = weight_r4
        self._weight_r5 = weight_r5

        self._list_of_observations = ["distance_from_desired_point",
                 "base_roll",
                 "base_pitch",
                 "base_yaw",
                 "contact_force_left_leg",
                 "contact_force_right_leg",
                 "joint_states_bum_zlj",
                 "joint_states_bum_xlj",
                 "joint_states_bum_ylj",
                 "joint_states_knee_left",
                 "joint_states_ankle_lj",
                 "joint_states_foot_lj",
                 "joint_states_bum_zrj",
                 "joint_states_bum_xrj",
                 "joint_states_bum_yrj",
                 "joint_states_knee_right",
                 "joint_states_ankle_rj",
                 "joint_states_foot_rj",
                 "joint_states_shoulder_zlj",
                 "joint_states_shoulder_xlj",
                 "joint_states_shoulder_ylj",
                 "joint_states_forearm_ylj",
                 "joint_states_shoulder_zrj",
                 "joint_states_shoulder_xrj",
                 "joint_states_shoulder_yrj",
                 "joint_states_forearm_yrj",]

        self._discrete_division = discrete_division
        # We init the observation ranges and We create the bins now for all the observations
        self.init_bins()

        self.base_position = Point()
        self.base_orientation = Quaternion()
        self.base_linear_acceleration = Vector3()
        self.left_contact_force = Vector3()
        self.right_contact_force = Vector3()
        self.joints_state = JointState()

        # Odom we only use it for the height detection and planar position ,
        #  because in real robots this data is not trivial.
        rospy.Subscriber("/odom", Odometry, self.odom_callback)
        # We use the IMU for orientation and linearacceleration detection
        rospy.Subscriber("/monoped/imu/data", Imu, self.imu_callback)
        # We use it to get the contact force, to know if its in the air or stumping too hard.
        rospy.Subscriber("/lower_left_leg_contactsensor_state", ContactsState, self.left_contact_callback)
        rospy.Subscriber("/lower_right_leg_contactsensor_state", ContactsState, self.right_contact_callback)
        # We use it to get the joints positions and calculate the reward associated to it
        rospy.Subscriber("/joint_states", JointState, self.joints_state_callback)

    def check_all_systems_ready(self):
        """
        We check that all systems are ready
        :return:
        """
        data_pose = None
        while data_pose is None and not rospy.is_shutdown():
            try:
                data_pose = rospy.wait_for_message("/odom", Odometry, timeout=0.1)
                self.base_position = data_pose.pose.pose.position
                rospy.logdebug("Current odom READY")
            except:
                rospy.logdebug("Current odom pose not ready yet, retrying for getting robot base_position")

        imu_data = None
        while imu_data is None and not rospy.is_shutdown():
            try:
                imu_data = rospy.wait_for_message("/catbot/imu/data", Imu, timeout=0.1)
                self.base_orientation = imu_data.orientation
                self.base_linear_acceleration = imu_data.linear_acceleration
                rospy.logdebug("Current imu_data READY")
            except:
                rospy.logdebug("Current imu_data not ready yet, retrying for getting robot base_orientation, and base_linear_acceleration")

        left_contacts_data = None

        #####################################################################################
        ########################### Check both legs #########################################

        while left_contacts_data is None and not rospy.is_shutdown():
            try:
                left_contacts_data = rospy.wait_for_message("/lower_left_leg_contactsensor_state", ContactsState, timeout=0.1)
                for state in left_contacts_data.states:
                    self.left_contact_force = state.total_wrench.force
                rospy.logdebug("Current LEFT contacts_data READY")
            except:
                rospy.logdebug("Current LEFT contacts_data not ready yet, retrying")

        right_contacts_data = None
        while right_contacts_data is None and not rospy.is_shutdown():
            try:
                right_contacts_data = rospy.wait_for_message("/lower_right_leg_contactsensor_state", ContactsState, timeout=0.1)
                for state in right_contacts_data.states:
                    self.right_contact_force = state.total_wrench.force
                rospy.logdebug("Current RIGHT contacts_data READY")
            except:
                rospy.logdebug("Current RIGHT contacts_data not ready yet, retrying")

        ##########################################################################################
        ##########################################################################################



        joint_states_msg = None
        while joint_states_msg is None and not rospy.is_shutdown():
            try:
                joint_states_msg = rospy.wait_for_message("/joint_states", JointState, timeout=0.1)
                self.joints_state = joint_states_msg
                rospy.logdebug("Current joint_states READY")
            except Exception as e:
                rospy.logdebug("Current joint_states not ready yet, retrying==>"+str(e))

        rospy.logdebug("ALL SYSTEMS READY")





    def set_desired_world_point(self, x, y, z):
        """
        Point where you want the Monoped to be
        :return:
        """
        self.desired_world_point.x = x
        self.desired_world_point.y = y
        self.desired_world_point.z = z


    def get_base_height(self):
        return abs(self.base_position.z)

    def get_base_rpy(self):
        euler_rpy = Vector3()
        euler = tf.transformations.euler_from_quaternion(
            [self.base_orientation.x, self.base_orientation.y, self.base_orientation.z, self.base_orientation.w])

        euler_rpy.x = euler[0]
        euler_rpy.y = euler[1]
        euler_rpy.z = euler[2]
        return euler_rpy

    def get_distance_from_point(self, p_end):
        """
        Given a Vector3 Object, get distance from current position
        :param p_end:
        :return:
        """
        a = numpy.array((self.base_position.x, self.base_position.y, self.base_position.z))
        b = numpy.array((p_end.x, p_end.y, p_end.z))

        distance = numpy.linalg.norm(a - b)

        return distance

    def get_left_contact_force_magnitude(self):
        """
        You will see that because the X axis is the one pointing downwards, it will be the one with
        higher value when touching the floor
        For a Robot of total mas of 0.55Kg, a gravity of 9.81 m/sec**2, Weight = 0.55*9.81=5.39 N
        Falling from around 5centimetres ( negligible height ), we register peaks around
        Fx = 7.08 N
        :return:
        """
        contact_force = self.left_contact_force
        contact_force_np = numpy.array((contact_force.x, contact_force.y, contact_force.z))
        force_magnitude = numpy.linalg.norm(contact_force_np)

        return force_magnitude

    
    def get_right_contact_force_magnitude(self):
        """
        You will see that because the X axis is the one pointing downwards, it will be the one with
        higher value when touching the floor
        For a Robot of total mas of 0.55Kg, a gravity of 9.81 m/sec**2, Weight = 0.55*9.81=5.39 N
        Falling from around 5centimetres ( negligible height ), we register peaks around
        Fx = 7.08 N
        :return:
        """
        contact_force = self.right_contact_force
        contact_force_np = numpy.array((contact_force.x, contact_force.y, contact_force.z))
        force_magnitude = numpy.linalg.norm(contact_force_np)

        return force_magnitude

    def get_joint_states(self):
        return self.joints_state

    def odom_callback(self,msg):
        self.base_position = msg.pose.pose.position

    def imu_callback(self,msg):
        self.base_orientation = msg.orientation
        self.base_linear_acceleration = msg.linear_acceleration

    def left_contact_callback(self,msg):
        """
        /lowerleg_contactsensor_state/states[0]/contact_positions ==> PointContact in World
        /lowerleg_contactsensor_state/states[0]/contact_normals ==> NormalContact in World

        ==> One is an array of all the forces, the other total,
         and are relative to the contact link referred to in the sensor.
        /lowerleg_contactsensor_state/states[0]/wrenches[]
        /lowerleg_contactsensor_state/states[0]/total_wrench
        :param msg:
        :return:
        """
        for state in msg.states:
            self.left_contact_force = state.total_wrench.force


    def right_contact_callback(self,msg):
        """
        /lowerleg_contactsensor_state/states[0]/contact_positions ==> PointContact in World
        /lowerleg_contactsensor_state/states[0]/contact_normals ==> NormalContact in World

        ==> One is an array of all the forces, the other total,
         and are relative to the contact link referred to in the sensor.
        /lowerleg_contactsensor_state/states[0]/wrenches[]
        /lowerleg_contactsensor_state/states[0]/total_wrench
        :param msg:
        :return:
        """
        for state in msg.states:
            self.right_contact_force = state.total_wrench.force


    

    def joints_state_callback(self,msg):
        self.joints_state = msg

    def catbot_height_ok(self):

        height_ok = self._min_height <= self.get_base_height() < self._max_height
        # print(self.get_base_height())
        return height_ok

    def catbot_orientation_ok(self):

        orientation_rpy = self.get_base_rpy()
        roll_ok = self._abs_max_roll > abs(orientation_rpy.x)
        pitch_ok = self._abs_max_pitch > abs(orientation_rpy.y)
        orientation_ok = roll_ok and pitch_ok
        return orientation_ok



#######################################################################################################
#######################################################################################################
#######################################################################################################
################################ REWARD CODE ##########################################################
#######################################################################################################
#######################################################################################################
#######################################################################################################





    def calculate_reward_joint_position(self, weight=1.0):
        """
        We calculate reward base on the joints configuration. The more near 0 the better.
        :return:
        """
        acumulated_joint_pos = 0.0
        for joint_pos in self.joints_state.position:
            # Abs to remove sign influence, it doesnt matter the direction of turn.
            acumulated_joint_pos += abs(joint_pos)
            rospy.logdebug("calculate_reward_joint_position>>acumulated_joint_pos=" + str(acumulated_joint_pos))
        reward = weight * acumulated_joint_pos
        rospy.logdebug("calculate_reward_joint_position>>reward=" + str(reward))
        return reward

    def calculate_reward_joint_effort(self, weight=1.0):
        """
        We calculate reward base on the joints effort readings. The more near 0 the better.
        :return:
        """
        acumulated_joint_effort = 0.0
        for joint_effort in self.joints_state.effort:
            # Abs to remove sign influence, it doesnt matter the direction of the effort.
            acumulated_joint_effort += abs(joint_effort)
            rospy.logdebug("calculate_reward_joint_effort>>joint_effort=" + str(joint_effort))
            rospy.logdebug("calculate_reward_joint_effort>>acumulated_joint_effort=" + str(acumulated_joint_effort))
        reward = weight * acumulated_joint_effort
        rospy.logdebug("calculate_reward_joint_effort>>reward=" + str(reward))
        return reward

    def calculate_left_reward_contact_force(self, weight=1.0):
        """
        We calculate reward base on the contact force.
        The nearest to the desired contact force the better.
        We use exponential to magnify big departures from the desired force.
        Default ( 7.08 N ) desired force was taken from reading of the robot touching
        the ground from a negligible height of 5cm.
        :return:
        """
        force_magnitude = self.get_left_contact_force_magnitude()
        force_displacement = force_magnitude - self._desired_force

        rospy.logdebug("calculate_left_reward_contact_force>>force_magnitude=" + str(force_magnitude))
        rospy.logdebug("calculate_left_reward_contact_force>>force_displacement=" + str(force_displacement))
        # Abs to remove sign
        reward = weight * abs(force_displacement)
        rospy.logdebug("calculate_left_reward_contact_force>>reward=" + str(reward))
        return reward

    def calculate_right_reward_contact_force(self, weight=1.0):
        """
        We calculate reward base on the contact force.
        The nearest to the desired contact force the better.
        We use exponential to magnify big departures from the desired force.
        Default ( 7.08 N ) desired force was taken from reading of the robot touching
        the ground from a negligible height of 5cm.
        :return:
        """
        force_magnitude = self.get_right_contact_force_magnitude()
        force_displacement = force_magnitude - self._desired_force

        rospy.logdebug("calculate_right_reward_contact_force>>force_magnitude=" + str(force_magnitude))
        rospy.logdebug("calculate_right_reward_contact_force>>force_displacement=" + str(force_displacement))
        # Abs to remove sign
        reward = weight * abs(force_displacement)
        rospy.logdebug("calculate_right_reward_contact_force>>reward=" + str(reward))
        return reward


    def calculate_reward_orientation(self, weight=1.0):
        """
        We calculate the reward based on the orientation.
        The more its closser to 0 the better because it means its upright
        desired_yaw is the yaw that we want it to be.
        to praise it to have a certain orientation, here is where to set it.
        :return:
        """
        curren_orientation = self.get_base_rpy()
        yaw_displacement = curren_orientation.z - self._desired_yaw
        rospy.logdebug("calculate_reward_orientation>>[R,P,Y]=" + str(curren_orientation))
        acumulated_orientation_displacement = abs(curren_orientation.x) + abs(curren_orientation.y) + abs(yaw_displacement)
        reward = weight * acumulated_orientation_displacement
        rospy.logdebug("calculate_reward_orientation>>reward=" + str(reward))
        return reward

    def calculate_reward_distance_from_des_point(self, weight=1.0):
        """
        We calculate the distance from the desired point.
        The closser the better
        :param weight:
        :return:reward
        """
        distance = self.get_distance_from_point(self.desired_world_point)
        reward = weight * distance
        rospy.logdebug("calculate_reward_orientation>>reward=" + str(reward))
        return reward

    def calculate_total_reward(self):
        """
        We consider VERY BAD REWARD -7 or less
        Perfect reward is 0.0, and total reward 1.0.
        The defaults values are chosen so that when the robot has fallen or very extreme joint config:
        r1 = -8.04
        r2 = -8.84
        r3 = -7.08
        r4 = -10.0 ==> We give priority to this, giving it higher value.
        :return:
        """

        r1 = self.calculate_reward_joint_position(self._weight_r1)
        r2 = self.calculate_reward_joint_effort(self._weight_r2)
        # Desired Force in Newtons, taken form idle contact with 9.81 gravity.
        r3_a = self.calculate_left_reward_contact_force(self._weight_r3)
        r3_b = self.calculate_right_reward_contact_force(self._weight_r3)
        r4 = self.calculate_reward_orientation(self._weight_r4)
        r5 = self.calculate_reward_distance_from_des_point(self._weight_r5)

        # The sign depend on its function.
        total_reward = self._alive_reward - r1 - r2 - r3_a - r3_b- r4 - r5

        rospy.logdebug("###############")
        rospy.logdebug("alive_bonus=" + str(self._alive_reward))
        rospy.logdebug("r1 joint_position=" + str(r1))
        rospy.logdebug("r2 joint_effort=" + str(r2))
        rospy.logdebug("r3a&b contact_force=" + str(r3_a) + " and " + str(r3_b))
        rospy.logdebug("r4 orientation=" + str(r4))
        rospy.logdebug("r5 distance=" + str(r5))
        rospy.logdebug("total_reward=" + str(total_reward))
        rospy.logdebug("###############")

        return total_reward

#######################################################################################################
#######################################################################################################






#######################################################################################################
#######################################################################################################
#######################################################################################################
########################################## Obsservation code ##########################################
#######################################################################################################
#######################################################################################################



    def get_observations(self):
        """
        Returns the state of the robot needed for OpenAI QLearn Algorithm
        The state will be defined by an array of the:
        1) distance from desired point in meters
        2) The pitch orientation in radians
        3) the Roll orientation in radians
        4) the Yaw orientation in radians
        5) Force in contact sensor in Newtons
        6-7-8) State of the 3 joints in radians

        observation = [distance_from_desired_point,
                 base_roll,
                 base_pitch,
                 base_yaw,
                 contact_force,
                 joint_states_haa,
                 joint_states_hfe,
                 joint_states_kfe]

        :return: observation
        """

        distance_from_desired_point = self.get_distance_from_point(self.desired_world_point)

        base_orientation = self.get_base_rpy()
        base_roll = base_orientation.x
        base_pitch = base_orientation.y
        base_yaw = base_orientation.z

        left_contact_force = self.get_left_contact_force_magnitude()
        right_contact_force = self.get_right_contact_force_magnitude()

        joint_states = self.get_joint_states()
        # joint_states_haa = joint_states.position[0]
        # joint_states_hfe = joint_states.position[1]
        # joint_states_kfe = joint_states.position[2]

        joint_states_bum_zlj = joint_states.position[0] 
        joint_states_bum_xlj = joint_states.position[1]
        joint_states_bum_ylj = joint_states.position[2]
        joint_states_knee_left = joint_states.position[3]
        joint_states_ankle_lj = joint_states.position[4]
        joint_states_foot_lj = joint_states.position[5]
        joint_states_bum_zrj = joint_states.position[6]
        joint_states_bum_xrj = joint_states.position[7]
        joint_states_bum_yrj = joint_states.position[8]
        joint_states_knee_right = joint_states.position[9]
        joint_states_ankle_rj = joint_states.position[10]
        joint_states_foot_rj = joint_states.position[11]
        joint_states_shoulder_zlj = joint_states.position[12]
        joint_states_shoulder_xlj = joint_states.position[13]
        joint_states_shoulder_ylj = joint_states.position[14]
        joint_states_forearm_ylj = joint_states.position[15]
        joint_states_shoulder_zrj = joint_states.position[16]
        joint_states_shoulder_xrj = joint_states.position[17]
        joint_states_shoulder_yrj = joint_states.position[18]
        joint_states_forearm_yrj = joint_states.position[19]

        observation = []
        for obs_name in self._list_of_observations:
            if obs_name == "distance_from_desired_point":
                observation.append(distance_from_desired_point)
            elif obs_name == "base_roll":
                observation.append(base_roll)
            elif obs_name == "base_pitch":
                observation.append(base_pitch)
            elif obs_name == "base_yaw":
                observation.append(base_yaw)
            
            elif obs_name == "contact_force_left_leg":
                observation.append(left_contact_force)

            elif obs_name == "contact_force_right_leg":
                observation.append(right_contact_force)
            
            elif obs_name == "joint_states_bum_zlj":
                observation.append(joint_states_bum_zlj)

            elif obs_name == "joint_states_bum_xlj":
                observation.append(joint_states_bum_xlj)
            
            elif obs_name == "joint_states_bum_ylj":
                observation.append(joint_states_bum_ylj)
            
            elif obs_name == "joint_states_knee_left":
                observation.append(joint_states_knee_left)

            elif obs_name == "joint_states_ankle_lj":
                observation.append(joint_states_ankle_lj)
            
            elif obs_name == "joint_states_foot_lj":
                observation.append(joint_states_foot_lj)
            
            elif obs_name == "joint_states_bum_zrj":
                observation.append(joint_states_bum_zrj)
            
            elif obs_name == "joint_states_bum_xrj":
                observation.append(joint_states_bum_xrj)
            
            elif obs_name == "joint_states_bum_yrj":
                observation.append(joint_states_bum_yrj)
            
            elif obs_name == "joint_states_knee_right":
                observation.append(joint_states_knee_right)
            
            elif obs_name == "joint_states_ankle_rj":
                observation.append(joint_states_ankle_rj)
            
            elif obs_name == "joint_states_foot_rj":
                observation.append(joint_states_foot_rj)
            
            elif obs_name == "joint_states_shoulder_zlj":
                observation.append(joint_states_shoulder_zlj)
            
            elif obs_name == "joint_states_shoulder_xlj":
                observation.append(joint_states_shoulder_xlj)
            
            elif obs_name == "joint_states_shoulder_ylj":
                observation.append(joint_states_shoulder_ylj)
            
            elif obs_name == "joint_states_forearm_ylj":
                observation.append(joint_states_forearm_ylj)
            
            elif obs_name == "joint_states_shoulder_zrj":
                observation.append(joint_states_shoulder_zrj)
            
            elif obs_name == "joint_states_shoulder_xrj":
                observation.append(joint_states_shoulder_xrj)
            
            elif obs_name == "joint_states_shoulder_yrj":
                observation.append(joint_states_shoulder_yrj)
            
            elif obs_name == "joint_states_forearm_yrj":
                observation.append(joint_states_forearm_yrj)

            else:
                raise NameError('Observation Asked does not exist=='+str(obs_name))

        return observation

    def get_state_as_string(self, observation):
        """
        This function will do two things:
        1) It will make discrete the observations
        2) Will convert the discrete observations in to state tags strings
        :param observation:
        :return: state
        """
        # print(obs)
        observations_discrete = self.assign_bins(observation)
        # print(observations_discrete)
        string_state = ''.join(map(str, observations_discrete))
        return string_state

    def assign_bins(self, observation):
        """
        Will make observations discrete by placing each value into its corresponding bin
        :param observation:
        :return:
        """
        state_discrete = numpy.zeros(len(self._list_of_observations))
        for i in range(len(self._list_of_observations)):
            state_discrete[i] = numpy.digitize(observation[i], self._bins[i])
        return state_discrete

    def init_bins(self):
        """
        We initalise all related to the bins
        :return:
        """
        self.fill_observations_ranges()
        self.create_bins()

    def fill_observations_ranges(self):
        """
        We create the dictionary for the ranges of the data related to each observation
        :return:
        """
        self._obs_range_dict = {}
        for obs_name in self._list_of_observations:

            if obs_name == "distance_from_desired_point":
                # We consider the range as based on the range of distance allowed in height
                delta = self._max_height - self._min_height
                max_value = delta
                min_value = -delta
            elif obs_name == "base_roll":
                max_value = self._abs_max_roll
                min_value = -self._abs_max_roll
            elif obs_name == "base_pitch":
                max_value = self._abs_max_pitch
                min_value = -self._abs_max_pitch
            elif obs_name == "base_yaw":
                # We consider that 360 degrees is max range
                max_value = 2*math.pi
                min_value = -2*math.pi
            # elif obs_name == "contact_force":
            #     # We consider that no force is the minimum, and the maximum is 2 times the desired
            #     # We dont want to make a very big range because we might loose the desired force
            #     # in the middle.
            #     max_value = 2*self._desired_force
            #     min_value = 0.0
            # elif obs_name == "joint_states_haa":
            #     # We consider the URDF maximum values
            #     max_value = 1.6
            #     min_value = -1.6
            # elif obs_name == "joint_states_hfe":
            #     max_value = 1.6
            #     min_value = -1.6
            # elif obs_name == "joint_states_kfe":
            #     max_value = 0.0
            #     min_value = -1.
            
            elif obs_name == "contact_force_left_leg":
                max_value = 2*self._desired_force
                min_value = 0.0

            elif obs_name == "contact_force_right_leg":
                max_value = 2*self._desired_force
                min_value = 0
            
            elif obs_name == "joint_states_bum_zlj":
                max_value = 0.354
                min_value = -0.354
            
            elif obs_name == "joint_states_bum_xlj":
                max_value = 1
                min_value = -0.345
            
            elif obs_name == "joint_states_bum_ylj":
                max_value = 1
                min_value = 0
                
            elif obs_name == "joint_states_knee_left":
                max_value = 0
                min_value = -1.3

            elif obs_name == "joint_states_ankle_lj":
                max_value = 0.3
                min_value = -1.3

            elif obs_name == "joint_states_foot_lj":
                max_value = 0.7
                min_value = -0.4
                
            elif obs_name == "joint_states_bum_zrj":
                max_value = 0.345
                min_value = -0.345

            elif obs_name == "joint_states_bum_xrj":
                max_value = 0.345
                min_value = -1

            elif obs_name == "joint_states_bum_yrj":
                max_value = 1
                min_value = 0

            elif obs_name == "joint_states_knee_right":
                max_value = 0
                min_value = -1.3

            elif obs_name == "joint_states_ankle_rj":
                max_value = 0.3
                min_value = -1.3

            elif obs_name == "joint_states_foot_rj":
                max_value = 0.7
                min_value = -0.4

            elif obs_name == "joint_states_shoulder_zlj":
                max_value = 0.1
                min_value = -1.65

            elif obs_name == "joint_states_shoulder_xlj":
                max_value = 1.6
                min_value = -0.1

            elif obs_name == "joint_states_shoulder_ylj":
                max_value = 0
                min_value = -3

            elif obs_name == "joint_states_forearm_ylj":
                max_value = 0
                min_value = -1.6
            

            elif obs_name == "joint_states_shoulder_zrj":
                max_value = 1.65
                min_value = -0.345

            elif obs_name == "joint_states_shoulder_xrj":
                max_value = 1.6
                min_value = -0.1

            elif obs_name == "joint_states_shoulder_yrj":
                max_value = 3
                min_value = 0

            elif obs_name == "joint_states_forearm_yrj":
                max_value = 0
                min_value = -1.6



            else:
                raise NameError('Observation Asked does not exist=='+str(obs_name))

            self._obs_range_dict[obs_name] = [min_value,max_value]

    def create_bins(self):
        """
        We create the Bins for the discretization of the observations
        self.desired_world_point = Vector3(0.0, 0.0, 0.0)
        self._min_height = min_height
        self._max_height = max_height
        self._abs_max_roll = abs_max_roll
        self._abs_max_pitch = abs_max_pitch
        self._joint_increment_value = joint_increment_value
        self._done_reward = done_reward
        self._alive_reward = alive_reward
        self._desired_force = desired_force
        self._desired_yaw = desired_yaw


        :return:bins
        """

        number_of_observations = len(self._list_of_observations)
        parts_we_disrcetize = self._discrete_division

        self._bins = numpy.zeros((number_of_observations, parts_we_disrcetize))
        for counter in range(number_of_observations):
            obs_name = self._list_of_observations[counter]
            min_value = self._obs_range_dict[obs_name][0]
            max_value = self._obs_range_dict[obs_name][1]
            self._bins[counter] = numpy.linspace(min_value, max_value, parts_we_disrcetize)


    def get_action_to_position(self, action):
        """
        Here we have the ACtions number to real joint movement correspondance.

        ################ REF MSG ###########################
        header: 
            seq: 19580
            stamp: 
                secs: 392
                nsecs: 602000000
        frame_id: ''
            name: 
            - ankle_lj
            - ankle_rj
            - bum_xlj
            - bum_xrj
            - bum_ylj
            - bum_yrj
            - bum_zlj
            - bum_zrj
            - foot_lj
            - foot_rj
            - forearm_ylj
            - forearm_yrj
            - knee_left
            - knee_right
            - shoulder_xlj
            - shoulder_xrj
            - shoulder_ylj
            - shoulder_yrj
            - shoulder_zlj
            - shoulder_zrj
            position: [-0.007284824276652557, -0.1500517780905657, -0.006958334788058629, 0.31161108333870313, 0.276632334511679, 0.10492614623858199, 0.27132706416670516, 0.2548615815704949, 0.27072180306669846, 0.11826704981980196, -0.23063292099829535, -1.1061912337240187e-06, -0.01670606919495743, -0.22528336368172397, 0.28563506406679373, 0.4942558180087344, -0.05062763347783239, -3.7051835102275277e-06, -0.11785893685638715, -0.34500026517548577]
            velocity: [0.0025289011119841547, -0.0021810351891762424, -0.00010961639879162189, -0.0013619365578214895, -0.00027297120066996177, -8.411690510157633e-05, -0.001099457721045053, -0.001115011216570017, 0.0006381177785299951, -0.00022994601552048976, -3.533738127605698e-05, -0.00036774276653233674, -0.0018609820242098721, 0.00172351229750848, 0.0002994666139951035, -0.0010172334458865948, -4.33444175358728e-05, 0.0009331598359361699, -0.0011948459902201163, 0.00012791353300390372]
            effort: [-1.2933892070254327, 0.3738143845665398, 0.16413215986016638, -3.027609172504677, -1.334652722652958, 0.43120933139476847, -2.789905121502221, -2.620176480961014, -1.1457683463440649, 0.26553733306816873, 7.707942018875258e-05, -2.2978158343655597, -1.1129495242152387, 0.7988351320911757, -0.4725217874037124, -2.7215938325488853, -8.731347488577512e-05, 0.4919735114407153, 1.0982153357375068, 3.461426101763916]



        ####################################################

        :param action: Integer that goes from 0 to 5, because we have 6 actions.
        :return:
        """
        # We get current Joints values
        joint_states = self.get_joint_states()
        joint_states_position = joint_states.position

        action_position = [0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,]

        rospy.logdebug("get_action_to_position>>>"+str(joint_states_position))
        if action == 0: #Increment ankle_lj
            action_position[0] = joint_states_position[0] + self._joint_increment_value
            action_position[1] = joint_states_position[1]
            action_position[2] = joint_states_position[2]
            action_position[3] = joint_states_position[3]
            action_position[4] = joint_states_position[4]
            action_position[5] = joint_states_position[5]
            action_position[6] = joint_states_position[6]
            action_position[7] = joint_states_position[7]
            action_position[8] = joint_states_position[8]
            action_position[9] = joint_states_position[9]
            action_position[10] = joint_states_position[10]
            action_position[11] = joint_states_position[11]
            action_position[12] = joint_states_position[12]
            action_position[13] = joint_states_position[13]
            action_position[14] = joint_states_position[14]
            action_position[15] = joint_states_position[15]
            action_position[16] = joint_states_position[16]
            action_position[17] = joint_states_position[17]
            action_position[18] = joint_states_position[18]
            action_position[19] = joint_states_position[19]
        elif action == 1: #Decrement ankle_rj
            action_position[0] = joint_states_position[0] - self._joint_increment_value
            action_position[1] = joint_states_position[1] 
            action_position[2] = joint_states_position[2]
            action_position[3] = joint_states_position[3]
            action_position[4] = joint_states_position[4]
            action_position[5] = joint_states_position[5]
            action_position[6] = joint_states_position[6]
            action_position[7] = joint_states_position[7]
            action_position[8] = joint_states_position[8]
            action_position[9] = joint_states_position[9]
            action_position[10] = joint_states_position[10]
            action_position[11] = joint_states_position[11]
            action_position[12] = joint_states_position[12]
            action_position[13] = joint_states_position[13]
            action_position[14] = joint_states_position[14]
            action_position[15] = joint_states_position[15]
            action_position[16] = joint_states_position[16]
            action_position[17] = joint_states_position[17]
            action_position[18] = joint_states_position[18]
            action_position[19] = joint_states_position[19]
        elif action == 2: #Increment bum_xlj
            action_position[0] = joint_states_position[0] 
            action_position[1] = joint_states_position[1] + self._joint_increment_value
            action_position[2] = joint_states_position[2] 
            action_position[3] = joint_states_position[3]
            action_position[4] = joint_states_position[4]
            action_position[5] = joint_states_position[5]
            action_position[6] = joint_states_position[6]
            action_position[7] = joint_states_position[7]
            action_position[8] = joint_states_position[8]
            action_position[9] = joint_states_position[9]
            action_position[10] = joint_states_position[10]
            action_position[11] = joint_states_position[11]
            action_position[12] = joint_states_position[12]
            action_position[13] = joint_states_position[13]
            action_position[14] = joint_states_position[14]
            action_position[15] = joint_states_position[15]
            action_position[16] = joint_states_position[16]
            action_position[17] = joint_states_position[17]
            action_position[18] = joint_states_position[18]
            action_position[19] = joint_states_position[19]
        
        elif action == 3: #Decrement bum_xlj
            action_position[0] = joint_states_position[0] 
            action_position[1] = joint_states_position[1] - self._joint_increment_value
            action_position[2] = joint_states_position[2]
            action_position[3] = joint_states_position[3] 
            action_position[4] = joint_states_position[4]
            action_position[5] = joint_states_position[5]
            action_position[6] = joint_states_position[6]
            action_position[7] = joint_states_position[7]
            action_position[8] = joint_states_position[8]
            action_position[9] = joint_states_position[9]
            action_position[10] = joint_states_position[10]
            action_position[11] = joint_states_position[11]
            action_position[12] = joint_states_position[12]
            action_position[13] = joint_states_position[13]
            action_position[14] = joint_states_position[14]
            action_position[15] = joint_states_position[15]
            action_position[16] = joint_states_position[16]
            action_position[17] = joint_states_position[17]
            action_position[18] = joint_states_position[18]
            action_position[19] = joint_states_position[19]
        
        elif action == 4: #Increment bum_xrj
            action_position[0] = joint_states_position[0] 
            action_position[1] = joint_states_position[1]
            action_position[2] = joint_states_position[2] + self._joint_increment_value
            action_position[3] = joint_states_position[3]
            action_position[4] = joint_states_position[4]
            action_position[5] = joint_states_position[5]
            action_position[6] = joint_states_position[6]
            action_position[7] = joint_states_position[7]
            action_position[8] = joint_states_position[8]
            action_position[9] = joint_states_position[9]
            action_position[10] = joint_states_position[10]
            action_position[11] = joint_states_position[11]
            action_position[12] = joint_states_position[12]
            action_position[13] = joint_states_position[13]
            action_position[14] = joint_states_position[14]
            action_position[15] = joint_states_position[15]
            action_position[16] = joint_states_position[16]
            action_position[17] = joint_states_position[17]
            action_position[18] = joint_states_position[18]
            action_position[19] = joint_states_position[19]
        
        elif action == 5: #Decrement haa_joint
            action_position[0] = joint_states_position[0] 
            action_position[1] = joint_states_position[1]
            action_position[2] = joint_states_position[2] - self._joint_increment_value
            action_position[3] = joint_states_position[3]
            action_position[4] = joint_states_position[4]
            action_position[5] = joint_states_position[5]
            action_position[6] = joint_states_position[6]
            action_position[7] = joint_states_position[7]
            action_position[8] = joint_states_position[8]
            action_position[9] = joint_states_position[9]
            action_position[10] = joint_states_position[10]
            action_position[11] = joint_states_position[11]
            action_position[12] = joint_states_position[12]
            action_position[13] = joint_states_position[13]
            action_position[14] = joint_states_position[14]
            action_position[15] = joint_states_position[15]
            action_position[16] = joint_states_position[16]
            action_position[17] = joint_states_position[17]
            action_position[18] = joint_states_position[18]
            action_position[19] = joint_states_position[19]
        
        elif action == 6: #Decrement haa_joint
            action_position[0] = joint_states_position[0] 
            action_position[1] = joint_states_position[1]
            action_position[2] = joint_states_position[2]
            action_position[3] = joint_states_position[3] + self._joint_increment_value
            action_position[4] = joint_states_position[4]
            action_position[5] = joint_states_position[5]
            action_position[6] = joint_states_position[6]
            action_position[7] = joint_states_position[7]
            action_position[8] = joint_states_position[8]
            action_position[9] = joint_states_position[9]
            action_position[10] = joint_states_position[10]
            action_position[11] = joint_states_position[11]
            action_position[12] = joint_states_position[12]
            action_position[13] = joint_states_position[13]
            action_position[14] = joint_states_position[14]
            action_position[15] = joint_states_position[15]
            action_position[16] = joint_states_position[16]
            action_position[17] = joint_states_position[17]
            action_position[18] = joint_states_position[18]
            action_position[19] = joint_states_position[19]
        
        elif action == 7: #Decrement haa_joint
            action_position[0] = joint_states_position[0] 
            action_position[1] = joint_states_position[1]
            action_position[2] = joint_states_position[2]
            action_position[3] = joint_states_position[3] - self._joint_increment_value
            action_position[4] = joint_states_position[4]
            action_position[5] = joint_states_position[5]
            action_position[6] = joint_states_position[6]
            action_position[7] = joint_states_position[7]
            action_position[8] = joint_states_position[8]
            action_position[9] = joint_states_position[9]
            action_position[10] = joint_states_position[10]
            action_position[11] = joint_states_position[11]
            action_position[12] = joint_states_position[12]
            action_position[13] = joint_states_position[13]
            action_position[14] = joint_states_position[14]
            action_position[15] = joint_states_position[15]
            action_position[16] = joint_states_position[16]
            action_position[17] = joint_states_position[17]
            action_position[18] = joint_states_position[18]
            action_position[19] = joint_states_position[19]
        
        elif action == 8: #Decrement haa_joint
            action_position[0] = joint_states_position[0] 
            action_position[1] = joint_states_position[1]
            action_position[2] = joint_states_position[2]
            action_position[3] = joint_states_position[3]
            action_position[4] = joint_states_position[4] + self._joint_increment_value
            action_position[5] = joint_states_position[5]
            action_position[6] = joint_states_position[6]
            action_position[7] = joint_states_position[7]
            action_position[8] = joint_states_position[8]
            action_position[9] = joint_states_position[9]
            action_position[10] = joint_states_position[10]
            action_position[11] = joint_states_position[11]
            action_position[12] = joint_states_position[12]
            action_position[13] = joint_states_position[13]
            action_position[14] = joint_states_position[14]
            action_position[15] = joint_states_position[15]
            action_position[16] = joint_states_position[16]
            action_position[17] = joint_states_position[17]
            action_position[18] = joint_states_position[18]
            action_position[19] = joint_states_position[19]
        
        elif action == 9: #Decrement haa_joint
            action_position[0] = joint_states_position[0] 
            action_position[1] = joint_states_position[1]
            action_position[2] = joint_states_position[2]
            action_position[3] = joint_states_position[3]
            action_position[4] = joint_states_position[4] - self._joint_increment_value
            action_position[5] = joint_states_position[5]
            action_position[6] = joint_states_position[6]
            action_position[7] = joint_states_position[7]
            action_position[8] = joint_states_position[8]
            action_position[9] = joint_states_position[9]
            action_position[10] = joint_states_position[10]
            action_position[11] = joint_states_position[11]
            action_position[12] = joint_states_position[12]
            action_position[13] = joint_states_position[13]
            action_position[14] = joint_states_position[14]
            action_position[15] = joint_states_position[15]
            action_position[16] = joint_states_position[16]
            action_position[17] = joint_states_position[17]
            action_position[18] = joint_states_position[18]
            action_position[19] = joint_states_position[19]
        
        elif action == 10: #Decrement haa_joint
            action_position[0] = joint_states_position[0] 
            action_position[1] = joint_states_position[1]
            action_position[2] = joint_states_position[2]
            action_position[3] = joint_states_position[3]
            action_position[4] = joint_states_position[4]
            action_position[5] = joint_states_position[5] + self._joint_increment_value
            action_position[6] = joint_states_position[6]
            action_position[7] = joint_states_position[7]
            action_position[8] = joint_states_position[8]
            action_position[9] = joint_states_position[9]
            action_position[10] = joint_states_position[10]
            action_position[11] = joint_states_position[11]
            action_position[12] = joint_states_position[12]
            action_position[13] = joint_states_position[13]
            action_position[14] = joint_states_position[14]
            action_position[15] = joint_states_position[15]
            action_position[16] = joint_states_position[16]
            action_position[17] = joint_states_position[17]
            action_position[18] = joint_states_position[18]
            action_position[19] = joint_states_position[19]
        
        elif action == 11: #Decrement haa_joint
            action_position[0] = joint_states_position[0] 
            action_position[1] = joint_states_position[1]
            action_position[2] = joint_states_position[2]
            action_position[3] = joint_states_position[3]
            action_position[4] = joint_states_position[4]
            action_position[5] = joint_states_position[5] - self._joint_increment_value
            action_position[6] = joint_states_position[6] 
            action_position[7] = joint_states_position[7]
            action_position[8] = joint_states_position[8]
            action_position[9] = joint_states_position[9]
            action_position[10] = joint_states_position[10]
            action_position[11] = joint_states_position[11]
            action_position[12] = joint_states_position[12]
            action_position[13] = joint_states_position[13]
            action_position[14] = joint_states_position[14]
            action_position[15] = joint_states_position[15]
            action_position[16] = joint_states_position[16]
            action_position[17] = joint_states_position[17]
            action_position[18] = joint_states_position[18]
            action_position[19] = joint_states_position[19]
        
        elif action == 12: #Decrement haa_joint
            action_position[0] = joint_states_position[0] 
            action_position[1] = joint_states_position[1]
            action_position[2] = joint_states_position[2]
            action_position[3] = joint_states_position[3]
            action_position[4] = joint_states_position[4]
            action_position[5] = joint_states_position[5]
            action_position[6] = joint_states_position[6] + self._joint_increment_value
            action_position[7] = joint_states_position[7]
            action_position[8] = joint_states_position[8]
            action_position[9] = joint_states_position[9]
            action_position[10] = joint_states_position[10]
            action_position[11] = joint_states_position[11]
            action_position[12] = joint_states_position[12]
            action_position[13] = joint_states_position[13]
            action_position[14] = joint_states_position[14]
            action_position[15] = joint_states_position[15]
            action_position[16] = joint_states_position[16]
            action_position[17] = joint_states_position[17]
            action_position[18] = joint_states_position[18]
            action_position[19] = joint_states_position[19]
        
        elif action == 13: #Decrement haa_joint
            action_position[0] = joint_states_position[0] 
            action_position[1] = joint_states_position[1]
            action_position[2] = joint_states_position[2]
            action_position[3] = joint_states_position[3]
            action_position[4] = joint_states_position[4]
            action_position[5] = joint_states_position[5]
            action_position[6] = joint_states_position[6] - self._joint_increment_value
            action_position[7] = joint_states_position[7]
            action_position[8] = joint_states_position[8]
            action_position[9] = joint_states_position[9]
            action_position[10] = joint_states_position[10]
            action_position[11] = joint_states_position[11]
            action_position[12] = joint_states_position[12]
            action_position[13] = joint_states_position[13]
            action_position[14] = joint_states_position[14]
            action_position[15] = joint_states_position[15]
            action_position[16] = joint_states_position[16]
            action_position[17] = joint_states_position[17]
            action_position[18] = joint_states_position[18]
            action_position[19] = joint_states_position[19]
        
        elif action == 14: #Decrement haa_joint
            action_position[0] = joint_states_position[0] 
            action_position[1] = joint_states_position[1]
            action_position[2] = joint_states_position[2]
            action_position[3] = joint_states_position[3]
            action_position[4] = joint_states_position[4]
            action_position[5] = joint_states_position[5]
            action_position[6] = joint_states_position[6]
            action_position[7] = joint_states_position[7] + self._joint_increment_value
            action_position[8] = joint_states_position[8]
            action_position[9] = joint_states_position[9]
            action_position[10] = joint_states_position[10]
            action_position[11] = joint_states_position[11]
            action_position[12] = joint_states_position[12]
            action_position[13] = joint_states_position[13]
            action_position[14] = joint_states_position[14]
            action_position[15] = joint_states_position[15]
            action_position[16] = joint_states_position[16]
            action_position[17] = joint_states_position[17]
            action_position[18] = joint_states_position[18]
            action_position[19] = joint_states_position[19]
        
        elif action == 15: #Decrement haa_joint
            action_position[0] = joint_states_position[0] 
            action_position[1] = joint_states_position[1]
            action_position[2] = joint_states_position[2]
            action_position[3] = joint_states_position[3]
            action_position[4] = joint_states_position[4]
            action_position[5] = joint_states_position[5]
            action_position[6] = joint_states_position[6]
            action_position[7] = joint_states_position[7] - self._joint_increment_value
            action_position[8] = joint_states_position[8]
            action_position[9] = joint_states_position[9]
            action_position[10] = joint_states_position[10]
            action_position[11] = joint_states_position[11]
            action_position[12] = joint_states_position[12]
            action_position[13] = joint_states_position[13]
            action_position[14] = joint_states_position[14]
            action_position[15] = joint_states_position[15]
            action_position[16] = joint_states_position[16]
            action_position[17] = joint_states_position[17]
            action_position[18] = joint_states_position[18]
            action_position[19] = joint_states_position[19]
        
        elif action == 16: #Decrement haa_joint
            action_position[0] = joint_states_position[0] 
            action_position[1] = joint_states_position[1]
            action_position[2] = joint_states_position[2]
            action_position[3] = joint_states_position[3]
            action_position[4] = joint_states_position[4]
            action_position[5] = joint_states_position[5]
            action_position[6] = joint_states_position[6]
            action_position[7] = joint_states_position[7]
            action_position[8] = joint_states_position[8] + self._joint_increment_value
            action_position[9] = joint_states_position[9]
            action_position[10] = joint_states_position[10]
            action_position[11] = joint_states_position[11]
            action_position[12] = joint_states_position[12]
            action_position[13] = joint_states_position[13]
            action_position[14] = joint_states_position[14]
            action_position[15] = joint_states_position[15]
            action_position[16] = joint_states_position[16]
            action_position[17] = joint_states_position[17]
            action_position[18] = joint_states_position[18]
            action_position[19] = joint_states_position[19]
        
        elif action == 17: #Decrement haa_joint
            action_position[0] = joint_states_position[0] 
            action_position[1] = joint_states_position[1]
            action_position[2] = joint_states_position[2]
            action_position[3] = joint_states_position[3]
            action_position[4] = joint_states_position[4]
            action_position[5] = joint_states_position[5]
            action_position[6] = joint_states_position[6]
            action_position[7] = joint_states_position[7]
            action_position[8] = joint_states_position[8] - self._joint_increment_value
            action_position[9] = joint_states_position[9]
            action_position[10] = joint_states_position[10]
            action_position[11] = joint_states_position[11]
            action_position[12] = joint_states_position[12]
            action_position[13] = joint_states_position[13]
            action_position[14] = joint_states_position[14]
            action_position[15] = joint_states_position[15]
            action_position[16] = joint_states_position[16]
            action_position[17] = joint_states_position[17]
            action_position[18] = joint_states_position[18]
            action_position[19] = joint_states_position[19]
        
        elif action == 18: #Decrement haa_joint
            action_position[0] = joint_states_position[0] 
            action_position[1] = joint_states_position[1]
            action_position[2] = joint_states_position[2]
            action_position[3] = joint_states_position[3]
            action_position[4] = joint_states_position[4]
            action_position[5] = joint_states_position[5]
            action_position[6] = joint_states_position[6]
            action_position[7] = joint_states_position[7]
            action_position[8] = joint_states_position[8]
            action_position[9] = joint_states_position[9] + self._joint_increment_value
            action_position[10] = joint_states_position[10]
            action_position[11] = joint_states_position[11]
            action_position[12] = joint_states_position[12]
            action_position[13] = joint_states_position[13]
            action_position[14] = joint_states_position[14]
            action_position[15] = joint_states_position[15]
            action_position[16] = joint_states_position[16]
            action_position[17] = joint_states_position[17]
            action_position[18] = joint_states_position[18]
            action_position[19] = joint_states_position[19]
        
        elif action == 19: #Decrement haa_joint
            action_position[0] = joint_states_position[0] 
            action_position[1] = joint_states_position[1]
            action_position[2] = joint_states_position[2]
            action_position[3] = joint_states_position[3]
            action_position[4] = joint_states_position[4]
            action_position[5] = joint_states_position[5]
            action_position[6] = joint_states_position[6]
            action_position[7] = joint_states_position[7]
            action_position[8] = joint_states_position[8]
            action_position[9] = joint_states_position[9] - self._joint_increment_value
            action_position[10] = joint_states_position[10]
            action_position[11] = joint_states_position[11]
            action_position[12] = joint_states_position[12]
            action_position[13] = joint_states_position[13]
            action_position[14] = joint_states_position[14]
            action_position[15] = joint_states_position[15]
            action_position[16] = joint_states_position[16]
            action_position[17] = joint_states_position[17]
            action_position[18] = joint_states_position[18]
            action_position[19] = joint_states_position[19]
        
        elif action == 20: #Decrement haa_joint
            action_position[0] = joint_states_position[0] 
            action_position[1] = joint_states_position[1]
            action_position[2] = joint_states_position[2]
            action_position[3] = joint_states_position[3]
            action_position[4] = joint_states_position[4]
            action_position[5] = joint_states_position[5]
            action_position[6] = joint_states_position[6]
            action_position[7] = joint_states_position[7]
            action_position[8] = joint_states_position[8]
            action_position[9] = joint_states_position[9] 
            action_position[10] = joint_states_position[10] + self._joint_increment_value
            action_position[11] = joint_states_position[11]
            action_position[12] = joint_states_position[12]
            action_position[13] = joint_states_position[13]
            action_position[14] = joint_states_position[14]
            action_position[15] = joint_states_position[15]
            action_position[16] = joint_states_position[16]
            action_position[17] = joint_states_position[17]
            action_position[18] = joint_states_position[18]
            action_position[19] = joint_states_position[19]
        
        elif action == 21: #Decrement haa_joint
            action_position[0] = joint_states_position[0] 
            action_position[1] = joint_states_position[1]
            action_position[2] = joint_states_position[2]
            action_position[3] = joint_states_position[3]
            action_position[4] = joint_states_position[4]
            action_position[5] = joint_states_position[5]
            action_position[6] = joint_states_position[6]
            action_position[7] = joint_states_position[7]
            action_position[8] = joint_states_position[8]
            action_position[9] = joint_states_position[9] 
            action_position[10] = joint_states_position[10] - self._joint_increment_value
            action_position[11] = joint_states_position[11]
            action_position[12] = joint_states_position[12]
            action_position[13] = joint_states_position[13]
            action_position[14] = joint_states_position[14]
            action_position[15] = joint_states_position[15]
            action_position[16] = joint_states_position[16]
            action_position[17] = joint_states_position[17]
            action_position[18] = joint_states_position[18]
            action_position[19] = joint_states_position[19]
        
        elif action == 22: #Decrement haa_joint
            action_position[0] = joint_states_position[0] 
            action_position[1] = joint_states_position[1]
            action_position[2] = joint_states_position[2]
            action_position[3] = joint_states_position[3]
            action_position[4] = joint_states_position[4]
            action_position[5] = joint_states_position[5]
            action_position[6] = joint_states_position[6]
            action_position[7] = joint_states_position[7]
            action_position[8] = joint_states_position[8]
            action_position[9] = joint_states_position[9] 
            action_position[10] = joint_states_position[10]
            action_position[11] = joint_states_position[11] + self._joint_increment_value
            action_position[12] = joint_states_position[12]
            action_position[13] = joint_states_position[13]
            action_position[14] = joint_states_position[14]
            action_position[15] = joint_states_position[15]
            action_position[16] = joint_states_position[16]
            action_position[17] = joint_states_position[17]
            action_position[18] = joint_states_position[18]
            action_position[19] = joint_states_position[19]
        
        elif action == 23: #Decrement haa_joint
            action_position[0] = joint_states_position[0] 
            action_position[1] = joint_states_position[1]
            action_position[2] = joint_states_position[2]
            action_position[3] = joint_states_position[3]
            action_position[4] = joint_states_position[4]
            action_position[5] = joint_states_position[5]
            action_position[6] = joint_states_position[6]
            action_position[7] = joint_states_position[7]
            action_position[8] = joint_states_position[8]
            action_position[9] = joint_states_position[9] 
            action_position[10] = joint_states_position[10]
            action_position[11] = joint_states_position[11] - self._joint_increment_value
            action_position[12] = joint_states_position[12]
            action_position[13] = joint_states_position[13]
            action_position[14] = joint_states_position[14]
            action_position[15] = joint_states_position[15]
            action_position[16] = joint_states_position[16]
            action_position[17] = joint_states_position[17]
            action_position[18] = joint_states_position[18]
            action_position[19] = joint_states_position[19]
        
        elif action == 24: #Decrement haa_joint
            action_position[0] = joint_states_position[0] 
            action_position[1] = joint_states_position[1]
            action_position[2] = joint_states_position[2]
            action_position[3] = joint_states_position[3]
            action_position[4] = joint_states_position[4]
            action_position[5] = joint_states_position[5]
            action_position[6] = joint_states_position[6]
            action_position[7] = joint_states_position[7]
            action_position[8] = joint_states_position[8]
            action_position[9] = joint_states_position[9] 
            action_position[10] = joint_states_position[10]
            action_position[11] = joint_states_position[11]
            action_position[12] = joint_states_position[12] + self._joint_increment_value
            action_position[13] = joint_states_position[13]
            action_position[14] = joint_states_position[14]
            action_position[15] = joint_states_position[15]
            action_position[16] = joint_states_position[16]
            action_position[17] = joint_states_position[17]
            action_position[18] = joint_states_position[18]
            action_position[19] = joint_states_position[19]
        
        elif action == 25: #Decrement haa_joint
            action_position[0] = joint_states_position[0] 
            action_position[1] = joint_states_position[1]
            action_position[2] = joint_states_position[2]
            action_position[3] = joint_states_position[3]
            action_position[4] = joint_states_position[4]
            action_position[5] = joint_states_position[5]
            action_position[6] = joint_states_position[6]
            action_position[7] = joint_states_position[7]
            action_position[8] = joint_states_position[8]
            action_position[9] = joint_states_position[9] 
            action_position[10] = joint_states_position[10]
            action_position[11] = joint_states_position[11]
            action_position[12] = joint_states_position[12] - self._joint_increment_value
            action_position[13] = joint_states_position[13]
            action_position[14] = joint_states_position[14]
            action_position[15] = joint_states_position[15]
            action_position[16] = joint_states_position[16]
            action_position[17] = joint_states_position[17]
            action_position[18] = joint_states_position[18]
            action_position[19] = joint_states_position[19]
        
        elif action == 26: #Decrement haa_joint
            action_position[0] = joint_states_position[0] 
            action_position[1] = joint_states_position[1]
            action_position[2] = joint_states_position[2]
            action_position[3] = joint_states_position[3]
            action_position[4] = joint_states_position[4]
            action_position[5] = joint_states_position[5]
            action_position[6] = joint_states_position[6]
            action_position[7] = joint_states_position[7]
            action_position[8] = joint_states_position[8]
            action_position[9] = joint_states_position[9]
            action_position[10] = joint_states_position[10]
            action_position[11] = joint_states_position[11]
            action_position[12] = joint_states_position[12]
            action_position[13] = joint_states_position[13] + self._joint_increment_value
            action_position[14] = joint_states_position[14]
            action_position[15] = joint_states_position[15]
            action_position[16] = joint_states_position[16]
            action_position[17] = joint_states_position[17]
            action_position[18] = joint_states_position[18]
            action_position[19] = joint_states_position[19]
        
        elif action == 27: #Decrement haa_joint
            action_position[0] = joint_states_position[0] 
            action_position[1] = joint_states_position[1]
            action_position[2] = joint_states_position[2]
            action_position[3] = joint_states_position[3]
            action_position[4] = joint_states_position[4]
            action_position[5] = joint_states_position[5]
            action_position[6] = joint_states_position[6]
            action_position[7] = joint_states_position[7]
            action_position[8] = joint_states_position[8]
            action_position[9] = joint_states_position[9] 
            action_position[10] = joint_states_position[10]
            action_position[11] = joint_states_position[11]
            action_position[12] = joint_states_position[12]
            action_position[13] = joint_states_position[13] - self._joint_increment_value
            action_position[14] = joint_states_position[14]
            action_position[15] = joint_states_position[15]
            action_position[16] = joint_states_position[16]
            action_position[17] = joint_states_position[17]
            action_position[18] = joint_states_position[18]
            action_position[19] = joint_states_position[19]
        
        elif action == 28: #Decrement haa_joint
            action_position[0] = joint_states_position[0] 
            action_position[1] = joint_states_position[1]
            action_position[2] = joint_states_position[2]
            action_position[3] = joint_states_position[3]
            action_position[4] = joint_states_position[4]
            action_position[5] = joint_states_position[5]
            action_position[6] = joint_states_position[6]
            action_position[7] = joint_states_position[7]
            action_position[8] = joint_states_position[8]
            action_position[9] = joint_states_position[9] 
            action_position[10] = joint_states_position[10]
            action_position[11] = joint_states_position[11]
            action_position[12] = joint_states_position[12]
            action_position[13] = joint_states_position[13]
            action_position[14] = joint_states_position[14] + self._joint_increment_value
            action_position[15] = joint_states_position[15]
            action_position[16] = joint_states_position[16]
            action_position[17] = joint_states_position[17]
            action_position[18] = joint_states_position[18]
            action_position[19] = joint_states_position[19]
        
        elif action == 29: #Decrement haa_joint
            action_position[0] = joint_states_position[0] 
            action_position[1] = joint_states_position[1]
            action_position[2] = joint_states_position[2]
            action_position[3] = joint_states_position[3]
            action_position[4] = joint_states_position[4]
            action_position[5] = joint_states_position[5]
            action_position[6] = joint_states_position[6]
            action_position[7] = joint_states_position[7]
            action_position[8] = joint_states_position[8]
            action_position[9] = joint_states_position[9] 
            action_position[10] = joint_states_position[10]
            action_position[11] = joint_states_position[11]
            action_position[12] = joint_states_position[12]
            action_position[13] = joint_states_position[13]
            action_position[14] = joint_states_position[14] - self._joint_increment_value
            action_position[15] = joint_states_position[15]
            action_position[16] = joint_states_position[16]
            action_position[17] = joint_states_position[17]
            action_position[18] = joint_states_position[18]
            action_position[19] = joint_states_position[19]
        
        elif action == 30: #Decrement haa_joint
            action_position[0] = joint_states_position[0] 
            action_position[1] = joint_states_position[1]
            action_position[2] = joint_states_position[2]
            action_position[3] = joint_states_position[3]
            action_position[4] = joint_states_position[4]
            action_position[5] = joint_states_position[5]
            action_position[6] = joint_states_position[6]
            action_position[7] = joint_states_position[7]
            action_position[8] = joint_states_position[8]
            action_position[9] = joint_states_position[9] 
            action_position[10] = joint_states_position[10]
            action_position[11] = joint_states_position[11]
            action_position[12] = joint_states_position[12]
            action_position[13] = joint_states_position[13]
            action_position[14] = joint_states_position[14]
            action_position[15] = joint_states_position[15] + self._joint_increment_value
            action_position[16] = joint_states_position[16]
            action_position[17] = joint_states_position[17]
            action_position[18] = joint_states_position[18]
            action_position[19] = joint_states_position[19]
        
        elif action == 31: #Decrement haa_joint
            action_position[0] = joint_states_position[0] 
            action_position[1] = joint_states_position[1]
            action_position[2] = joint_states_position[2]
            action_position[3] = joint_states_position[3]
            action_position[4] = joint_states_position[4]
            action_position[5] = joint_states_position[5]
            action_position[6] = joint_states_position[6]
            action_position[7] = joint_states_position[7]
            action_position[8] = joint_states_position[8]
            action_position[9] = joint_states_position[9] 
            action_position[10] = joint_states_position[10]
            action_position[11] = joint_states_position[11]
            action_position[12] = joint_states_position[12]
            action_position[13] = joint_states_position[13]
            action_position[14] = joint_states_position[14]
            action_position[15] = joint_states_position[15] - self._joint_increment_value
            action_position[16] = joint_states_position[16]
            action_position[17] = joint_states_position[17]
            action_position[18] = joint_states_position[18]
            action_position[19] = joint_states_position[19]
        
        elif action == 32: #Decrement haa_joint
            action_position[0] = joint_states_position[0] 
            action_position[1] = joint_states_position[1]
            action_position[2] = joint_states_position[2]
            action_position[3] = joint_states_position[3]
            action_position[4] = joint_states_position[4]
            action_position[5] = joint_states_position[5]
            action_position[6] = joint_states_position[6]
            action_position[7] = joint_states_position[7]
            action_position[8] = joint_states_position[8]
            action_position[9] = joint_states_position[9] 
            action_position[10] = joint_states_position[10]
            action_position[11] = joint_states_position[11]
            action_position[12] = joint_states_position[12]
            action_position[13] = joint_states_position[13]
            action_position[14] = joint_states_position[14]
            action_position[15] = joint_states_position[15]
            action_position[16] = joint_states_position[16] + self._joint_increment_value
            action_position[17] = joint_states_position[17]
            action_position[18] = joint_states_position[18]
            action_position[19] = joint_states_position[19]
        
        elif action == 33: #Decrement haa_joint
            action_position[0] = joint_states_position[0] 
            action_position[1] = joint_states_position[1]
            action_position[2] = joint_states_position[2]
            action_position[3] = joint_states_position[3]
            action_position[4] = joint_states_position[4]
            action_position[5] = joint_states_position[5]
            action_position[6] = joint_states_position[6]
            action_position[7] = joint_states_position[7]
            action_position[8] = joint_states_position[8]
            action_position[9] = joint_states_position[9] 
            action_position[10] = joint_states_position[10]
            action_position[11] = joint_states_position[11]
            action_position[12] = joint_states_position[12]
            action_position[13] = joint_states_position[13]
            action_position[14] = joint_states_position[14]
            action_position[15] = joint_states_position[15]
            action_position[16] = joint_states_position[16] - self._joint_increment_value
            action_position[17] = joint_states_position[17]
            action_position[18] = joint_states_position[18]
            action_position[19] = joint_states_position[19]
        
        elif action == 34: #Decrement haa_joint
            action_position[0] = joint_states_position[0] 
            action_position[1] = joint_states_position[1]
            action_position[2] = joint_states_position[2]
            action_position[3] = joint_states_position[3]
            action_position[4] = joint_states_position[4]
            action_position[5] = joint_states_position[5]
            action_position[6] = joint_states_position[6]
            action_position[7] = joint_states_position[7]
            action_position[8] = joint_states_position[8]
            action_position[9] = joint_states_position[9] 
            action_position[10] = joint_states_position[10]
            action_position[11] = joint_states_position[11]
            action_position[12] = joint_states_position[12]
            action_position[13] = joint_states_position[13]
            action_position[14] = joint_states_position[14]
            action_position[15] = joint_states_position[15]
            action_position[16] = joint_states_position[16] 
            action_position[17] = joint_states_position[17] + self._joint_increment_value
            action_position[18] = joint_states_position[18]
            action_position[19] = joint_states_position[19]
        
        elif action == 35: #Decrement haa_joint
            action_position[0] = joint_states_position[0] 
            action_position[1] = joint_states_position[1]
            action_position[2] = joint_states_position[2]
            action_position[3] = joint_states_position[3]
            action_position[4] = joint_states_position[4]
            action_position[5] = joint_states_position[5]
            action_position[6] = joint_states_position[6]
            action_position[7] = joint_states_position[7]
            action_position[8] = joint_states_position[8]
            action_position[9] = joint_states_position[9] 
            action_position[10] = joint_states_position[10]
            action_position[11] = joint_states_position[11]
            action_position[12] = joint_states_position[12]
            action_position[13] = joint_states_position[13]
            action_position[14] = joint_states_position[14]
            action_position[15] = joint_states_position[15]
            action_position[16] = joint_states_position[16] 
            action_position[17] = joint_states_position[17] - self._joint_increment_value
            action_position[18] = joint_states_position[18]
            action_position[19] = joint_states_position[19]
        
        elif action == 36: #Decrement haa_joint
            action_position[0] = joint_states_position[0] 
            action_position[1] = joint_states_position[1]
            action_position[2] = joint_states_position[2]
            action_position[3] = joint_states_position[3]
            action_position[4] = joint_states_position[4]
            action_position[5] = joint_states_position[5]
            action_position[6] = joint_states_position[6]
            action_position[7] = joint_states_position[7]
            action_position[8] = joint_states_position[8]
            action_position[9] = joint_states_position[9] 
            action_position[10] = joint_states_position[10]
            action_position[11] = joint_states_position[11]
            action_position[12] = joint_states_position[12]
            action_position[13] = joint_states_position[13]
            action_position[14] = joint_states_position[14]
            action_position[15] = joint_states_position[15]
            action_position[16] = joint_states_position[16] 
            action_position[17] = joint_states_position[17]
            action_position[18] = joint_states_position[18] + self._joint_increment_value
            action_position[19] = joint_states_position[19]
        
        elif action == 37: #Decrement haa_joint
            action_position[0] = joint_states_position[0] 
            action_position[1] = joint_states_position[1]
            action_position[2] = joint_states_position[2]
            action_position[3] = joint_states_position[3]
            action_position[4] = joint_states_position[4]
            action_position[5] = joint_states_position[5]
            action_position[6] = joint_states_position[6]
            action_position[7] = joint_states_position[7]
            action_position[8] = joint_states_position[8]
            action_position[9] = joint_states_position[9] 
            action_position[10] = joint_states_position[10]
            action_position[11] = joint_states_position[11]
            action_position[12] = joint_states_position[12]
            action_position[13] = joint_states_position[13]
            action_position[14] = joint_states_position[14]
            action_position[15] = joint_states_position[15]
            action_position[16] = joint_states_position[16] 
            action_position[17] = joint_states_position[17]
            action_position[18] = joint_states_position[18] - self._joint_increment_value
            action_position[19] = joint_states_position[19]
        
        elif action == 38: #Decrement haa_joint
            action_position[0] = joint_states_position[0] 
            action_position[1] = joint_states_position[1]
            action_position[2] = joint_states_position[2]
            action_position[3] = joint_states_position[3]
            action_position[4] = joint_states_position[4]
            action_position[5] = joint_states_position[5]
            action_position[6] = joint_states_position[6]
            action_position[7] = joint_states_position[7]
            action_position[8] = joint_states_position[8]
            action_position[9] = joint_states_position[9] 
            action_position[10] = joint_states_position[10]
            action_position[11] = joint_states_position[11]
            action_position[12] = joint_states_position[12]
            action_position[13] = joint_states_position[13]
            action_position[14] = joint_states_position[14]
            action_position[15] = joint_states_position[15]
            action_position[16] = joint_states_position[16] 
            action_position[17] = joint_states_position[17]
            action_position[18] = joint_states_position[18] 
            action_position[19] = joint_states_position[19] + self._joint_increment_value
        
        elif action == 39: #Decrement haa_joint
            action_position[0] = joint_states_position[0] 
            action_position[1] = joint_states_position[1]
            action_position[2] = joint_states_position[2]
            action_position[3] = joint_states_position[3]
            action_position[4] = joint_states_position[4]
            action_position[5] = joint_states_position[5]
            action_position[6] = joint_states_position[6]
            action_position[7] = joint_states_position[7]
            action_position[8] = joint_states_position[8]
            action_position[9] = joint_states_position[9] 
            action_position[10] = joint_states_position[10]
            action_position[11] = joint_states_position[11]
            action_position[12] = joint_states_position[12]
            action_position[13] = joint_states_position[13]
            action_position[14] = joint_states_position[14]
            action_position[15] = joint_states_position[15]
            action_position[16] = joint_states_position[16] 
            action_position[17] = joint_states_position[17]
            action_position[18] = joint_states_position[18]
            action_position[19] = joint_states_position[19] - self._joint_increment_value       

        return action_position

    def process_data(self):
        """
        We return the total reward based on the state in which we are in and if its done or not
        ( it fell basically )
        :return: reward, done
        """
        catbot_height_ok = self.catbot_height_ok()
        catbot_orientation_ok = self.catbot_orientation_ok()
        # print(catbot_height_ok, catbot_orientation_ok)

        done = not(catbot_height_ok and catbot_orientation_ok)
        if done:
            rospy.logdebug("It fell, so the reward has to be very low")
            total_reward = self._done_reward
        else:
            rospy.logdebug("Calculate normal reward because it didn't fall.")
            total_reward = self.calculate_total_reward()

        return total_reward, done

    def testing_loop(self):

        rate = rospy.Rate(50)
        while not rospy.is_shutdown():
            self.calculate_total_reward()
            rate.sleep()


if __name__ == "__main__":
    rospy.init_node('monoped_state_node', anonymous=True)
    monoped_state = CatbotState(max_height=3.0,
                                 min_height=0.6,
                                 abs_max_roll=0.7,
                                 abs_max_pitch=0.7)
    monoped_state.testing_loop()
