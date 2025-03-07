import avalanche as avl
import torch
from avalanche.evaluation import metrics as metrics
from models import MLP
from experiments.utils import set_seed, create_default_args


def lfl_pmnist(override_args=None):
    """
    LFL on Permuted MNIST.

    Note that the model must be a subclass of Avalanche `BaseModel` and must implement
    the `get_features` method which, given an input `x`, returns the model hidden features
    before the final classifier.
    """
    args = create_default_args({'cuda': 0, 'lambda_e': [0.0001], 'epochs': 3,
                                'hidden_size': 256, 'hidden_layers': 1,
                                'learning_rate': 0.01, 'train_mb_size': 128, 'seed': 0}, override_args)
    set_seed(args.seed)
    device = torch.device(f"cuda:{args.cuda}"
                          if torch.cuda.is_available() and
                          args.cuda >= 0 else "cpu")

    if not isinstance(args.lambda_e, (list, tuple)):
        raise ValueError("lambda_e parameter should be a list of floating numbers. " 
                         "Provide list with one element to apply the same lambda_e " 
                         "to all experiences.")

    benchmark = avl.benchmarks.PermutedMNIST(4)
    model = MLP(hidden_size=args.hidden_size, hidden_layers=args.hidden_layers)
    optimizer = torch.optim.SGD(model.parameters(), lr=args.learning_rate)
    criterion = torch.nn.CrossEntropyLoss()

    interactive_logger = avl.logging.InteractiveLogger()
    eval_plugin = avl.training.plugins.EvaluationPlugin(
        avl.evaluation.metrics.accuracy_metrics(minibatch=True, epoch=True, experience=True, stream=True),
        avl.evaluation.metrics.loss_metrics(minibatch=True, epoch=True, experience=True, stream=True),
        avl.evaluation.metrics.forgetting_metrics(experience=True),
        loggers=[interactive_logger], benchmark=benchmark
    )

    lambda_e = args.lambda_e[0] if len(args.lambda_e) == 1 else args.lambda_e

    strategy = avl.training.LFL(
        model,
        optimizer,
        criterion,
        lambda_e=lambda_e,
        train_epochs=args.epochs,
        device=device,
        train_mb_size=args.train_mb_size,
        eval_mb_size=256,
        evaluator=eval_plugin
    )

    res = None
    for experience in benchmark.train_stream:
        strategy.train(experience)
        res = strategy.eval(benchmark.test_stream)

    return res


if __name__ == '__main__':
    res = lfl_pmnist()
    print(res)
