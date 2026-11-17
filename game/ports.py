"""Ports of the domain: every ``Protocol`` the game needs from the outside world.

Adapters in ``api/`` implement them; the entry point injects the adapters. A port is
named after a game capability and its methods after game actions, never after a
vendor call. Each port declares the errors its adapters translate vendor failures
into.
"""
