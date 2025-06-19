import solver_test as S
import controller as C
import time
import pickle
from collections import defaultdict, Counter
from player import Player
import json





class Collector(Player):

    merge_encounters = 0
    solution_stats = defaultdict(Counter)
    merge = True
    collect_region_data = True


    def save_solution_stats(filepath="solution_stats.json"):
        # Convert internal defaultdict(Counter) to plain nested dict
        serializable = {
            str(region_size): {str(sol_count): count for sol_count, count in sorted(counter.items())}
            for region_size, counter in sorted(Collector.solution_stats.items())
        }

        with open(filepath, 'w') as f:
            json.dump(serializable, f, indent=4, sort_keys=True)
    def load_solution_stats(filepath="solution_stats.json"):
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                Collector.solution_stats = defaultdict(Counter, {
                    int(size): Counter({int(sol): count for sol, count in sols.items()})
                    for size, sols in data.items()
                })
        except FileNotFoundError:
            Collector.solution_stats = defaultdict(Counter)

class SolverData(S.Solver):
    def __init__(self):
        super().__init__()

    # def solve_exhaustive_and_open(self):
    #     self.solve_exhaustive()
    #     info_found = self.open_known_tiles()
    #     return info_found
    def solve_exhaustive(self):
        start = time.time()
        ccs = self.get_ccs()
        regions = self.convert_ccs_to_regions(ccs)
        #self.store_ccs_as_regions(ccs)
        # for r in self.regions_set:
        #     print(r.locs)
        #paths_explored = 0
        self.start_time = time.time()
        for region in regions:

            region_solved = self.check_for_existing_solutions_in_set(region,self.regions_set)
            if region_solved is not None:
                # if solutions to region are not updated with current board state
                if not region_solved.is_equal(region): 
                    self.update_solutions_with_new_constraints(region_solved,region)
                    self.mark_tile_probs(region_solved.locs,region_solved.sols_bit)
            else:
                subregions = []
                remaining = set()

                for subregion in self.regions_set:
                    if subregion.is_subset_of_region(region):
                        subregions.append(subregion)
                    else:
                        remaining.add(subregion)
                if len(subregions) > 0:
                    Collector.merge_encounters +=1

                if len(subregions) < 0 and Collector.merge:
                    merged_region = self.merge_region_with_existing_regions(region,subregions)
                    self.mark_tile_probs(merged_region.locs,merged_region.sols_bit)

                    self.regions_set = remaining
                    self.regions_set.add(merged_region)
                    region.sols_bit=merged_region.sols_bit


                        
                    

                else:
                    #if region.num_locs() <=10:
                        #print(region.locs)
                        sols = self.find_solutions(region)
                        # print(sols)
                        # print(len(sols))
                        sol_set = set()
                        # for sol in sols:
                        #     sol_set.add(tuple(sol))
                        # print(len(sol_set))
                        # print(sorted(region.locs_to_check,key=lambda coord: (coord[0], coord[1])))
                        # print(len(region.locs_to_check))
                        self.mark_tile_probs(region.locs,sols)
                        region.sols_bit = sols
                        self.regions_set.add(region)

                    # else:
                    #     #start=time.time()
                    #     sols = self.find_solutions_subdiv(region)
                    #     self.mark_tile_probs(region.locs,sols)
                    #     region.sols_bit = sols
                    #     self.regions_set.add(region)
                num_sols = len(region.sols_bit)

                region_size = len(region.locs)
                if  Collector.collect_region_data:
                    # print(f'{region_size}: {num_sols}')
                    Collector.solution_stats[region_size][num_sols] +=1
        print(time.time()-start)            
