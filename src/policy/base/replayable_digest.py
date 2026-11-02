"""Serializable exact transcript hashing from retained public-history update bytes."""
import hashlib
class Digest:
    def __init__(self):self.chunks=[];self.hash=hashlib.sha256()
    def update(self,data):
        data=bytes(data);self.chunks.append(data);self.hash.update(data)
    def hexdigest(self):return self.hash.hexdigest()
    def __getstate__(self):return self.chunks
    def __setstate__(self,chunks):
        self.__init__()
        for chunk in chunks:self.update(chunk)
