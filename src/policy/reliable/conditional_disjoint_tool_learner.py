"""Apply the tested discovery boundary after conditional planning."""
from disjoint_tool_word_learner import Learner as Disjoint
from conditional_tool_word_learner import Learner as Conditional


class Learner(Disjoint, Conditional):
    # The MRO runs conditional planning first, then checks its final selection.
    # Both frozen components retain their original implementation and memory.
    pass
