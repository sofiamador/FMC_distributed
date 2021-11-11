import copy
import math
import random
import matplotlib.pyplot as plt

from Allocation_Solver_Fisher import FisherAsynchronousSolver
from Communication_Protocols import CommunicationProtocol, CommunicationProtocolUniform, CommunicationProtocolDefault, \
    CommunicationProtocolDistanceBaseDelayPois, CommunicationProtocolMessageLossConstant, \
    CommunicationProtocolDistanceBaseMessageLoss, CommunicationProtocolDistanceBaseDelayPoisAndLoss, \
    CommunicationProtocolMessageLossConstantAndUniform, CommunicationProtocolPois
from Data_fisher_market import get_data_fisher
from TSG_rij import calculate_rij_tsg
from TaskStaticGenerator import SingleTaskGeneratorTSG, SinglePlayerGeneratorTSG

plt.style.use('seaborn-whitegrid')
import pandas as pd
from Simulation import MapHubs, TaskArrivalEvent, find_responsible_agent, TaskSimple, AbilitySimple
from Allocation_Solver_Abstract import AllocationSolver
import string

simulation_reps = None
termination_time_constant = 50000
map_width = None
map_length = None
data_jumps = None
current_ro = None

process_debug = True

def rand_id_str(rand):
    ans = ''.join(rand.choices(string.ascii_uppercase + string.digits, k=10))
    return ans


def create_ability_dict(ability_dict):
    ability_dict[0] = AbilitySimple(ability_type=0, ability_name="Basic")
    ability_dict[1] = AbilitySimple(ability_type=1, ability_name="Interview")
    ability_dict[2] = AbilitySimple(ability_type=2, ability_name="First-Aid")
    ability_dict[3] = AbilitySimple(ability_type=3, ability_name="Observe")
    ability_dict[4] = AbilitySimple(ability_type=4, ability_name="Gun")
    return ability_dict


class TaskArrivalEventStatic(TaskArrivalEvent):
    def __init__(self, task, players, solver: AllocationSolver):
        self.time = 0
        self.task = task
        self.players = players
        self.solver = solver

    def handle_event(self, simulation):
        self.solver.add_task_to_solver(self.task)
        simulation.solve()


def get_task_importance(task: TaskSimple):
    return task.importance


class SimulationStatic():
    def __init__(self, rep_number, solver: AllocationSolver, map_length, map_width, players_required_ratio=0.5,
                 create_ability_dict=create_ability_dict, tasks_per_center=2, number_of_centers=2):
        self.create_ability_dict = create_ability_dict
        self.players_required_ratio = players_required_ratio
        self.rand = random.Random(rep_number * 17)
        self.seed_number = rep_number
        self.solver = solver
        self.map = MapHubs(seed=self.seed_number * 1717, number_of_centers=number_of_centers, sd_multiplier=0.05,
                           length_y=map_length, width_x=map_width)

        self.tasks_per_center = tasks_per_center

        self.tasks = []
        self.create_tasks()

        self.players = []
        self.create_players_given_ratio()
        # self.draw_map() # show map of tasks location for debug

    def add_solver(self, solver: AllocationSolver):
        self.solver = solver

        for task in self.tasks:
            find_responsible_agent(task=task, players=self.players)

        for player in self.players:
            self.solver.add_player_to_solver(player)

        for task in self.tasks:
            self.solver.add_task_to_solver(task)

    def create_tasks(self):
        total_number_of_tasks = self.tasks_per_center * len(self.map.centers_location)
        for _ in range(total_number_of_tasks):
            task = SingleTaskGeneratorTSG(rand=self.rand, map_=self.map).random_task
            self.tasks.append(task)

            # SingleTaskStaticPoliceGenerator(rand=self.rand, map=self.map,
            #                                create_ability_dict=self.create_ability_dict).random_task

    def draw_map(self):
        x = []
        y = []
        importance = []
        name = []
        type_ = []

        for t in self.tasks:
            x.append(t.location[0])
            y.append(t.location[1])
            type_.append("task")

        for cent in self.map.centers_location:
            x.append(cent[0])
            y.append(cent[1])
            type_.append("center")

        for player in self.players:
            x.append(player.location[0])
            y.append(player.location[1])
            type_.append("player")

        df = pd.DataFrame(dict(x=x, y=y, type_=type_))

        fig, ax = plt.subplots()

        colors = {'center': 'red', 'task': 'blue', 'player': 'green'}

        ax.scatter(df['x'], df['y'], c=df['type_'].map(colors))

        # plt.scatter(x, y, color='black')
        plt.xlim(0, self.map.width)
        plt.ylim(0, self.map.length)
        plt.show()

    def create_players_given_ratio(self):
        number_players_required = self.get_number_of_tasks_required()
        number_of_players = math.floor(self.players_required_ratio * number_players_required)
        self.tasks = sorted(self.tasks, key=get_task_importance, reverse=True)
        self.create_players(number_of_players)
        self.set_tasks_neighbors()

    def set_tasks_neighbors(self):
        ids_ = []
        for player in self.players:
            ids_.append(player.id_)
        for task in self.tasks:
            task.create_neighbours_list(ids_)

    def create_players(self, number_of_players, dict_input={1: 14, 4: 6, 8: 1}):
        dict_copy = copy.deepcopy(dict_input)
        while number_of_players != 0:

            if self.all_values_are_zero(dict_copy.values()):
                dict_copy = copy.deepcopy(dict_input)
            else:
                for k, v in dict_copy.items():
                    if v != 0:
                        player = SinglePlayerGeneratorTSG(rand=self.rand, map_=self.map, ability_number=k,
                                                          is_static_simulation=True).rnd_player
                        self.players.append(player)
                        dict_copy[k] = v - 1
                        number_of_players -= 1
                        if number_of_players == 0:
                            break

    def all_values_are_zero(self, values):
        for v in values:
            if v != 0:
                return False
        return True

    def get_number_of_tasks_required(self):
        ans = 0
        for task in self.tasks:
            for mission in task.missions_list:
                ans += mission.max_players
        return ans


