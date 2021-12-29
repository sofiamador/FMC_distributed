import enum
import random
import sys
import abc
from abc import ABC
from datetime import time
import numpy as np

from typing import List

global solver_debug


class Status(enum.Enum):
    """
    Enum that represents the status of the player in the simulation
    """
    IDLE = 0
    ON_MISSION = 1
    TO_MISSION = 2


class Entity:
    """
    Class that represents a basic entity in the simulation
    """

    def __init__(self, id_, location, last_time_updated=0):
        """
        :param id_: The id of the entity
        :type  id_: str
        :param location: The location of the entity. A list of of coordination.
        :type location: list of floats
        :param last_time_updated:

        """
        self.id_ = id_
        self.location = location
        self.neighbours = []
        self.last_time_updated = last_time_updated

    def update_time(self, tnow):
        if tnow >= self.last_time_updated:
            self.last_time_updated = tnow
        else:
            raise Exception("last time updated is higher than tnow")

    def create_neighbours_list(self, entities_list: list, f_are_neighbours):
        """
        Method that populates the neighbours list of the entity. It accepts list of potential neighbours
        and a function that returns whether a pair of entities are neighbours
        :param entities_list: List of entities that are potential neighbours
        :type entities_list: list ot Entity
        :param f_are_neighbours: Function that receives 2 entities and return true if they can be neighbours
        :type f_are_neighbours: function
        :return: None
        """
        raise NotImplementedError

    def __hash__(self):
        return hash(self.id_)

    def __eq__(self, other):
        return self.id_ == other.id_

    def __str__(self):
        return str(self.id_)


def calculate_distance_input_location(location1, location2):
    """
    Calculates the distance between two entities. Each entity must have a location property.
    :param location1:first location
    :type location1: list
    :param location2:second location
    :type location2: list
    :return: Euclidean distance between two entities
    :rtype: float
    """

    distance = 0
    n = min(len(location1), len(location2))
    for i in range(n):
        distance += (location1[i] - location2[i]) ** 2

    return distance ** 0.5


def calculate_distance(entity1: Entity, entity2: Entity):
    """
    Calculates the distance between two entities. Each entity must have a location property.
    :param entity1:first entity
    :type entity1: Entity
    :param entity2:second entity
    :type entity1: Entity
    :return: Euclidean distance between two entities
    :rtype: float
    """
    location1 = entity1.location
    location2 = entity2.location
    return calculate_distance_input_location(location1, location2)


def are_neighbours(entity1: Entity, entity2: Entity):
    """
    The functions checks if the entities (players) can be neighbours
    :param entity1: first entity
    :type entity1: Entity
    :param entity2: second entity
    :type entity1: Entity
    :return: bool
    """
    return True


def is_player_can_be_allocated_to_task(task, player):
    """
    Function that checks if the player can be allocated to an task according to player's abilities and required abilities
    to the task.
    :param task: The task that is checked.
    :type task: TaskSimple
    :param player: The player that is checked if it suitable for the task according to hos abilities.
    :return:
    """
    # for mission in task.missions_list:
    #    for ability in mission.abilities:
    #        if ability in player.abilities:
    #            return True
    return True


class AbilitySimple:
    """
       Class that represents a simple ability that the missions require and the players have
    """

    def __init__(self, ability_type, ability_name=None):
        """
        :param ability_type: The type of the ability
        :type ability_type: int
        :param ability_name: The name of the ability. If the name is not given it will be set to the type of the ability
        (casted to str) 
        :type ability_name: str
        """

        self.ability_type = ability_type
        self.ability_name = ability_name
        if self.ability_name is None:
            self.ability_name = str(ability_type)

    def __hash__(self):
        return hash(self.ability_type)

    def __eq__(self, other):
        return self.ability_type == other.ability_type

    def __str__(self):
        return self.ability_name

    def get_ability_type(self):
        return self.ability_type


class MissionMetrics:

    def __init__(self):
        pass


