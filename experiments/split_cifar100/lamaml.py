import avalanche as avl
import torch
from torch.nn import CrossEntropyLoss

from avalanche.evaluation import metrics as metrics
from avalanche.training.storage_policy import ReservoirSamplingBuffer
from avalanche.training.plugins import ReplayPlugin
from avalanche.training.supervised.lamaml import LaMAML

from models.models_lamaml import ConvCIFAR
from experiments.utils import set_seed, create_default_args


def lamaml_scifar100(override_args=None):
    # Args
    args = create_default_args(
        {'cuda': 0, 'n_inner_updates': 5, 'second_order': True,
         'grad_clip_norm': 1.0, 'learn_lr': True, 'lr_alpha': 0.25,
         'sync_update': False, 'mem_size': 200, 'lr': 0.1,
         'train_mb_size': 10, 'train_epochs': 10, 'seed': 0}, override_args
    )

    set_seed(args.seed)
    device = torch.device(f"cuda:{args.cuda}"
                          if torch.cuda.is_available() and
                          args.cuda >= 0 else "cpu")
    # Benchmark
    benchmark = avl.benchmarks.SplitCIFAR100(n_experiences=20,
                                             return_task_id=True)

    # Loggers and metrics
    interactive_logger = avl.logging.InteractiveLogger()

    evaluation_plugin = avl.training.plugins.EvaluationPlugin(
        metrics.accuracy_metrics(epoch=True, experience=True, stream=True),
        loggers=[interactive_logger], benchmark=benchmark)

    # Buffer
    rs_buffer = ReservoirSamplingBuffer(max_size=args.mem_size)
    replay_plugin = ReplayPlugin(
        mem_size=args.mem_size,
        batch_size=args.train_mb_size,
        batch_size_mem=args.train_mb_size,
        task_balanced_dataloader=False,
        storage_policy=rs_buffer
    )

    # Strategy
    model = ConvCIFAR()
    cl_strategy = LaMAML(
        model,
        torch.optim.SGD(model.parameters(), lr=args.lr),
        CrossEntropyLoss(),
        n_inner_updates=args.n_inner_updates,
        second_order=args.second_order,
        grad_clip_norm=args.grad_clip_norm,
        learn_lr=args.learn_lr,
        lr_alpha=args.lr_alpha,
        sync_update=args.sync_update,
        train_mb_size=args.train_mb_size,
        train_epochs=args.train_epochs,
        eval_mb_size=100,
        device=device,
        plugins=[replay_plugin],
        evaluator=evaluation_plugin,
    )

    res = None
    for experience in benchmark.train_stream:
        cl_strategy.train(experience)
        res = cl_strategy.eval(benchmark.test_stream)
    return res


if __name__ == '__main__':
    res = lamaml_scifar100()
    print(res)
