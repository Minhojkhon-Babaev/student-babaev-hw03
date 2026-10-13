#!/usr/bin/env python3
"""Показать фактические SQL-выводы в браузере для снимков выполнения."""

from __future__ import annotations

import hashlib
import html
import json

from db import ROOT

PAGES = {
    "plans_narrow": ("Узкий запрос до и после индекса", [
        "bench/heap_narrow.txt", "bench/index_narrow.txt",
    ]),
    "plans_wide": ("Широкий запрос до и после индекса", [
        "bench/heap_wide.txt", "bench/index_wide.txt",
    ]),
    "partition": ("Секции узкого и широкого запросов", [
        "bench/part_narrow.txt", "bench/part_wide.txt",
    ]),
    "patroni": ("Роли и маркеры после switchover", [
        "patroni_roles_after.txt", "patroni_markers_after.txt", "patroni_replica_write.txt",
    ]),
    "restore": ("Проверка восстановленной базы", ["restore_check.txt"]),
    "mvcc": ("Две сессии и блокировка UPDATE", ["mvcc_two_sessions.txt"]),
}


def main() -> None:
    output = ROOT / "evidence" / "views"
    output.mkdir(parents=True, exist_ok=True)
    source_manifest = {}
    hw02 = ROOT.parent / "student-babaev-hw02"
    for name in ["weather.csv", "city.csv"]:
        path = ROOT / "data" / "control" / name
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        previous = hw02 / "data" / "control" / name
        if previous.exists():
            assert hashlib.sha256(previous.read_bytes()).hexdigest() == digest
        source_manifest[name] = {"sha256": digest, "origin": f"../student-babaev-hw02/data/control/{name}"}
    (ROOT / "evidence/source_manifest.json").write_text(
        json.dumps(source_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    links = []
    for slug, (title, files) in PAGES.items():
        blocks = []
        for name in files:
            text = (ROOT / "evidence" / name).read_text(encoding="utf-8")
            # Для снимков планов не повторяем таблицу результата:
            # полный вывод сохранён в исходном evidence/bench/*.txt.
            if name.startswith("bench/"):
                metric = text.split("\n\n", 1)[0]
                plan = text[text.index("\nSort  "):] if "\nSort  " in text else text
                text = metric + "\n\n" + plan.strip()
            blocks.append(f"<section><h2>{html.escape(name)}</h2><pre>{html.escape(text)}</pre></section>")
        page = f"""<!doctype html><html lang="ru"><meta charset="utf-8">
<title>{html.escape(title)}</title>
<style>
body{{font:16px system-ui;margin:28px;color:#152436;background:#f3f6fa}}
h1{{font-size:24px;margin:0 0 12px}}h2{{font-size:16px;color:#25628f;margin:0 0 10px}}
p{{color:#51657a}}section{{padding:20px;background:white;border:1px solid #d5dfeb;border-radius:10px;margin:18px 0}}
pre{{font:13px/1.55 monospace;white-space:pre-wrap;overflow-wrap:anywhere;margin:0}}
</style><h1>ДЗ 3 · {html.escape(title)}</h1>
<p>Фактический вывод выполненных команд. Источники указаны над каждым блоком.</p>
{''.join(blocks)}</html>"""
        (output / f"{slug}.html").write_text(page, encoding="utf-8")
        links.append(f'<li><a href="{slug}.html">{html.escape(title)}</a></li>')
    (output / "index.html").write_text(
        '<!doctype html><meta charset="utf-8"><title>ДЗ 3 Проверки</title><h1>Проверки ДЗ 3</h1><ul>'
        + "".join(links) + "</ul>", encoding="utf-8",
    )
    print("Evidence views:", output)


if __name__ == "__main__":
    main()
