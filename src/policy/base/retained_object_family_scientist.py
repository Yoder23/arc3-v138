"""Keep the tested interaction policy and serialize its exact action transcript."""
from object_family_scientist import Scientist as Base
from replayable_digest import Digest


class Scientist(Base):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.trace_hash = Digest()
