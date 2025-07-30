import ast

def parse_trials(filename):
    trials = []
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                trial = ast.literal_eval(line)
                if isinstance(trial, dict) and 'seed' in trial and 'time' in trial:
                    trials.append(trial)
            except (SyntaxError, ValueError):
                continue  # skip headers or malformed lines
    return sorted(trials, key=lambda t: t['seed'])

# Parse and sort trials
trials1 = parse_trials('t1.txt')
trials2 = parse_trials('t2.txt')

# Calculate win rates
def compute_win_rate(trials):
    wins = sum(1 for t in trials if t['won'])
    return wins / len(trials) if trials else 0

win_rate1 = compute_win_rate(trials1)
win_rate2 = compute_win_rate(trials2)

# Compute deltas and collect mismatches
trial_deltas = []
mismatches = []

for t1, t2 in zip(trials1, trials2):
    if t1['seed'] != t2['seed']:
        mismatches.append((t1, t2, 'Seed mismatch'))
        continue
    if t1['won'] != t2['won']:
        mismatches.append((t1, t2, 'Won mismatch'))
        continue

    delta = abs(t1['time'] - t2['time'])
    if delta >= 0.1:
        trial_deltas.append({
            'seed': t1['seed'],
            'won': t1['won'],
            'time1': t1['time'],
            'time2': t2['time'],
            'delta': delta
        })

# Sort by descending delta
trial_deltas.sort(key=lambda x: x['delta'], reverse=True)

# Write t3.txt (with win rates and filtered trials)
with open('t3.txt', 'w') as f:
    f.write("Trials with delta >= 0.1, sorted by descending absolute time delta\n")
    f.write(f"Win rate in t1.txt: {win_rate1:.2%}\n")
    f.write(f"Win rate in t2.txt: {win_rate2:.2%}\n")
    f.write("Format: seed, won, time1, time2, delta\n\n")
    for trial in trial_deltas:
        f.write(f"{trial}\n")

# Write t4.txt (mismatches)
with open('t4.txt', 'w') as f:
    f.write("Mismatched trials between t1 and t2\n")
    f.write("Each entry includes t1, t2, and a reason\n\n")
    for t1, t2, reason in mismatches:
        f.write(f"Reason: {reason}\n")
        f.write(f"t1: {t1}\n")
        f.write(f"t2: {t2}\n\n")
