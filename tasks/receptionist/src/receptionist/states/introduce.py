"""
State machine that introduces the greeted guest to all other guests/host present in the 
seating area.

"""

import rospy
import smach
from smach import UserData
from lasr_skills import Say, LookToPoint
from typing import Dict, List, Any, Optional


def stringify_guest_data(
    guest_data: Dict[str, Any], guest_id: str, describe_features: bool
) -> str:
    """Converts the guest data for a specified guest into a string that can be used
    for the robot to introduce the guest to the other guests/host.

    Args:
        guest_data (Dict[str, Any]): guest data dictionary.
        guest_id (str): guest id key to use to get the guest data.

    Returns:
        str: string representation of the guest data.
    """

    relevant_guest_data = guest_data[guest_id]["attributes"]

    relevant_guest_data.setdefault(
        "clip_attributes",
        {
            "glasses": False,
            "hat": False,
            "long_hair": False,
            "short_sleeve_t_shirt": False,
        },
    )

    guest_str = f"{relevant_guest_data['name']}, their favourite drink is {relevant_guest_data['drink']}. "

    if not relevant_guest_data["detection"] or not describe_features:
        return guest_str

    if relevant_guest_data["clip_attributes"]["long_hair"]:
        guest_str += "They have long hair. "
    else:
        guest_str += "They have short hair. "

    t_shirt = (
        "short sleeve"
        if relevant_guest_data["clip_attributes"]["short_sleeve_t_shirt"]
        else "long sleeve"
    )

    if (
        relevant_guest_data["clip_attributes"]["glasses"]
        and relevant_guest_data["clip_attributes"]["hat"]
    ):
        guest_str += f"They are wearing a {t_shirt} t shirt, glasses and a hat. "
    elif (
        relevant_guest_data["clip_attributes"]["glasses"]
        and not relevant_guest_data["clip_attributes"]["hat"]
    ):
        guest_str += f"They are wearing a {t_shirt} t shirt and glasses and they are not wearing a hat. "
    elif (
        not relevant_guest_data["clip_attributes"]["glasses"]
        and relevant_guest_data["clip_attributes"]["hat"]
    ):
        guest_str += f"They wearing a {t_shirt} t shirt and hat and they are not wearing glasses. "
    elif (
        not relevant_guest_data["clip_attributes"]["glasses"]
        and not relevant_guest_data["clip_attributes"]["hat"]
    ):
        guest_str += f"They wearing a {t_shirt} t shirt and they are not wearing glasses or a hat. "
    return guest_str


class GetStrGuestData(smach.State):
    def __init__(self, guest_id: str, describe_features: bool = False):
        super().__init__(
            outcomes=["succeeded"],
            input_keys=["guest_data"],
            output_keys=["guest_str"],
        )
        self._guest_id = guest_id
        self._describe_features = describe_features

    def execute(self, userdata: UserData) -> str:
        guest_str = stringify_guest_data(
            userdata.guest_data, self._guest_id, self._describe_features
        )
        userdata.guest_str = guest_str
        return "succeeded"


class GetGuestName(smach.State):
    def __init__(self, guest_id: str):
        super().__init__(
            outcomes=["succeeded"],
            input_keys=["guest_data"],
            output_keys=["requested_name"],
        )
        self._guest_id = guest_id

    def execute(self, userdata: UserData) -> str:
        requested_name = userdata.guest_data[self._guest_id]["name"]
        userdata.requested_name = requested_name
        return "succeeded"


class GetIntroductionString(smach.State):
    def __init__(self):
        super().__init__(
            outcomes=["succeeded"],
            input_keys=["guest_str", "requested_name"],
            output_keys=["introduction_str"],
        )

    def execute(self, userdata: UserData) -> str:
        introduction_str = (
            f"Hello {userdata.requested_name}, this is {userdata.guest_str}."
        )
        userdata.introduction_str = introduction_str
        return "succeeded"


class Introduce(smach.StateMachine):
    def __init__(
        self,
        guest_to_introduce: str,
        guest_to_introduce_to: Optional[str] = None,
        describe_features: bool = False,
        everyone: Optional[bool] = False,
    ):
        super().__init__(
            outcomes=["succeeded", "failed"],
            input_keys=["guest_data", ""],
        )
        assert not (guest_to_introduce_to is None and not everyone)

        with self:
            if everyone:
                smach.StateMachine.add(
                    "GetStrGuestData",
                    GetStrGuestData(
                        guest_id=guest_to_introduce, describe_features=describe_features
                    ),
                    transitions={"succeeded": "SayIntroduce"},
                )
                smach.StateMachine.add(
                    "SayIntroduce",
                    Say(
                        format_str="Hello everyone, this is {}.",
                    ),
                    transitions={
                        "succeeded": "succeeded",
                        "preempted": "failed",
                        "aborted": "failed",
                    },
                    remapping={"placeholders": "guest_str"},
                )

            else:
                smach.StateMachine.add(
                    "GetStrGuestData",
                    GetStrGuestData(
                        guest_id=guest_to_introduce, describe_features=describe_features
                    ),
                    transitions={"succeeded": "GetGuestName"},
                )

                smach.StateMachine.add(
                    "GetGuestName",
                    GetGuestName(guest_id=guest_to_introduce_to),
                    transitions={"succeeded": "GetIntroductionString"},
                )

                smach.StateMachine.add(
                    "GetIntroductionString",
                    GetIntroductionString(),
                    transitions={"succeeded": "SayIntroduce"},
                    remapping={
                        "guest_str": "guest_str",
                        "requested_name": "requested_name",
                    },
                )

                smach.StateMachine.add(
                    "SayIntroduce",
                    Say(),
                    transitions={
                        "succeeded": "succeeded",
                        "preempted": "failed",
                        "aborted": "failed",
                    },
                    remapping={"text": "introduction_str"},
                )
