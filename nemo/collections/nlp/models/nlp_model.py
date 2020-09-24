
# Copyright (c) 2020, NVIDIA CORPORATION.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from abc import ABC, abstractmethod
from typing import Dict, List

import torch

from nemo.core.classes import ModelPT
from nemo.utils import logging, AppState

#from megatron import get_args, initialize_megatron
from megatron import mpu

from pytorch_lightning.core.lightning import LightningModule
from pytorch_lightning.overrides.data_parallel import LightningDistributedDataParallel

__all__ = ['NLPModel']

class NLPModel(ModelPT, ABC):

    # def __init__(self):
    #     super.__init__()
    #     self._app_state = AppState()

    def init_ddp_connection(self, global_rank: int, world_size: int, is_slurm_managing_tasks: bool = True) -> None:
        """ Override LightningModule DDP initialization """
        app_state = AppState()

        if app_state.model_parallel_size is not None:
            # args = get_args()
            # initialize_megatron()
            LightningModule.init_ddp_connection(self, global_rank, world_size, is_slurm_managing_tasks)
            if app_state.model_parallel_group is None:
                mpu.initialize_model_parallel(app_state.model_parallel_size)
                app_state.model_parallel_group = mpu.get_model_parallel_group()
                app_state.data_parallel_group = mpu.get_data_parallel_group()
                app_state.model_parallel_rank = torch.distributed.get_rank(
                    group=app_state.model_parallel_group
                )
                app_state.data_parallel_rank = torch.distributed.get_rank(
                    group=app_state.data_parallel_group
                )
                device_id = torch.cuda.current_device()
                logging.info(f'device_id: {device_id}')
                logging.info(f'mp_rank: {app_state.model_parallel_rank}')
                logging.info(f'dp_rank: {app_state.data_parallel_rank}')

        else:
            return LightningModule.init_ddp_connection(self, global_rank, world_size, is_slurm_managing_tasks)

    def configure_ddp(self, model, device_ids):
        """ Override LightningModule ddp if using model parallel. """

        logging.info(f'device_ids: {device_ids}')

        app_state = AppState()

        if app_state.model_parallel_size is not None:
            logging.info("Configuring DDP for model parallelism.")
            logging.info(f"data_parallel_group: {app_state.data_parallel_group}")
            # with model parallelism, multiple GPUs form a large "logical GPU"
            # this means that data parallel groups span multiple GPUs


            device_id = app_state.device_id
            model = LightningDistributedDataParallel(
                model,
                device_ids=[device_id],
                output_device=device_id,
                process_group=app_state.data_parallel_group
            )
            return model

        else:
            logging.info("Did not detect model parallel using LightningModule.configure_ddp")
            return LightningModule.configure_ddp(self, model, device_ids)
    

