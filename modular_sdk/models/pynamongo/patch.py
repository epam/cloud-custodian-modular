from pynamodb.attributes import AttributeContainerMeta

from .attributes import MONGO_ATTRIBUTE_PATCH_MAPPING


def _patched__new__(cls, name, bases, namespace, discriminator=None):
    meta = namespace.get('Meta')
    if meta and getattr(meta, 'mongo_attributes', False) is True:
        for k, v in namespace.items():
            if patched := MONGO_ATTRIBUTE_PATCH_MAPPING.get(v.__class__):
                namespace[k] = patched(
                    hash_key=v.is_hash_key,
                    range_key=v.is_range_key,
                    null=v.null,
                    default=v.default,
                    default_for_new=v.default_for_new,
                    attr_name=v.attr_name,
                )
    return super(AttributeContainerMeta, cls).__new__(
        cls, name, bases, namespace
    )


def patch_attributes():
    """
    Call before models declaration
    """
    AttributeContainerMeta.__new__ = _patched__new__
