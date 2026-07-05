import csv, statistics

# Check the tail of a soft vision.csv for K_trans values
with open('my_test/data/soft_date/第一实验员/第一组实验/vision.csv', 'r', encoding='utf-8-sig') as f:
    reader = list(csv.DictReader(f))
    # Show last 10 rows
    print('Last 10 rows of soft vision.csv:')
    for row in reader[-10:]:
        print(f"  K_trans={row['K_trans']:>8} K_rot={row['K_rot']:>8} K_fb={row['K_fb']:>8} deadband={row['deadband']:>8} damping={row['damping_ratio']:>8}")
    
    # Unique K_trans values  
    kt_vals = sorted(set(float(r['K_trans']) for r in reader))
    print(f'\nUnique K_trans values (first 15): {kt_vals[:15]}')
    print(f'Unique K_trans values total: {len(kt_vals)}')
    
    # Check when K_trans first drops - look for when it's below 100
    for i, r in enumerate(reader):
        if float(r['K_trans']) < 100:
            print(f'K_trans first < 100 at row {i}, time={r["time"]}')
            break
    else:
        print('K_trans never < 100 in this file')
    
    # Last 100 rows avg
    last_vals = [float(r['K_trans']) for r in reader[-100:]]
    print(f'Last 100 rows avg K_trans: {statistics.mean(last_vals):.1f}')
    
    # Check when button=1 (active phase)
    for i, r in enumerate(reader):
        if r['button'] == '1' or r['button'] == 1:
            print(f'First button=1 at row {i}, time={r["time"]}')
            break
    
    print(f'Total rows: {len(reader)}')

# Also check the summary json
import json
with open('my_test/data/soft_date/第一实验员/第一组实验/vision_stiffness_summary.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
    print(f'\nSummary file keys: {list(data.keys()) if isinstance(data, dict) else "not dict"}')
    if isinstance(data, dict):
        for k, v in data.items():
            print(f'  {k}: {str(v)[:100]}')