def f_termination_condition_constant_mailer_nclo(agents_algorithm, mailer,
                                                 termination_time_constant=termination_time_constant):
    if mailer.time_mailer.get_clock() < termination_time_constant:
        return False
    return True


def find_relevant_measure_from_dict(nclo, data_map_of_measure):
    while nclo != 0:
        if nclo in data_map_of_measure.keys():
            return data_map_of_measure[nclo]
        else:
            nclo = nclo - 1
    return 0


def get_data_prior_statistic(data_):
    data_keys = get_data_fisher().keys()
    data_prior_statistic = {}
    for measure_name in data_keys:
        data_prior_statistic[measure_name] = {}
        for nclo in range(0, termination_time_constant, data_jumps):
            data_prior_statistic[measure_name][nclo] = []
            for rep in range(simulation_reps):
                data_of_rep = data_[rep]
                data_map_of_measure = data_of_rep[measure_name]
                the_measure = find_relevant_measure_from_dict(nclo, data_map_of_measure)
                data_prior_statistic[measure_name][nclo].append(the_measure)
    return data_prior_statistic


def calc_avg(data_prior_statistic):
    data_keys = get_data_fisher().keys()
    ans = {}
    for key in data_keys:
        ans[key] = {}
        data_per_nclo = data_prior_statistic[key]
        for nclo, measure_list in data_per_nclo.items():
            ans[key][nclo] = sum(measure_list) / len(measure_list)
    return ans


def organize_data_to_dict(data_prior_statistic):
    ans = {}

    for title, nclo_dict in data_prior_statistic.items():
        nclo_list = []
        for nclo, single_measure in nclo_dict.items():
            nclo_list.append(nclo)
        ans["NCLO"] = nclo_list
        break

    for title, nclo_dict in data_prior_statistic.items():
        measure_list = []
        for nclo, single_measure in nclo_dict.items():
            measure_list.append(single_measure)
        ans[title] = measure_list

    return ans


def organize_data_to_dict_for_avg(data_avg):
    ans = {}

    for title, nclo_dict in data_avg.items():
        nclo_list = []
        for nclo, single_measure in nclo_dict.items():
            nclo_list.append(nclo)
        ans["NCLO"] = nclo_list
        break

    for title, nclo_dict in data_avg.items():
        measure_list = []
        for nclo, single_measure in nclo_dict.items():
            measure_list.append(single_measure)
        ans[title] = measure_list

    return ans


def create_data_statistics(data_):
    # data_prior_statistic = get_data_prior_statistic(data_)
    # return organize_data_to_dict(data_prior_statistic)

    data_prior_statistic = get_data_prior_statistic(data_)
    data_avg = calc_avg(data_prior_statistic)
    return organize_data_to_dict_for_avg(data_avg)


