_LAYER_REF=None

def layer_ref():
    global _LAYER_REF
    if _LAYER_REF is None:
        from .core import Layer,Ref
        _LAYER_REF=(Layer,Ref)
    return _LAYER_REF
