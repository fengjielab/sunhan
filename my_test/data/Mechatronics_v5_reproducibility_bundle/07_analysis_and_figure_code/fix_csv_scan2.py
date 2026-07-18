import csv, json, statistics, math, os
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path('my_test/data')

def scan_csvs():
    op_map = {'第一': 'P01', '第二': 'P02', '第三': 'P03'}
    mode_map = {
        'default': 'A', 'soft_obj': 'B', 'medium_obj': 'B', 'hard_obj': 'B',
        'vision': 'C', 'vision_observe': 'D', 'vision_stiffness': 'E',
    }
    
    results = {}
    
    for attr in ['soft_date', 'medium_date', 'hard_date']:
        attr_short = attr.split('_')[0]
        base = str(DATA_DIR / attr)
        if not os.path.isdir(base):
            continue
        
        for op_dir_name in os.listdir(base):
            op_dir = os.path.join(base, op_dir_name)
            if not os.path.isdir(op_dir):
                continue
            op_name = None
            for cn, en in op_map.items():
                if cn in op_dir_name:
                    op_name = en
                    break
            if op_name is None:
                continue
            
            for gdir_name in os.listdir(op_dir):
                gdir = os.path.join(op_dir, gdir_name)
                if not os.path.isdir(gdir):
                    continue
                gnum = None
                for ch in gdir_name:
                    if ch.isdigit():
                        gnum = int(ch)
                        break
                if gnum is None:
                    continue
                
                for fname in os.listdir(gdir):
                    if not fname.endswith('.csv'):
                        continue
                    stem = fname[:-4]  # remove .csv
                    if stem in mode_map:
                        mode = mode_map[stem]
                        key = (attr_short, op_name, gnum, mode)
                        results[key] = os.path.join(gdir, fname)
    
    return results

csvs = scan_csvs()
print(f"Found {len(csvs)} CSV files")
for mode in ['A','B','C','D','E']:
    count = sum(1 for k in csvs if k[3]==mode)
    print(f"  Mode {mode}: {count}")

# Check params from all C-mode files
print("\n=== Final params verification (C mode, last 50 rows) ===")
for attr in ['soft', 'medium', 'hard']:
    kt_all, kr_all, dr_all, kf_all, db_all = [], [], [], [], []
    for key, path in csvs.items():
        a, op, gnum, mode = key
        if mode != 'C' or a != attr:
            continue
        with open(path, 'r', encoding='utf-8-sig') as f:
            reader = list(csv.DictReader(f))
        if len(reader) < 50:
            continue
        last = reader[-50:]
        kt_all.extend(float(r['K_trans']) for r in last)
        kr_all.extend(float(r['K_rot']) for r in last)
        dr_all.extend(float(r['damping_ratio']) for r in last)
        kf_all.extend(float(r['K_fb']) for r in last)
        db_all.extend(float(r['deadband']) for r in last)
    
    if kt_all:
        print(f"{attr}: K_t={statistics.mean(kt_all):.1f}, K_r={statistics.mean(kr_all):.1f}, ζ={statistics.mean(dr_all):.2f}")
        print(f"      K_f={statistics.mean(kf_all):.3f}, d={statistics.mean(db_all):.3f}")
        paper = {'soft': (50,5,0.8,0.2,0.3), 'medium': (150,10,1.0,0.5,0.4), 'hard': (200,13,1.2,0.7,0.5)}
        p = paper[attr]
        ok = all([abs(statistics.mean(kt_all)-p[0])<1, abs(statistics.mean(kr_all)-p[1])<1, abs(statistics.mean(kf_all)-p[3])<0.05])
        print(f"      Match paper: {'OK' if ok else 'MISMATCH'}")


# Compute C-E process metrics
print("\n=== C-E Process Metrics ===")

def compute_stops(path):
    with open(path, 'r', encoding='utf-8-sig') as f:
        reader = list(csv.DictReader(f))
    if len(reader) < 10:
        return None
    
    times, xs, ys, zs = [], [], [], []
    for r in reader:
        try:
            times.append(float(r['time']))
            xs.append(float(r['x']))
            ys.append(float(r['y']))
            zs.append(float(r['z']))
        except:
            continue
    if len(times) < 10:
        return None
    
    speeds = []
    for i in range(1, len(times)):
        dt = times[i] - times[i-1]
        if dt <= 0: continue
        dx, dy, dz = xs[i]-xs[i-1], ys[i]-ys[i-1], zs[i]-zs[i-1]
        speeds.append(math.sqrt(dx*dx+dy*dy+dz*dz)/dt)
    
    stop_count = 0
    in_stop = False
    stop_start = 0
    for i in range(len(speeds)):
        v, t = speeds[i], times[i+1]
        if v < 0.005:
            if not in_stop:
                in_stop, stop_start = True, t
        else:
            if in_stop and t - stop_start >= 0.30:
                stop_count += 1
            in_stop = False
    
    return stop_count

c_stops, e_stops = [], []
for key, path in csvs.items():
    a, op, gnum, mode = key
    if mode == 'C':
        s = compute_stops(path)
        if s is not None: c_stops.append(s)
    elif mode == 'E':
        s = compute_stops(path)
        if s is not None: e_stops.append(s)

print(f"C mode stops per trial: {statistics.mean(c_stops):.2f}±{statistics.stdev(c_stops):.2f} (n={len(c_stops)})")
print(f"E mode stops per trial: {statistics.mean(e_stops):.2f}±{statistics.stdev(e_stops):.2f} (n={len(e_stops)})")
print(f"C-E difference: {statistics.mean(c_stops)-statistics.mean(e_stops):.2f}")

# E mode TLX
print("\n=== E mode TLX ===")
tlx_rows = []
with open('my_test/data/nasa_tlx_results/nasa.md', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        tlx_rows.append(row)

dims = ["mental_demand","physical_demand","temporal_demand","performance","effort","frustration"]
e_tlx = [r for r in tlx_rows if r['mode'] == 'E']
if e_tlx:
    raw_tlxs = [statistics.mean(float(r[d]) for d in dims) for r in e_tlx]
    print(f"E mode Raw TLX: {statistics.mean(raw_tlxs):.2f}±{statistics.stdev(raw_tlxs):.2f}")

c_tlx = [r for r in tlx_rows if r['mode'] == 'C']
if c_tlx:
    raw_tlxs = [statistics.mean(float(r[d]) for d in dims) for r in c_tlx]
    print(f"C mode Raw TLX: {statistics.mean(raw_tlxs):.2f}±{statistics.stdev(raw_tlxs):.2f}")