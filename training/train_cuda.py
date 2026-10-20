"""Run on NVIDIA CUDA GPU with sufficient VRAM; install bitsandbytes first."""
import argparse, torch
from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig, TrainingArguments
from peft import LoraConfig
from trl import SFTTrainer, SFTConfig

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--model',default='Qwen/Qwen3-0.6B');ap.add_argument('--epochs',type=float,default=1);ap.add_argument('--output',default='outputs/adapter');args=ap.parse_args()
    if not torch.cuda.is_available():raise RuntimeError('NVIDIA CUDA GPU required. For Mac see README MLX instructions.')
    tok=AutoTokenizer.from_pretrained(args.model)
    quant=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type='nf4',bnb_4bit_compute_dtype=torch.float16,bnb_4bit_use_double_quant=True)
    model=AutoModelForCausalLM.from_pretrained(args.model,quantization_config=quant,device_map='auto')
    ds=load_dataset('json',data_files={'train':'data/processed/train.jsonl','validation':'data/processed/val.jsonl'})
    def fmt(ex):return {'text':tok.apply_chat_template([{'role':'user','content':ex['prompt']},{'role':'assistant','content':ex['answer']}],tokenize=False,add_generation_prompt=False,enable_thinking=False)}
    ds=ds.map(fmt)
    cfg=SFTConfig(output_dir=args.output,num_train_epochs=args.epochs,per_device_train_batch_size=1,gradient_accumulation_steps=8,learning_rate=2e-4,max_length=768,logging_steps=10,save_strategy='epoch',eval_strategy='epoch',report_to='none',gradient_checkpointing=True,packing=False,dataset_text_field='text',bf16=torch.cuda.is_bf16_supported(),fp16=not torch.cuda.is_bf16_supported())
    trainer=SFTTrainer(model=model,args=cfg,train_dataset=ds['train'],eval_dataset=ds['validation'],peft_config=LoraConfig(r=8,lora_alpha=16,lora_dropout=0.05,target_modules=['q_proj','v_proj'],task_type='CAUSAL_LM'),processing_class=tok)
    trainer.train();trainer.save_model(args.output);tok.save_pretrained(args.output)
if __name__=='__main__':main()
