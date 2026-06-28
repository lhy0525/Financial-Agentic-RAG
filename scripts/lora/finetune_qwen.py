from dataclasses import dataclass, field
import json
import math
import logging
import os
from pathlib import Path
from typing import Dict, Optional, List
import torch
from torch.utils.data import Dataset
import transformers
from transformers import (
    AutoConfig,
    AutoTokenizer,
    AutoModelForCausalLM,
    BitsAndBytesConfig,
    Trainer,
)
from transformers.integrations.deepspeed import is_deepspeed_zero3_enabled
from transformers.trainer_pt_utils import LabelSmoother
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training,PeftModel,AdaLoraConfig,AdaLoraModel
from accelerate.utils import DistributedType
import numpy as np
import random

DEFAULT_SQL_LORA_TRAIN_DATA = str(
    Path(__file__).resolve().parents[2] / "data" / "lora" / "train" / "sql-lora-train.json"
)


def seed_it(seed):
    random.seed(seed) #可以注释掉
    os.environ["PYTHONSEED"] = str(seed)
    np.random.seed(seed)
    torch.cuda.manual_seed(seed)
    torch.cuda.manual_seed_all(seed) #这个懂吧
    torch.backends.cudnn.deterministic = True #确定性固定
    torch.backends.cudnn.benchmark = True #False会确定性地选择算法，会降低性能
    torch.backends.cudnn.enabled = True  #增加运行效率，默认就是True
    torch.manual_seed(seed)

def torch_gc():
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.ipc_collect()
        
IGNORE_TOKEN_ID = LabelSmoother.ignore_index

    
@dataclass
class ModelArguments:
    model_name_or_path: Optional[str] = field(default="Qwen/Qwen2.5-Coder-7B-Instruct")


@dataclass
class DataArguments:
    data_path: str = field(
        default=DEFAULT_SQL_LORA_TRAIN_DATA, metadata={"help": "Path to the training data."}
    )
    eval_data_path: str = field(
        default=None, metadata={"help": "Path to the evaluation data."}
    )
    lazy_preprocess: bool = False


@dataclass
class TrainingArguments(transformers.TrainingArguments):
    cache_dir: Optional[str] = field(default=None)
    optim: str = field(default="adamw_torch")
    model_max_length: int = field(
        default=8192,
        metadata={
            "help": "Maximum sequence length. Sequences will be right padded (and possibly truncated)."
        },
    )
    use_lora: bool = False
    use_adalora: bool = False
    system_message:str ='You are a helpful assistant' #系统提示词
    


@dataclass
class LoraArguments:
    # LORA 方法配置
    lora_r: int = 32
    lora_alpha: int = 64
    lora_dropout: float = 0.05
    lora_target_modules: List[str] = field(
        default_factory=lambda: [
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ]
    )
    lora_weight_path: str = ""
    lora_bias: str = "none"
    q_lora: bool = False
    # adalora方法配置
    r: int=20
    target_modules=[
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
        "gate_proj",
        "up_proj",
        "down_proj",
    ]
    
    


local_rank = None

def rank0_print(*args):
    if local_rank == 0:
        print(*args)


def convert_conversation_to_messages(source, system_message: str) -> List[Dict[str, str]]:
    messages: List[Dict[str, str]] = []
    if system_message:
        messages.append({"role": "system", "content": system_message})

    turns = list(source)
    if turns and turns[0].get("from") not in {"user", "system"}:
        turns = turns[1:]

    role_map = {"user": "user", "assistant": "assistant", "system": "system"}
    for sentence in turns:
        role = role_map.get(sentence.get("from"))
        if role is None:
            raise ValueError(f"Unsupported conversation role: {sentence.get('from')}")
        content = str(sentence.get("value", ""))
        if role == "system" and system_message:
            continue
        messages.append({"role": role, "content": content})
    return messages


def _chat_template_ids(
    tokenizer: transformers.PreTrainedTokenizer,
    messages: List[Dict[str, str]],
    *,
    add_generation_prompt: bool,
) -> List[int]:
    ids = tokenizer.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=add_generation_prompt,
    )
    if hasattr(ids, "tolist"):
        ids = ids.tolist()
    return list(ids)


def _ensure_pad_token(tokenizer: transformers.PreTrainedTokenizer) -> None:
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token_id = tokenizer.eos_token_id


def _pad_or_truncate(values: List[int], max_len: int, pad_value: int) -> List[int]:
    if len(values) >= max_len:
        return values[:max_len]
    return values + [pad_value] * (max_len - len(values))


def generate_response(model, tokenizer, prompt: str, system_message: str, max_new_tokens: int = 512) -> str:
    messages = convert_conversation_to_messages(
        [{"from": "user", "value": prompt}],
        system_message,
    )
    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    inputs = tokenizer([text], return_tensors="pt").to(model.device)
    outputs = model.generate(**inputs, max_new_tokens=max_new_tokens)
    generated_ids = outputs[0][inputs.input_ids.shape[-1]:]
    return tokenizer.decode(generated_ids, skip_special_tokens=True).strip()




