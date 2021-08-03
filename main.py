if __name__ == "__main__":
    import optax
    import jax.random as random

    from data_loader import get_dataset, linear_data, train_test_split
    from models import MLP, Resnet
    from train import train
    from utils import mse_loss

    n_features = 10
    n_layers = 2
    lr = 5 * 1e-3
    num_epochs = 10
    batch_size = 32
    single_batch = False
    n_datapoints = 1000
    bias = 15.15

    X, Y = linear_data(seed=123415, n=n_datapoints, p=n_features, bias=bias,)
    full_dataset = get_dataset(
        X,
        Y,
        batch_size=batch_size,
        buffer_size=n_datapoints,
        single_batch=single_batch,
        numpy=False,
    )
    train_data, test_data = train_test_split(full_dataset, test_share=0.3)
    print(
        len(full_dataset),
        batch_size,
        batch_size * len(full_dataset),
        n_datapoints,
    )
    train(
        rng=random.PRNGKey(11234),
        model=Resnet(
            [n_features for _ in range(n_layers)] + [1], dropout=False
        ),
        optimizer=optax.adam(lr),
        train_dataset=train_data,
        eval_dataset=test_data,
        loss_fn=mse_loss,
        num_epochs=num_epochs,
        inputs_shape=(n_features,),
        bias=bias,
        layer_name=str(n_layers),
        print_every=1,
        output_dir="logs",
        hist_every=1,
    )
else:
    import sys

    print("main.py should not be imported and used only as a script.")
    sys.exit(1)