def create_data_communication(amount_of_lines):
    protocol_name_list = []
    timestamp_list = []

    for _ in range(amount_of_lines):
        protocol_name_list.append(communication_protocol.name)
        if communication_protocol.is_with_timestamp:
            timestamp_list.append("TS")
        else:
            timestamp_list.append("No_TS")

    ans = {}
    ans["Communication Protocol"] = protocol_name_list
    ans["timestamp"] = timestamp_list
    return ans


def run_single_simulation(rep_num, players_required_ratio, tasks_per_center, number_of_centers, map_length, map_width,
                          ro=1):
    communication_protocol.set_seed(rep_num)

    ss = SimulationStatic(rep_number=rep_num, solver=None, map_length=map_length, map_width=map_width,
                          players_required_ratio=players_required_ratio
                          , tasks_per_center=tasks_per_center, number_of_centers=number_of_centers)

    fisher_solver = FisherAsynchronousSolver(
        f_termination_condition=f_termination_condition_constant_mailer_nclo,
        f_global_measurements=get_data_fisher(),
        f_communication_disturbance=communication_protocol.get_communication_disturbance,
        future_utility_function=calculate_rij_tsg,
        is_with_timestamp=communication_protocol.is_with_timestamp,
        ro=ro)

    ss.add_solver(fisher_solver)
    fisher_solver.solve()
    return fisher_solver.get_measurements()


def create_data_simulation(amount_of_lines, players_required_ratio, tasks_per_center, number_of_centers, algo_name):
    algo_name_list = []
    players_required_ratio_list = []
    tasks_per_center_list = []
    number_of_centers_list = []

    for _ in range(amount_of_lines):
        algo_name_list.append(algo_name)
        players_required_ratio_list.append(players_required_ratio)
        tasks_per_center_list.append(tasks_per_center)
        number_of_centers_list.append(number_of_centers)
    ans = {}
    ans["Algorithm"] = algo_name_list
    ans["Players Required Ratio"] = players_required_ratio_list
    ans["Tasks Per Center"] = tasks_per_center_list
    ans["Number Of Centers"] = number_of_centers_list
    return ans


def get_data_single_output_dict():
    data_statistics = create_data_statistics(data_)
    amount_of_lines = len(data_statistics["NCLO"])
    data_communication = create_data_communication(amount_of_lines)
    data_simulation = create_data_simulation(amount_of_lines, players_required_ratio, tasks_per_center,
                                             number_of_centers, algo_name)
    data_output = {}
    for k, v in data_simulation.items():
        data_output[k] = v

    for k, v in data_communication.items():
        data_output[k] = v

    for k, v in data_statistics.items():
        data_output[k] = v

    return data_output


