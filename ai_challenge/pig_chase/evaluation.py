# Copyright (c) 2017 Microsoft Corporation.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the "Software"), to deal in the Software without restriction, including without limitation the
#  rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of
# the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
#  TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# ===================================================================================================================

import os
import sys
from time import sleep

from common import parse_clients_args, ENV_AGENT_NAMES
from agent import PigChaseChallengeAgent
from common import ENV_AGENT_NAMES
from environment import PigChaseEnvironment, PigChaseSymbolicStateBuilder

# Enforce path
sys.path.insert(0, os.getcwd())
sys.path.insert(1, os.path.join(os.path.pardir, os.getcwd()))


class PigChaseEvaluator(object):

    def __init__(self, clients, agent_100k, agent_500k, state_builder):
        assert len(clients) >= 2, 'Not enough clients provided'

        self._clients = clients
        self._agent_100k = agent_100k
        self._agent_500k = agent_500k
        self._state_builder = state_builder
        self._accumulators = {'100k': [], '500k': []}

    def save(self, filepath):
        """
        Save the evaluation results in a JSON file 
        understandable by the leaderboard
        :param filepath: Path where to store the results file
        :return: 
        """
        from json import dumps
        from os.path import exists, join, pardir, abspath
        from os import makedirs
        from numpy import mean

        # Compute metrics
        metrics = {key: mean(buffer)
                   for key, buffer in self._accumulators.items()}

        try:
            filepath = abspath(filepath)
            parent = join(pardir, filepath)
            if not exists(parent):
                makedirs(parent)

            with open(filepath, 'w') as f_out:
                f_out.write(dumps(metrics))

        except Exception as e:
            print('Unable to save the results: %s' % e)

    def run(self):
        from multiprocessing import Process

        env = PigChaseEnvironment(self._clients, self._state_builder,
                                  role=1, randomize_positions=True)
        print('==================================')
        print('Starting evaluation of Agent @100k')

        p = Process(target=run_challenge_agent, args=(self._clients, ))
        p.start()
        sleep(5)
        agent_loop(self._agent_100k, env, self._accumulators['100k'])
        p.terminate()

        p = Process(target=run_challenge_agent, args=(self._clients, ))
        p.start()
        sleep(5)
        agent_loop(self._agent_500k, env, self._accumulators['500k'])
        p.terminate()


def run_challenge_agent(clients):
    builder = PigChaseSymbolicStateBuilder()
    env = PigChaseEnvironment(clients, builder, role=0,
                              randomize_positions=True)
    agent = PigChaseChallengeAgent(ENV_AGENT_NAMES[0])
    agent_loop(agent, env, None)


def agent_loop(agent, env, metrics_acc):
    agent_done = False
    reward = 0
    episode = 0
    obs = env.reset()

    while episode < 10:
        # check if env needs reset
        if env.done:
            print('Episode %d (%.2f)%%' % (episode, (episode / 100) * 10.))

            obs = env.reset()
            while obs is None:
                # this can happen if the episode ended with the first
                # action of the other agent
                print('Warning: received obs == None.')
                obs = env.reset()

            episode += 1

        # select an action
        action = agent.act(obs, reward, agent_done, is_training=True)
        # take a step
        obs, reward, agent_done = env.do(action)

        if metrics_acc is not None:
            metrics_acc.append(reward)
