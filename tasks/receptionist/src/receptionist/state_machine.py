import smach

from geometry_msgs.msg import Pose
from shapely.geometry import Polygon
from lasr_skills import GoToLocation, WaitForPersonInArea, Say, AskAndListen
from receptionist.states import (
    ParseNameAndDrink,
    GetGuestAttributes,
    Introduce,
    SeatGuest,
)


class Receptionist(smach.StateMachine):
    def __init__(
        self,
        wait_pose: Pose,
        wait_area: Polygon,
        seat_pose: Pose,
        seat_area: Polygon,
        host_data: dict,
    ):
        smach.StateMachine.__init__(self, outcomes=["succeeded", "failed"])

        with self:
            self.userdata.guest_data = {"host": host_data, "guest1": {}, "guest2": {}}

            smach.StateMachine.add(
                "GO_TO_WAIT_LOCATION_GUEST_1",
                GoToLocation(wait_pose),
                transitions={
                    "succeeded": "SAY_WAITING_GUEST_1",
                    "failed": "SAY_WAITING_GUEST_1",
                },
            )

            smach.StateMachine.add(
                "SAY_WAITING_GUEST_1",
                Say(text="I am waiting for a guest."),
                transitions={
                    "succeeded": "WAIT_FOR_PERSON_GUEST_1",
                    "aborted": "WAIT_FOR_PERSON_GUEST_1",
                    "preempted": "WAIT_FOR_PERSON_GUEST_1",
                },
            )

            smach.StateMachine.add(
                "WAIT_FOR_PERSON_GUEST_1",
                WaitForPersonInArea(wait_area),
                transitions={
                    "succeeded": "GET_NAME_AND_DRINK_GUEST_1",
                    "failed": "GET_NAME_AND_DRINK_GUEST_1",
                },
            )


            ######## Asking first Guest for Drink and Name ######

            smach.StateMachine.add(
                "GET_NAME_AND_DRINK_GUEST_1",
                AskAndListen("What is your name and favourite drink?"),
                transitions={
                    "succeeded": "PARSE_NAME_AND_DRINK_GUEST_1",
                    "failed": "PARSE_NAME_AND_DRINK_GUEST_1",
                },
            )

            smach.StateMachine.add(
                "PARSE_NAME_AND_DRINK_GUEST_1",
                ParseNameAndDrink("guest1"),
                transitions={
                    "succeeded": "GET_GUEST_ATTRIBUTES_GUEST_1",
                    "failed": "REPEAT_GET_NAME_AND_DRINK_GUEST_1",
                },
                remapping={"guest_transcription": "transcribed_speech"},
            )


            smach.StateMachine.add(
                "REPEAT_GET_NAME_AND_DRINK_GUEST_1",
                AskAndListen("Sorry, I didn't get that. What is your name and favourite drink?"),
                transitions={
                    "succeeded": "REPEAT_PARSE_NAME_AND_DRINK_GUEST_1",
                    "failed": "SAY_CONTINUE",
                },
            )


            smach.StateMachine.add(
                "REPEAT_PARSE_NAME_AND_DRINK_GUEST_1",
                ParseNameAndDrink("guest1"),
                transitions={
                    "succeeded": "GET_GUEST_ATTRIBUTES_GUEST_1",
                    "failed": "SAY_CONTINUE",
                },
                remapping={"guest_transcription": "transcribed_speech"},
            )

            smach.StateMachine.add(
                "SAY_CONTINUE",
                Say(text="Sorry, I didn't get that. I will carry on."),
                transitions={
                    "succeeded": "GET_GUEST_ATTRIBUTES_GUEST_1",
                    "aborted": "GET_GUEST_ATTRIBUTES_GUEST_1",
                    "preempted": "GET_GUEST_ATTRIBUTES_GUEST_1",
                },
            )


          






            ####### GET GUEST ATTRIBUTES ######

            smach.StateMachine.add(
                "GET_GUEST_ATTRIBUTES_GUEST_1",
                GetGuestAttributes("guest1"),
                transitions={
                    "succeeded": "SAY_FOLLOW_GUEST_1",
                    "failed": "SAY_FOLLOW_GUEST_1",
                },
            )

            smach.StateMachine.add(
                "SAY_FOLLOW_GUEST_1",
                Say(text="Please follow me, I will guide you to the other guests"),
                transitions={
                    "succeeded": "GO_TO_SEAT_LOCATION_GUEST_1",
                    "preempted": "failed",
                    "aborted": "failed",
                },
            )

            smach.StateMachine.add(
                "GO_TO_SEAT_LOCATION_GUEST_1",
                GoToLocation(seat_pose),
                transitions={
                    "succeeded": "SAY_WAIT_GUEST_1",
                    "failed": "SAY_WAIT_GUEST_1",
                },
            )

            smach.StateMachine.add(
                "SAY_WAIT_GUEST_1",
                Say(text="Please wait here on my left"),
                transitions={
                    "succeeded": "INTRODUCE_GUEST_1_TO_HOST",
                    "preempted": "failed",
                    "aborted": "failed",
                },
            )

            smach.StateMachine.add(
                "INTRODUCE_GUEST_1_TO_HOST",
                Introduce(guest_to_introduce="guest1", guest_to_introduce_to="host"),
                transitions={
                    "succeeded": "INTRODUCE_HOST_TO_GUEST_1",
                    "failed": "INTRODUCE_HOST_TO_GUEST_1",
                },
            )

            smach.StateMachine.add(
                "INTRODUCE_HOST_TO_GUEST_1",
                Introduce(guest_to_introduce="host", guest_to_introduce_to="guest1"),
                transitions={
                    "succeeded": "SEAT_GUEST_1",
                    "failed": "SEAT_GUEST_1",
                },
            )

            smach.StateMachine.add(
                "SEAT_GUEST_1",
                SeatGuest(seat_area),
                transitions={
                    "succeeded": "GO_TO_WAIT_LOCATION_GUEST_2",
                    "failed": "GO_TO_WAIT_LOCATION_GUEST_2",
                },
            )

            """
            Guest 2
            """

            smach.StateMachine.add(
                "GO_TO_WAIT_LOCATION_GUEST_2",
                GoToLocation(wait_pose),
                transitions={
                    "succeeded": "SAY_WAITING_GUEST_2",
                    "failed": "SAY_WAITING_GUEST_2",
                },
            )

            smach.StateMachine.add(
                "SAY_WAITING_GUEST_2",
                Say(text="I am waiting for a guest."),
                transitions={
                    "succeeded": "WAIT_FOR_PERSON_GUEST_2",
                    "aborted": "WAIT_FOR_PERSON_GUEST_2",
                    "preempted": "WAIT_FOR_PERSON_GUEST_2",
                },
            )

            smach.StateMachine.add(
                "WAIT_FOR_PERSON_GUEST_2",
                WaitForPersonInArea(wait_area),
                transitions={
                    "succeeded": "GET_NAME_AND_DRINK_GUEST_2",
                    "failed": "GET_NAME_AND_DRINK_GUEST_2",
                },
            )


            ####### Asking second guest for drink and name #######

            smach.StateMachine.add(
                "GET_NAME_AND_DRINK_GUEST_2",
                AskAndListen("What is your name and favourite drink?"),
                transitions={
                    "succeeded": "PARSE_NAME_AND_DRINK_GUEST_2",
                    "failed": "PARSE_NAME_AND_DRINK_GUEST_2",
                },
            )

            smach.StateMachine.add(
                "PARSE_NAME_AND_DRINK_GUEST_2",
                ParseNameAndDrink("guest2"),
                transitions={
                    "succeeded": "GET_GUEST_ATTRIBUTES_GUEST_2",
                    "failed": "REPEAT_GET_NAME_AND_DRINK_GUEST_2",
                },
                remapping={"guest_transcription": "transcribed_speech"},
            )



            smach.StateMachine.add(
                "REPEAT_GET_NAME_AND_DRINK_GUEST_2",
                AskAndListen("Sorry, I didn't get that. What is your name and favourite drink?"),
                transitions={
                    "succeeded": "REPEAT_PARSE_NAME_AND_DRINK_GUEST_2",
                    "failed": "SAY_CONTINUE_2",
                },
            )

            smach.StateMachine.add(
                "REPEAT_PARSE_NAME_AND_DRINK_GUEST_2",
                ParseNameAndDrink("guest1"),
                transitions={
                    "succeeded": "GET_GUEST_ATTRIBUTES_GUEST_2",
                    "failed": "SAY_CONTINUE_2",
                },
                remapping={"guest_transcription": "transcribed_speech"},
            )


            smach.StateMachine.add(
                "SAY_CONTINUE_2",
                Say(text="Sorry, I didn't get that. I will carry on."),
                transitions={
                    "succeeded": "GET_GUEST_ATTRIBUTES_GUEST_2",
                    "aborted": "GET_GUEST_ATTRIBUTES_GUEST_2",
                    "preempted": "GET_GUEST_ATTRIBUTES_GUEST_2",
                },
            )

            smach.StateMachine.add(
                "GET_GUEST_ATTRIBUTES_GUEST_2",
                GetGuestAttributes("guest2"),
                transitions={
                    "succeeded": "SAY_FOLLOW_GUEST_2",
                    "failed": "SAY_FOLLOW_GUEST_2",
                },
            )

            smach.StateMachine.add(
                "SAY_FOLLOW_GUEST_2",
                Say(text="Please follow me, I will guide you to the other guests"),
                transitions={
                    "succeeded": "GO_TO_SEAT_LOCATION_GUEST_2",
                    "preempted": "failed",
                    "aborted": "failed",
                },
            )

            smach.StateMachine.add(
                "GO_TO_SEAT_LOCATION_GUEST_2",
                GoToLocation(seat_pose),
                transitions={
                    "succeeded": "SAY_WAIT_GUEST_2",
                    "failed": "SAY_WAIT_GUEST_2",
                },
            )

            smach.StateMachine.add(
                "SAY_WAIT_GUEST_2",
                Say(text="Please wait here on my left"),
                transitions={
                    "succeeded": "INTRODUCE_GUEST_2_TO_EVERYONE",
                    "preempted": "failed",
                    "aborted": "failed",
                },
            )

            # Look at guest 2 

            smach.StateMachine.add(
                "INTRODUCE_GUEST_2_TO_EVERYONE",
                Introduce(guest_to_introduce="guest2", everyone=True),
                transitions={
                    "succeeded": "INTRODUCE_HOST_TO_GUEST_2",
                    "failed": "INTRODUCE_HOST_TO_GUEST_2",
                },
            )


            # Check if host is sat where they are sat 
            # Look at the host 

            smach.StateMachine.add(
                "INTRODUCE_HOST_TO_GUEST_2",
                Introduce(guest_to_introduce="host", guest_to_introduce_to="guest2"),
                transitions={
                    "succeeded": "INTRODUCE_GUEST_1_TO_GUEST_2",
                    "failed": "INTRODUCE_GUEST_1_TO_GUEST_2",
                },
            )


            # Look at guest 1 
            smach.StateMachine.add(
                "INTRODUCE_GUEST_1_TO_GUEST_2",
                Introduce(guest_to_introduce="guest1", guest_to_introduce_to="guest2"),
                transitions={
                    "succeeded": "SEAT_GUEST_2",
                    "failed": "SEAT_GUEST_2",
                },
            )

            smach.StateMachine.add(
                "SEAT_GUEST_2",
                SeatGuest(seat_area),
                transitions={"succeeded": "GO_TO_FINISH_LOCATION", "failed": "GO_TO_FINISH_LOCATION"},
            )

            """
            Finish
            """
            smach.StateMachine.add(
                "GO_TO_FINISH_LOCATION",
                GoToLocation(wait_pose),
                transitions={
                    "succeeded": "SAY_FINISHED",
                    "failed": "SAY_FINISHED",
                },
            )
            smach.StateMachine.add(
                "SAY_FINISHED",
                Say(text="I am done."),
                transitions={
                    "succeeded": "succeeded",
                    "aborted": "failed",
                    "preempted": "succeeded",
                },
            )
