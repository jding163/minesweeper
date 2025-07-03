import ast
import copy
from itertools import combinations, product
from scipy import stats
from collections import defaultdict

def remove_coordinates(coords, sols, coords_to_remove):
    # Make copies so input is not modified
    new_coords = coords[:]
    new_sols = copy.deepcopy(sols)

    # Get indices to remove
    indices_to_remove = [new_coords.index(c) for c in coords_to_remove if c in new_coords]
    indices_to_remove.sort(reverse=True)

    # Remove coordinates from copy
    for idx in indices_to_remove:
        new_coords.pop(idx)

    # Remove solution values at corresponding indices
    if all(isinstance(row, list) for row in new_sols):  # 2D
        for row in new_sols:
            for idx in indices_to_remove:
                row.pop(idx)
    else:  # 1D
        for idx in indices_to_remove:
            new_sols.pop(idx)

    return new_coords, new_sols

def find_matching_sols(coords, sols, locs, bits):
    # Map locs to indices in coords
    indices = [coords.index(loc) for loc in locs]

    # Ensure 2D format for sols
    if not all(isinstance(row, list) for row in sols):
        sols = [sols]

    # Collect all sols that match
    matching = []
    for sol in sols:
        if all(sol[i] == bit for i, bit in zip(indices, bits)):
            matching.append(sol)

    return matching
def save_data(filepath, coords, sols):
    with open(filepath, 'w') as f:
        f.write(f"{coords}\n")  # First line: all coordinates

        # Second and onward: each solution row on a separate line
        #if all(isinstance(row, list) for row in sols):  # 2D list
        for row in sols:
            f.write(f"{row}\n")
        #else:  # Single solution (1D list)
            f.write(f"{sols}\n")


# with open('t1.txt', 'r') as f:
#     lines = f.readlines()
#     coords = ast.literal_eval(lines[0].strip())  # Parse line 1
#     sols = ast.literal_eval(lines[1].strip())  # Parse line 2
# print(len(sols))
# locs = [(9,13),(10,13)]
# sols_a = find_matching_sols(coords,sols,locs,[1,0])
# sols_b = find_matching_sols(coords,sols,locs,[0,1])
# coords_a, sols_a = remove_coordinates(coords,sols_a,locs)
# coords_b, sols_b = remove_coordinates(coords,sols_b,locs)


# sols_a_set = set(tuple(sol) for sol in sols_a)
# sols_b_set = set(tuple(sol) for sol in sols_b)

# print(len(sols_a))
# print(len(sols_b))
# sols_set = sols_a_set ^ sols_b_set
# print(len(sols_set))

# print(len(sols))
# locs = [(8,14),(8,15)]
# sols_a = find_matching_sols(coords,sols,locs,[1,0])
# sols_b = find_matching_sols(coords,sols,locs,[0,1])
# coords_a, sols_a = remove_coordinates(coords,sols_a,locs)
# coords_b, sols_b = remove_coordinates(coords,sols_b,locs)
# sols_a_set = set(tuple(sol) for sol in sols_a)
# sols_b_set = set(tuple(sol) for sol in sols_b)

# print(len(sols_a))
# print(len(sols_b))
# sols_set = sols_a_set ^ sols_b_set
# print(len(sols_set))

# print(len(sols))
# locs = [(10,7),(10,8)]
# sols_a = find_matching_sols(coords,sols,locs,[1,0])
# sols_b = find_matching_sols(coords,sols,locs,[0,1])
# coords_a, sols_a = remove_coordinates(coords,sols_a,locs)
# coords_b, sols_b = remove_coordinates(coords,sols_b,locs)
# sols_a_set = set(tuple(sol) for sol in sols_a)
# sols_b_set = set(tuple(sol) for sol in sols_b)

# print(len(sols_a))
# print(len(sols_b))
# sols_set = sols_a_set ^ sols_b_set
# print(len(sols_set))

# print(len(sols))
# locs = [(9,1),(8,1)]
# sols_a = find_matching_sols(coords,sols,locs,[1,0])
# sols_b = find_matching_sols(coords,sols,locs,[0,1])
# coords_a, sols_a = remove_coordinates(coords,sols_a,locs)
# coords_b, sols_b = remove_coordinates(coords,sols_b,locs)
# sols_a_set = set(tuple(sol) for sol in sols_a)
# sols_b_set = set(tuple(sol) for sol in sols_b)

# print(len(sols_a))
# print(len(sols_b))
# sols_set = sols_a_set ^ sols_b_set
# print(len(sols_set))

# sols_a = find_matching_sols(coords,sols,[(7,13)],[1])
# print(len(sols_a))

# for i in range(1):
#     print(i)

# print("Coordinates:", coords)
# print("sols:", sols)


def distribute_ones(n, length):
    """Generate all binary lists of a given length with n ones."""
    if n > length:
        return []
    result = []
    for ones_positions in combinations(range(length), n):
        arr = [0] * length
        for pos in ones_positions:
            arr[pos] = 1
        result.append(arr)
    return result

def expand_sols_flat(sols, lens):
    all_group_distributions = []
    for count, length in zip(sols, lens):
        if length == 0:
            all_group_distributions.append([[]])
        elif count == 0:
            all_group_distributions.append([[0] * length])
        else:
            all_group_distributions.append(distribute_ones(count, length))

    # Cartesian product to form all full combinations
    grouped_sols = product(*all_group_distributions)

    # Flatten each solution across all groups
    flattened_sols = [sum(solution, []) for solution in grouped_sols]
    return flattened_sols



def convolve_mine_distributions(dist_frontier, nf, prob_nonfrontier_tile):
    # Turn frontier dist into dict for easier access
    frontier_dict = dict(dist_frontier)
    
    # Build nonfrontier binomial distribution
    max_total = max(frontier_dict) + nf
    dist_total = defaultdict(float)

    for total_mines in range(max_total + 1):
        prob = 0.0
        for frontier_mines in range(0, total_mines + 1):
            nonfrontier_mines = total_mines - frontier_mines
            if frontier_mines in frontier_dict and 0 <= nonfrontier_mines <= nf:
                p_frontier = frontier_dict[frontier_mines]
                p_nonfrontier = stats.binom.pmf(nonfrontier_mines, nf, prob_nonfrontier_tile)
                prob += p_frontier * p_nonfrontier
        dist_total[total_mines] = prob

    return sorted(dist_total.items())

dist = [(0, 0.16666666666666669), (1, 0.6070282881306504), (2, 0.22630504520268302)]
prob_nonfrontier_tile = 0.208
nf = 2
total_distribution = convolve_mine_distributions(dist, nf, prob_nonfrontier_tile)
for count, prob in total_distribution:
    print(f"{count} mines: {prob:.6f}")