class PlayerSimple(Entity):
    """
    Class that represents a basic player in the simulation
    """

    def __init__(self, id_, current_location, speed, status=Status.IDLE,
                 abilities=None, tnow=0, base_location=None, productivity=1):
        """
        :param id_: The id of the player
        :type  id_: str
        :param current_location: The location of the player
        :type current_location: list of float
        :param status: The status of the player
        :type  status: Status
        :param abilities: abilities of the player
        :type  abilities: set of AbilitySimple
        :param current_task: The current task that was allocated to player. If the the player is idle this field will be None.
        :type current_task: TaskSimple
        :param current_mission: The current sub-task of the player. If the the player is idle this field will be None.
        :type current_mission: MissionSimple

        """
        Entity.__init__(self, id_, current_location, tnow)
        if abilities is None:
            abilities = [AbilitySimple(ability_type=0)]
        self.speed = speed
        self.status = status
        self.abilities = abilities
        self.current_task = None
        self.current_mission = None
        self.tasks_responsible = []
        self.neighbours = []
        self.base_location = base_location
        self.productivity = productivity
        self.schedule = []  # [(task,mission,time)]

    def update_status(self, new_status: Status, tnow: float) -> None:
        """
        Updates the status of the player
        :param new_status:the new status of the player
        :param tnow: the time when status of the player is updated
        :return:None
        """
        self.status = new_status
        self.update_time(tnow)

    def update_location(self, location, tnow):
        """
        Updates the location of the player
        :param location:
        :param tnow:
        :return:
        """
        self.location = location
        self.update_time(tnow)

    def create_neighbours_list(self, players_list, f_are_neighbours=are_neighbours):
        """
        creates neighbours list of players
        :param players_list:
        :param f_are_neighbours:
        :return:None
        """
        for p in players_list:
            if self.id_ != p.id_ and f_are_neighbours(self, p):
                self.neighbours.append(p)

    def calculate_relative_location(self, tnow):
        if self.status == Status.TO_MISSION:
            travel_time = calculate_distance(self, self.current_task) / self.speed
            time_delta = tnow - self.last_time_updated
            ratio_of_the_time = time_delta / travel_time
            for i in range(len(self.location)):
                self.location[i] = self.location[i] + (
                        self.current_task.location[i] - self.location[i]) * ratio_of_the_time
            self.update_time(tnow)


class MissionSimple:
    """
    Class that represents a simple mission (as a part of the task)
    """

    def __init__(self, mission_id, initial_workload, arrival_time_to_the_system,
                 abilities=(AbilitySimple(ability_type=0)),
                 min_players=1, max_players=1):
        """
        Simple mission constructor
        :param mission_id: Mission's id
        :type mission_id: str
        :param initial_workload: The required workload of the mission (in seconds)
        :type initial_workload: float
        :param arrival_time_to_the_system: The time that task (with the mission)  arrived
        :param abilities:
        :param min_players:
        :param max_players:
        """

        self.mission_id = mission_id
        self.abilities = abilities
        self.min_players = min_players
        self.max_players = max_players
        self.initial_workload = initial_workload
        self.remaining_workload = initial_workload
        self.players_allocated_to_the_mission = []
        self.players_handling_with_the_mission = []
        self.is_done = False
        self.arrival_time_to_the_system = arrival_time_to_the_system
        self.last_updated = arrival_time_to_the_system

        #####----------

        self.x0_simulation_time_mission_enter_system = self.arrival_time_to_the_system
        self.x1_simulation_time_first_player_arrive = None # update when mission finish
        self.x2_delay = None #will be update x1-x0 when mission finish


        self.simulation_time_of_first_agent = None
        self.delay = None

        self.abandonment_counter = 0
        self.total_abandonment_counter = 0

        self.simulation_time_finished = None
        self.time_take_to_finish = None
        self.finish_optimal_absolute_time = self.initial_workload/self.max_players

        # optimal_time_of_missions = []
        # for mission in self.missions_list:
        #    mission.
        # self.task_finish_optimal_time = max()

    def update_workload(self, tnow):
        delta = tnow - self.last_updated
        self.workload_updating(delta)
        if self.remaining_workload < 0.0001:
            self.is_done = True
        self.last_updated = tnow

    def workload_updating(self, delta):
        productivity = 0
        for p in self.players_handling_with_the_mission:
            productivity += p.productivity
        self.remaining_workload -= delta * productivity
        if self.remaining_workload < -0.01:
            raise Exception("Negative workload to mission" + str(self.mission_id))

    def add_allocated_player(self, player):
        if player in self.players_allocated_to_the_mission:
            raise Exception("Double allocation of the same player to one mission: player " + str(player.id_))
        self.players_allocated_to_the_mission.append(player)

    def add_handling_player(self, player):
        if player in self.players_handling_with_the_mission:
            raise Exception("Double handling of the the same player to one mission" + str(self.mission_id))
        self.players_handling_with_the_mission.append(player)

    def remove_allocated_player(self, player):
        if player not in self.players_allocated_to_the_mission:
            raise Exception("Allocated player is not exist in the mission" + str(self.mission_id))
        self.players_allocated_to_the_mission.remove(player)

    def remove_handling_player(self, player):
        if player.status == Status.ON_MISSION:
            if player not in self.players_handling_with_the_mission:
                raise Exception("Allocated player is not exist in the mission")
            self.players_handling_with_the_mission.remove(player)
        self.remove_allocated_player(player)

    def __hash__(self):
        return hash(self.mission_id)

    def __eq__(self, other):
        return self.mission_id == other.mission_id

    def __str__(self):
        return str(self.mission_id)


