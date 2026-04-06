"""
Gemma-4-E2B 显存测试脚本
测试模型加载和推理时的显存占用
"""

import torch
import time
from transformers import AutoModelForCausalLM, AutoTokenizer
import subprocess
import os

def get_gpu_memory():
    """获取GPU显存使用情况"""
    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,nounits,noheader"],
        capture_output=True, text=True
    )
    lines = result.stdout.strip().split("\n")
    memories = [int(x.strip()) for x in lines]
    return memories

def test_gemma_e2b():
    print("=" * 60)
    print("Gemma-4-E2B 显存测试")
    print("=" * 60)

    # 设置使用单GPU
    os.environ['CUDA_VISIBLE_DEVICES'] = '0'

    # 检查初始显存
    print("\n[1] 检查初始显存...")
    initial_mem = get_gpu_memory()
    print(f"    初始显存: {initial_mem[0]} MB")

    # 模型路径 - 根据实际情况修改
    model_path = "/root/models/google/gemma-4-E2B-it"
    print(f"\n[2] 加载模型: {model_path}")

    # 加载tokenizer
    print("    加载 tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)

    # 加载模型
    print("    加载模型...")
    start_time = time.time()
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        trust_remote_code=True,
        torch_dtype=torch.bfloat16,
        device_map="cuda:0"
    )
    load_time = time.time() - start_time
    print(f"    加载完成! 耗时: {load_time:.1f}s")

    # 检查加载后显存
    loaded_mem = get_gpu_memory()
    print(f"\n[3] 加载后显存:")
    print(f"    GPU 0: {loaded_mem[0]} MB")
    print(f"    显存增量: {loaded_mem[0] - initial_mem[0]} MB")

    # 准备测试输入
    print("\n[4] 执行推理测试...")
    prompt = "What is the capital of France?"
    inputs = tokenizer(prompt, return_tensors="pt").to("cuda:0")

    # 推理前显存
    pre_infer_mem = get_gpu_memory()
    print(f"    推理前显存: {pre_infer_mem[0]} MB")

    # 执行推理
    start_time = time.time()
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=50,
            do_sample=True,
            temperature=0.7,
            pad_token_id=tokenizer.eos_token_id
        )
    infer_time = time.time() - start_time

    # 推理后显存
    post_infer_mem = get_gpu_memory()
    print(f"    推理后显存: {post_infer_mem[0]} MB")

    # 解码输出
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    print(f"\n[5] 推理结果:")
    print(f"    输入: {prompt}")
    print(f"    输出: {response[:200]}")
    print(f"    推理耗时: {infer_time:.2f}s")

    # 汇总报告
    print("\n" + "=" * 60)
    print("测试报告汇总")
    print("=" * 60)
    print(f"初始状态: {initial_mem[0]} MB")
    print(f"模型加载后: {loaded_mem[0]} MB")
    print(f"推理时: {post_infer_mem[0]} MB")
    print(f"加载显存增量: {loaded_mem[0] - initial_mem[0]} MB")
    print(f"推理额外开销: {post_infer_mem[0] - loaded_mem[0]} MB")
    print("=" * 60)

if __name__ == "__main__":
    test_gemma_e2b()
