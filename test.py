import ast
import copy

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


with open('t1.txt', 'r') as f:
    lines = f.readlines()
    coords = ast.literal_eval(lines[0].strip())  # Parse line 1
    sols = ast.literal_eval(lines[1].strip())  # Parse line 2
print(len(sols))
locs = [(9,13),(10,13)]
sols_a = find_matching_sols(coords,sols,locs,[1,0])
sols_b = find_matching_sols(coords,sols,locs,[0,1])
coords_a, sols_a = remove_coordinates(coords,sols_a,locs)
coords_b, sols_b = remove_coordinates(coords,sols_b,locs)


sols_a_set = set(tuple(sol) for sol in sols_a)
sols_b_set = set(tuple(sol) for sol in sols_b)

print(len(sols_a))
print(len(sols_b))
sols_set = sols_a_set ^ sols_b_set
print(len(sols_set))

print(len(sols))
locs = [(8,14),(8,15)]
sols_a = find_matching_sols(coords,sols,locs,[1,0])
sols_b = find_matching_sols(coords,sols,locs,[0,1])
coords_a, sols_a = remove_coordinates(coords,sols_a,locs)
coords_b, sols_b = remove_coordinates(coords,sols_b,locs)
sols_a_set = set(tuple(sol) for sol in sols_a)
sols_b_set = set(tuple(sol) for sol in sols_b)

print(len(sols_a))
print(len(sols_b))
sols_set = sols_a_set ^ sols_b_set
print(len(sols_set))

print(len(sols))
locs = [(10,7),(10,8)]
sols_a = find_matching_sols(coords,sols,locs,[1,0])
sols_b = find_matching_sols(coords,sols,locs,[0,1])
coords_a, sols_a = remove_coordinates(coords,sols_a,locs)
coords_b, sols_b = remove_coordinates(coords,sols_b,locs)
sols_a_set = set(tuple(sol) for sol in sols_a)
sols_b_set = set(tuple(sol) for sol in sols_b)

print(len(sols_a))
print(len(sols_b))
sols_set = sols_a_set ^ sols_b_set
print(len(sols_set))

print(len(sols))
locs = [(9,1),(8,1)]
sols_a = find_matching_sols(coords,sols,locs,[1,0])
sols_b = find_matching_sols(coords,sols,locs,[0,1])
coords_a, sols_a = remove_coordinates(coords,sols_a,locs)
coords_b, sols_b = remove_coordinates(coords,sols_b,locs)
sols_a_set = set(tuple(sol) for sol in sols_a)
sols_b_set = set(tuple(sol) for sol in sols_b)

print(len(sols_a))
print(len(sols_b))
sols_set = sols_a_set ^ sols_b_set
print(len(sols_set))

sols_a = find_matching_sols(coords,sols,[(7,13)],[1])
print(len(sols_a))

# print("Coordinates:", coords)
# print("sols:", sols)