#!/usr/bin/env python3
import rospy
import smach
import smach_ros
from typing import Dict, List
from lasr_skills import (
    GoToLocation,
    FindPerson,
    Guide,
    HandoverObject,
    Say,
    ReceiveObject,
    FindPersonAndTell,
    CountPeople,
    LookToPoint,
)

from lasr_person_following.msg import FollowAction, FollowGoal

from gpsr.states import (
    Talk,
    QuestionAnswer,
    GoFindTheObject,
    ObjectComparison,
    CountObject,
)
import os
import rospkg

from geometry_msgs.msg import (
    Pose,
    Point,
    Quaternion,
    Polygon,
    PoseWithCovarianceStamped,
    PointStamped,
)
from std_msgs.msg import Header

STATE_COUNT = 0
from lasr_skills import GoToLocation


"""
Helpers
"""


def increment_state_count() -> int:
    global STATE_COUNT
    STATE_COUNT += 1
    return STATE_COUNT


def get_location_room(location: str) -> str:
    rooms = rospy.get_param("/gpsr/arena/rooms")
    for room in rooms:
        if location in rooms[room]["beacons"]:
            return room
    raise ValueError(f"Location {location} not found in the arena")


def get_current_pose() -> Pose:
    pose = rospy.wait_for_message("/amcl_pose", PoseWithCovarianceStamped)
    return pose.pose.pose


def get_location_pose(location: str, person: bool, dem_manipulation=False) -> Pose:
    location_room = get_location_room(location)
    if person:
        location_pose: Dict = rospy.get_param(
            f"/gpsr/arena/rooms/{location_room}/beacons/{location}/person_detection_pose"
        )
    elif not dem_manipulation:
        location_pose: Dict = rospy.get_param(
            f"/gpsr/arena/rooms/{location_room}/beacons/{location}/object_detection_pose"
        )
    else:
        location_pose: Dict = rospy.get_param(
            f"/gpsr/arena/roomss/{location_room}/beacons/{location}/dem_manipulation_pose"
        )

    return Pose(
        position=Point(**location_pose["position"]),
        orientation=Quaternion(**location_pose["orientation"]),
    )


def get_room_pose(room: str) -> Pose:
    location_pose: Dict = rospy.get_param(f"/gpsr/arena/rooms/{room}/pose")
    return Pose(
        position=Point(**location_pose["position"]),
        orientation=Quaternion(**location_pose["orientation"]),
    )


def get_person_detection_poses(room: str) -> List[Pose]:
    poses = []
    for pose in rospy.get_param(f"/gpsr/arena/rooms/{room}/people_search_poses"):
        poses.append(
            Pose(
                position=Point(**pose["position"]),
                orientation=Quaternion(**pose["orientation"]),
            )
        )
    return poses


def get_room_polygon(room: str) -> Polygon:
    return Polygon(
        [Point(**p) for p in rospy.get_param(f"/gpsr/arena/rooms/{room}/room_polygon")]
    )


def get_person_detection_polygon(location: str) -> Polygon:
    location_room = get_location_room(location)
    return Polygon(
        [
            Point(**p)
            for p in rospy.get_param(
                f"/gpsr/arena/rooms/{location_room}/beacons/{location}/person_detection_polygon"
            )
        ]
    )


def get_object_detection_polygon(location: str) -> Polygon:
    location_room = get_location_room(location)
    return Polygon(
        [
            Point(**p)
            for p in rospy.get_param(
                f"/gpsr/arena/rooms/{location_room}/beacons/{location}/object_detection_polygon"
            )
        ]
    )


def get_look_point(location: str) -> PointStamped:
    location_room = get_location_room(location)
    look_point = rospy.get_param(
        f"/gpsr/arena/rooms/{location_room}/beacons/{location}/object_detection_point"
    )
    return PointStamped(
        header=Header(frame_id="map"),
        point=Point(**look_point),
    )


def get_objects_from_category(category: str) -> List[str]:
    return rospy.get_param(f"/gpsr/objects/{category}")


"""
Verbs
"""


