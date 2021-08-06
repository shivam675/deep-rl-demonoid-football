#! /usr/bin/env python

from human_arm.hand_scripts.scripts.mangekyo import main
import rospy
import sys
import copy
import moveit_commander
import moveit_msgs.msg
import geometry_msgs.msg
import actionlib
import math
from geometry_msgs.msg import Twist
from set_joint_angles import *






def ex(msg):
    x_vel = msg.linear.x
    y_vel = msg.linear.y
    yaw = msg.angular.z

    




if __name__ == '__main__':
    rospy.init_node("demonoid_walk", anonymous=True)
    sub = rospy.Subscriber("/cmd_vel", Twist, callback=ex, queue_size=10)
    main()