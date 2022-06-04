#!/usr/bin/env python

import rospy
import math
from std_msgs.msg import String
from std_msgs.msg import Float64

class JointPub(object):
    def __init__(self):

        self.publishers_array = []
        self._bum_zlj_pub = rospy.Publisher('/bum_zlj_joint_position_controller/command', Float64, queue_size=1)
        self._bum_xlj_pub = rospy.Publisher('/bum_xlj_joint_position_controller/command', Float64, queue_size=1)
        self._bum_ylj_pub = rospy.Publisher('/bum_ylj_joint_position_controller/command', Float64, queue_size=1)
        self._knee_left_pub = rospy.Publisher('/knee_left_joint_position_controller/command', Float64, queue_size=1)
        self._ankle_lj_pub = rospy.Publisher('/ankle_lj_joint_position_controller/command', Float64, queue_size=1)
        self._foot_lj_pub = rospy.Publisher('/foot_lj_joint_position_controller/command', Float64, queue_size=1)
        self._bum_zrj_pub = rospy.Publisher('/bum_zrj_joint_position_controller/command', Float64, queue_size=1)
        self._bum_xrj_pub = rospy.Publisher('/bum_xrj_joint_position_controller/command', Float64, queue_size=1)
        self._bum_yrj_pub = rospy.Publisher('/bum_yrj_joint_position_controller/command', Float64, queue_size=1)
        self._knee_right_pub = rospy.Publisher('/knee_right_joint_position_controller/command', Float64, queue_size=1)
        self._ankle_rj_pub = rospy.Publisher('/ankle_rj_joint_position_controller/command', Float64, queue_size=1)
        self._foot_rj_pub = rospy.Publisher('/foot_rj_joint_position_controller/command', Float64, queue_size=1)
        self._shoulder_zlj_pub = rospy.Publisher('/shoulder_zlj_joint_position_controller/command', Float64, queue_size=1)
        self._shoulder_xlj_pub = rospy.Publisher('/shoulder_xlj_joint_position_controller/command', Float64, queue_size=1)
        self._shoulder_ylj_pub = rospy.Publisher('/shoulder_ylj_joint_position_controller/command', Float64, queue_size=1)
        self._forearm_ylj_pub = rospy.Publisher('/forearm_ylj_joint_position_controller/command', Float64, queue_size=1)
        self._shoulder_zrj_pub = rospy.Publisher('/shoulder_zrj_joint_position_controller/command', Float64, queue_size=1)
        self._shoulder_xrj_pub = rospy.Publisher('/shoulder_xrj_joint_position_controller/command', Float64, queue_size=1)
        self._shoulder_yrj_pub = rospy.Publisher('/shoulder_yrj_joint_position_controller/command', Float64, queue_size=1)
        self._forearm_yrj_pub = rospy.Publisher('/forearm_yrj_joint_position_controller/command', Float64, queue_size=1)


        self.publishers_array = [
            self._bum_zlj_pub,
            self._bum_xlj_pub,
            self._bum_ylj_pub,
            self._knee_left_pub,
            self._ankle_lj_pub,
            self._foot_lj_pub,
            self._bum_zrj_pub,
            self._bum_xrj_pub,
            self._bum_yrj_pub,
            self._knee_right_pub,
            self._ankle_rj_pub,
            self._foot_rj_pub,
            self._shoulder_zlj_pub,
            self._shoulder_xlj_pub,
            self._shoulder_ylj_pub,
            self._forearm_ylj_pub,
            self._shoulder_zrj_pub,
            self._shoulder_xrj_pub,
            self._shoulder_yrj_pub,
            self._forearm_yrj_pub,
        ]

        self.init_pos = [
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            ]

    def set_init_pose(self):
        """
        Sets joints to initial position [0,0,0]
        :return:
        """
        self.check_publishers_connection()
        self.move_joints(self.init_pos)


    def check_publishers_connection(self):
        """
        Checks that all the publishers are working
        :return:
        """

        rate = rospy.Rate(10)  # 10hz
        
        
        while (self._bum_zlj_pub.get_num_connections() == 0):
            rospy.logdebug("No susbribers to _bum_zlj_pub yet so we wait and try again")
            try:
                rate.sleep()
            except rospy.ROSInterruptException:
                # This is to avoid error when world is rested, time when backwards.
                pass
        rospy.logdebug("_bum_zlj_pub Publisher Connected")

        while (self._bum_xlj_pub.get_num_connections() == 0):
            rospy.logdebug("No susbribers to _bum_xlj_pub yet so we wait and try again")
            try:
                rate.sleep()
            except rospy.ROSInterruptException:
                # This is to avoid error when world is rested, time when backwards.
                pass
        rospy.logdebug("_bum_xlj_pub Publisher Connected")

        while (self._bum_ylj_pub.get_num_connections() == 0):
            rospy.logdebug("No susbribers to _bum_ylj_pub yet so we wait and try again")
            try:
                rate.sleep()
            except rospy.ROSInterruptException:
                # This is to avoid error when world is rested, time when backwards.
                pass
        rospy.logdebug("_bum_ylj_pub Publisher Connected")

        while (self._knee_left_pub.get_num_connections() == 0):
            rospy.logdebug("No susbribers to _knee_left_pub yet so we wait and try again")
            try:
                rate.sleep()
            except rospy.ROSInterruptException:
                # This is to avoid error when world is rested, time when backwards.
                pass
        rospy.logdebug("_knee_left_pub Publisher Connected")

        while (self._ankle_lj_pub.get_num_connections() == 0):
            rospy.logdebug("No susbribers to _ankle_lj_pub yet so we wait and try again")
            try:
                rate.sleep()
            except rospy.ROSInterruptException:
                # This is to avoid error when world is rested, time when backwards.
                pass
        rospy.logdebug("_ankle_lj_pub Publisher Connected")

        while (self._foot_lj_pub.get_num_connections() == 0):
            rospy.logdebug("No susbribers to _foot_lj_pub yet so we wait and try again")
            try:
                rate.sleep()
            except rospy.ROSInterruptException:
                # This is to avoid error when world is rested, time when backwards.
                pass
        rospy.logdebug("_foot_lj_pub Publisher Connected")

        while (self._bum_zrj_pub.get_num_connections() == 0):
            rospy.logdebug("No susbribers to _bum_zrj_pub yet so we wait and try again")
            try:
                rate.sleep()
            except rospy.ROSInterruptException:
                # This is to avoid error when world is rested, time when backwards.
                pass
        rospy.logdebug("_bum_zrj_pub Publisher Connected")

        while (self._bum_xrj_pub.get_num_connections() == 0):
            rospy.logdebug("No susbribers to _bum_xrj_pub yet so we wait and try again")
            try:
                rate.sleep()
            except rospy.ROSInterruptException:
                # This is to avoid error when world is rested, time when backwards.
                pass
        rospy.logdebug("_bum_xrj_pub Publisher Connected")

        while (self._bum_yrj_pub.get_num_connections() == 0):
            rospy.logdebug("No susbribers to _bum_yrj_pub yet so we wait and try again")
            try:
                rate.sleep()
            except rospy.ROSInterruptException:
                # This is to avoid error when world is rested, time when backwards.
                pass
        rospy.logdebug("_bum_yrj_pub Publisher Connected")

        while (self._knee_right_pub.get_num_connections() == 0):
            rospy.logdebug("No susbribers to _knee_right_pub yet so we wait and try again")
            try:
                rate.sleep()
            except rospy.ROSInterruptException:
                # This is to avoid error when world is rested, time when backwards.
                pass
        rospy.logdebug("_knee_right_pub Publisher Connected")

        while (self._ankle_rj_pub.get_num_connections() == 0):
            rospy.logdebug("No susbribers to _ankle_rj_pub yet so we wait and try again")
            try:
                rate.sleep()
            except rospy.ROSInterruptException:
                # This is to avoid error when world is rested, time when backwards.
                pass
        rospy.logdebug("_ankle_rj_pub Publisher Connected")

        while (self._foot_rj_pub.get_num_connections() == 0):
            rospy.logdebug("No susbribers to _foot_rj_pub yet so we wait and try again")
            try:
                rate.sleep()
            except rospy.ROSInterruptException:
                # This is to avoid error when world is rested, time when backwards.
                pass
        rospy.logdebug("_foot_rj_pub Publisher Connected")

        while (self._shoulder_zlj_pub.get_num_connections() == 0):
            rospy.logdebug("No susbribers to _shoulder_zlj_pub yet so we wait and try again")
            try:
                rate.sleep()
            except rospy.ROSInterruptException:
                # This is to avoid error when world is rested, time when backwards.
                pass
        rospy.logdebug("_shoulder_zlj_pub Publisher Connected")

        while (self._shoulder_xlj_pub.get_num_connections() == 0):
            rospy.logdebug("No susbribers to _shoulder_xlj_pub yet so we wait and try again")
            try:
                rate.sleep()
            except rospy.ROSInterruptException:
                # This is to avoid error when world is rested, time when backwards.
                pass
        rospy.logdebug("_shoulder_xlj_pub Publisher Connected")

        while (self._shoulder_ylj_pub.get_num_connections() == 0):
            rospy.logdebug("No susbribers to _shoulder_ylj_pub yet so we wait and try again")
            try:
                rate.sleep()
            except rospy.ROSInterruptException:
                # This is to avoid error when world is rested, time when backwards.
                pass
        rospy.logdebug("_shoulder_ylj_pub Publisher Connected")

        while (self._forearm_ylj_pub.get_num_connections() == 0):
            rospy.logdebug("No susbribers to _forearm_ylj_pub yet so we wait and try again")
            try:
                rate.sleep()
            except rospy.ROSInterruptException:
                # This is to avoid error when world is rested, time when backwards.
                pass
        rospy.logdebug("_forearm_ylj_pub Publisher Connected")

        while (self._shoulder_zrj_pub.get_num_connections() == 0):
            rospy.logdebug("No susbribers to _shoulder_zrj_pub yet so we wait and try again")
            try:
                rate.sleep()
            except rospy.ROSInterruptException:
                # This is to avoid error when world is rested, time when backwards.
                pass
        rospy.logdebug("_shoulder_zrj_pub Publisher Connected")

        while (self._shoulder_xrj_pub.get_num_connections() == 0):
            rospy.logdebug("No susbribers to _shoulder_xrj_pub yet so we wait and try again")
            try:
                rate.sleep()
            except rospy.ROSInterruptException:
                # This is to avoid error when world is rested, time when backwards.
                pass
        rospy.logdebug("_shoulder_xrj_pub Publisher Connected")

        while (self._shoulder_yrj_pub.get_num_connections() == 0):
            rospy.logdebug("No susbribers to _shoulder_yrj_pub yet so we wait and try again")
            try:
                rate.sleep()
            except rospy.ROSInterruptException:
                # This is to avoid error when world is rested, time when backwards.
                pass
        rospy.logdebug("_shoulder_yrj_pub Publisher Connected")


        while (self._forearm_yrj_pub.get_num_connections() == 0):
            rospy.logdebug("No susbribers to _forearm_yrj_pub yet so we wait and try again")
            try:
                rate.sleep()
            except rospy.ROSInterruptException:
                # This is to avoid error when world is rested, time when backwards.
                pass
        rospy.logdebug("_forearm_yrj_pub Publisher Connected")


        rospy.logdebug("All Publishers READY")





    def joint_mono_des_callback(self, msg):
        rospy.logdebug(str(msg.joint_state.position))

        self.move_joints(msg.joint_state.position)






    def move_joints(self, joints_array):

        i = 0
        for publisher_object in self.publishers_array:
          joint_value = Float64()
          joint_value.data = joints_array[i]
          rospy.logdebug("JointsPos>>"+str(joint_value))
          publisher_object.publish(joint_value)
          i += 1




    def start_loop(self, rate_value = 2.0):
        rospy.logdebug("Start Loop")
        pos1 = [0.0,0.0,1.6]
        pos2 = [0.0,0.0,-1.6]
        position = "pos1"
        rate = rospy.Rate(rate_value)
        while not rospy.is_shutdown():
          if position == "pos1":
            self.move_joints(pos1)
            position = "pos2"
          else:
            self.move_joints(pos2)
            position = "pos1"
          rate.sleep()

    def start_sinus_loop(self, rate_value = 2.0):
        rospy.logdebug("Start Loop")
        w = 0.0
        x = 2.0*math.sin(w)
        #pos_x = [0.0,0.0,x]
        #pos_x = [x, 0.0, 0.0]
        pos_x = [0.0, x, 0.0]
        rate = rospy.Rate(rate_value)
        while not rospy.is_shutdown():
            self.move_joints(pos_x)
            w += 0.05
            x = 2.0 * math.sin(w)
            #pos_x = [0.0, 0.0, x]
            #pos_x = [x, 0.0, 0.0]
            pos_x = [0.0, x, 0.0]
            rate.sleep()


if __name__=="__main__":
    rospy.init_node('joint_publisher_node')
    joint_publisher = JointPub()
    rate_value = 50.0
    #joint_publisher.start_loop(rate_value)
    # joint_publisher.start_sinus_loop(rate_value)