def greet(command_param: Dict, sm: smach.StateMachine) -> None:
    if "room" in command_param:
        waypoints: List[Pose] = get_person_detection_poses(command_param["room"])
        polygon: Polygon = get_room_polygon(command_param["room"])
    elif "location" in command_param:
        waypoints: List[Pose] = [get_location_pose(command_param["location"], True)]
        polygon: Polygon = get_person_detection_polygon(command_param["location"])
    else:
        raise ValueError(
            "Greet command received with no room or location in command parameters"
        )

    if "name" in command_param:
        criteria = "name"
        criteria_value = command_param["name"]
    elif "clothes" in command_param:
        criteria = "clothes"
        criteria_value = command_param["clothes"]
    elif "gesture" in command_param:
        criteria = "gesture"
        criteria_value = command_param["gesture"]
        if "pointing" in criteria_value:
            if "left" in criteria_value:
                criteria_value = "pointing_to_the_left"
            elif "right" in criteria_value:
                criteria_value = "pointing_to_the_right"
        elif "raising" in criteria_value:
            if "left" in criteria_value:
                criteria_value = "raising_left_arm"
            elif "right" in criteria_value:
                criteria_value = "raising_right_arm"
        elif "waving" in criteria_value:
            criteria_value = "waving"
        rospy.loginfo(f"CRITERIA VALUE: {criteria_value}")

    elif "pose" in command_param:
        criteria = "pose"
        criteria_value = command_param["pose"]
    else:
        raise ValueError(
            "Greet command received with no name, clothes, gesture, or pose in command parameters"
        )

    sm.add(
        f"STATE_{increment_state_count()}",
        FindPerson(
            waypoints=waypoints,
            polygon=polygon,
            criteria=criteria,
            criteria_value=criteria_value,
        ),
        transitions={
            "succeeded": f"STATE_{STATE_COUNT + 1}",
            "failed": "failed",
        },
    )


def talk(command_param: Dict, sm: smach.StateMachine) -> None:
    """
    This combines talk and tell as they use the same verb.

    Talk:
        - Say a given response
        - Say a given response to a person in a given gesture at a given location.

    Tell:
        People

        Need additional find person skill, then handle the following commands here

        - Tell me the name of the person at a given room or location.
        - Tell me the pose of the person at a given room or location.
        - Tell me the gesture of the person at a given room or location.

        Objects

        This can all be a single skill that takes img_msg, runs inference, outputs object name

        - Tell me what is the biggest object at a given placement location
        - Tell me what is the largest object at a given placement location
        - Tell me what is the smallest object at a given placement location
        - Tell me what is the heaviest object at a given placement location
        - Tell me what is the lightest object at a given placement location
        - Tell me what is the thinnest object at a given placement location

        - Tell me what is the biggest object in a given category at a given placement location
        - Tell me what is the largest object in a given category at a given placement location
        - Tell me what is the smallest object in a given category at a given placement location
        - Tell me what is the heaviest object in a given category at a given placement location
        - Tell me what is the lightest object in a given category at a given placement location
        - Tell me what is the thinnest object at in a given category a given placement location


    """
    if "talk" in command_param:
        if "gesture" in command_param:
            if not "room" in command_param:
                raise ValueError(
                    "Talk command with gesture but no room in command parameters"
                )
            waypoints: List[Pose] = get_person_detection_poses(command_param["room"])
            polygon: Polygon = get_room_polygon(command_param["room"])
            sm.add(
                f"STATE_{increment_state_count()}",
                FindPersonAndTell(
                    waypoints=waypoints,
                    polygon=polygon,
                    criteria="gesture",
                    criteria_value=command_param["gesture"],
                ),
                transitions={
                    "succeeded": f"STATE_{STATE_COUNT + 1}",
                    "failed": "failed",
                },
            )

        sm.add(
            f"STATE_{increment_state_count()}",
            Talk(command_param["talk"]),
            transitions={"succeeded": f"STATE_{STATE_COUNT + 1}", "failed": "failed"},
        )
    elif "personinfo" in command_param:
        query: str = command_param["personinfo"]
        if query not in ["name", "pose", "gesture"]:
            raise ValueError(
                f"Person info query {query} not recognised. Must be 'name', 'pose', or 'gesture'"
            )

        if "room" in command_param:
            waypoints: List[Pose] = get_person_detection_poses(command_param["room"])
            polygon: Polygon = get_room_polygon(command_param["room"])
        elif "location" in command_param:
            waypoints: List[Pose] = [get_location_pose(command_param["location"], True)]
            polygon: Polygon = get_person_detection_polygon(command_param["location"])
        else:
            raise ValueError(
                "Tell command received with personinfo, but no room or location in command parameters"
            )

        sm.add(
            f"STATE_{increment_state_count()}",
            FindPersonAndTell(
                waypoints=waypoints,
                polygon=polygon,
                criteria="name",
            ),
            transitions={
                "succeeded": f"STATE_{STATE_COUNT + 1}",
                "failed": "failed",
            },
        )

        sm.add(
            f"STATE_{increment_state_count()}",
            GoToLocation(location=get_current_pose()),
            transitions={
                "succeeded": f"STATE_{STATE_COUNT + 1}",
                "failed": "failed",
            },
        )

        sm.add(
            f"STATE_{increment_state_count()}",
            Say(format_str="The " + query + " of the person is {}"),
            transitions={
                "succeeded": f"STATE_{STATE_COUNT + 1}",
                "failed": "failed",
            },
            remapping={"placeholders": "query_result"},
        )

    elif "object_category" in command_param:
        if not "location" in command_param:
            raise ValueError(
                "Tell command with object but no room in command parameters"
            )
        location_param_room = f"/gpsr/arena/rooms/{command_param['location']}"
        sm.add(
            f"STATE_{increment_state_count()}",
            GoToLocation(location_param=f"{location_param_room}/pose"),
            transitions={
                "succeeded": f"STATE_{STATE_COUNT + 1}",
                "failed": "failed",
            },
        )
        # TODO: combine the weight list within
        # TODO: add speak out the result
        weight_list = rospy.get_param("/Object_list/Object")
        sm.add(
            f"STATE_{increment_state_count()}",
            ObjectComparison(
                filter=command_param["object_category"],
                operation_label="weight",
                weight=weight_list,
            ),
            transitions={
                "succeeded": f"STATE_{STATE_COUNT + 1}",
                "failed": "failed",
            },
        )

        sm.add(
            f"STATE_{increment_state_count()}",
            ObjectComparison(
                filter=command_param["object_category"],
                operation_label="size",  # need the relation between command and operation
                weight=weight_list,
            ),
            transitions={
                "succeeded": f"STATE_{STATE_COUNT + 1}",
                "failed": "failed",
            },
        )

    elif "personinfo" in command_param:
        # personinfo: pose, gesture, name
        pass


