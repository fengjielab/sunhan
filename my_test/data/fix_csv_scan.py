import csv, json, statistics, math
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path('my_test/data')

def scan_csvs():
    """Scan Chinese-named directories"""
    # Map attr->operator->group->(mode->path)
    op_map = {'第一': 'P01', '第二': 'P02', '第三': 'P03'}
    mode_map = {
        'default': 'A', 'soft_obj': 'B', 'medium_obj': 'B', 'hard_obj': 'B',
        'vision': 'C', 'vision_observe': 'D', 'vision_stiffness': 'E',
    }
    
    results = {}  # (attr, op, group, mode) -> path
    
    for attr in ['soft_date', 'medium_date', 'hard_date']:
        attr_short = attr.split('_')[0]
        base = DATA_DIR / attr
        if not base.exists():
            continue
        
        for op_dir in base.iterdir():
            if not op_dir.is_dir():
                continue
            op_name = None
            for cn, en in op_map.items():
                if cn in op_dir.name:
                    op_name = en
                    break
            if op_name is None:
                continue
            
            for group_dir in op_dir.iterdir():
                if not group_dir.is_dir():
                    continue
                # Extract group number
                gnum = None
                for ch in group_dir.name:
                    if ch.isdigit():
                        gnum = int(ch)
                        break
                if gnum is None:
                    continue
                
                for fpath in group_dir.glob('*.csv'):
                    stem = fpath.stem
                    if stem in mode_map:
                        mode = mode_map[stem]
                        key = (attr_short, op_name, gnum, mode)
                        results[key] = fpath
    
    return results

# Scan
csvs = scan_csvs()
print(f"Found {len(csvs)} CSV files")
for mode in ['A','B','C','D','E']:
    count = sum(1 for k in csvs if k[3]==mode)
    print(f"  Mode {mode}: {count}")

# Check final params from ALL C-mode files
print("\n=== Final params verification (C mode, last 50 rows of each) ===")
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
        # Take last 50 rows
        last = reader[-50:]
        kt_all.extend(float(r['K_trans']) for r in last)
        kr_all.extend(float(r['K_rot']) for r in last)
        dr_all.extend(float(r['damping_ratio']) for r in last)
        kf_all.extend(float(r['K_fb']) for r in last)
        db_all.extend(float(r['deadband']) for r in last)
    
    if kt_all:
        print(f"{attr}: K_t={statistics.mean(kt_all):.1f}±{statistics.stdev(kt_all):.1f}, K_r={statistics.mean(kr_all):.1f}±{statistics.stdev(kr_all):.1f}, ζ={statistics.mean(dr_all):.2f}±{statistics.stdev(dr_all):.2f}")
        print(f"      K_f={statistics.mean(kf_all):.3f}±{statistics.stdev(kf_all):.3f}, d={statistics.mean(db_all):.3f}±{statistics.stdev(db_all):.3f}")
        # Compare with paper
        paper = {
            'soft': (50, 5, 0.8, 0.2, 0.3),
            'medium': (150, 10, 1.0, 0.5, 0.4),
            'hard': (200, 13, 1.2, 0.7, 0.5),
        }
        p = paper[attr]
        ok = (abs(statistics.mean(kt_all)-p[0]) < 1 and abs(statistics.mean(kr_all)-p[1]) < 1 
              and abs(statistics.mean(dr_all)-p[2]) < 0.05 and abs(statistics.mean(kf_all)-p[3]) < 0.05
              and abs(statistics.mean(db_all)-p[4]) < 0.05)
        print(f"      Paper match: {'✅' if ok else '❌'}")
        if not ok:
            print(f"      Paper: K_t={p[0]}, K_r={p[1]}, ζ={p[2]}, K_f={p[3]}, d={p[4]}")
    print()

# Also check E mode params
print("=== Final params verification (E mode) ===")
for attr in ['soft', 'medium', 'hard']:
    kt_all, kr_all, dr_all, kf_all, db_all = [], [], [], [], []
    for key, path in csvs.items():
        a, op, gnum, mode = key
        if mode != 'E' or a != attr:
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
        print(f"      K_f={statistics.mean(kf_all):.3f} (expected 0.5=default), d={statistics.mean(db_all):.3f} (expected 0.4=default)")
    print()

# Now compute C-E process metrics
print("\n=== C-E Process Metrics ===")
SPEED_THRESHOLD = 0.005
STOP_MIN_DURATION = 0.30

def compute_metrics(path):
    with open(path, 'r', encoding='utf-8-sig') as f:
        reader = list(csv.DictReader(f))
    if len(reader) < 10:
        return None
    
    times = []
    xs, ys, zs = [], [], []
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
    
    # speeds
    speeds = []
    for i in range(1, len(times)):
        dt = times[i] - times[i-1]
        if dt <= 0:
            continue
        dx = xs[i] - xs[i-1]
        dy = ys[i] - ys[i-1]
        dz = zs[i] - zs[i-1]
        v = math.sqrt(dx*dx + dy*dy + dz*dz) / dt
        speeds.append(v)
    
    # stops
    stop_count = 0
    in_stop = False
    stop_start = 0
    for i in range(len(speeds)):
        v = speeds[i]
        t = times[i+1]
        if v < SPEED_THRESHOLD:
            if not in_stop:
                in_stop = True
                stop_start = t
        else:
            if in_stop:
                if t - stop_start >= STOP_MIN_DURATION:
                    stop_count += 1
                in_stop = False
    
    return {'stop_count': stop_count, 'n': len(times), 'duration': times[-1]-times[0]}

c_metrics = []
e_metrics = []

for key, path in csvs.items():
    a, op, gnum, mode = key
    if mode not in ('C', 'E'):
        continue
    result = compute_metrics(path)
    if result:
        result['attr'] = a
        result['mode'] = mode
        if mode == 'C':
            c_metrics.append(result)
        else:
            e_metrics.append(result)

print(f"C mode: {len(c_metrics)} trials")
print(f"  Stop count: {statistics.mean([m['stop_count'] for m in c_metrics]):.2f}±{statistics.stdev([m['stop_count'] for m in c_metrics]):.2f}")
print(f"E mode: {len(e_metrics)} trials")
print(f"  Stop count: {statistics.mean([m['stop_count'] for m in e_metrics]):.2f}±{statistics.stdev([m['stop_count'] for m in e_metrics]):.2f}")

# C-E difference
print("\n  C-E paired difference:")
c_by_key = {}
e_by_key = {}
for m in c_metrics:
    c_by_key[f"{m['attr']}_{m['mode']}"] = m
for m in e_metrics:
    e_by_key[f"{m['attr']}_{m['mode']}"] = m

# Just compare overall
c_mean = statistics.mean([m['stop_count'] for m in c_metrics])
e_mean = statistics.mean([m['stop_count'] for m in e_metrics])
print(f"  Mean stop difference C-E: {c_mean - e_mean:.2f}")
print(f"  C stops: {c_mean:.2f} per trial vs E stops: {e_mean:.2f} per trial")