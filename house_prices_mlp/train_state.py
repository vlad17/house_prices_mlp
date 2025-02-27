from typing import Any, Callable

from flax import struct
from flax.training.train_state import TrainState


class TrainStateWithLoss(TrainState):
    loss_fn: Callable = struct.field(pytree_node=False)
    batch_stats: Any