def guide(command_param: Dict, sm: smach.StateMachine) -> None:
    """
    Guide commands can be of the following form:

    - Guide a person in front of the robot to a given room.
    - Guide a named person from a start location to a destination room or location.
    - Guide a person in a given gesture from a given start location to a destination room or location.
    - Guide a person in a given pose from a given start location to a destination room or location.
    - Guide a person in a given set of clothes from a given start location to a destination room or location.

    """

    find_person = False
    if "start" not in command_param:
        pass
    elif "name" in command_param:
        criteria = "name"
        criteria_value = command_param["name"]
        find_person = True
    elif "clothes" in command_param:
        criteria = "clothes"
        criteria_value = command_param["clothes"]
        find_person = True
    elif "gesture" in command_param:
        criteria = "gesture"
        criteria_value = command_param["gesture"]
        find_person = True
    elif "pose" in command_param:
        criteria = "pose"
        criteria_value = command_param["pose"]
        find_person = True
    else:
        location_pose = get_room_pose(command_param["room"])
        location_name = command_param["room"]

    if find_person:
        start_loc = command_param["start"]
        start_pose = get_location_pose(start_loc, person=True)
        room = get_location_room(start_loc)
        polygon: Polygon = get_room_polygon(room)

        sm.add(
            f"STATE_{increment_state_count()}",
            FindPerson(
                waypoints=[start_pose],
                polygon=polygon,
                criteria=criteria,
                criteria_value=criteria_value,
            ),
            transitions={
                "succeeded": f"STATE_{STATE_COUNT + 1}",
                "failed": "failed",
            },
        )

        try:
            location_pose = get_location_pose(command_param["end"], person=True)
            location_name = command_param["end"]
        except KeyError:
            location_pose = get_room_pose(command_param["end"])
            location_name = command_param["end"]
    else:
        if "room" in command_param:
            location_pose = get_room_pose(command_param["room"])
            location_name = command_param["room"]
        elif "location" in command_param:
            location_pose = get_location_pose(command_param["location"], True)
            location_name = command_param["location"]
        else:
            raise ValueError(
                "Guide command received with no room or location in command parameters"
            )

    sm.add(
        f"STATE_{increment_state_count()}",
        Guide(location_name=location_name, location_pose=location_pose),
        transitions={"succeeded": f"STATE_{STATE_COUNT + 1}", "failed": "failed"},
    )


