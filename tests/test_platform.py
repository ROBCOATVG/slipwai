"""What the applications run on, dated against the support table: the Platform axis and the way up for each product.

What this gates is that nothing here is inferred: a version is read only where the tree pins it — the record's
`toolchain.version`, a manifest's declared versions with `${property}` resolved, a `Dockerfile`'s `FROM` — and dated
against the shipped table on the day given; a cycle the table does not know is `unknown` and said so; the row climbs
only as the facts allow; an expired product leads the recommendation's `before` list with its option, and is the
recommendation itself where `why` names nothing; the page and the checker say the same. Experimental, with the rest
of adoption (experimental).
"""
from __future__ import annotations

import datetime
import json
import tempfile
import unittest
from pathlib import Path

from slipwai.convergence import detected
from slipwai.layout import Layout
from slipwai.origin import Adoption, adoption_of
from slipwai.platform import (
    STATUSES,
    cycle_of,
    image_products,
    inventory,
    maven_products,
    numbers,
    status_of,
    support_table,
    with_platform,
)
from slipwai.programme import UPGRADE_PATHS, phrase
from slipwai.project.structure_page import structure_page
from slipwai.services import App
from slipwai.strategy import recommend, with_recommendation
from slipwai.structure import structure

TODAY = datetime.date(2026, 9, 8)
POM = """<project>
  <parent><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-parent</artifactId>
    <version>2.7.18</version></parent>
  <packaging>war</packaging>
  <properties><spring.version>3.2.8.RELEASE</spring.version><maven.compiler.source>1.7</maven.compiler.source></properties>
  <dependencies>
    <dependency><groupId>org.springframework</groupId><artifactId>spring-webmvc</artifactId>
      <version>${spring.version}</version></dependency>
    <dependency><groupId>junit</groupId><artifactId>junit</artifactId><version>3.8.1</version><scope>test</scope></dependency>
    <dependency><groupId>javax.servlet</groupId><artifactId>servlet-api</artifactId><version>2.4</version></dependency>
    <dependency><groupId>mysql</groupId><artifactId>mysql-connector-java</artifactId><version>5.1.6</version></dependency>
  </dependencies>
</project>
"""


def wrapped(name: str, path: str, ecosystem: str, version: str = "", audit: str | None = None, **fields) -> App:
    return App(name, path, "service", "java", None, 0, generated=False,
               commands={"test": "./mvnw -B -q test", "audit": audit},
               toolchain={"kind": {"maven": "java", "node": "node"}.get(ecosystem, ecosystem), "version": version,
                          "ecosystem": ecosystem}, **fields)


