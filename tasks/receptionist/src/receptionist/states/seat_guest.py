import smach
import rospy

from typing import List
from shapely.geometry import Polygon

import numpy as np

from geometry_msgs.msg import Point, PointStamped
from lasr_skills import (
    PlayMotion,
    Detect3DInArea,
    LookToPoint,
    Say,
    WaitForPerson,
    Wait,
)

from receptionist.states import PointCloudSweep, RunAndProcessDetections

from std_msgs.msg import Header


class SeatGuest(smach.StateMachine):

    class ProcessDetectionsSofa(smach.State):
        def __init__(self, max_people_on_sofa: int):
            smach.State.__init__(
                self,
                outcomes=["has_free_space", "full_sofa"],
                input_keys=["detections_3d"],
                output_keys=["has_free_space"],
            )
            self.max_people_on_sofa = max_people_on_sofa

        def execute(self, userdata) -> str:
            if len(userdata.detections_3d) < self.max_people_on_sofa:
                print(f" the detections are {len(userdata.detections_3d)}")
                return "has_free_space"
            return "full_sofa"

    class ProcessDetections(smach.State):
        def __init__(self):
            smach.State.__init__(
                self,
                outcomes=["succeeded", "failed"],
                input_keys=[
                    "detections_3d",
                ],
                output_keys=["seat_position"],
            )

        def execute(self, userdata) -> str:

            seat_detections = [
                det for det in userdata.detections_3d if det.name == "chair"
            ]
            person_detections = [
                det for det in userdata.detections_3d if det.name == "person"
            ]

            person_polygons: List[Polygon] = [
                Polygon(np.array(person.xyseg).reshape(-1, 2))
                for person in person_detections
            ]

            print(
                f"There are {len(seat_detections)} seats and {len(person_detections)} people."
            )

            for seat in seat_detections:
                seat_polygon: Polygon = Polygon(np.array(seat.xyseg).reshape(-1, 2))
                seat_is_empty: bool = True
                for person_polygon in person_polygons:
                    print("Person polygon")
                    print()
                    print(person_polygon.intersection(seat_polygon).area)
                    print(person_polygon.area)
                    print(
                        person_polygon.intersection(seat_polygon).area
                        / person_polygon.area
                    )
                    print(person_polygon.intersects(seat_polygon))

                    # get the percentage of the person that is on the seat
                    if (
                        person_polygon.intersection(seat_polygon).area
                        / person_polygon.area
                        > 0.2
                    ):
                        seat_is_empty = False
                        print("Person is on the seat/n")
                        print(person_polygon.intersection(seat_polygon).area)
                        print(person_polygon.area)
                        break

                if seat_is_empty:
                    userdata.seat_position = PointStamped(
                        point=seat.point, header=Header(frame_id="map")
                    )
                    print(seat.point)
                    return "succeeded"

            return "failed"

    def __init__(
        self,
        seat_area: Polygon,
        sofa_area: Polygon,
        sweep_points: List[Point],
        max_people_on_sofa: int,
    ):
        smach.StateMachine.__init__(self, outcomes=["succeeded", "failed"])
        with self:
            # TODO: stop doing this
            self.userdata.people_detections = []
            self.userdata.seat_detections = []
            self.userdata.seat_position = PointStamped()

            smach.StateMachine.add(
                "LOOK_CENTRE",
                PlayMotion(motion_name="look_centre"),
                transitions={
                    "succeeded": "DETECT_SOFA",
                    "aborted": "DETECT_SOFA",
                    "preempted": "DETECT_SOFA",
                },
            )

            smach.StateMachine.add(
                "DETECT_SOFA",
                Detect3DInArea(sofa_area, filter=["person"]),
                transitions={"succeeded": "CHECK_SOFA", "failed": "failed"},
            )
            smach.StateMachine.add(
                "CHECK_SOFA",
                self.ProcessDetectionsSofa(0),
                transitions={
                    "full_sofa": "SWEEP",
                    "has_free_space": "SAY_SIT_ON_SOFA",
                },
            )

            smach.StateMachine.add(
                "SAY_SIT_ON_SOFA",
                Say("Please sit on the sofa."),
                transitions={
                    "succeeded": "WAIT_FOR_GUEST_SEAT",
                    "aborted": "failed",
                    "preempted": "failed",
                },
            )

            smach.StateMachine.add(
                "SWEEP",
                PointCloudSweep(
                    sweep_points=sweep_points,
                ),
                transitions={
                    "succeeded": "RUN_AND_PROCESS_DETECTIONS",
                    "failed": "failed",
                },
            )

            smach.StateMachine.add(
                "RUN_AND_PROCESS_DETECTIONS",
                RunAndProcessDetections(seat_area),
                transitions={"succeeded": "LOOK_TO_POINT", "failed": "failed"},
                remapping={"empty_seat_point": "seat_position"},
            )

            smach.StateMachine.add(
                "LOOK_TO_POINT",
                LookToPoint(),
                transitions={
                    "succeeded": "SAY_SIT",
                    "aborted": "failed",
                    "timed_out": "SAY_SIT",
                },
                remapping={"pointstamped": "seat_position"},
            )
            smach.StateMachine.add(
                "SAY_SIT",
                Say("Please sit in the seat that I am looking at."),
                transitions={
                    "succeeded": "WAIT_FOR_GUEST_SEAT",
                    "aborted": "failed",
                    "preempted": "failed",
                },
            )

            smach.StateMachine.add(
                "WAIT_FOR_GUEST_SEAT",
                Wait(5),
                transitions={
                    "succeeded": "RESET_HEAD",
                    "failed": "RESET_HEAD",
                },
            )

            smach.StateMachine.add(
                "RESET_HEAD",
                PlayMotion("look_centre"),
                transitions={
                    "succeeded": "succeeded",
                    "aborted": "failed",
                    "preempted": "failed",
                },
            )
