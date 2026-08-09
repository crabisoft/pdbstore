"""Frameworks and drivers.

The outermost layer, holding everything that talks to something concrete: a
filesystem, a compression utility, a PE or PDB file format, a configuration
file. Nothing in this layer is imported by the interactors — they only ever see
the gateways declared in :mod:`pdbstore.usecases.gateways`.

For historical reasons the file format parsers, the cab compressor and the
console output still live under :mod:`pdbstore.io` and :mod:`pdbstore.util`.
They belong to this layer and the layering rules treat them as such; only their
physical location is pending, and moving them is a breaking change deferred to
the next major version.
"""
