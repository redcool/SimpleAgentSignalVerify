"""统一报告结构。每个命令都产出同一种信封，方便流水线消费。"""
import json
from pathlib import Path


class Report(dict):
    """一个带方法链的最小报告对象。

    必填字段：tool / version / inputs / method / results / limitations
    约定：limitations 必须非空——没有局限的工具是不存在的，写空说明没想清楚。
    """

    def __init__(self, tool, version="0.1.0"):
        super().__init__({
            "tool": tool,
            "version": version,
            "inputs": {},
            "method": "",
            "results": {},
            "limitations": [],
        })

    def input(self, key, value):
        self["inputs"][key] = str(value)
        return self

    def method(self, text):
        self["method"] = text
        return self

    def result(self, key, value):
        self["results"][key] = value
        return self

    def limitation(self, text):
        self["limitations"].append(text)
        return self


def write_report(report, path):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return p