def preprocess(
    sources,
    tokenizer: transformers.PreTrainedTokenizer,
    max_len: int,
    system_message:str
) -> Dict:
    _ensure_pad_token(tokenizer)
    input_ids, targets = [], []
    for source in sources:
        messages = convert_conversation_to_messages(source, system_message)
        input_id = _chat_template_ids(tokenizer, messages, add_generation_prompt=False)
        target = [IGNORE_TOKEN_ID] * len(input_id)

        if messages and messages[-1]["role"] == "assistant":
            prompt_ids = _chat_template_ids(
                tokenizer,
                messages[:-1],
                add_generation_prompt=True,
            )
            assistant_start = min(len(prompt_ids), len(input_id))
            target[assistant_start:] = input_id[assistant_start:]

        input_ids.append(_pad_or_truncate(input_id, max_len, tokenizer.pad_token_id))
        targets.append(_pad_or_truncate(target, max_len, IGNORE_TOKEN_ID))

    input_ids = torch.tensor(input_ids, dtype=torch.long)
    targets = torch.tensor(targets, dtype=torch.long)

    return dict(
        input_ids=input_ids,
        labels=targets,
        attention_mask=input_ids.ne(tokenizer.pad_token_id),
    )


class SupervisedDataset(Dataset):
    """Dataset for supervised fine-tuning."""

    def __init__(self, raw_data, tokenizer: transformers.PreTrainedTokenizer, max_len: int,system_message:str):
        super(SupervisedDataset, self).__init__()

        rank0_print("Formatting inputs...")
        sources = [example["conversations"] for example in raw_data]
        data_dict = preprocess(sources, tokenizer, max_len,system_message = system_message)

        self.input_ids = data_dict["input_ids"]
        self.labels = data_dict["labels"]
        self.attention_mask = data_dict["attention_mask"]

    def __len__(self):
        return len(self.input_ids)

    def __getitem__(self, i) -> Dict[str, torch.Tensor]:
        return dict(
            input_ids=self.input_ids[i],
            labels=self.labels[i],
            attention_mask=self.attention_mask[i],
        )


class LazySupervisedDataset(Dataset):
    """Dataset for supervised fine-tuning."""

    def __init__(self, raw_data, tokenizer: transformers.PreTrainedTokenizer, max_len: int,system_message):
        super(LazySupervisedDataset, self).__init__()
        self.tokenizer = tokenizer
        self.max_len = max_len

        rank0_print("Formatting inputs...Skip in lazy mode")
        self.tokenizer = tokenizer
        self.raw_data = raw_data
        self.cached_data_dict = {}
        self.system_message = system_message

    def __len__(self):
        return len(self.raw_data)

    def __getitem__(self, i) -> Dict[str, torch.Tensor]:
        if i in self.cached_data_dict:
            return self.cached_data_dict[i]

        ret = preprocess([self.raw_data[i]["conversations"]], self.tokenizer, self.max_len,system_message = self.system_message)
        ret = dict(
            input_ids=ret["input_ids"][0],
            labels=ret["labels"][0],
            attention_mask=ret["attention_mask"][0],
        )
        self.cached_data_dict[i] = ret

        return ret


def make_supervised_data_module(
    tokenizer: transformers.PreTrainedTokenizer, data_args, max_len,system_message
) -> Dict:
    """Make dataset and collator for supervised fine-tuning."""
    dataset_cls = (
        LazySupervisedDataset if data_args.lazy_preprocess else SupervisedDataset
    )
    rank0_print("Loading data...")

    train_json = json.load(open(data_args.data_path, "r"))
    train_dataset = dataset_cls(train_json, tokenizer=tokenizer, max_len=max_len,system_message= system_message)

    if data_args.eval_data_path:
        eval_json = json.load(open(data_args.eval_data_path, "r"))
        eval_dataset = dataset_cls(eval_json, tokenizer=tokenizer, max_len=max_len,system_message= system_message)
    else:
        eval_dataset = None

    return dict(train_dataset=train_dataset, eval_dataset=eval_dataset)


