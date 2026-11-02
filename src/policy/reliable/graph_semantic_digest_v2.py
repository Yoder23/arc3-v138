"""Bounded-memory semantic Merkle digest matching the v3 state representation.

Mutable identity/alias order is retained. Purely immutable tuple subtrees are
memoized by identity but represented by value, as in graph_state_semantics_v3.
This avoids constructing two expanded Python trees during a handoff check.
"""
import hashlib
import types
import math


def semantic_digest(value):
    seen={};held=[];immutable={};scalar_cache={};tag_cache={}
    def digest(parts):
        h=hashlib.sha256()
        for p in parts:
            assert isinstance(p,bytes)
            h.update(len(p).to_bytes(8,'big'));h.update(p)
        return h.digest()
    def atom(v):
        if v is None:return b'none'
        if type(v) is bool:return b'true' if v else b'false'
        if type(v) is int:return str(v).encode('ascii')
        if type(v) is float:return repr(0.0 if v==0 else v).encode('ascii')
        if type(v) is str:return v.encode('utf-8','surrogatepass')
        if isinstance(v,bytes):return v
        raise TypeError(type(v))
    def tag(v):
        typ=type(v)
        if typ not in tag_cache:tag_cache[typ]=digest((typ.__module__.encode(),typ.__qualname__.encode()))
        return tag_cache[typ]
    def pure(v):
        """A cached subtree may not consume mutable alias indexes."""
        if v is None or type(v) in (bool,int,float,str,bytes):return True
        if type(v) not in (tuple,frozenset):return False
        key=id(v)
        if key in immutable:return immutable[key][0]
        held.append(v);result=all(pure(x) for x in v);immutable[key]=(result,None)
        return result
    def walk(v):
        t=tag(v)
        if v is None or type(v) in (int,float,str,bool):
            if type(v) is float and math.isnan(v):raise ValueError('Non-reflexive NaN has no canonical equality contract')
            key=(type(v),v)
            if key not in scalar_cache:scalar_cache[key]=digest((t,atom(v)))
            return scalar_cache[key]
        if isinstance(v,bytes):return digest((t,v))
        if isinstance(v,(types.FunctionType,types.BuiltinFunctionType,type)):
            return digest((t,v.__module__.encode(),v.__qualname__.encode()))
        if hasattr(v,'copy') and hasattr(v,'hexdigest') and hasattr(v,'update') and hasattr(v,'name'):
            suffix=v.copy();suffix.update(b'\x00semantic-continuation-check')
            return digest((t,v.name.encode(),v.hexdigest().encode(),suffix.hexdigest().encode()))
        if hasattr(v,'tolist'):
            return digest((t,str(getattr(v,'dtype','')).encode(),walk(tuple(getattr(v,'shape',()))),walk(v.tolist())))
        if isinstance(v,(tuple,frozenset)):
            cache=pure(v);key=id(v)
            if cache and immutable[key][1] is not None:return immutable[key][1]
            values=sorted(v,key=repr) if isinstance(v,frozenset) else v
            out=digest([t]+[walk(x) for x in values])
            if cache:immutable[key]=(True,out)
            return out
        key=id(v)
        if key in seen:return digest((b'alias',str(seen[key]).encode()))
        index=len(seen);seen[key]=index;held.append(v);prefix=[t,str(index).encode()]
        if isinstance(v,dict):
            factory=getattr(v,'default_factory',None)
            name=None if factory is None else (factory.__module__,factory.__qualname__)
            return digest(prefix+[walk(name)]+[digest((walk(k),walk(x))) for k,x in v.items()])
        if isinstance(v,list):return digest(prefix+[walk(x) for x in v])
        if isinstance(v,set):return digest(prefix+[walk(x) for x in sorted(v,key=repr)])
        if hasattr(v,'__dict__'):return digest(prefix+[walk(vars(v))])
        raise TypeError(type(v))
    return walk(value).hex()
