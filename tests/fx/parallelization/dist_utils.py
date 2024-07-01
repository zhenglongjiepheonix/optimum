import os
import torch
import torch.distributed as dist
import torch.multiprocessing as mp
from typing import Callable, List, Optional
from transformers import set_seed

SEED = 42
NUM_AVAILABLE_DEVICES = torch.cuda.device_count()


def dist_init(
    rank: int,
    world_size: int,
    backend: str = 'nccl',
    master_addr: str = '127.0.0.1',
    master_port: str = '29500',
):
    os.environ["RANK"] = str(rank)
    os.environ["WORLD_SIZE"] = str(world_size)
    os.environ["MASTER_ADDR"] = master_addr
    os.environ["MASTER_PORT"] = master_port

    dist.init_process_group(
        backend=backend,
        init_method="env://",
        world_size=world_size,
        rank=rank,
    )

    torch.cuda.set_device(rank)

def runner(rank: int, fn:Callable, deterministic: bool, *args, **kwargs):
    if deterministic:
        set_seed(SEED)
    fn(rank, *args, **kwargs)

def spawn(world_size: int, fn: Callable, *args, deterministic: bool = False):
    mp.spawn(fn=runner, args=(fn, deterministic, world_size, *args), nprocs=world_size, join=True)

def tearDown(group: Optional[dist.ProcessGroup] = None):
    dist.destroy_process_group(group)

def gather_at_main_process(tensor: torch.Tensor, group: dist.ProcessGroup, rank: int, world_size: int) -> List[torch.Tensor]:
    if world_size == 1:
        return [tensor]

    tensor = tensor.contiguous()
    if rank == 0:
        tensors = [torch.empty_like(tensor) for _ in range(world_size)]
        tensors[rank] = tensor
    else:
        tensors = None
    dist.gather(tensor=tensor, gather_list=tensors, dst=0, group=group)
    return tensors
