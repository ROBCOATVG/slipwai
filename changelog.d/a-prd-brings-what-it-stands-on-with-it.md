MINOR

**A product requirements document carries the files it stands on into the project.** `--prd` copied one
document's text to `docs/prd.md` and nothing else, so a PRD that embedded the wireframes somebody drew and
cited a brand sheet landed as a *Look and feel* section pointing at nothing — and the mock-up stage, whose
whole job is not inventing screens, had a direction it could read about but not see.

Two things travel now, both into `docs/design/`:

- **What the document itself names.** Its relative links and images are resolved against the directory it
  was read from, copied in, and the links rewritten to where they landed — a file carried in under a name
  the document still spells the old way is a file nobody finds.
- **`--design <dir>`**, a folder handed over whole, for the material the PRD happens not to link: a
  stylesheet, a competitor teardown, screenshots.

`commands/mockups.md` reads the directory before it draws a surface and is told to **follow a direction
somebody already settled rather than invent one**, naming the file each decision came from. The docs index
lists what arrived under *Handed over*, by name — a PNG has no first line to read, and material that is
there and unlisted is material the next reader does not know they have.

**Nothing outside the document's own directory travels.** A link to `../../.ssh/id_rsa`, a symlink out of
the tree, an absolute path: each is left exactly as it is rather than followed. A PRD is a file somebody
was handed, and a generate that copied whatever it pointed at would read anything its author could name.
A handed-over tree is bounded at 200 files and 50MB, so a home directory pointed at by mistake is a
refusal naming the size rather than a generate that appears to hang.
