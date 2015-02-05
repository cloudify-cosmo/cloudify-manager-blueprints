########
# Copyright (c) 2014 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.


from exec_env import exec_globals


def get_task(tasks_file, task_name):
    with open(tasks_file) as tasks_code:
        exec_globs = exec_globals(tasks_file)
        try:
            exec(tasks_code, exec_globs)
        except Exception as e:
            raise RuntimeError(
                "Could not load '{0}' ({1}: {2})".format(
                    tasks_file, type(e).__name__, e))
        task = exec_globs.get(task_name)
        if not task:
            raise RuntimeError(
                "Could not find task '{0}' in '{1}'"
                .format(task_name, tasks_file))
        if not callable(task):
            raise RuntimeError(
                "'{0}' in '{1}' is not callable"
                .format(task_name, tasks_file))
        return task