def deliver(command_param: Dict, sm: smach.StateMachine) -> None:
    """
    The possible deliver commands are:
        - deliver an object the robot aleady has to me
        - deliver an object the robot already has to a person in a given gesture in a given room.
        - deliver an object the robot already has to a person in a given pose in a given room.
        - deliver an object the robot already has to a person with a given name in a given room.


    """

    if "room" in command_param:
        waypoints: List[Pose] = get_person_detection_poses(command_param["room"])
        polygon: Polygon = get_room_polygon(command_param["room"])

    if "name" in command_param:
        criteria = "name"
        criteria_value = command_param["name"]
    elif "gesture" in command_param:
        criteria = "gesture"
        criteria_value = command_param["gesture"]
    elif "pose" in command_param:
        criteria = "pose"
        criteria_value = command_param["pose"]
    else:
        criteria = None
        waypoints = [get_current_pose()]

    sm.add(
        f"STATE_{increment_state_count()}",
        FindPerson(
            waypoints=waypoints,
            polygon=polygon,
            criteria=criteria,
            criteria_value=criteria_value,
        ),
        transitions={
            "succeeded": f"STATE_{STATE_COUNT + 1}",
            "failed": "failed",
        },
    )

    if "object" in command_param:
        object_name = command_param["object"]
    elif "object_category" in command_param:
        object_name = command_param["object_category"]
    else:
        raise ValueError(
            "Deliver command received with no object or object category in command parameters"
        )

    sm.add(
        f"STATE_{increment_state_count()}",
        HandoverObject(object_name=object_name),
        transitions={
            "succeeded": f"STATE_{STATE_COUNT + 1}",
            "failed": "failed",
        },
    )


def place(command_param: Dict, sm: smach.StateMachine) -> None:

    if "location" in command_param:
        location_pose = get_location_pose(
            command_param["location"], False, dem_manipulation=True
        )
    else:
        raise ValueError(
            "Place command received with no location in command parameters"
        )

    sm.add(
        f"STATE_{increment_state_count()}",
        GoToLocation(location=location_pose),
        transitions={
            "succeeded": f"STATE_{STATE_COUNT + 1}",
            "failed": "failed",
        },
    )

    if "object" in command_param:
        object_name = command_param["object"]
    elif "object_category" in command_param:
        object_name = command_param["object_category"]
    else:
        raise ValueError(
            "Place command received with no object or object category in command parameters"
        )

    sm.add(
        f"STATE_{increment_state_count()}",
        HandoverObject(object_name=object_name),
        transitions={
            "succeeded": f"STATE_{STATE_COUNT + 1}",
            "failed": "failed",
        },
    )

    sm.add(
        f"STATE_{increment_state_count()}",
        Say(text=f"Please place the object on the {command_param['location']}"),
        transitions={
            "succeeded": f"STATE_{STATE_COUNT + 1}",
            "aborted": "failed",
            "preempted": "failed",
        },
    )


def take(command_param: Dict, sm: smach.StateMachine) -> None:

    if "object" in command_param:
        criteria = "object"
        criteria_value = command_param["object"]
    elif "object_category" in command_param:
        criteria = "object_category"
        criteria_value = command_param["object_category"]
    else:
        raise ValueError(
            "Take command received with no object or object category in command parameters"
        )
    if "location" in command_param:
        location_pose = get_location_pose(command_param["location"], False)
    else:
        raise ValueError("Take command received with no location in command parameters")

    # TODO: this should use find, to find the object at the location
    sm.add(
        f"STATE_{increment_state_count()}",
        GoToLocation(location=location_pose),
        transitions={
            "succeeded": f"STATE_{STATE_COUNT + 1}",
            "failed": "failed",
        },
    )

    sm.add(
        f"STATE_{increment_state_count()}",
        Say(
            text=f"Please pick up the {criteria_value} on the {command_param['location']} for me."
        ),
        transitions={
            "succeeded": f"STATE_{STATE_COUNT + 1}",
            "aborted": "failed",
            "preempted": "failed",
        },
    )

    sm.add(
        f"STATE_{increment_state_count()}",
        GoToLocation(
            location=get_location_pose(
                command_param["location"], False, dem_manipulation=True
            ),
        ),
        transitions={
            "succeeded": f"STATE_{STATE_COUNT + 1}",
            "failed": "failed",
        },
    )

    sm.add(
        f"STATE_{increment_state_count()}",
        ReceiveObject(object_name=criteria_value),
        transitions={
            "succeeded": f"STATE_{STATE_COUNT + 1}",
            "failed": "failed",
        },
    )


