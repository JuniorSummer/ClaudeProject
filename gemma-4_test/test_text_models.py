"""
Qwen2.5-3B 和 Yi-6B 显存对比测试脚本
测试纯文本模型的显存占用
"""

import torch
import time
from transformers import AutoModelForCausalLM, AutoTokenizer
import subprocess

def get_gpu_memory():
    """获取GPU显存使用情况"""
    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,nounits,noheader"],
        capture_output=True, text=True
    )
    lines = result.stdout.strip().split("\n")
    memories = [int(x.strip()) for x in lines]
    return memories

def test_model(model_name, model_path):
    """测试单个模型的显存占用"""
    print("\n" + "=" * 60)
    print(f"{model_name} 显存测试")
    print("=" * 60)

    # 清理显存
    torch.cuda.empty_cache()
    import gc
    gc.collect()

    # 检查初始显存
    print("\n[1] 检查初始显存...")
    initial_mem = get_gpu_memory()
    print(f"    GPU 0: {initial_mem[0]} MB, GPU 1: {initial_mem[1]} MB, 总计: {sum(initial_mem)} MB")

    # 加载tokenizer
    print(f"\n[2] 加载模型: {model_path}")
    print("    加载 tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)

    # 加载模型
    print("    加载模型...")
    start_time = time.time()
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        trust_remote_code=True,
        torch_dtype=torch.float16,
        device_map="auto"
    )
    load_time = time.time() - start_time
    print(f"    加载完成! 耗时: {load_time:.1f}s")

    # 检查加载后显存
    loaded_mem = get_gpu_memory()
    print(f"\n[3] 加载后显存:")
    print(f"    GPU 0: {loaded_mem[0]} MB, GPU 1: {loaded_mem[1]} MB, 总计: {sum(loaded_mem)} MB")

    # 准备测试输入
    print("\n[4] 执行推理测试...")
    prompt = "What is the capital of France? Please answer briefly."
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

    # 执行推理
    start_time = time.time()
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=30,
            do_sample=True,
            temperature=0.7,
            pad_token_id=tokenizer.eos_token_id
        )
    infer_time = time.time() - start_time

    # 推理后显存
    post_infer_mem = get_gpu_memory()
    print(f"    推理后显存: GPU 0: {post_infer_mem[0]} MB, GPU 1: {post_infer_mem[1]} MB")

    # 解码输出
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    print(f"\n[5] 推理结果: {response[:100]}...")
    print(f"    推理耗时: {infer_time:.2f}s")

    # 返回结果
    result = {
        "model": model_name,
        "initial_mem": sum(initial_mem),
        "loaded_mem": sum(loaded_mem),
        "inference_mem": sum(post_infer_mem),
        "load_time": load_time,
        "inference_time": infer_time,
        "gpu0_loaded": loaded_mem[0],
        "gpu1_loaded": loaded_mem[1],
        "gpu0_infer": post_infer_mem[0],
        "gpu1_infer": post_infer_mem[1]
    }

    # 清理模型
    del model
    del tokenizer
    torch.cuda.empty_cache()
    gc.collect()

    return result

def main():
    print("=" * 60)
    print("纯文本模型显存对比测试")
    print("Qwen2.5-3B vs Yi-6B")
    print("=" * 60)

    # 模型路径 - 根据实际情况修改
    models = [
        ("Qwen2.5-3B", "/root/autodl-tmp/models/Qwen/Qwen2.5-3B"),
        ("Yi-6B", "/root/autodl-tmp/models/01ai/Yi-6B")
    ]

    results = []
    for name, path in models:
        try:
            result = test_model(name, path)
            results.append(result)
        except Exception as e:
            print(f"测试 {name} 失败: {e}")

    # 打印对比报告
    if results:
        print("\n" + "=" * 60)
        print("对比报告汇总")
        print("=" * 60)
        print(f"{'模型':<15} {'加载显存':<15} {'推理显存':<15} {'加载时间':<12} {'推理时间':<12}")
        print("-" * 70)
        for r in results:
            print(f"{r['model']:<15} {r['loaded_mem']:<15} {r['inference_mem']:<15} {r['load_time']:.1f}s{'':<6} {r['inference_time']:.2f}s")
        print("=" * 60)

if __name__ == "__main__":
    main()