class PlatformTest(unittest.TestCase):
    def test_the_table_is_dated_and_every_cycle_carries_a_date_or_an_open_end(self) -> None:
        table = support_table()
        datetime.date.fromisoformat(table["snapshot"])
        for key, product in table["products"].items():
            self.assertTrue(product["title"], key)
            self.assertTrue(product["cycles"], key)
            for cycle, entry in product["cycles"].items():
                self.assertIn("eol", entry, f"{key} {cycle}")
                if entry["eol"] is not None:
                    datetime.date.fromisoformat(entry["eol"])
            self.assertIn(key, UPGRADE_PATHS, f"{key}: every product the table dates has a way up named")

    def test_a_version_is_matched_to_the_longest_cycle_it_starts_with_and_dated_on_the_day_given(self) -> None:
        self.assertEqual(numbers("^4.18.2"), "4.18.2")
        self.assertEqual(numbers("net8.0"), "8.0")
        self.assertEqual(numbers("3.2.8.RELEASE"), "3.2.8")
        self.assertEqual(numbers(">= 3.9"), "3.9")
        self.assertEqual(numbers(""), "")
        cycles: dict[str, dict] = {"3.2": {}, "4.3": {}, "5": {}}
        self.assertEqual(cycle_of("3.2.8.RELEASE", cycles), "3.2")
        self.assertEqual(cycle_of("5.10.2", cycles), "5")
        self.assertIsNone(cycle_of("6.1.0", cycles), "a cycle the table does not know is nothing, not the nearest")
        self.assertEqual(status_of("2016-12-31", TODAY), "end-of-life")
        self.assertEqual(status_of("2026-11-30", TODAY), "ending", "within 180 days")
        self.assertEqual(status_of("2029-12-31", TODAY), "supported")
        self.assertEqual(status_of(None, TODAY), "supported", "no end of life announced")
        self.assertEqual(set(STATUSES), {"supported", "ending", "end-of-life", "unknown"})

    def test_a_pom_pins_the_framework_the_test_framework_and_the_servlet_api_with_properties_resolved(self) -> None:
        self.assertEqual(maven_products(POM), [
            ("spring-boot", "2.7.18"), ("spring-framework", "3.2.8.RELEASE"), ("junit", "3.8.1"), ("servlet", "2.4"),
        ])
        self.assertEqual(image_products("FROM tomcat:8.5-jdk8\nFROM --platform=linux/amd64 node:20-alpine AS build\n"
                                        "FROM scratch\nFROM build\n"), [("tomcat", "8.5-jdk8"), ("node", "20-alpine")])

    def test_the_inventory_reads_the_tree_dates_it_and_the_row_climbs_only_as_the_facts_allow(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pom.xml").write_text(POM)
            (root / "Dockerfile").write_text("FROM tomcat:8.5-jdk8\nCOPY target/app.war /usr/local/tomcat/webapps/\n")
            app = wrapped("shop", ".", "maven", version="8", provenance={"toolchain": "confirmed"})
            record = inventory(root, [app], TODAY)
            self.assertEqual((record["snapshot"], record["dated"], record["provenance"]),
                             (support_table()["snapshot"], "2026-09-08", "detected"))
            by_product = {p["product"]: p for p in record["products"]}
            self.assertEqual(set(by_product), {"java", "spring-boot", "spring-framework", "junit", "servlet", "tomcat"})
            self.assertEqual((by_product["java"]["status"], by_product["java"]["evidence"]),
                             ("ending", "`toolchain.version` (confirmed)"))
            spring = by_product["spring-framework"]
            self.assertEqual((spring["version"], spring["cycle"], spring["status"], spring["eol"], spring["evidence"]),
                             ("3.2.8", "3.2", "end-of-life", "2016-12-31", "`pom.xml`"))
            self.assertEqual((by_product["junit"]["cycle"], by_product["junit"]["status"]), ("3", "end-of-life"))
            self.assertEqual(by_product["servlet"]["status"], "end-of-life")
            self.assertEqual((by_product["tomcat"]["version"], by_product["tomcat"]["status"],
                              by_product["tomcat"]["evidence"]), ("8.5", "end-of-life", "`Dockerfile` FROM"))
            self.assertEqual(phrase(spring), "Spring Framework 3.2.8 left support on 2016-12-31")

            adoption = with_platform(root, Adoption(), [app], TODAY)
            rows = {row["axis"]: row for row in detected([app], adoption)}
            self.assertEqual((rows["platform"]["rung"], rows["platform"]["provenance"]), ("inventoried", "detected"))
            self.assertIn("Spring Framework 3.2.8 left support on 2016-12-31", rows["platform"]["evidence"])
            self.assertIn("JUnit 3.8.1 left support on 2006-02-16", rows["platform"]["evidence"])

            # Nothing pinned, nothing read: the floor, unrecorded, so /ground asks.
            (root / "pom.xml").write_text("<project><artifactId>bare</artifactId></project>\n")
            (root / "Dockerfile").unlink()
            bare = with_platform(root, Adoption(), [wrapped("shop", ".", "maven")], TODAY)
            self.assertEqual(bare.platform["products"], [])
            row = {r["axis"]: r for r in detected([wrapped("shop", ".", "maven")], bare)}["platform"]
            self.assertEqual((row["rung"], row["provenance"]), ("unknown", "unrecorded"))

            # Everything in support: `supported`, and `audited` once every application records an audit.
            current = wrapped("shop", ".", "maven", version="21")
            adoption = with_platform(root, Adoption(), [current], TODAY)
            self.assertEqual({r["axis"]: r for r in detected([current], adoption)}["platform"]["rung"], "supported")
            audited = wrapped("shop", ".", "maven", version="21", audit="./mvnw -B -q dependency-check:check")
            self.assertEqual({r["axis"]: r for r in detected([audited], adoption)}["platform"]["rung"], "audited")

            # A cycle the table does not know is `unknown`, written as such, and holds the row at `inventoried`.
            (root / "pom.xml").write_text(POM.replace("3.2.8.RELEASE", "9.9.9"))
            odd = with_platform(root, Adoption(), [current], TODAY)
            spring = next(p for p in odd.platform["products"] if p["product"] == "spring-framework")
            self.assertEqual((spring["status"], spring["cycle"]), ("unknown", None))
            self.assertEqual(phrase(spring), "Spring Framework 9.9.9 is not in the support table")
            row = {r["axis"]: r for r in detected([current], odd)}["platform"]
            self.assertIn("not in the support table", row["evidence"])

    def test_an_expired_platform_leads_the_recommendation_and_is_it_where_why_names_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pom.xml").write_text(POM)
            app = wrapped("shop", ".", "maven", version="8")
            products = inventory(root, [app], TODAY)["products"]
            rows = detected([app], Adoption())
            capability = recommend("add new capabilities; introduce an AI-assisted delivery flow", rows, products)
            self.assertEqual((capability["recommended"], capability["trigger"]), ("strangler-fig", "capability"))
            self.assertTrue(capability["before"][0].startswith("the platform in support — Spring Boot 2.7.18 left"))
            self.assertIn("the platform in support — Spring Framework 3.2.8 left support on 2016-12-31; the way up is "
                          "Spring Framework 6", capability["before"][1])
            self.assertLess(capability["before"].index(next(b for b in capability["before"] if "JUnit" in b)),
                            capability["before"].index(next(b for b in capability["before"] if "pipeline" in b)),
                            "the platform leads the list; the delivery rungs follow")
            self.assertIn("the tree names a platform problem: JUnit 3.8.1 left support on 2006-02-16",
                          capability["because"])
            self.assertTrue(any("JUnit 5 (Jupiter)" in line and "no mocking framework" in line
                                for line in capability["before"]))
            nothing = recommend(None, rows, products)
            self.assertEqual((nothing["recommended"], nothing["trigger"]), ("in-place", "platform"))
            self.assertIn("the tree itself names a platform problem", nothing["because"][0])
            unread = recommend("because", rows, products)
            self.assertEqual(unread["recommended"], "in-place")
            self.assertEqual(recommend(None, rows, [])["recommended"], "leave-it", "no platform fact, no trigger")

            # Through the record: with_recommendation reads the platform the adoption carries; the manifest round-trips.
            dated_ = with_platform(root, Adoption(), [app], TODAY)
            adoption = with_recommendation(root, Layout("delivery"), dated_, [app])
            self.assertEqual(adoption.strategy["recommended"], "in-place")
            record = adoption.record()
            self.assertEqual(list(record)[:3], ["platform", "strategy", "convergence"])
            back = adoption_of({"origin": "adopted", **json.loads(json.dumps(record))})
            assert back is not None
            self.assertEqual(back.platform, adoption.platform)

    def test_the_architecture_view_says_what_each_application_runs_on_and_the_way_up(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pom.xml").write_text(POM)
            (root / "src/main/java").mkdir(parents=True)
            (root / "src/main/java/App.java").write_text("class App {}\n")
            app = wrapped("shop", ".", "maven", version="8", provenance={"toolchain": "confirmed"})
            adoption = with_platform(root, Adoption(), [app], TODAY)
            adoption = Adoption(**{**adoption.__dict__, "convergence": detected([app], adoption)})
            page = structure_page(structure(root, [app], "delivery"), adoption, Layout("delivery"))
            self.assertIn("### What it runs on", page)
            self.assertIn("| Spring Framework | 3.2.8 | `end-of-life` | 2016-12-31 | `pom.xml` |", page)
            self.assertIn("| Java | 8 | `ending` | 2026-11-30 | `toolchain.version` (confirmed) |", page)
            self.assertIn("**JUnit 3.8.1 left support on 2006-02-16.** The way up: JUnit 5 (Jupiter)", page)
            self.assertIn("The Platform row stands at `inventoried`", page)
            self.assertIn(f"support table of {support_table()['snapshot']}", page)


class JarTest(unittest.TestCase):
    def test_the_jars_an_ant_build_commits_name_their_products(self) -> None:
        from slipwai.platform import jar_products
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("lib/spring-core-3.2.8.RELEASE.jar", "lib/spring-webmvc-3.2.8.RELEASE.jar", "junit-4.12.jar",
                         "lib/servlet-api-2.5.jar", "lib/mysql-connector-java-5.1.23-bin.jar", "lib/rs2xml.jar",
                         "build/classes/junit-3.8.1.jar"):
                (root / name).parent.mkdir(parents=True, exist_ok=True)
                (root / name).write_bytes(b"PK")
            self.assertEqual(jar_products(root, root), [
                ("junit", "4.12", "junit-4.12.jar"), ("servlet", "2.5", "lib/servlet-api-2.5.jar"),
                ("spring-framework", "3.2.8.RELEASE", "lib/spring-core-3.2.8.RELEASE.jar"),
            ])


if __name__ == "__main__":
    unittest.main()
