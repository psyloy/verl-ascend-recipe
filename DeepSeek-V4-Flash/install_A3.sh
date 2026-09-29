#!/bin/bash
set -ex
CANN_INSTALL_PATH=${CANN_INSTALL_PATH:-"/usr/local/Ascend"}
source ${CANN_INSTALL_PATH}/ascend-toolkit/set_env.sh
source ${CANN_INSTALL_PATH}/nnal/atb/set_env.sh

pip config set global.index-url https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
PIP_EXTRA="--extra-index-url https://triton-ascend.osinfra.cn/pypi/simple/ --trusted-host triton-ascend.osinfra.cn"

echo "1. install vllm v0.23.0 from source"
git clone -b v0.23.0 https://github.com/vllm-project/vllm.git
(cd vllm && VLLM_TARGET_DEVICE=empty pip install -e .)

echo "2. install vllm-ascend from source"
git clone -b releases/v0.23.0 https://github.com/vllm-project/vllm-ascend.git
(cd vllm-ascend && pip install -r requirements.txt ${PIP_EXTRA} && COMPILE_CUSTOM_KERNELS=1 pip install --no-build-isolation --no-deps -v -e . ${PIP_EXTRA})

echo "3. install mbridge"
git clone -b v0.15.1 https://github.com/ISEEKYAN/mbridge.git
(cd mbridge && pip install -e .)

echo "4. install MindSpeed & Megatron-LM & MindSpeed-LLM"
git clone -b 26.2.0_core_r0.12.1 https://gitcode.com/ascend/MindSpeed.git
(cd MindSpeed && pip install -r requirements.txt && pip install -v -e .)

git clone -b core_v0.12.1 https://github.com/NVIDIA/Megatron-LM.git
(cd Megatron-LM && pip install -v -e .)

git clone -b 26.2.0 https://gitcode.com/ascend/MindSpeed-LLM.git
(cd MindSpeed-LLM && cp pretrain_deepseek4.py mindspeed_llm && pip install -r requirements.txt)

echo "5. install verl (release/v0.9.0)"
git clone -b release/v0.9.0 https://github.com/verl-project/verl.git
(cd verl && pip install -r requirements-npu.txt ${PIP_EXTRA} && pip install -v -e .)

echo "6. update triton-ascend && transformers"
pip install triton-ascend==3.2.2 transformers==5.8.1 ${PIP_EXTRA}

echo "7. apply patch"
PATCH_DIR="$(dirname "${BASH_SOURCE[0]}")/patch"
apply_patches() {  # <repo-dir> <tree-name>
    local repo=$1 tree=$2 p
    echo "--- apply patches: ${tree} (A3) ---"
    for p in "${PATCH_DIR}/A3/${tree}"/*.patch; do
        echo "apply $(basename "$p")"
        (cd "$repo" && git apply --whitespace=nowarn "$p")
    done
}

apply_patches mbridge mbridge
apply_patches vllm-ascend vllm-ascend
apply_patches verl verl
apply_patches MindSpeed-LLM mindspeed-llm

cd verl
ln -sfn ../MindSpeed/mindspeed mindspeed
ln -sfn ../MindSpeed-LLM/mindspeed_llm mindspeed_llm
ln -sfn ../Megatron-LM/megatron megatron
ln -sfn ../mbridge/mbridge mbridge
ln -sfn ../vllm-ascend/vllm_ascend vllm_ascend
ln -sfn ../vllm/vllm vllm