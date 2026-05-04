# 标定板文件

本目录用于存放可打印的标定板文件。

默认推荐：

1. `charuco_a4_5x7_30mm.pdf`
2. `charuco_a4_5x7_30mm.png`
3. `charuco_a4_5x7_30mm.json`

参数说明：

1. 棋盘格尺寸：`5 x 7`
2. 方格边长：`30 mm`
3. ArUco 码边长：`22 mm`
4. 字典：`DICT_5X5_100`
5. 页面：`A4`
6. 打印要求：`100%` 实际尺寸，关闭“适应页面”

重新生成命令：

```bash
python3 /home/mfj/biaoding/generate_charuco_board.py
```

打印后建议：

1. 用尺子量一下单个方格边长，确认接近 `30 mm`
2. 把纸张贴到硬质平板上，避免弯曲
3. 标定过程中不要手持标定板
