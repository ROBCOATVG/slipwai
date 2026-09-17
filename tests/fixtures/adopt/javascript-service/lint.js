// The repository's own linter, red on day one on purpose: `TODO` is not allowed, and src/prices.js has one.
const fs = require("node:fs");
let findings = 0;
for (const file of fs.readdirSync("src")) {
  fs.readFileSync(`src/${file}`, "utf8").split("\n").forEach((line, index) => {
    if (line.includes("TODO")) {
      console.log(`src/${file}:${index + 1}:1: no-todo: TODO is not allowed`);
      findings += 1;
    }
  });
}
process.exit(findings ? 1 : 0);
