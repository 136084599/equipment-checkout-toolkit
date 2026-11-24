# -*- coding: utf-8 -*-
"""导出：把留证记录 / 借还单 / 库存台账导成 CSV（Excel 能直接打开）。

为什么用 CSV：Excel、WPS、Numbers、pandas 都能开，不依赖任何库；
导出时带 UTF-8 BOM，中文不会乱码。

支持的类型见 KINDS。
"""
import csv
import io
import json
import os
from datetime import datetime, timedelta

# 导出类型注册表：key -> (中文名, 说明)
KINDS = {
    "records": ("留证记录", "本系统记录的「谁在什么时候动了哪一层哪些物品」，含照片/视频文件名"),
    "bills": ("借还明细", "借还台数据库里的借还流水（领用/归还/盘点），一行一件"),
    "stock": ("库存台账", "借还台数据库里当前在册的物品与标签"),
    "goods": ("物品清单", "借还台数据库里的物品目录（编码/名称/规格）"),
}


def _csv_bytes(header, rows):
    """带 BOM 的 CSV。用 excel 方言，换行统一 CRLF。"""
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\r\n")
    w.writerow(header)
    for r in rows:
        w.writerow(r)
    return ("\ufeff" + buf.getvalue()).encode("utf-8")


def _in_range(day, start, end):
    if not day:
        return False
    if start and day < start:
        return False
    if end and day > end:
        return False
    return True


def _day_of(s):
    return str(s or "")[:10]


# ---------------------------------------------------------------- 留证记录
def records_csv(index_path, start="", end="", record_transform=None):
    """一行一件物品；没有明细字段的记录也出一行汇总。"""
    header = ["时间", "动作", "件数", "台子", "层", "物品编码", "物品名称",
              "规格", "RFID", "未登记", "涉及台子", "识别到的人", "疑似误报",
              "照片", "视频", "动图"]
    rows = []
    if not os.path.exists(index_path):
        return _csv_bytes(header, rows)
    with open(index_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            if not isinstance(r, dict):
                continue
            if not _in_range(_day_of(r.get("time")), start, end):
                continue
            if record_transform is not None:
                r = record_transform(r)
            base = [r.get("time", ""), r.get("action", ""), r.get("count", ""),
                    "", "", "", "", "", "", "",
                    "、".join(r.get("racks") or []),
                    "、".join(r.get("people") or []),
                    "是" if r.get("noise") else "",
                    r.get("photo", ""), r.get("video", ""), r.get("video_preview", "")]
            items = r.get("items") or []
            if not items:
                rows.append(base)
                continue
            for it in items:
                if not isinstance(it, dict):
                    continue
                row = list(base)
                row[3] = it.get("rack_name", "")
                row[4] = it.get("layer", "")
                row[5] = it.get("goods_code", "")
                row[6] = it.get("goods_name", "")
                row[7] = it.get("goods_spec", "")
                row[8] = it.get("rfid", "")
                row[9] = "是" if it.get("no_record") else ""
                rows.append(row)
    return _csv_bytes(header, rows)


# ---------------------------------------------------------------- 借还明细
def bills_csv(db, start="", end=""):
    header = ["时间", "单据号", "业务类型", "操作人", "账号", "物品编码",
              "物品名称", "规格", "RFID", "设备SN", "柜号", "层号", "库位码"]
    rows = []
    for r in db.details_range(start, end):
        rows.append([
            r["ctime"], r["bill_no"], r["business"],
            r["user_name"] or r["bill_user"], r["user_account"],
            r["goods_code"], r["goods_name"], r["goods_spec"], r["rfid"],
            r["dev_sn"], r["chest_no"], r["cell_no"], r["storage_code"],
        ])
    return _csv_bytes(header, rows)


# ---------------------------------------------------------------- 库存 / 物品
def stock_csv(db):
    header = ["RFID", "物品编码", "物品名称", "规格", "状态", "设备SN", "柜号", "更新时间"]
    rows = []
    for r in db.stock_all():
        rows.append([r["rfid"], r["goods_code"], r["goods_name"], r["goods_spec"],
                     r["state"], r["dev_sn"], r["chest_no"], r["ctime"]])
    return _csv_bytes(header, rows)


def goods_csv(db):
    header = ["物品编码", "物品名称", "规格", "单位", "单价", "备注"]
    rows = []
    for r in db.goods_all():
        rows.append([r["goods_code"], r["goods_name"], r["goods_spec"],
                     r["unit"], r["price"], r["remark"]])
    return _csv_bytes(header, rows)


# ---------------------------------------------------------------- 统一入口
def build(kind, store=None, db=None, start="", end="", record_transform=None):
    """返回 (文件名, 内容 bytes)。kind 见 KINDS。"""
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    if start or end:
        rng = f"_{start or '开始'}_{end or '至今'}"
    else:
        rng = "_全部"
    if kind == "records":
        with store._lock:
            data = records_csv(store.index, start, end, record_transform)
        return f"留证记录{rng}_{stamp}.csv", data
    if kind == "bills":
        return f"借还明细{rng}_{stamp}.csv", bills_csv(db, start, end)
    if kind == "stock":
        return f"库存台账_{stamp}.csv", stock_csv(db)
    if kind == "goods":
        return f"物品清单_{stamp}.csv", goods_csv(db)
    raise ValueError(f"不支持的导出类型：{kind}")


def default_range(days=7):
    """默认时间范围：最近 N 天（含今天）。"""
    end = datetime.now().date()
    start = end - timedelta(days=days - 1)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")
