#!/usr/bin/env python3
import smach
import rospy

from gpsr.regex_command_parser import Configuration, gpsr_compile_and_parse
from gpsr.states import CommandSimilarityMatcher
from lasr_skills import AskAndListen, GoToLocation
from geometry_msgs.msg import Pose, Point, Quaternion


class ParseCommand(smach.State):
    def __init__(self, data_config: Configuration):
        """Takes in a string containing the command and runs the command parser
        that outputs a dictionary of parameters for the command.

        Args:
            data_config (Configuration): Configuration object containing the regex patterns
        """
        smach.State.__init__(
            self,
            outcomes=["succeeded", "failed"],
            input_keys=["raw_command"],
            output_keys=["parsed_command"],
        )
        self.data_config = data_config

    def execute(self, userdata):
        rospy.loginfo(f"Received command : {userdata.raw_command.lower()}")
        try:
            userdata.parsed_command = gpsr_compile_and_parse(
                self.data_config, userdata.raw_command.lower()
            )
        except Exception as e:
            rospy.logerr(e)
            return "failed"
        return "succeeded"


class CommandParserStateMachine(smach.StateMachine):

    class CheckResponse(smach.State):

        def __init__(self):
            smach.State.__init__(
                self,
                outcomes=["correct", "incorrect"],
                input_keys=["transcribed_speech"],
            )

        def execute(self, userdata):
            if "yes" in userdata.transcribed_speech.lower():  # TODO: make this smarter
                return "correct"
            return "incorrect"

    def __init__(
        self,
        data_config: Configuration,
        n_vecs_per_txt_file: int = 1177943,
        total_txt_files: int = 10,
    ):
        """State machine that takes in a command, matches it to a known command, and
        outputs the parsed command.

        Args:
            data_config (Configuration): Configuration object containing the regex patterns
            n_vecs_per_txt_file (int, optional): number of vectors in each gpsr txt
            file. Defaults to 1177943.
            total_txt_files (int, optional): total number of gpsr txt files. Defaults to 10.
        """
        self._command_counter = 0
        self._command_counter_threshold = 3

        smach.StateMachine.__init__(self, outcomes=["succeeded", "failed"])

        with self:

            start_pose_param = rospy.get_param("/gpsr/arena/start_pose")

            smach.StateMachine.add(
                "GO_TO_START",
                GoToLocation(
                    location=Pose(
                        position=Point(**start_pose_param["position"]),
                        orientation=Quaternion(**start_pose_param["orientation"]),
                    )
                ),
                transitions={
                    "succeeded": "ASK_FOR_COMMAND",
                    "failed": "ASK_FOR_COMMAND",
                },
            )

            smach.StateMachine.add(
                "ASK_FOR_COMMAND",
                AskAndListen(tts_phrase="Hello, please tell me your command."),
                transitions={"succeeded": "SAY_CHECK_COMMAND", "failed": "failed"},
                remapping={"transcribed_speech": "raw_command"},
            )

            smach.StateMachine.add(
                "ASK_FOR_COMMAND_AGAIN",
                AskAndListen(tts_phrase="Okay, please could you repeat your command?"),
                transitions={"succeeded": "SAY_CHECK_COMMAND", "failed": "failed"},
                remapping={"transcribed_speech": "raw_command"},
            )

            smach.StateMachine.add(
                "SAY_CHECK_COMMAND",
                AskAndListen(
                    tts_phrase_format_str="You said {}, is that correct? Please respond 'tiago, yes that's correct' or 'tiago, no that's incorrect'."
                ),
                transitions={
                    "correct": "PARSE_COMMAND",
                    "incorrect": "CHECK_COMMAND_COUNTER",
                },
                remapping={"placeholders": "raw_command"},
            )

            smach.StateMachine.add(
                "PARSE_COMMAND",
                ParseCommand(data_config),
                transitions={
                    "succeeded": "succeeded",
                    "failed": "failed",
                },
                remapping={"parsed_command": "parsed_command"},
            )

            smach.StateMachine.add(
                "CHECK_COMMAND_COUNTER",
                smach.CBState(
                    self._increment_counter, outcomes=["continue", "exceeded"]
                ),
                transitions={
                    "continue": "ASK_FOR_COMMAND_AGAIN",
                    "exceeded": "failed",  # TODO: use QR code here
                },
            )

            smach.StateMachine.add(
                "COMMAND_SIMILARITY_MATCHER",
                CommandSimilarityMatcher([n_vecs_per_txt_file] * total_txt_files),
                transitions={"succeeded": "PARSE_COMMAND", "failed": "failed"},
                remapping={
                    "command": "raw_command",
                    "matched_command": "raw_command",
                },
            )

    def _increment_counter(self, userdata):
        """Increment counter and determine whether command has been parsed over the number of times
        set by the threshold.
        """
        self._command_counter += 1
        if self._command_counter >= self._command_counter_threshold:
            self._command_counter = 0
            return "exceeded"
        return "continue"
