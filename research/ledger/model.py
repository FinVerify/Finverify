"""Pinned local model/adapter loader used only by the execution CLIs."""


def load_generator(base_model: str, adapter: str, tokenizer_path: str):
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, pipeline

    tokenizer = AutoTokenizer.from_pretrained(tokenizer_path, local_files_only=True)
    quantization = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.float16)
    model = AutoModelForCausalLM.from_pretrained(base_model, quantization_config=quantization,
                                                 torch_dtype=torch.float16, device_map="auto",
                                                 local_files_only=True)
    model = PeftModel.from_pretrained(model, adapter, local_files_only=True)
    return tokenizer, pipeline("text-generation", model=model, tokenizer=tokenizer, device_map="auto")
