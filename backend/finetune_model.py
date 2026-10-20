from datasets import load_dataset, Audio
from transformers import (
    Wav2Vec2ForCTC,
    Wav2Vec2Processor,
    TrainingArguments,
    Trainer,
    TrainerCallback,
)
from dataclasses import dataclass
from typing import Any, Dict, List, Union

import math
import re

import jiwer
import numpy as np
import torch

BASE_MODEL = "facebook/wav2vec2-base-960h"


def clean_text(text):
    # the base model's vocabulary is upper-case letters, apostrophe and "|"; lower-case letters would all become <unk>
    text = text.upper().replace("’", "'").replace("-", " ")
    text = re.sub(r"[^A-Z' ]+", '', text)
    return re.sub(r"\s+", " ", text).strip()


dataset = load_dataset(
    "csv",
    data_files={"train": "data/train.csv", "validation": "data/val.csv"},
    delimiter=","
)
# digits are read out in the audio but can't be spelled by the vocabulary; drop those utterances
dataset = dataset.filter(lambda b: not re.search(r"\d", b["transcript"]))

dataset = dataset.cast_column("path", Audio(sampling_rate=16000))

processor = Wav2Vec2Processor.from_pretrained(BASE_MODEL)
model = Wav2Vec2ForCTC.from_pretrained(
    BASE_MODEL,
    ctc_loss_reduction="mean",
    ctc_zero_infinity=True,
    pad_token_id=processor.tokenizer.pad_token_id,
)
# transformers leaves the SpecAugment mask vector uninitialised when loading this checkpoint (it is not
# saved in it); NaNs there turn every training loss into NaN, so initialise it as wav2vec2 does
torch.nn.init.uniform_(model.wav2vec2.masked_spec_embed)
assert not torch.isnan(model.wav2vec2.masked_spec_embed).any()
model.freeze_feature_encoder()


def prepare_batch(batch):
    audio = batch["path"]
    batch["input_values"] = processor(audio["array"], sampling_rate=16000).input_values[0]
    batch["input_length"] = len(batch["input_values"])
    batch["labels"] = processor(text=clean_text(batch["transcript"])).input_ids
    return batch


dataset = dataset.map(prepare_batch, remove_columns=dataset["train"].column_names)
unk = processor.tokenizer.unk_token_id
unk_share = np.mean([i == unk for ids in dataset["train"]["labels"] for i in ids])
assert unk_share < 0.01, f"{unk_share:.0%} of label tokens are <unk>; the labels do not match the vocabulary"


@dataclass
class DataCollatorCTCWithPadding:
    processor: Wav2Vec2Processor
    padding: Union[bool, str] = True

    def __call__(self, features: List[Dict[str, Any]]) -> Dict[str, Any]:
        input_features = [{"input_values": f["input_values"]} for f in features]
        label_features = [{"input_ids": f["labels"]} for f in features]

        batch = self.processor.pad(
            input_features,
            padding=self.padding,
            return_tensors="pt"
        )
        labels_batch = self.processor.tokenizer.pad(
            label_features,
            padding=self.padding,
            return_tensors="pt"
        )

        labels = labels_batch["input_ids"].masked_fill(labels_batch["input_ids"] == self.processor.tokenizer.pad_token_id, -100)
        batch["labels"] = labels
        return batch


def compute_metrics(pred):
    pred_ids = np.argmax(pred.predictions, axis=-1)
    label_ids = pred.label_ids.copy()
    label_ids[label_ids == -100] = processor.tokenizer.pad_token_id
    hyp = processor.batch_decode(pred_ids)
    ref = processor.batch_decode(label_ids, group_tokens=False)
    return {"wer": jiwer.wer(ref, hyp), "cer": jiwer.cer(ref, hyp)}


class StopOnBrokenTraining(TrainerCallback):
    # a NaN gradient norm or a logged loss of exactly 0 means no real update is happening
    def on_log(self, args, state, control, logs=None, **kwargs):
        logs = logs or {}
        if "loss" in logs and (logs["loss"] == 0 or math.isnan(logs.get("grad_norm", 0.0))):
            raise RuntimeError(f"training is broken at step {state.global_step}: {logs}")


data_collator = DataCollatorCTCWithPadding(processor=processor, padding=True)

training_args = TrainingArguments(
    output_dir="./wav2vec2-nigerian-english",
    group_by_length=True,
    length_column_name="input_length",
    per_device_train_batch_size=8,
    per_device_eval_batch_size=8,
    eval_strategy="steps",
    num_train_epochs=10,
    fp16=torch.cuda.is_available(),
    save_steps=200,
    eval_steps=200,
    logging_steps=50,
    learning_rate=1e-4,
    warmup_steps=500,
    save_total_limit=2,
    load_best_model_at_end=True,
    metric_for_best_model="wer",
    greater_is_better=False,
    push_to_hub=False,
)

trainer = Trainer(
    model=model,
    data_collator=data_collator,
    args=training_args,
    train_dataset=dataset["train"],
    eval_dataset=dataset["validation"],
    processing_class=processor,
    compute_metrics=compute_metrics,
    callbacks=[StopOnBrokenTraining()],
)

print("before fine-tuning:", trainer.evaluate())
trainer.train()
print("after fine-tuning:", trainer.evaluate())

trainer.save_model("./wav2vec2-nigerian-english")
processor.save_pretrained("./wav2vec2-nigerian-english")