def train():
    global local_rank

    parser = transformers.HfArgumentParser(
        (ModelArguments, DataArguments, TrainingArguments, LoraArguments)
    )
    (
        model_args,
        data_args,
        training_args,
        lora_args,
    ) = parser.parse_args_into_dataclasses()

    # This serves for single-gpu qlora.
    if getattr(training_args, 'deepspeed', None) and int(os.environ.get("WORLD_SIZE", 1))==1:
        training_args.distributed_state.distributed_type = DistributedType.DEEPSPEED

    local_rank = training_args.local_rank

    device_map = None
    world_size = int(os.environ.get("WORLD_SIZE", 2))
    ddp = world_size != 1
    if lora_args.q_lora:
        device_map = {"": int(os.environ.get("LOCAL_RANK") or 0)} if ddp else "auto"
        if len(training_args.fsdp) > 0 or is_deepspeed_zero3_enabled():
            logging.warning(
                "FSDP or ZeRO3 are incompatible with QLoRA."
            )

    model_name_lower = model_args.model_name_or_path.lower()
    is_chat_model = any(marker in model_name_lower for marker in ["chat", "instruct"])
    if (
            training_args.use_lora
            and not lora_args.q_lora
            and is_deepspeed_zero3_enabled()
            and not is_chat_model
    ):
        raise RuntimeError("ZeRO3 is incompatible with LoRA when finetuning on base model.")

    model_load_kwargs = {
        'low_cpu_mem_usage': not is_deepspeed_zero3_enabled(),
    }

    config = AutoConfig.from_pretrained(
        model_args.model_name_or_path,
        cache_dir=training_args.cache_dir,
        trust_remote_code=True,
    )
    config.use_cache = False

    quantization_config = None
    if training_args.use_lora and lora_args.q_lora:
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
        )

    # Load model and tokenizer
    model = AutoModelForCausalLM.from_pretrained(
        model_args.model_name_or_path,
        config=config,
        cache_dir=training_args.cache_dir,
        device_map=device_map,
        trust_remote_code=True,
        quantization_config=quantization_config,
        **model_load_kwargs,
    )
    tokenizer = AutoTokenizer.from_pretrained(
        model_args.model_name_or_path,
        cache_dir=training_args.cache_dir,
        model_max_length=training_args.model_max_length,
        padding_side="right",
        use_fast=False,
        trust_remote_code=True,
    )
    _ensure_pad_token(tokenizer)

    if training_args.use_lora:
        print('========================当前正在使用LORA微调===================')
        if lora_args.q_lora or is_chat_model:
            modules_to_save = None
        else:
            modules_to_save = ["wte", "lm_head"]
        lora_config = LoraConfig(
            r=lora_args.lora_r,
            lora_alpha=lora_args.lora_alpha,
            target_modules=lora_args.lora_target_modules,
            lora_dropout=lora_args.lora_dropout,
            bias=lora_args.lora_bias,
            task_type="CAUSAL_LM",
            modules_to_save=modules_to_save  # This argument serves for adding new tokens.
        )
        if lora_args.q_lora:
            model = prepare_model_for_kbit_training(
                model, use_gradient_checkpointing=training_args.gradient_checkpointing
            )

        model = get_peft_model(model, lora_config)

        # Print peft trainable params
        model.print_trainable_parameters()

        if training_args.gradient_checkpointing:
            model.enable_input_require_grads()
    elif training_args.use_adalora:
        print('========================当前正在使用adaLORA微调===================')
        if lora_args.q_lora or is_chat_model:
            modules_to_save = None
        else:
            modules_to_save = ["wte", "lm_head"]
        ada_lora_config = AdaLoraConfig(
            r=lora_args.r,
            target_modules=lora_args.target_modules,
            lora_dropout=lora_args.lora_dropout,
            task_type="CAUSAL_LM",
            modules_to_save=modules_to_save  # This argument serves for adding new tokens.
        )
        model = get_peft_model(model,ada_lora_config)
         # Print peft trainable params
        model.print_trainable_parameters()
        model.is_parallelizable = True
        model.model_parallel = True

        if training_args.gradient_checkpointing:
            model.enable_input_require_grads()
        
    print(training_args)
    # Load data
    data_module = make_supervised_data_module(
        tokenizer=tokenizer, data_args=data_args, max_len=training_args.model_max_length,system_message = training_args.system_message
    )

    # Start trainner
    trainer = Trainer(
        model=model, tokenizer=tokenizer, args=training_args, **data_module
    )
    trainer.train()


def merge_model():
    parser = transformers.HfArgumentParser(
        (ModelArguments, DataArguments, TrainingArguments, LoraArguments)
    )
    (
        model_args,
        data_args,
        training_args,
        lora_args,
    ) = parser.parse_args_into_dataclasses()
    model = AutoModelForCausalLM.from_pretrained(model_args.model_name_or_path,device_map="auto", trust_remote_code=True)
    model = PeftModel.from_pretrained(model,training_args.output_dir)
    print("Loaded PEFT model. Merging...")
    model.merge_and_unload()
    print("Merge complete.")
    return model,model_args.model_name_or_path
def test_lora_model():
    model,old_model_path = merge_model()
    torch_gc()
    tokenizer = AutoTokenizer.from_pretrained(
    old_model_path,
    trust_remote_code=True,
)
    prompt = "大连派思燃气系统股份有限公司在何时获得美国GE公司的合格供应商认证？"
    response = generate_response(model, tokenizer, prompt, "你是一个SQL生成器。请只输出可执行SQL，不要输出解释。")
    print(response)
    torch_gc()
    
if __name__ == "__main__":
    seed_it(2024)
    train()
    # test_lora_model()
