#!/usr/bin/python3
# coding=utf-8

#   Copyright 2026 EPAM Systems
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

""" Tool """


def make_room_names(labels):
    """ Make names of matching rooms """
    rooms = []
    #
    if "tasknode_task" in labels:
        room = f'room:tasknode_task:{labels["tasknode_task"]}'
        rooms.append(room)
    #
    if "task_result_id" in labels:
        room = f'room:task_result_id:{labels["task_result_id"]}'
        rooms.append(room)
    #
    if {"project", "report_id", "build_id"}.issubset(set(labels)):
        room = ":".join([
            "room",
            "project", labels["project"],
            "report_id", labels["report_id"],
            "build_id", labels["build_id"],
        ])
        rooms.append(room)
    #
    return rooms
