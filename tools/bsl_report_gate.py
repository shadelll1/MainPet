#!/usr/bin/env python3
"""Разбирает JSON-отчет BSL Language Server: печатает сводку и падает, если есть замечания
уровня Error (ошибки и потенциальные уязвимости). Предупреждения и подсказки только выводятся.

Запуск: python3 tools/bsl_report_gate.py bsl-report/bsl-json.json
"""
import collections
import json
import sys
import urllib.parse

report = json.load(open(sys.argv[1], encoding="utf-8"))
by_severity = collections.Counter()
blocking = []
for file_info in report["fileinfos"]:
    path = urllib.parse.unquote(file_info["path"]).split("/src/")[-1]
    for diagnostic in file_info["diagnostics"]:
        severity = diagnostic["severity"]
        by_severity[severity] += 1
        if severity == "Error":
            line = diagnostic["range"]["start"]["line"] + 1
            blocking.append("%s:%d [%s] %s" % (path, line, diagnostic["code"], diagnostic["message"]))

print("Замечания BSL LS: " + ", ".join("%s=%d" % item for item in sorted(by_severity.items())))
for item in blocking:
    print("ОШИБКА " + item)
sys.exit(1 if blocking else 0)
