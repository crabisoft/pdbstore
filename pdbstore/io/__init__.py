def is_compression_supported() -> bool:
    """Check if CAB compression is supported

    :return: True if supported, else False
    """

    # Make local import to avoid unwanted search operation
    from pdbstore.io.cab import compress  # pylint: disable=import-outside-toplevel

    return compress is not None
