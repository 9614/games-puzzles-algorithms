from __future__ import division
import time
import random
from math import sqrt, log
from copy import deepcopy
INF = float('inf')


class UctNode:
    def __init__(self, action=None, parent=None):
        self.action = action
        self.parent = parent
        self.N = 0  # times this position was visited
        self.Q = 0  # average reward (wins-losses) from this position
        self._children = []
        self.outcome = None

    def expand(self, game_state):
        for action in game_state.legal_actions():
            self._children.append(UctNode(action, self))

    def backup(self, score=0):
        """Update the node statistics on the path from the passed node to
        root to reflect the value of the given `simulation_statistics`.
        """
        self.N += 1
        self.Q += score
        if self.parent:
            self.parent.backup(score=-score)

    def value(self, explore=0):
        return self.lcb(explore=explore)

    def ucb(self, explore=0):
        """Return the upper confidence bound of this node.

        The parameter `explore` specifies how much the value should favor
        nodes that have yet to be thoroughly explored versus nodes that
        seem to have a high win rate. `explore` is set to zero by default
        which means that the action with the highest winrate will have
        the greatest value.
        """
        if self.N == 0:
            if explore == 0:
                return 0
            else:
                return INF
        else:
            return (self.Q / self.N + explore
                    * sqrt(2 * log(self.parent.N) / self.N))

    def lcb(self, explore=0):
        """Return the lower confidence bound of this node.

        The parameter `explore` specifies how much the value should favor
        nodes that have yet to be thoroughly explored versus nodes that
        seem to have a high win rate. `explore` is set to zero by default
        which means that the action with the highest winrate will have
        the greatest value.
        """
        # unless explore is set to zero, maximally favor unexplored nodes
        if self.N == 0:
            return 0
        else:
            return (self.Q / self.N - explore
                    * sqrt(2 * log(self.parent.N) / self.N))

    def child_nodes(self):
        return self._children

    def is_leaf(self):
        return len(self._children) < 1

    def is_root(self):
        return self.parent is None

    def favorite_child(self, exploration=0):
        max_value = max(
            self.child_nodes(),
            key=lambda n: n.value(exploration)).value(exploration)
        max_nodes = [n for n in self.child_nodes() if (n.value(exploration)
                                                       == max_value)]
        return random.choice(max_nodes)

    def __len__(self):
        count = 1
        for child in self.child_nodes():
            count += len(current_node)
        return count


class MctsAgent(object):
    class Mcts(object):
        class InfiniteSearch(Exception): pass
        class TimeIsUp(Exception): pass

        @classmethod
        def with_same_parameters(self, other):
            return self(node_generator=other._node_generator,
                        exploration=other._exploration)

        def __init__(self, node_generator=UctNode, exploration=1):
            self._node_generator = node_generator
            self._exploration = exploration
            self.root = None

        def reset(self):
            self.root = None

        def good_action(self,
                        game_state,
                        time_available=-1,
                        num_iterations=-1):
            """Return a good action to play in `game_state`.

            Parameters:
            `game_state`: The state of the game for which an action is
            requested. Must adhere to the generic game state interface
            described by `games_puzzles_algorithms.games.fake_game_state`.
            `time_available`: The time allotted to search for a good action.
            Negative values imply that there is no time limit.
            Setting this to zero will ensure that an action is selected
            uniformly at random.
            `num_iterations`: The number of search iterations (rollouts) to
            complete. Negative values imply that there is not iteration
            limit. Setting this to zero will ensure that an action is selected
            uniformly at random.

            `time_available` and `num_iterations` cannot both be negative.
            """
            self.search(game_state,
                        time_available=time_available,
                        num_iterations=num_iterations)
            return self._root.favorite_child().action

        def search(self, root_state, time_available=-1, num_iterations=-1):
            """Execute MCTS from `root_state`.

            Parameters:
            `root_state`: The state of the game from which to search.
            Must adhere to the generic game state interface
            described by `games_puzzles_algorithms.games.fake_game_state`.
            `time_available`: The time allotted to search for a good action.
            Negative values imply that there is no time limit.
            Setting this to zero will ensure that no search is done.
            `num_iterations`: The number of search iterations (rollouts) to
            complete. Negative values imply that there is not iteration
            limit. Setting this to zero will ensure that no search is done.

            `time_available` and `num_iterations` cannot both be negative.
            """
            if time_available < 0 and num_iterations < 0:
                raise self.InfiniteSearch(
                    "Must specify a time or iteration limit.")
            if root_state.is_terminal(): return None

            start_time = time.clock()

            my_root_state = deepcopy(root_state)

            self._root = self._node_generator()
            self._root.expand(root_state)

            num_iterations_completed = 0

            def time_is_available():
                return (time.clock() - start_time) < time_available

            while num_iterations_completed < num_iterations:
                try:
                    node, game_state, num_actions = self.select_node(
                        self._root,
                        my_root_state,
                        time_is_available=time_is_available)
                except self.TimeIsUp:
                    break
                node.backup(**self.roll_out(game_state))
                for _ in range(num_actions):
                    game_state.undo()
                num_iterations_completed += 1

            # stderr.write("Ran "+str(num_iterations_completed)+ " rollouts
            # in " +\
            #     str(time.clock() - self.start_time)+" sec\n")
            # stderr.write("Node count: "+str(self.tree_size())+"\n")

        def node_value(self, n):
            return n.ucb(self._exploration)

        def select_node(self,
                        node,
                        game_state,
                        time_is_available=lambda: True):
            num_actions = 0
            my_child_nodes = node.child_nodes()
            while my_child_nodes:
                if not time_is_available(): raise self.TimeIsUp()

                max_value = self.node_value(
                    max(
                        my_child_nodes,
                        key=lambda n: self.node_value(n)
                    )
                )
                max_nodes = [n for n in my_child_nodes if (self.node_value(n)
                                                           == max_value)]
                node = random.choice(max_nodes)

                game_state.play(node.action)
                num_actions += 1

                # If some child node has not been explored select it
                # before expanding other children
                if node.N == 0:
                    return (node, game_state, num_actions)
                else:
                    my_child_nodes = node.child_nodes()

            # If we reach a leaf node generate its children and
            # return one of them
            if node.expand(game_state):
                node = random.choice(node.child_nodes())
                game_state.play(node.action)
            return (node, game_state, num_actions)

        def roll_out(self, state, player_of_interest):
            """
            Simulate a play-out from the passed game state, `state`.

            Return roll out statistics from the perspective of
            `player_of_interest`.
            """
            if state.is_terminal():
                return {'score': state.score(player_of_interest)}
            else:
                outcome = None
                for action in state.legal_actions():
                    for _ in state.do_after_play(action):
                        outcome = self.roll_out(state, player_of_interest)
                return outcome

        def __len__(self):
            """Return the number of nodes in search tree."""
            return len(self.root)

    def __init__(self,
                 node_generator=UctNode,
                 exploration=1,
                 num_iterations=-1):
        self.num_search_iterations = num_iterations
        self._search_tree = self.Mcts(node_generator, exploration)

    def select_action(self, game_state, time_available=-1):
        return self._search_tree.good_action(
             game_state,
             time_available=time_available,
             num_iterations=self.num_search_iterations)

    def reset(self): self._search_tree.reset()