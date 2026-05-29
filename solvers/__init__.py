"""Pluggable solver backends for Frontier.

Each backend mirrors the engine's existing solve contract (same inputs, returns a
``Run`` of ``Solution``s in the identical shape) so it can be swapped in behind a
gate without any downstream changes. See ``cuopt_backend`` for the cuOpt QP spike.
"""
