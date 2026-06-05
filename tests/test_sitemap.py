import json
import xml.etree.ElementTree as ET

import build_sitemap


def test_build_sitemap_from_tools_and_generated_pages(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    (tmp_path / "tools.json").write_text(
        json.dumps(
            [
                {
                    "filename": "index.html",
                    "url": "/",
                    "updated": "2025-01-02T03:04:05-08:00",
                },
                {
                    "filename": "xml-validator.html",
                    "url": "/xml-validator",
                    "updated": "2025-11-19T12:30:00-08:00",
                },
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "index.html").write_text("<!doctype html>", encoding="utf-8")
    (tmp_path / "by-month.html").write_text("<!doctype html>", encoding="utf-8")

    build_sitemap.build_sitemap()

    tree = ET.parse(tmp_path / "sitemap.xml")
    namespace = {"sitemap": build_sitemap.SITEMAP_NAMESPACE}
    urls = tree.findall("sitemap:url", namespace)

    locs = [url.findtext("sitemap:loc", namespaces=namespace) for url in urls]
    assert locs == [
        "https://tools.simonwillison.net/",
        "https://tools.simonwillison.net/by-month",
        "https://tools.simonwillison.net/xml-validator",
    ]

    lastmods = {
        url.findtext("sitemap:loc", namespaces=namespace): url.findtext(
            "sitemap:lastmod", namespaces=namespace
        )
        for url in urls
    }
    assert lastmods["https://tools.simonwillison.net/"] == "2025-01-02"
    assert lastmods["https://tools.simonwillison.net/by-month"] == "2025-11-19"
    assert lastmods["https://tools.simonwillison.net/xml-validator"] == "2025-11-19"
