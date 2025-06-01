from datasets import load_dataset, Audio
from transformers import (
    Wav2Vec2ForCTC,
    Wav2Vec2Processor,
    TrainingArguments,
    Trainer,
)
from dataclasses import dataclass
from typing import Any, Dict, List, Union

import re

def clean_text(text):
    text = text.lower()
    text = re.sub(r"[^a-zA-Z' ]+", '', text)  # keep only letters, apostrophes, and spaces
    return text.strip()

dataset = load_dataset(
    "csv",
    data_files={"train": "data/train.csv", "validation": "data/val.csv"},
    delimiter=","
)

dataset = dataset.cast_column("path", Audio(sampling_rate=16000))

processor = Wav2Vec2Processor.from_pretrained("facebook/wav2vec2-base-960h")
model = Wav2Vec2ForCTC.from_pretrained(
    "facebook/wav2vec2-base-960h",
    ctc_loss_reduction="mean",
    pad_token_id=processor.tokenizer.pad_token_id,
)
model.freeze_feature_encoder()
def prepare_batch(batch):
    audio = batch["path"]
    batch["input_values"] = processor(audio["array"], sampling_rate=16000).input_values[0]
    batch["input_length"] = len(batch["input_values"])
    cleaned = clean_text(batch["transcript"])
    batch["labels"] = processor(text=cleaned).input_ids
    return batch

dataset = dataset.map(prepare_batch, remove_columns=dataset["train"].column_names)

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
        with self.processor.as_target_processor():
            labels_batch = self.processor.pad(
                label_features,
                padding=self.padding,
                return_tensors="pt"
            )

        labels = labels_batch["input_ids"].masked_fill(labels_batch["input_ids"] == self.processor.tokenizer.pad_token_id, -100)
        batch["labels"] = labels
        return batch

data_collator = DataCollatorCTCWithPadding(processor=processor, padding=True)

training_args = TrainingArguments(
    output_dir="./wav2vec2-nigerian-english",
    group_by_length=False,
    per_device_train_batch_size=8,
    per_device_eval_batch_size=8,
    # evaluation_strategy="steps", 
    num_train_epochs=10,
    fp16=True,
    save_steps=200,
    # eval_steps=200,   
    logging_steps=100,
    learning_rate=1e-4,
    warmup_steps=500,
    save_total_limit=2,
    push_to_hub=False,
)

trainer = Trainer(
    model=model,
    data_collator=data_collator,
    args=training_args,
    train_dataset=dataset["train"],
    # eval_dataset=dataset["validation"],
    # tokenizer=processor.tokenizer,  # REMOVE THIS
    processor=processor,
)

trainer.train()

# Manual evaluation after training
trainer.evaluate(eval_dataset=dataset["validation"])

trainer.save_model("./wav2vec2-nigerian-english")
processor.save_pretrained("./wav2vec2-nigerian-english")
