# 添加 lemon（柠檬）到 soft 类别映射 — 实施计划

## 需求

在 `biaoding/vision_physics_mapper.py` 的 `DEFAULT_TABLE` 中添加 `lemon` 条目，
使得 `my_test/interactive_teleop.py` 以 `--mode vision` 运行时，
YOLO 识别到柠檬能和其他 soft 物品（apple/banana/orange）一样映射到软物体手感参数。

## 涉及文件

| 文件 | 修改类型 |
|------|---------|
| [`biaoding/vision_physics_mapper.py`](../biaoding/vision_physics_mapper.py:138) | 在 `DEFAULT_TABLE` 的 soft 区块中添加 `lemon` |
| [`biaoding/physics_table.json`](../biaoding/physics_table.json:1) | 添加对应的 `lemon` 条目，保持数据持久化同步 |

## 参数值

lemon 参数与 orange 完全相同（soft 类别）：

```python
"lemon": {
    "K_trans": 50, "K_rot": 5, "D_trans": 14.1, "D_rot": 4.5, "M": 0.5,
    "K_fb": 0.3, "deadband": 0.25,
    "gripper_speed": 0.02, "gripper_force_limit": 8.0,
    "admittance_K": 60.0, "approach_speed": 0.02,
    "label": "soft",
    "description": "软-柠檬: 低刚度 50N/m, 略小死区",
}
```

## 放置位置

- 在 `DEFAULT_TABLE` 中，放在 `orange` 条目之后、`teddy bear` 之前（soft 区块内，按字母/逻辑顺序排列）
- 在 `physics_table.json` 中，放在 `orange` 之后、`bottle` 之前

## 验证方式

运行以下命令验证 lemon 能被正确映射：

```bash
cd /home/mfj/sunhan
python3 -c "
from biaoding.vision_physics_mapper import VisionPhysicsMapper
mapper = VisionPhysicsMapper()
p = mapper.lookup('lemon')
print(f'label={p.label}, K_trans={p.K_trans}, desc={p.description}')
assert p.label == 'soft', '标签应为 soft'
assert p.K_trans == 50, '刚度应为 50'
print('✓ lemon 正确映射到 soft 手感参数')
"
```