def create_communication_protocols(is_with_timestamp,perfect_communication,ubs, constants_for_distances, constants_for_distances_and_loss, p_losses,distance_loss_ratios,p_loss_and_ubs,poises):
    ans = []



    for p_ub in p_loss_and_ubs:
        p = p_ub[0]
        ub = p_ub[1]
        name = "U(0," + str(ub) + "),p_loss"+str(p)
        ans.append(CommunicationProtocolMessageLossConstantAndUniform(name=name, is_with_timestamp=is_with_timestamp, p_loss=p,UB=ub))

    for pois in poises:
        name = "pois(" + str(pois) + ")"
        ans.append(CommunicationProtocolPois(name=name, is_with_timestamp=is_with_timestamp, lambda_ = pois))

    for ub in ubs:
        name = "U(0," + str(ub) + ")"
        ans.append(CommunicationProtocolUniform(name=name, is_with_timestamp=is_with_timestamp, UB=ub))

        # if only_with_timestamp:
        #     ans.append(CommunicationProtocolUniform(name=name, is_with_timestamp=True, UB=ub))
        # else:
        #     if ub != 0:
        #         for bool in [True, False]:
        #             ans.append(CommunicationProtocolUniform(name=name, is_with_timestamp=bool, UB=ub))
        #     else:
        #         ans.append(
        #             CommunicationProtocolUniform(name=name, is_with_timestamp=False, UB=ub))

    for constant_ in constants_for_distances:
        name = "Pois(Dij_x" + str(constant_) + ")"
        ans.append(CommunicationProtocolDistanceBaseDelayPois(is_with_timestamp=is_with_timestamp, name=name, length=map_length, width=map_width, constant_=constant_))
        # if only_with_timestamp:
        #     ans.append( CommunicationProtocolDistanceBaseDelayPois(is_with_timestamp=True, name=name, length=map_length,
        #                                                            width=map_width, constant_=constant_))
        # else:
        #     if constant_ != 0:
        #         for bool in [True, False]:
        #             ans.append(
        #                 CommunicationProtocolDistanceBaseDelayPois(is_with_timestamp=bool, name=name, length=map_length,
        #                                                            width=map_width, constant_=constant_))
        #     else:
        #         ans.append(CommunicationProtocolDistanceBaseDelayPois(is_with_timestamp=False, name=name, length=map_length,
        #                                                               width=map_width, constant_=constant_))

    for constant_ in constants_for_distances_and_loss:
        name = "Pois(Dij_x" + str(constant_) + ") + Distance Loss"
        ans.append(CommunicationProtocolDistanceBaseDelayPoisAndLoss(is_with_timestamp=is_with_timestamp, name=name, length=map_length,width=map_width, constant_=constant_))
        # if constant_ != 0:
        #
        #     if only_with_timestamp:
        #         ans.append(
        #             CommunicationProtocolDistanceBaseDelayPoisAndLoss(is_with_timestamp=True, name=name,
        #                                                               length=map_length,
        #                                                               width=map_width, constant_=constant_))
        #     else:
        #
        #         for bool in [True, False]:
        #             ans.append(
        #                 CommunicationProtocolDistanceBaseDelayPoisAndLoss(is_with_timestamp=bool, name=name,
        #                                                                   length=map_length,
        #                                                                   width=map_width, constant_=constant_))
        # else:
        #     ans.append(
        #         CommunicationProtocolDistanceBaseDelayPoisAndLoss(is_with_timestamp=False, name=name, length=map_length,
        #                                                           width=map_width, constant_=constant_))
    for p_loss in p_losses:
        name = "p loss = " + str(p_loss)
        ans.append(CommunicationProtocolMessageLossConstant(name=name, is_with_timestamp=False, p_loss=p_loss))


    for distance_loss_ratio in distance_loss_ratios:
        name = "Distance Loss "+str(distance_loss_ratio)

        ans.append(CommunicationProtocolDistanceBaseMessageLoss(name=name, is_with_timestamp=False,length=map_length,
                                                                  width=map_width,distance_loss_ratio=distance_loss_ratio))

    if perfect_communication:
        ans.append(CommunicationProtocolDefault(name="Perfect Communication"))

    return ans

if __name__ == '__main__':
    players_required_ratios = [0.5]
    tasks_per_center = 2
    number_of_centers = 4
    simulation_reps = 100
    data_jumps = 100
    map_width = 90
    map_length = 90
    algo_name = "FMC_ASY"
    ros = [1]

    is_with_timestamp = False
    perfect_communication = False
    ubs = []#[500, 1000, 5000]
    p_losses = []#[0.1, 0.5, 0.9]
    p_loss_and_ubs = []#[[0.25,1000]]
    constants_for_distances = []#[500, 1000, 5000]
    constants_for_distances_and_loss = []#[500, 1000, 5000]
    distance_loss_ratios = [1,0.9,0.7,0.5,0.3,0.2]
    poises = []
    communication_protocols = create_communication_protocols(is_with_timestamp,perfect_communication,ubs, constants_for_distances, constants_for_distances_and_loss, p_losses,distance_loss_ratios,p_loss_and_ubs,poises)

    data_output_list = []
    for players_required_ratio in players_required_ratios:
        for communication_protocol in communication_protocols:
            data_ = {}
            for ro in ros:
                current_ro = ro
                if process_debug:
                    print("players_required_ratios =", players_required_ratio, ";", "communication protocol =",
                          communication_protocol.name)

                for i in range(simulation_reps):
                    if process_debug:
                        print(i)

                    data_[i] = run_single_simulation(i, players_required_ratio, tasks_per_center, number_of_centers,
                                                     map_length, map_width, ro)

                data_single_output_dict = get_data_single_output_dict()
                data_frame = pd.DataFrame.from_dict(data_single_output_dict)
                file_name = "reps_"+str(simulation_reps)+"_"+algo_name +"_ro_"+str(current_ro)+"_ratio_"+str(players_required_ratio)+"_"+communication_protocol.name

                if communication_protocol.is_with_timestamp:
                    file_name = file_name+"_TS.csv"
                else:
                    file_name = file_name+"_no_TS.csv"
                data_frame.to_csv(file_name, sep=',')

                data_output_list.append(data_frame)

    data_output = pd.concat(data_output_list)
    data_output.to_csv(algo_name + ".csv", sep=',')