def answer(command_param: Dict, sm: smach.StateMachine) -> None:
    data_root = os.path.join(rospkg.RosPack().get_path("gpsr"), "data")
    sm.add(
        f"STATE_{increment_state_count()}",
        QuestionAnswer(
            index_path=os.path.join(data_root, "questions.index"),
            txt_path=os.path.join(data_root, "questions.txt"),
            xml_path=os.path.join(data_root, "questions.xml"),
            k=1,
        ),
        transitions={
            "succeeded": f"STATE_{STATE_COUNT + 1}",
            "failed": "failed",
        },
    )


def go(command_param: Dict, sm: smach.StateMachine, person: bool) -> None:
    """
    The possible GO commands are:
        - Go to a location or room and then...

    Person is used to denote whether the robot should go to the location's person
    pose or object pose.

    """
    if "location" in command_param:
        target_pose = get_location_pose(command_param["location"], person)
    elif "room" in command_param:
        target_pose = get_room_pose(command_param["room"])
    else:
        raise ValueError(
            "Go command received with no location or room in command parameters"
        )

    sm.add(
        f"STATE_{increment_state_count()}",
        GoToLocation(location=target_pose),
        transitions={
            "succeeded": f"STATE_{STATE_COUNT + 1}",
            "failed": "failed",
        },
    )


def bring(command_param: Dict, sm: smach.StateMachine) -> None:
    raise NotImplementedError("Bring command not implemented")


def find(command_param: Dict, sm: smach.StateMachine) -> None:
    """
    find a object in the given room
    """

    if "object_category" in command_param:
        raise NotImplementedError("Find command not implemented")
        if not "location" in command_param:
            raise ValueError(
                "find command with object but no room in command parameters"
            )
        location_param_room = f"/gpsr/arena/rooms/{command_param['location']}"
        sm.add(
            f"STATE_{increment_state_count()}",
            GoFindTheObject(
                location_param=location_param_room,
                filter=command_param["object_category"],
            ),
            transitions={
                "succeeded": f"STATE_{STATE_COUNT + 1}",
                "failed": "failed",
            },
        )

    elif "gesture" in command_param:
        greet(command_param, sm)


def meet(command_param: Dict, sm: smach.StateMachine) -> None:
    """
    Meet commands can be of the following form:

    - Meet a person at a location and execute another command.
    - Meet a person in a room and execute another command.
    - Meet a person in a rooom then find them in another room.
    """
    greet(command_param, sm)


