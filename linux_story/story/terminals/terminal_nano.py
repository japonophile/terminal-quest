#!/usr/bin/env python

#
# Copyright (C) 2014, 2015 Kano Computing Ltd.
# License: http://www.gnu.org/licenses/gpl-2.0.txt GNU General Public License v2
#
# A terminal for one of the challenges

import os
import threading
import time
import ast
from linux_story.story.terminals.terminal_echo import TerminalEcho
from linux_story.commands_real import nano


class TerminalNano(TerminalEcho):
    terminal_commands = ["ls", "cat", "cd", "mv", "echo", "mkdir", "nano"]
    SAVING_NANO_PROMPT = "Save modified buffer (ANSWERING \"No\" WILL DESTROY CHANGES) ? "
    SAVE_FILENAME = "File Name to Write"

    def __init__(self):

        ##############################################
        # nano variables
        self.nano_running = False
        self.nano_content = ""
        self.last_nano_prompt = ""
        self.ctrl_x = False
        self.on_nano_filename_screen = False
        self.exited_nano = True
        self.nano_x = 0
        self.nano_y = 0
        self.save_prompt_showing = False
        self.nano_filename = ""
        ################################################

        TerminalEcho.__init__(self)

    def do_nano(self, line):
        self.set_nano_running(True)

        # Read nano in a separate thread
        t = threading.Thread(target=self.try_and_get_nano_contents)
        t.daemon = True
        t.start()

        nano(self.real_path, line)

    ##################################################################
    # nano functions

    def set_nano_running(self, nano_running):
        '''Set this while nano is running
        '''
        self.nano_running = nano_running

    def get_nano_running(self):
        return self.nano_running

    def quit_nano(self):
        self.cancel_everything()
        self.set_nano_running(False)

    def set_nano_content(self, nano_content):
        '''Setter for the self.nano_content for this Step
        '''
        self.nano_content = nano_content

    def get_nano_content(self):
        '''Getter for the self.nano_content for this Step
        '''
        return self.nano_content

    def check_nano_content(self):
        '''These can be updated by the individual Step instances
        to do something with the changed values
        '''
        # Do something with the self.nano_content
        pass

    def set_nano_x(self, x):
        '''These can be updated by the individual Step instances
        to do something with the changed values
        '''
        self.nano_x = x

    def set_nano_y(self, y):
        '''These can be updated by the individual Step instances
        to do something with the changed values
        '''
        self.nano_y = y

    def set_ctrl_x_nano(self, ctrl_x):
        '''Setting whether the user pressed Ctrl X.
        ctrl_x is a bool.
        '''
        self.ctrl_x = ctrl_x

    def get_ctrl_x_nano(self):
        '''Getting whether the user pressed Ctrl X.
        '''
        return self.ctrl_x

    def set_last_prompt(self, last_prompt):
        '''Save last prompt.  This means we can see what the response
        is responding to.
        '''
        self.last_nano_prompt = last_prompt

    def set_on_filename_screen(self, on_filename_screen):
        self.on_nano_filename_screen = on_filename_screen

    def get_on_filename_screen(self):
        return self.on_nano_filename_screen

    def get_last_prompt(self):
        return self.last_nano_prompt

    def set_nano_content_values(self, content_dict):
        '''Set the x, y coordinates and the content.
        content_dict = {'x': 1, 'y': 2, 'text': ['line1', 'line2']}
        '''
        self.set_nano_x(content_dict["x"])
        self.set_nano_x(content_dict["y"])
        nano_content = "\n".join(content_dict["text"])
        self.set_nano_content(nano_content)
        self.set_save_prompt_showing(False)

    def cancel_everything(self):
        '''If the response of any prompt or statusbar is Cancel,
        then everything should be set to False
        '''
        self.set_save_prompt_showing(False)
        self.set_ctrl_x_nano(False)
        self.set_on_filename_screen(False)

    def set_save_prompt_showing(self, showing):
        self.save_prompt_showing = showing

    def get_save_prompt_showing(self):
        return self.save_prompt_showing

    def set_nano_filename(self, filename):
        self.nano_filename = filename

    def get_nano_filename(self):
        return self.nano_filename

    def try_and_get_nano_contents(self):
        try:
            self.get_nano_contents()
        except:
            self.send_text("\nFailed to get nano contents")

    def get_nano_contents(self):
        pipename = "/tmp/linux-story-nano-pipe"

        if not os.path.exists(pipename):
            os.mkfifo(pipename)

        f = open(pipename)

        while self.get_nano_running():
            time.sleep(0.1)
            line = None

            for line in iter(f.readline, ''):

                # Assuming we're receiving something of the form
                # {x: 1, y: 1, text: ["line1", "line2"]}
                # {response: this is the response message}

                data = ast.literal_eval(line)

                if "contents" in data:
                    self.cancel_everything()
                    value = data["contents"]

                    if self.get_nano_content() != self.end_text:
                        self.set_nano_content_values(value)

                if "statusbar" in data:
                    value = data["statusbar"]
                    # Everything is set to False, since anything could
                    # have been cancelled
                    if value.strip().lower() == "cancelled":
                        self.cancel_everything()

                if "response" in data:
                    value = data["response"]
                    # If the last prompt is the saving nano buffer prompt,
                    # then the user has tried to exit without saving
                    # his/her work.

                    if self.get_last_prompt() == self.SAVING_NANO_PROMPT:
                        if value.lower() == "cancel":
                            self.cancel_everything()

                        elif value.lower() == "yes":
                            # Starting to save.
                            # Bring up the relevent prompt about entering
                            # the filename and pressing Y.
                            # Set variable that says the player is on this
                            # screen
                            self.set_save_prompt_showing(True)
                            self.set_on_filename_screen(True)

                        elif value.lower() == "no":
                            # Exited nano and chose not to save
                            # This may not need to be recorded.
                            self.quit_nano()

                    elif self.get_last_prompt() == self.SAVE_FILENAME:
                        if value.lower() == "no":
                            self.quit_nano()
                        elif value.lower() == "cancel":
                            self.cancel_everything()

                        # TODO: not sure this is needed
                        elif value.lower() == "aborted enter":
                            self.cancel_everything()

                if "prompt" in data:
                    value = data["prompt"]
                    self.set_last_prompt(value)

                    if value == self.SAVE_FILENAME:
                        self.set_save_prompt_showing(False)
                        self.set_on_filename_screen(True)

                    # Do we set anything here?
                    elif value == self.SAVING_NANO_PROMPT:
                        self.set_save_prompt_showing(True)
                        self.set_on_filename_screen(False)

                if "saved" in data:
                    self.set_nano_filename(data["filename"])

                if "finish" in data:
                    self.quit_nano()

            else:
                if line:
                    # Run a check for self.nano_content.
                    # If this returns True, break out of the loop.
                    if self.check_nano_content():
                        return
