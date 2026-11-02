"""Compare cyclic controller state, aliases and replayable digest continuations."""
import types

def normalized(value):
    seen={};held=[]
    def walk(v):
        tag=(type(v).__module__,type(v).__qualname__)
        if v is None or type(v) in (int,float,str,bool):return tag,v
        if isinstance(v,bytes):return tag,v.hex()
        if isinstance(v,(types.FunctionType,types.BuiltinFunctionType,type)):
            return tag,v.__module__,v.__qualname__
        if hasattr(v,'copy') and hasattr(v,'hexdigest') and hasattr(v,'update') and hasattr(v,'name'):
            suffix=v.copy();suffix.update(b'\x00semantic-continuation-check')
            return tag,v.name,v.hexdigest(),suffix.hexdigest()
        if hasattr(v,'tolist'):return tag,str(getattr(v,'dtype','')),tuple(getattr(v,'shape',())),walk(v.tolist())
        if isinstance(v,tuple):return tag,[walk(x) for x in v]
        if isinstance(v,frozenset):return tag,[walk(x) for x in sorted(v,key=repr)]
        key=id(v)
        if key in seen:return ('alias',seen[key])
        index=len(seen);seen[key]=index;held.append(v)
        if isinstance(v,dict):
            factory=getattr(v,'default_factory',None)
            name=None if factory is None else (factory.__module__,factory.__qualname__)
            return tag,index,name,[(walk(k),walk(x)) for k,x in v.items()]
        if isinstance(v,(tuple,list)):return tag,index,[walk(x) for x in v]
        if isinstance(v,(set,frozenset)):return tag,index,[walk(x) for x in sorted(v,key=repr)]
        if hasattr(v,'__dict__'):return tag,index,walk(vars(v))
        raise TypeError(type(v))
    return walk(value)