class TaskSimple(Entity):
    """
    Class that represents a simple task in the simulation
    """

    def __init__(self, id_, location, importance, missions_list: list, arrival_time=0):
        """
        :param id_: The id of the task
        :type  id_: str
        :param location: The location of the task
        :type location: list of float
        :param importance: The importance of the task
        :type importance: int
        :param missions_list: the missions of the
        :param type_: The type of the task
        :type type_: int
        :param player_responsible, simulation will assign a responsible player to perform that algorithmic task
        computation and message delivery
        """
        Entity.__init__(self, id_, location, arrival_time)
        self.missions_list = missions_list
        self.player_responsible = None
        self.importance = importance
        self.arrival_time = arrival_time #arrival time to system
        self.done_missions = []
        self.is_done = False

        #----------------
        #self.simulation_time_of_first_agent = None
        #self.delay = None

        #self.abandonment_counter = 0
        #self.total_abandonment_counter = 0

        #self.simulation_time_of_task_finished = None
        #optimal_time_of_missions = []
        #for mission in self.missions_list:
        #    mission.
        #self.task_finish_optimal_time = max()


    def create_neighbours_list(self, players_list,
                               f_is_player_can_be_allocated_to_mission=is_player_can_be_allocated_to_task):
        """
        Creates 
        :param players_list:
        :param f_is_player_can_be_allocated_to_mission:
        :return:
        """
        for a in players_list:
            if f_is_player_can_be_allocated_to_mission(self, a):
                self.neighbours.append(a.id_)

    def update_workload_for_missions(self, tnow):

        for m in self.missions_list:
            m.update_workload(tnow)
        self.update_time(tnow)

    def mission_finished(self, mission):
        #try:
        mission.is_done = True
        self.missions_list.remove(mission)
        self.done_missions.append(mission)
        if len(self.missions_list) == 0:
            self.is_done = True
        #except:
        #    print("from sim comp line 380")


def amount_of_task_responsible(player):
    return len(player.tasks_responsible)


def find_and_allocate_responsible_player(task: TaskSimple, players):
    distances = []
    for player in players:
        # for mission in task.missions_list:
        #     for ability in mission.abilities:
        #         if ability in player.abilities:
        distances.append(calculate_distance(task, player))

    min_distance = min(distances)

    players_min_distances = []

    for player in players:
        if calculate_distance(task, player) == min_distance:
            # for mission in task.missions_list:
            #     for ability in mission.abilities:
            #         if ability in player.abilities:
            players_min_distances.append(player)

    selected_player = min(players_min_distances, key=amount_of_task_responsible)
    selected_player.tasks_responsible.append(task)
    task.player_responsible = selected_player


class MapSimple:
    """
    Class that represents the map for the simulation. The tasks and the players must be located using generate_location
    method. The simple map is in the shape of rectangle (with width and length parameters).
    """

    def __init__(self, number_of_centers=3, seed=1, length=9.0, width=9.0):
        """
        :param number_of_centers: number of centers in the map. Each center represents a possible base for the player.
        :type: int
        :param seed: seed for random object
        :type: int
        :param length: The length of the map
        :type: float
        :param width: The length of the map
        :type: float
        """
        self.length = length
        self.width = width
        self.rand = random.Random(seed)
        self.centers_location = []
        for _ in range(number_of_centers):
            self.centers_location.append(self.generate_location())

    def generate_location(self):
        """
        :return: random location on the map
        :rtype: list of float
        """
        x1 = self.rand.random()
        x2 = self.rand.random()
        return [self.width * x1, self.length * x2]

    def get_center_location(self):
        return self.rand.choice(self.centers_location)


class MapHubs(MapSimple):
    def __init__(self, number_of_centers=3, seed=1, length_y=9.0, width_x=9.0, sd_multiplier=0.5):
        MapSimple.__init__(self, number_of_centers, seed, length_y, width_x)
        self.sd_multiplier = sd_multiplier

    def generate_location_gauss_around_center(self):
        rand_center = self.get_center_location()
        valid_location = False
        ans = 0
        while not valid_location:
            ans = self.generate_gauss_location(rand_center)
            if 0 < ans[0] < self.width and 0 < ans[1] < self.length:
                valid_location = True
        return ans

    def generate_gauss_location(self, rand_center):
        x_center = rand_center[0]
        x_sd = self.width * self.sd_multiplier
        rand_x = self.rand.gauss(mu=x_center, sigma=x_sd)

        y_center = rand_center[1]
        y_sd = self.length * self.sd_multiplier
        rand_y = self.rand.gauss(mu=y_center, sigma=y_sd)
        return [rand_x, rand_y]


class PlayerGenerator(ABC):
    def __init__(self, map_=MapSimple(seed=1), seed=1):
        """

        :param map_:
        :param seed:
        """
        self.map = map_
        self.random = random.Random(seed)

    @abc.abstractmethod
    def get_player(self):
        """
        :rtype: TaskSimple
        """
        return NotImplementedError


class TaskGenerator(ABC):
    def __init__(self, map_=MapSimple(seed=1), seed=1):
        """

        :param map_:
        :param seed:
        """
        self.map = map_
        self.random = random.Random(seed)
        self.rnd_numpy = np.random.default_rng(seed=seed)

    @abc.abstractmethod
    def get_task(self, tnow):
        """
        :rtype: TaskSimple
        """
        return NotImplementedError

    @abc.abstractmethod
    def time_gap_between_tasks(self):
        return NotImplementedError
