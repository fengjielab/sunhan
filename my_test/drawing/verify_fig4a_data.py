import pandas as pd
import numpy as np

df = pd.read_csv('../data/vision_validation/results/vision_validation_per_image.csv')

# ============ 1. 混淆矩阵 ============
print("===== 1. 混淆矩阵核验 =====")
print(f"总样本数: {len(df)}")
print(f"类别识别正确数 (class_correct): {df['class_correct'].sum()}/{len(df)}")
print(f"策略触发正确数 (trigger_correct): {df['trigger_correct'].sum()}/{len(df)}")

# 检查是否有任何分类错误
errors = df[df['expected_coco'] != df['predicted_coco']]
print(f"分类错误数: {len(errors)}")

# 构建混淆矩阵
print("\n混淆矩阵 (行=True, 列=Pred):")
cm = pd.crosstab(df['expected_coco'], df['predicted_coco'], rownames=['True'], colnames=['Pred'])
print(cm)

# ============ 2. 按对象统计置信度和时间 ============
classes = ['apple', 'banana', 'cup', 'bottle', 'mouse', 'scissors']
print("\n===== 2. 按对象统计置信度和处理时间 =====")
for obj in classes:
    sub = df[df['object'] == obj]
    conf_mean = sub['confidence'].mean()
    time_mean = sub['inference_ms'].mean()
    conf_std = sub['confidence'].std()
    time_std = sub['inference_ms'].std()
    print(f"{obj:8s} | 数量={len(sub):2d} | 平均置信度={conf_mean:.3f} (std={conf_std:.4f}) | 平均时间={time_mean:.2f}ms (std={time_std:.2f})")

# 总平均置信度和时间
print(f"\n总体平均置信度: {df['confidence'].mean():.3f}")
print(f"总体平均时间: {df['inference_ms'].mean():.2f}ms")

# ============ 3. 论文对照 ============
print("\n===== 3. 论文数值对照表 (论文第302行附近表格) =====")
paper_data = {
    'apple':    {'n':30, 'acc':1.0, 'trigger':1.0, 'conf':0.771, 'time':56.66},
    'banana':   {'n':30, 'acc':1.0, 'trigger':1.0, 'conf':0.948, 'time':50.45},
    'bottle':   {'n':30, 'acc':1.0, 'trigger':1.0, 'conf':0.726, 'time':49.71},
    'cup':      {'n':30, 'acc':1.0, 'trigger':1.0, 'conf':0.820, 'time':47.61},
    'mouse':    {'n':30, 'acc':1.0, 'trigger':1.0, 'conf':0.914, 'time':46.79},
    'scissors': {'n':30, 'acc':1.0, 'trigger':1.0, 'conf':0.938, 'time':49.27},
}
header = f"{'对象':8s} | {'论文conf':>8s} | {'实际conf':>8s} | {'差值':>6s} | {'论文time':>8s} | {'实际time':>8s} | {'差值':>6s}"
print(header)
print("-" * len(header))
for obj in classes:
    sub = df[df['object'] == obj]
    conf = sub['confidence'].mean()
    t = sub['inference_ms'].mean()
    pd_c = paper_data[obj]['conf']
    pd_t = paper_data[obj]['time']
    print(f"{obj:8s} | {pd_c:8.3f} | {conf:8.3f} | {conf-pd_c:+6.3f} | {pd_t:8.2f} | {t:8.2f} | {t-pd_t:+6.2f}")

# ============ 4. 检查各对象置信度范围 ============
print("\n===== 4. 各对象置信度详情 =====")
for obj in classes:
    sub = df[df['object'] == obj]
    print(f"\n{obj}: 共{len(sub)}张")
    print(f"  置信度: min={sub['confidence'].min():.3f}, max={sub['confidence'].max():.3f}, mean={sub['confidence'].mean():.3f}")
    print(f"  时间: min={sub['inference_ms'].min():.2f}, max={sub['inference_ms'].max():.2f}, mean={sub['inference_ms'].mean():.2f}")

# ============ 5. 检查论文中"180/180 100%"声明 ============
print("\n===== 5. 论文关键声明核验 =====")
print(f"论文: '类别识别和策略触发达到 180/180 (100%)'")
print(f"实际: 类别识别正确 {df['class_correct'].sum()}/{len(df)} = {df['class_correct'].sum()/len(df)*100:.1f}%")
print(f"实际: 策略触发正确 {df['trigger_correct'].sum()}/{len(df)} = {df['trigger_correct'].sum()/len(df)*100:.1f}%")
print(f"论文: '平均置信度为 0.853'")
print(f"实际: 平均置信度 = {df['confidence'].mean():.3f}")
print(f"论文: '单帧 wall-clock 处理时间为 50.08 ms'")
print(f"实际: 平均时间 = {df['inference_ms'].mean():.2f}ms")