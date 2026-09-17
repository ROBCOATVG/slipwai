"""Slipwai, the factory: one command that scaffolds a new product monorepo.

`cli` is the entry point, `scaffold` assembles a project, and `project/` holds one module per part of
the repository being generated. Nothing here reads the working directory: every path comes from
`assets`, so the same answers produce the same project from anywhere.
"""
