"""Big issues that are quick wins: what the survey sees in a tree that is cheap to fix and expensive to leave.

What this gates is that each finding is read off the tree — a secret shaped like one or keyed like one, IDE and
build output tracked, a dependency source over plain HTTP, a lockfile the package manager would write, an archive
tracked — with the file that shows it and the fix, and never the value; that a reference is not a secret; that
the survey carries them, the record and the page say them, the report says them first, and a refresh drops what
the tree stops showing. Experimental, with the rest of adoption (experimental).
"""
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from test_adopt import repository, slipwai

from slipwai.quick_wins import KINDS, quick_wins
from slipwai.survey import survey

KEY = "SG." + "a" * 22 + "." + "b" * 43
FILES = {
    "pom.xml": "<project><repositories><repository><id>x</id><url>http://repo.example.com/m2</url></repository>"
               "</repositories><url>http://example.com</url></project>\n",
    "src/main/java/Mail.java": f'class Mail {{ static final String KEY = "{KEY}"; String password = password; }}\n',
    "src/main/webapp/WEB-INF/spring-security.xml": '<user name="admin" password="pass" authorities="ROLE_ADMIN" />\n',
    # Spring's bean XML: the key in one attribute, the value in the next, or in a child — the form the second real
    # adoption's data source used, which the keyed pattern walked past.
    "src/main/webapp/WEB-INF/mvc-dispatcher-servlet.xml": (
        '<bean id="dataSource">\n  <property name="username" value="root"/>\n'
        '  <property name="password" value="s3cretpw"/>\n  <property name="url"><value>jdbc:x</value></property>\n'
        '  <property name="password"><value>${DB_PASSWORD}</value></property>\n</bean>\n'
    ),
    "src/main/resources/db.properties": "db.url=jdbc:mysql://localhost/shop\ndb.password=${DB_PASSWORD}\n",
    "web/package.json": '{"name": "web", "private": true, "scripts": {"test": "node --test"}}\n',
    ".idea/workspace.xml": "<project/>\n", "Shop.iml": "<module/>\n", "lib/legacy.jar": "PK\x03\x04",
    "mvnw": "MVNW_PASSWORD='' ;;\n",
}


class QuickWinsTest(unittest.TestCase):
    def test_each_kind_is_read_off_the_tree_with_the_file_and_the_fix_and_never_the_value(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), "shop", FILES)
            found = {(f.kind, f.where): f for f in quick_wins(repo, [], set(), "delivery")}
            self.assertEqual({k for k, _ in found}, set(KINDS), "every kind fires once on this tree")
            secrets = {where: f for (kind, where), f in found.items() if kind == "secret-in-tree"}
            security = "src/main/webapp/WEB-INF/spring-security.xml:1"
            datasource = "src/main/webapp/WEB-INF/mvc-dispatcher-servlet.xml:3"
            self.assertEqual(set(secrets), {"src/main/java/Mail.java:1", security, datasource},
                             "the property form is read; its placeholder form on line 5 is not a secret")
            self.assertIn("`password` has a literal value", secrets[datasource].what)
            self.assertIn("a SendGrid key is written", secrets["src/main/java/Mail.java:1"].what)
            self.assertIn("`password` has a literal value", secrets[security].what)
            self.assertTrue(all("rotate" in f.fix for f in secrets.values()))
            everything = json.dumps([f.record() for f in found.values()])
            self.assertNotIn(KEY, everything, "the value is never repeated")
            self.assertNotIn("pass\"", everything)
            self.assertNotIn("s3cretpw", everything)
            # A placeholder, a reference and the wrapper's own empty default are not secrets.
            self.assertNotIn(("secret-in-tree", "src/main/resources/db.properties:2"), found)
            self.assertNotIn(("secret-in-tree", "mvnw:1"), found)
            noise = [f for (kind, _), f in found.items() if kind == "ide-or-build-output-tracked"]
            self.assertEqual({f.where for f in noise}, {".idea/workspace.xml", "Shop.iml"})
            self.assertIn("`.gitignore`", noise[0].fix)
            self.assertEqual(found[("insecure-dependency-source", "pom.xml")].what,
                             "a dependency repository is fetched over plain HTTP")
            self.assertIn("no lockfile beside `package.json`", found["no-lockfile", "web/package.json"].what)
            self.assertEqual(found["archive-tracked", "lib/legacy.jar"].what,
                             "1 binary archive(s) under version control")

            # The survey carries them; a tree with nothing has none.
            self.assertEqual(len(survey(repo).quick_wins), len(found))
            clean = repository(Path(directory), "clean", {"package.json": '{"name": "c", "private": true}\n',
                                                         "package-lock.json": "{}\n"})
            self.assertEqual(quick_wins(clean, [], set(), "delivery"), [])

    def test_adopt_says_them_first_the_page_carries_them_and_a_refresh_drops_what_is_fixed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), "shop", {
                "package.json": '{"name": "shop", "private": true, "scripts": {"test": "node --test"}}\n',
                "test/a.test.js": "test('a', () => {});\n", ".idea/x.xml": "<project/>\n",
            })
            result = slipwai(repo, "adopt", "--yes")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Quick wins: 2 big issue(s) that are cheap to fix — ide-or-build-output-tracked at "
                          ".idea/x.xml; no-lockfile at package.json", result.stdout)
            document = json.loads((repo / "project.json").read_text())
            self.assertEqual([w["kind"] for w in document["survey"]["quickWins"]],
                             ["ide-or-build-output-tracked", "no-lockfile"])
            page = (repo / "delivery/survey/survey.md").read_text()
            self.assertIn("## Big issues that are quick wins", page)
            self.assertIn("| `no-lockfile` | `package.json` |", page)
            essay = (repo / "delivery/docs/change-strategy.md").read_text()
            self.assertIn("### The programme", essay)
            self.assertIn("| 1 | IntelliJ's `.idea/` is under version control —", essay)
            self.assertIn("now — a slice of its own whatever the strategy", essay)
            drive = (repo / "delivery/commands/drive.md").read_text()
            self.assertIn("from the programme `delivery/docs/change-strategy.md`", drive)
            # Fixed in the tree, gone from the record and the page after /survey — nothing to tick.
            subprocess.run(["git", "rm", "-rq", ".idea"], cwd=repo, check=True, capture_output=True)
            (repo / "package-lock.json").write_text("{}\n")
            subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
            subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@local", "commit", "-qm", "fixed"], cwd=repo,
                           check=True)
            refreshed = slipwai(repo, "adopt", "--refresh")
            self.assertEqual(refreshed.returncode, 0, refreshed.stderr)
            self.assertIn("quick wins: 2 fixed since the last survey; 0 remain", refreshed.stdout)
            document = json.loads((repo / "project.json").read_text())
            self.assertEqual(document["survey"]["quickWins"], [])
            self.assertIn("None the survey can see", (repo / "delivery/survey/survey.md").read_text())

    def test_the_jars_under_an_ant_build_are_its_classpath_and_not_a_quick_win(self) -> None:
        from slipwai.quick_wins import archives_tracked
        ant = ["build.xml", "lib/mysql-connector-java-5.1.23-bin.jar", "jcalendar-1.4.jar", "src/Login.java"]
        self.assertEqual(archives_tracked(ant), [])
        nested = ["apps/desk/build.xml", "apps/desk/lib/a.jar", "apps/web/lib/b.jar", "vendor.zip"]
        self.assertEqual([f.where for f in archives_tracked(nested)], ["apps/web/lib/b.jar (+1 more)"])


if __name__ == "__main__":
    unittest.main()