def count(command_param: Dict, sm: smach.StateMachine) -> None:
    """
    Count commands can be of the following form:

    - Tell me how many objects there are of a given category at a placement location
    - Tell me how many people there are in a given gesture in a given room
    - Tell me how many people there are in a given pose in a given room
    - Tell me how many people there are wearing given clothes in a given room
    """

    people: bool = False

    if "pose" in command_param:
        criteria = "pose"
        criteria_value = command_param["pose"]
        people = True
    elif "gesture" in command_param:
        criteria = "gesture"
        criteria_value = command_param["gesture"]
        people = True
    elif "clothes" in command_param:
        criteria = "clothes"
        criteria_value = command_param["clothes"]
        people = True
    elif "object_category" in command_param:
        criteria = "object_category"
        criteria_value = command_param["object_category"]
    else:
        raise ValueError(
            "Count command received with no pose, gesture, clothes, or object category in command parameters"
        )

    if people:
        if "room" in command_param:
            waypoints: List[Pose] = get_person_detection_poses(command_param["room"])
            polygon: Polygon = get_room_polygon(command_param["room"])
        else:
            raise ValueError(
                "Count command received pose, gesture, clothes, or object category but no room in command parameters"
            )

        sm.add(
            f"STATE_{increment_state_count()}",
            CountPeople(
                waypoints=waypoints,
                polygon=polygon,
                criteria=criteria,
                criteria_value=criteria_value,
            ),
            transitions={
                "succeeded": f"STATE_{STATE_COUNT + 1}",
                "failed": "failed",
            },
        )

        sm.add(
            f"STATE_{increment_state_count()}",
            GoToLocation(location=get_current_pose()),
            transitions={
                "succeeded": f"STATE_{STATE_COUNT + 1}",
                "failed": "failed",
            },
        )

        sm.add(
            f"STATE_{increment_state_count()}",
            Say(
                format_str="There are {}"
                + criteria_value
                + " people in the "
                + command_param["room"]
            ),
            transitions={
                "succeeded": f"STATE_{STATE_COUNT + 1}",
                "failed": "failed",
            },
            remapping={"placeholders": "people_count"},
        )

    else:
        if not "location" in command_param:
            raise ValueError(
                "Count command with object but no room in command parameters"
            )
        location_pose = get_location_pose(command_param["location"], False)
        location_polygon = get_object_detection_polygon(command_param["location"])

        sm.add(
            f"STATE_{increment_state_count()}",
            GoToLocation(location=location_pose),
            transitions={
                "succeeded": f"STATE_{STATE_COUNT + 1}",
                "failed": "failed",
            },
        )

        sm.add(
            f"STATE_{increment_state_count()}",
            LookToPoint(pointstamped=get_look_point(command_param["location"])),
            transitions={
                "succeeded": f"STATE_{STATE_COUNT + 1}",
                "aborted": "failed",
                "timed_out": f"STATE_{STATE_COUNT + 1}",
            },
        )

        sm.add(
            f"STATE_{increment_state_count()}",
            CountObject(
                location_polygon,
                objects=get_objects_from_category(command_param["object_category"]),
            ),
            transitions={"succeeded": f"STATE_{STATE_COUNT + 1}", "failed": "failed"},
        )

        sm.add(
            f"STATE_{increment_state_count()}",
            GoToLocation(location=get_current_pose()),
            transitions={
                "succeeded": f"STATE_{STATE_COUNT + 1}",
                "failed": "failed",
            },
        )

        sm.add(
            f"STATE_{increment_state_count()}",
            Say(
                format_str="There are {} "
                + criteria_value
                + " on the "
                + command_param["location"]
            ),
            transitions={
                "succeeded": f"STATE_{STATE_COUNT + 1}",
                "failed": "failed",
            },
            remapping={"placeholders": "object_count"},
        )


# )


def follow(command_param: Dict, sm: smach.StateMachine) -> None:
    sm.add(
        f"STATE_{increment_state_count()}",
        smach_ros.SimpleActionState(
            "/follow_person",
            FollowAction,
            goal=FollowGoal(),
        ),
        transitions={
            "succeeded": f"STATE_{STATE_COUNT + 1}",
            "aborted": "failed",
            "preempted": "failed",
        },
    )


"""
Build
"""


def build_state_machine(parsed_command: Dict) -> smach.StateMachine:
    """Constructs the parameterized state machine for the GPSR task,
    given the parsed command.

    Args:
        parsed_command (Dict): parsed command.

    Returns:
        smach.StateMachine: paramaterized state machine ready to be executed.
    """
    command_verbs: List[str] = parsed_command["commands"]
    command_params: List[Dict] = parsed_command["command_params"]
    sm = smach.StateMachine(outcomes=["succeeded", "failed"])
    with sm:
        for index, (command_verb, command_param) in enumerate(
            zip(command_verbs, command_params)
        ):
            if command_verb == "greet":
                greet(command_param, sm)
            elif command_verb == "talk":
                talk(command_param, sm)
            elif command_verb == "guide":
                guide(command_param, sm)
            elif command_verb == "deliver" and len(command_params) > 1:
                deliver(command_param, sm)
            elif command_verb == "deliver" and len(command_params) == 1:
                bring(command_param, sm)
            elif command_verb == "place":
                place(command_param, sm)
            elif command_verb == "take":
                take(command_param, sm)
            elif command_verb == "answer":
                answer(command_param, sm)
            elif command_verb == "go":
                person = not any(
                    [
                        param in ["object", "object_category"]
                        for param in command_params[index:]
                    ]
                )
                go(command_param, sm, person)
            elif command_verb == "find":
                find(command_param, sm)
            elif command_verb == "meet":
                meet(command_param, sm)
            elif command_verb == "count":
                count(command_param, sm)
            elif command_verb == "follow":
                follow(command_param, sm)
            else:
                raise ValueError(f"Unrecognised command verb: {command_verb}")

        @smach.cb_interface(outcomes=["succeeded"])
        def terminal_cb(_):
            return "succeeded"

        sm.add(
            f"STATE_{increment_state_count()}",
            smach.CBState(terminal_cb),
            transitions={"succeeded": "succeeded"},
        )

    rospy.loginfo(f"State machine: {sm}")
    return sm
