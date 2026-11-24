# 借还台离线工具

两个 Python 模块可脱离现场设备使用。`scene_motion.py` 判断已提供的运动观测，`exporter.py` 按时间范围导出借还记录。需要 Python 3，无第三方依赖。

## 用模拟记录生成 CSV

在仓库根目录保存并运行下面的脚本。它会生成一条虚构的借还记录，再写出 `demo.csv`。

```python
from pathlib import Path
import json
from exporter import records_csv

record = {
    'time': '2026-11-25 09:00:00',
    'action': '借出',
    'count': 1,
    'items': [{'rack_name': '演示台', 'goods_code': 'DEMO01', 'goods_name': '示例物品'}],
}
log = Path('demo.jsonl')
log.write_text(json.dumps(record, ensure_ascii=False) + '\n', encoding='utf-8')
Path('demo.csv').write_bytes(records_csv(log))
```

CSV 每件物品一行。可以向 `records_csv` 传入 `start`、`end` 筛选日期。实际现场系统的设备接入、摄像头、人脸特征和借还记录由原部署管理。
