import csv, statistics, json

# Check all three C-mode visions
for attr, dir_path in [
    ('soft', 'my_test/data/soft_date/第一实验员/第一组实验/vision.csv'),
    ('medium', 'my_test/data/medium_date/第一实验员/第一组实验/vision.csv'),
    ('hard', 'my_test/data/hard_date/第一实验员/第一组实验/vision.csv'),
]:
    with open(dir_path, 'r', encoding='utf-8-sig') as f:
        reader = list(csv.DictReader(f))
    
    last_rows = reader[-30:]
    print(f'=== {attr} vision.csv (last 5 rows) ===')
    for row in last_rows[-5:]:
        print(f"  K_trans={float(row['K_trans']):8.1f} K_rot={float(row['K_rot']):8.1f} damp={float(row['damping_ratio']):8.2f} K_fb={float(row['K_fb']):8.3f} dead={float(row['deadband']):8.3f}")
    
    # Average of last 50 rows
    kt = [float(r['K_trans']) for r in reader[-50:]]
    kr = [float(r['K_rot']) for r in reader[-50:]]
    dr = [float(r['damping_ratio']) for r in reader[-50:]]
    kf = [float(r['K_fb']) for r in reader[-50:]]
    db = [float(r['deadband']) for r in reader[-50:]]
    print(f"  Last 50 avg: K_t={statistics.mean(kt):.1f}, K_r={statistics.mean(kr):.1f}, ζ={statistics.mean(dr):.2f}, K_f={statistics.mean(kf):.3f}, d={statistics.mean(db):.3f}")
    
    # Check when K_trans first reaches target (within 5% of final)
    final_kt = statistics.mean(kt)
    for i, r in enumerate(reader):
        if abs(float(r['K_trans']) - final_kt) / final_kt < 0.02:
            print(f"  First near-final K_trans at row {i}, time={r['time']}")
            break
    
    print()

# Also check E mode summary files for params
for attr, json_path in [
    ('soft', 'my_test/data/soft_date/第一实验员/第一组实验/vision_stiffness_summary.json'),
    ('medium', 'my_test/data/medium_date/第一实验员/第一组实验/vision_stiffness_summary.json'),
    ('hard', 'my_test/data/hard_date/第一实验员/第一组实验/vision_stiffness_summary.json'),
]:
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f'E mode {attr} final_params: {data["final_params"]}')

# Also check medium/hard vision_stiffness.csv
for attr, csv_path in [
    ('soft', 'my_test/data/soft_date/第一实验员/第一组实验/vision_stiffness.csv'),
    ('medium', 'my_test/data/medium_date/第一实验员/第一组实验/vision_stiffness.csv'),
    ('hard', 'my_test/data/hard_date/第一实验员/第一组实验/vision_stiffness.csv'),
]:
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = list(csv.DictReader(f))
    
    if len(reader) < 50:
        print(f'{attr} stiffness CSV too short: {len(reader)} rows')
        continue
    
    # Last 50 avg
    kt = [float(r['K_trans']) for r in reader[-50:]]
    kr = [float(r['K_rot']) for r in reader[-50:]]
    dr = [float(r['damping_ratio']) for r in reader[-50:]]
    kf = [float(r['K_fb']) for r in reader[-50:]]
    db = [float(r['deadband']) for r in reader[-50:]]
    print(f'\n{attr} E(stiffness) last50: K_t={statistics.mean(kt):.1f}, K_r={statistics.mean(kr):.1f}, ζ={statistics.mean(dr):.2f}, K_f={statistics.mean(kf):.3f}, d={statistics.mean(db):.3f}')