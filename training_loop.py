"""
Simple training module in Flax.

TODO: switch to clu for logging
TODO: switch to ml collections for config parameters
"""

import os


from flax.training import checkpoints
import jax
import jax.numpy as jnp
import jax.random as random
import tensorflow as tf
import tensorflow_datasets as tfds


from board import SummaryWriter
from models import CustomMLP, init_params
from train_state import TrainStateWithLoss
from train_utils import update_running


@jax.jit
def train_step(rng, x_num, x_cat, y, state: TrainStateWithLoss):
    """Updates the training state on a batch (x_num, x_cat, y) of data.

    We can jit this function because our state subclasses a jax PyTreeNode.
    """

    def pure_loss(params):
        predicted = state.apply_fn(
            params, x_num, x_cat, rngs={"dropout": rng}
        )  # TODO generalize this dropout arg
        loss_items = state.loss_fn(y, predicted)
        return jnp.mean(loss_items), predicted

    (loss_step, predicted_step), grad_step = jax.value_and_grad(
        pure_loss, has_aux=True
    )(state.params)
    state = state.apply_gradients(grads=grad_step)
    residuals_step = y - predicted_step
    return state, loss_step, residuals_step


@jax.jit
def eval_step(rng, x_num, x_cat, y, state: TrainStateWithLoss):
    """Evaluates the current training state on a batch (x_num, x_cat, y) of data.

    We can jit this function because our state subclasses a jax PyTreeNode.
    """

    def pure_loss(params):
        predicted = state.apply_fn(
            params, x_num, x_cat, rngs={"dropout": rng}
        )  # TODO generalize this rngs arg
        loss_items = state.loss_fn(y, predicted)
        return jnp.mean(loss_items), predicted

    loss_step, predicted_step = pure_loss(state.params)
    residuals_step = y - predicted_step
    return loss_step, residuals_step


def train(
    rng,
    model,
    optimizer,
    train_dataset,
    eval_dataset,
    loss_fn,
    num_epochs,
    num_input_shape,
    cat_input_shape,
    smoothing_alpha: float = 0.9,
    hist_every=None,
    print_every=None,
    single_batch=False,
):
    if not os.path.isdir("logs"):
        os.makedirs("logs")
        print(f"Directory 'logs' did not exist and was created.")
    writer = SummaryWriter("logs")
    if hist_every is not None:
        assert isinstance(hist_every, int)
    if print_every is not None:
        assert isinstance(print_every, int)

    rng, init_params_rng = random.split(rng, num=2)
    params = init_params(
        init_params_rng,
        num_input_shape,
        cat_input_shape,
        dropout=model.dropout
    )

    train_state = TrainStateWithLoss(
        step=0,
        apply_fn=model.apply,
        loss_fn=loss_fn,
        params=params,
        tx=optimizer,
        opt_state=optimizer.init(params),
    )

    if single_batch:
        train_dataset = train_dataset.take(1)

    step = 0
    for _ in range(num_epochs):
        running_train_loss = None
        running_eval_loss = None
        for ((x_train, y_train), (x_eval, y_eval)) in tfds.as_numpy(
            tf.data.Dataset.zip((train_dataset, eval_dataset))
        ):
            rng, rng_train, rng_eval = random.split(rng, num=3)
            train_state, loss_step, res_step = train_step(
                rng=rng_train, x=x_train, y=y_train, state=train_state,
            )
            loss_eval_step, _ = eval_step(
                rng_eval, x=x_eval, y=y_eval, state=train_state,
            )
            running_train_loss = update_running(
                obs=loss_step, loss=running_train_loss, decay=smoothing_alpha,
            )
            running_eval_loss = update_running(
                obs=loss_eval_step,
                loss=running_eval_loss,
                decay=smoothing_alpha,
            )
            step += 1
            if (print_every is not None) and (step % print_every == 0):
                writer.scalar("train_loss", running_train_loss, step=step)
                writer.scalar("validation_loss", running_eval_loss, step=step)
                print(f"Step {step} | Loss: {loss_step:.3f}")
            if (hist_every is not None) and (step % hist_every == 0):
                writer.histogram("train_hist", res_step, bins=5, step=step)
            if (save_every is not None) and (step % save_every == 0):
                checkpoints.save_checkpoint(
                    "checkpoints", train_state, train_state.step, keep=5
                )  # TODO - proper checkpoints directory
    return params
