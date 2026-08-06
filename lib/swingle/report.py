"""Shared finding collector.

A single module-global list, cleared in place by reset() so importers that bind
`findings` keep pointing at the same object. Every command entrypoint calls reset()
at its start; validators call find().
"""
findings = []


def find(message):
    findings.append(message)


def reset():
    findings.clear()
